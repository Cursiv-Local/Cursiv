"""Provider controls on the existing chat header; all callbacks own their GUI state."""
import threading
from functools import wraps
from PyQt6.QtWidgets import QPushButton, QMessageBox


def load_saved_keys():
    from settings_dialog import load_keys
    return {k:v for k,v in load_keys().items() if isinstance(v,str)}


def provider_turn(function):
    @wraps(function)
    def call(self,*args,**kwargs):
        from cursiv_engine.chat import provider_manager as manager
        from cursiv_engine.chat.activity import guard
        target=kwargs.get('turn_target') or self._run_target()
        if hasattr(self, '_worker_view'):
            self = self._worker_view(target)
        with (manager.turn_options(research_authorized=getattr(self,'_provider_turn_authorized',False),
                workspace=self._cfg.get('workspace'),local_only=bool(self._cfg.get('project_local_only')),
                cancel=target[1] if target else self._cancel_event,destination=getattr(self,'_provider_turn_destination',None)),
                guard(lambda:not target or (self._current_run_target(target) and (target[1] is None or not target[1].is_set())))):
            return function(self,*args,**kwargs)
    return call


class ProviderControlsMixin:
    def _managed_prefix(self,text):
        from chat_panel import cc
        from cursiv_engine.chat.provider_registry import get
        force,stripped=cc.hey_prefix(text)
        if force:
            provider,separator,model=force.partition('::')
            if not separator:
                model=self._cfg.get('selected_model','') if self._cfg.get('selected_provider')==provider else ''
                model=model or (get(provider).catalog[0] if get(provider).catalog else '')
            force='manager:'+provider+'::'+model
        return force,stripped

    def _authorize_provider_text(self,text):
        force,_=self._managed_prefix(text)
        if force:
            provider,model=force.removeprefix('manager:').split('::',1)
            return self._authorize_provider_turn(provider_override=provider,model_override=model)
        return self._authorize_provider_turn()

    def _native_image_command(self,text):
        from chat_panel import cc
        return cc._image_request_prompt(text) is not None

    def _has_current_provider_retry(self):
        failed=getattr(self,'_failed_provider_request',None)
        return bool(failed and failed[0] and failed[1][2:] == self._run_target()[2:])

    def _show_provider_recovery(self, retry, settings=None):
        """Recovery buttons appear only beside a provider failure; no permanent bottom prompt."""
        self._retry_provider_btn.setVisible(bool(retry))
        self._provider_settings_btn.setVisible(bool(retry if settings is None else settings))

    def _provider_force(self):
        provider = self._cfg.get('selected_provider', '')
        if provider == 'cloud_auto':
            return 'manager:cloud_auto'
        if not provider:
            return 'manager:local_auto'
        return 'manager:' + provider + '::' + self._cfg.get('selected_model', '')

    def _save_provider_selection(self):
        from cursiv_engine.chat import provider_settings as settings
        provider = self._cfg.get('selected_provider', '')
        settings.select('cloud_auto' if provider == 'cloud_auto' else 'manual' if provider else 'local_auto',
                        provider if provider not in ('', 'cloud_auto') else 'ollama', self._cfg.get('selected_model', ''))

    def _provider_model_text(self, value):
        self._cfg['selected_model'] = value.strip()
        if not getattr(self, '_restoring_provider', False):
            self._save_provider_selection()

    def _populate_provider_models(self, provider, values=None):
        from cursiv_engine.chat import provider_manager as manager
        if values is None:
            values, _ = manager.models(provider)
        chosen = self._cfg.get('selected_model', '')
        self._restoring_provider = True
        self._cloud_model_box.clear()
        self._cloud_model_box.addItem('Choose model or enter exact ID', '')
        for item in values:
            state = 'live' if item.verified else item.source + '; availability not verified'
            self._cloud_model_box.addItem(f'{item.name or item.id} · {state}', item.id)
            specs = [f'{provider} · {item.id}', state]
            for label, value in (('Context tokens', item.context), ('Installed bytes', item.size),
                                  ('Tools', item.tools), ('Vision', item.vision), ('Structured output', item.structured),
                                  ('Quantization', item.quantization)):
                if value is not None and value != '':
                    specs.append(f'{label}: {value}')
            from PyQt6.QtCore import Qt
            self._cloud_model_box.setItemData(self._cloud_model_box.count()-1, '\n'.join(specs), Qt.ItemDataRole.ToolTipRole)
        self._exact_model.setText(chosen)
        self._restoring_provider = False

    def _pick_provider_model(self, index):
        self._exact_model.setText(self._cloud_model_box.itemData(index) or '')

    def _refresh_provider_models(self):
        from cursiv_engine.chat import provider_manager as manager
        provider = self._cfg.get('selected_provider') or 'ollama'
        if provider == 'cloud_auto':
            return
        self._provider_refresh.setEnabled(False)
        def work():
            values, error = manager.models(provider, refresh=True)
            try:
                self._signals.provider_models.emit(provider, values, error.message if error else '')
            except RuntimeError:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _provider_models_ready(self, provider, values, error):
        self._provider_refresh.setEnabled(True)
        if provider != (self._cfg.get('selected_provider') or 'ollama'):
            return
        if provider == 'ollama':
            self._on_models([m.id for m in values if m.verified] or None)
            from PyQt6.QtCore import Qt
            for item in values:
                index=self._model_box.findData('model:'+item.id)
                if index >= 0:
                    text=item.id + (' · live' if item.verified else ' · '+item.source+'; availability not verified')
                    if item.size is not None:
                        text += f' · {item.size/2**30:.2f} GiB'
                    self._model_box.setItemData(index,text,Qt.ItemDataRole.ToolTipRole)
        else:
            self._populate_provider_models(provider, values)
        self._provider_refresh.setToolTip(error or 'Model list refreshed. Cached/catalog entries remain selectable.')

    def _open_provider_settings(self):
        win = self.window()
        if hasattr(win, '_open_settings'):
            win._open_settings('AI Providers')
        else:
            from settings_dialog import SettingsDialog
            SettingsDialog(self, 'AI Providers').exec()

    def _authorize_provider_turn(self,provider_override=None,model_override=None):
        from cursiv_engine.chat import provider_http as http, provider_settings as settings
        from cursiv_engine.chat.provider_types import ProviderError
        provider = provider_override if provider_override is not None else self._cfg.get('selected_provider', '')
        self._provider_turn_destination=None
        self._cfg['project_local_only'] = settings.project_local_only(self._cfg.get('workspace'))
        if not provider:
            return False
        if provider == 'cloud_auto':
            from cursiv_engine.chat import provider_manager
            try:
                provider,model=provider_manager.choose('cloud_auto')
                url=http.location(provider)[0]
            except ProviderError:
                return False
            destination=provider+' / '+model+' at '+url
        else:
            try:
                url, local, _ = http.preflight(provider, credential=settings.key(provider),
                                            local_only=self._cfg.get('project_local_only', False))
                model=model_override if model_override is not None else self._cfg.get('selected_model','')
                self._provider_turn_destination=(provider,url,model)
                if local:
                    return False
            except ProviderError:
                return False  # request reports offline/missing key without a network call
            destination = provider + ' / ' + model+' at '+url
        self._provider_turn_destination=(provider,url,model)
        if self._cfg.get('project_local_only'):
            return False
        return QMessageBox.question(self, 'Send research data to cloud AI?',
            f'Send this prompt, attachments, the current conversation, and relevant retrieved notebook, memory and document context to {destination}? '
            'Provider charges may apply. This authorizes this request only; it does not upload the workspace or grant file tools.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def _retry_provider_request(self):
        from cursiv_engine.chat import provider_manager as manager
        failed = getattr(self, '_failed_provider_request', None)
        if not failed or self._streaming:
            return
        request, owner = failed[:2]
        # A failed prompt belongs to its conversation/person/workspace, not to a new tab.
        target = self._run_target()
        if owner[2:] != target[2:]:
            self._append_system('Retry belongs to another conversation or workspace. Return there to retry.')
            return
        selector=(self._cfg.get('selected_provider',''),self._cfg.get('selected_model',''))
        original_selector=failed[2] if len(failed)>2 else (request.provider,request.model)
        if selector==original_selector:
            provider,model=request.provider,request.model
        elif selector[0] in ('','cloud_auto'):
            try:
                provider,model=manager.choose('cloud_auto' if selector[0]=='cloud_auto' else 'local_auto')
            except Exception:
                self._append_system('No permitted model is available in this routing mode. Choose an exact provider/model or start its service.')
                return
        else:
            provider,model=selector
        from cursiv_engine.chat import provider_http
        url=provider_http.location(provider)[0]
        changed = (provider, model) != (request.provider, request.model) or bool(request.endpoint_url and request.endpoint_url !=url)
        if changed and QMessageBox.question(self, 'Retry destination changed',
                f'Retry using {provider} / {model} at {url} instead of {request.provider} / {request.model} at {request.endpoint_url}?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        authorized = self._authorize_provider_turn(provider_override=provider,model_override=model)
        from dataclasses import replace
        request = replace(request, research_authorized=authorized,
                          local_only=bool(self._cfg.get('project_local_only')), cancel=None,
                          authorized_destination=getattr(self,'_provider_turn_destination',None) if authorized else None)
        original_prompt = next((m.get('content', '') for m in reversed(request.messages) if m.get('role') == 'user' and isinstance(m.get('content'), str)), '')
        self._begin_turn(original_prompt)
        request = replace(request, cancel=self._cancel_event)
        target = self._run_target()
        cfg=dict(self._cfg)
        def work():
            full = ''
            if request.capability == 'text':
                self._signals.run_event.emit(target, dict(kind='generation_started'))
            for text in manager.retry(request, provider=provider, model=model, authorize_changed=changed):
                full += text
                result = manager.outcome()
                self._signals.run_event.emit(target, dict(kind='chunk', text=text,
                    provenance=result.metadata() if result else None))
            result = manager.outcome()
            if result.error:
                self._signals.run_event.emit(target, dict(kind='provider_failure', text=result.error_message,
                    request=manager.snapshot(), provenance=result.metadata()))
            else:
                if not self._current_run_target(target) or request.cancel.is_set(): return
                if result.artifacts:
                    from chat_panel import cc
                    from commands_images import save_result
                    try:
                        path=save_result(cc._runtime(),result,cfg)
                    except Exception:
                        self._signals.run_event.emit(target,dict(kind='error',text='The provider returned an image, but Cursiv could not save it locally. Check the image folder before deliberately requesting another generation.'))
                        return
                    self._signals.run_event.emit(target,dict(kind='image',text=path))
                full += '\n\n*[' + result.label() + ']*'
                self._signals.run_event.emit(target, dict(kind='replace', text=full))
                self._signals.run_event.emit(target, dict(kind='done', history=[('assistant', full)],
                    exchange=None, provenance=result.metadata()))
        threading.Thread(target=work, daemon=True).start()

    @provider_turn
    def _run_paste_analysis(self, png_bytes: bytes, width: int, height: int, turn_target=None,cfg_snapshot=None) -> None:
        try:
            from chat_panel import cc
            target=turn_target or self._run_target()
            if not self._current_run_target(target): return
            result = cc.analyze_pasted_image(png_bytes,cfg_snapshot or dict(self._cfg), width, height)
            self._deliver_result(result,[], '[pasted image]',turn_target=target)
        except Exception as e:
            self._signals.run_event.emit(turn_target or self._run_target(),dict(kind='error',text='Image request failed before completion.'))
