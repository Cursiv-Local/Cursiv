"""Registry-driven Settings → AI Providers; no credential is passed in a signal."""
import threading
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QInputDialog, QMessageBox, QProgressDialog


def build(dialog, layout):
    from cursiv_engine.chat import provider_registry as registry, provider_settings as settings, provider_manager as manager
    layout.addWidget(dialog._explain('Every provider stays selectable. Manual choices never fall back. '
        'Local Automatic never sends cloud requests. Saving a key does not enable cloud routing. '
        'Research-data sharing requires confirmation for each cloud request.'))
    panel = getattr(dialog._win, '_chat_panel', None)
    workspace = panel._cfg.get('workspace') if panel else ''
    if workspace:
        local_only = QCheckBox('Keep this workspace local only (blocks all cloud inference)')
        local_only.setChecked(settings.project_local_only(workspace))
        local_only.toggled.connect(lambda on: settings.project_local_only(workspace,on))
        layout.addWidget(local_only)
    layout.addWidget(dialog._explain('USB: the separate “Also copy my AI keys” option remains available. '
        'That explicit private export contains readable keys; anyone holding the drive can use them.', 'small'))
    dialog._provider_status_widgets = {}
    dialog._sig.provider_status.connect(lambda provider, text: dialog._provider_status_widgets[provider].setText(text))
    def progress(percent, text):
        popup = getattr(dialog, '_provider_download', None)
        if popup is not None:
            popup.setLabelText(text)
            popup.setValue(percent)
    dialog._sig.provider_progress.connect(progress)
    for spec in registry.providers():
        card = dialog._card(layout)
        title = QLabel(spec.name)
        title.setStyleSheet('font-weight:600;')
        card.addWidget(title)
        status = QLabel(manager.status(spec.id))
        status.setWordWrap(True)
        card.addWidget(status)
        dialog._provider_status_widgets[spec.id] = status
        if spec.id in ('ollama', 'lmstudio', 'custom'):
            current = settings.endpoint(spec.id)
            url = QLineEdit(current.get('url') or spec.base_url)
            url.setPlaceholderText('Base URL: https://host/v1 or http://127.0.0.1:port/v1')
            name = QLineEdit(current.get('name', ''))
            name.setPlaceholderText('Display name (optional)')
            model = QLineEdit(current.get('model', ''))
            model.setPlaceholderText('Exact model ID (optional discovery fallback)')
            timeout = QLineEdit(str(current.get('timeout', 60)))
            timeout.setPlaceholderText('Timeout seconds (2–300)')
            for widget in (url, name, model, timeout):
                card.addWidget(widget)
            save = QPushButton('Save endpoint')
            def save_endpoint(_=False, provider=spec.id, u=url, n=name, m=model, t=timeout, label=status):
                try:
                    settings.configure_endpoint(provider, url=u.text().strip(), name=n.text().strip(),
                                                model=m.text().strip(), timeout=float(t.text()))
                    label.setText('Endpoint saved. Connection not tested. Origin changes remove the custom credential.')
                except Exception:
                    label.setText('Endpoint rejected. Check its URL and timeout; remote endpoints require HTTPS.')
            save.clicked.connect(save_endpoint)
            card.addWidget(save)
        if spec.credential:
            edit = QLineEdit()
            edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setPlaceholderText('New/replacement key — existing keys are never displayed')
            card.addWidget(edit)
            row = QHBoxLayout()
            save = QPushButton('Save key')
            remove = QPushButton('Remove key')
            row.addWidget(save)
            row.addWidget(remove)
            card.addLayout(row)
            def save_key(_=False, provider=spec.id, widget=edit, label=status):
                value = widget.text().strip()
                if not value:
                    label.setText('Paste a key first.')
                    return
                try:
                    label.setText(settings.save_key(provider, value))
                    widget.clear()
                    dialog.keys_changed.emit()
                except Exception:
                    label.setText('Could not store the credential securely.')
            def remove_key(_=False, provider=spec.id, widget=edit, label=status):
                try:
                    settings.save_key(provider, '')
                    widget.clear()
                    label.setText('Credential removed for this device.')
                    dialog.keys_changed.emit()
                except Exception:
                    label.setText('Could not remove the credential.')
            save.clicked.connect(save_key)
            remove.clicked.connect(remove_key)
            if not spec.local:
                authorize = QCheckBox('Allow this provider in Cloud Automatic (may incur costs)')
                authorize.setChecked(spec.id in settings.load().get('cloud_authorized', []))
                authorize.toggled.connect(lambda on, p=spec.id: settings.authorize_cloud(p, on))
                card.addWidget(authorize)
        actions = QHBoxLayout()
        for caption in ('Test connection', 'Refresh models'):
            button = QPushButton(caption)
            def refresh(_=False, provider=spec.id, label=status):
                label.setText('Checking connection and model list…')
                def work():
                    try:
                        found, error = manager.models(provider, refresh=True)
                        text = error.message if error else f'Connection verified. {sum(m.verified for m in found)} live model IDs.'
                    except Exception:
                        text = 'Connection check failed. No credentials or upstream error bodies are shown.'
                    try:
                        dialog._sig.provider_status.emit(provider, text)
                    except RuntimeError:
                        pass
                threading.Thread(target=work, daemon=True).start()
            button.clicked.connect(refresh)
            actions.addWidget(button)
        card.addLayout(actions)
        if spec.id == 'ollama':
            card.addWidget(dialog._explain('Any installed compatible Ollama model can be selected. '
                'Downloads start only after you confirm Download model below. '
                'Model size and quantization appear when reported; performance is hardware-dependent.', 'small'))
            row = QHBoxLayout()
            pull = QPushButton('Download model…')
            remove = QPushButton('Remove model…')
            hardware = QPushButton('Check RAM, GPU and disk')
            row.addWidget(pull); row.addWidget(remove); row.addWidget(hardware)
            card.addLayout(row)
            card.addWidget(dialog._explain('Approximate model tiers: 4B lightweight; 8B balanced; 14B advanced; '
                '30B/32B high memory. These are estimates, not RAM requirements or performance guarantees. '
                'Normal research functions remain available with Qwen3 4B.', 'small'))
            def manage(download):
                from cursiv_engine.chat import provider_local
                from cursiv_engine.chat.provider_types import ProviderError
                model, ok = QInputDialog.getText(dialog,'Ollama model','Exact model ID:')
                if not ok or not model.strip():
                    return
                model = model.strip()
                question = (f'Download {model} using Ollama? This uses internet access and disk space; model size varies.' if download else
                            f'Remove the installed Ollama model {model}? Other applications may also use it.')
                if QMessageBox.question(dialog,'Confirm model download' if download else 'Confirm model removal',question,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
                cancel = threading.Event()
                popup = QProgressDialog('Starting…','Cancel',0,100,dialog)
                popup.setAutoClose(False)
                popup.canceled.connect(cancel.set)
                dialog._provider_download = popup
                popup.show()
                def work():
                    try:
                        if download:
                            for percent, text in provider_local.pull(model,consent=True,cancel=cancel):
                                dialog._sig.provider_progress.emit(percent,text)
                        else:
                            provider_local.remove(model,confirmed=True)
                        text='Model operation completed. Refresh models to update the picker.'
                    except ProviderError as exc:
                        text=exc.message
                    except Exception:
                        text='Model operation failed. Check Ollama and retry explicitly.'
                    try:
                        dialog._sig.provider_status.emit('ollama',text)
                        dialog._sig.provider_progress.emit(100,text)
                    except RuntimeError:
                        pass
                threading.Thread(target=work,daemon=True).start()
            pull.clicked.connect(lambda:manage(True))
            remove.clicked.connect(lambda:manage(False))
            def inspect_hardware():
                def work():
                    from cursiv_engine.core.tools import system_info
                    try:
                        dialog._sig.provider_status.emit('ollama',system_info())
                    except RuntimeError:
                        pass
                threading.Thread(target=work,daemon=True).start()
            hardware.clicked.connect(inspect_hardware)
