"""Existing desktop controls: visibility, session persistence, owned errors and Retry."""
import time
from PyQt6.QtCore import QCoreApplication
from cursiv_engine.chat import provider_registry as registry, provider_settings as settings, provider_manager as manager
from cursiv_engine.chat import provider_adapters as adapters
from cursiv_engine.chat.provider_types import Request
from test_chat_feedback import panel


def test_every_provider_is_selectable_and_has_catalog_or_manual_input(panel):
    visible = {panel._provider_box.itemData(i) for i in range(panel._provider_box.count())}
    assert {p.id for p in registry.providers()} <= visible
    for provider in registry.providers():
        index = panel._provider_box.findData(provider.id)
        assert panel._provider_box.model().item(index).isEnabled()
        panel._provider_box.setCurrentIndex(index)
        panel._on_provider_chosen(index)
        if provider.id != 'ollama':
            panel._exact_model.setText('my-model:exact')
            assert panel._cfg['selected_model'] == 'my-model:exact'
            assert panel._provider_force() == 'manager:'+provider.id+'::my-model:exact'


def test_selection_restores_in_new_panel(panel):
    import chat_panel
    settings.select('manual','groq','chosen-model')
    other = chat_panel.ChatPanel()
    try:
        assert other._provider_box.currentData() == 'groq'
        assert other._exact_model.text() == 'chosen-model'
        assert other._cfg['selected_model'] == 'chosen-model'
        assert settings.load()['model'] == 'chosen-model'
    finally:
        other.deleteLater()


def test_model_failure_is_not_an_assistant_success_and_retry_does_not_dispatch_tools(panel, monkeypatch):
    import chat_panel
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate,'allowed',lambda:True)
    monkeypatch.setattr(settings,'key',lambda p:'')
    panel._cfg.update(selected_provider='openai',selected_model='chosen-model')
    original='Explain these research observations in plain language.'
    def generate(message, history, **kw):
        yield from manager.infer(Request('openai','chosen-model',[{'role':'user','content':message}]))
    monkeypatch.setattr(chat_panel,'_cursiv_chat',generate)
    panel._begin_turn(original)
    panel._run_turn(original,[])
    assert panel._history == [{'role':'user','content':original,'provider_provenance':panel._history[0]['provider_provenance']}]
    assert panel._history[0]['provider_provenance']['error'] == 'missing_api_key'
    assert panel._cfg['selected_model'] == 'chosen-model' and not panel._streaming
    assert panel._failed_provider_request[0].messages[0]['content'] == original
    monkeypatch.setattr(settings,'key',lambda p:'synthetic-credential')
    monkeypatch.setattr(panel,'_authorize_provider_turn',lambda **kwargs:True)
    dispatch=[]
    monkeypatch.setattr(chat_panel.cc,'notebook_command',lambda *a,**k:dispatch.append(a))
    def stream(req,result,credential):
        result.text='Recovered answer.'
        result.actual_model='reported-model'
        result.responding_provider=req.provider
        result.finish_reason='stop'
        yield result.text
    monkeypatch.setattr(adapters,'stream',stream)
    panel._retry_provider_request()
    end=time.monotonic()+3
    while panel._streaming and time.monotonic()<end:
        QCoreApplication.processEvents()
        time.sleep(.01)
    assert not panel._streaming and dispatch == []
    assert [m['role'] for m in panel._history] == ['user','assistant']
    assert 'Recovered answer.' in panel._history[1]['content']
    assert panel._history[1]['provider_provenance']['actual_model'] == 'reported-model'
    assert not panel._history[1]['provider_provenance']['error']


def test_retry_cannot_cross_conversation_boundary(panel, monkeypatch):
    panel._failed_provider_request=(Request('ollama','qwen3:4b-instruct',[]),panel._run_target())
    panel._conv_id='different-conversation'
    called=[]
    monkeypatch.setattr(manager,'retry',lambda *a,**k:called.append(a))
    panel._retry_provider_request()
    assert called == []


def test_stopped_ollama_remains_selectable_and_retains_model(panel):
    panel._provider_box.setCurrentIndex(panel._provider_box.findData('ollama'))
    panel._on_provider_chosen(panel._provider_box.currentIndex())
    panel._cfg['selected_model']='previously-installed:4b'
    panel._on_models(None)
    assert panel._model_box.findData('model:previously-installed:4b') >= 0
    assert panel._provider_box.isEnabled() and panel._model_box.isEnabled()
    assert panel._cfg['selected_model']=='previously-installed:4b'


def test_project_local_only_setting_is_scoped_and_persistent(tmp_path):
    one,two=tmp_path/'one',tmp_path/'two'
    assert not settings.project_local_only(one)
    settings.project_local_only(one,True)
    assert settings.project_local_only(one) and not settings.project_local_only(two)
    settings.project_local_only(one,False)
    assert not settings.project_local_only(one)


def test_usb_key_export_is_still_explicit_and_includes_device_keys(tmp_path, monkeypatch):
    import json
    from cursiv_engine.core import keystore
    import usb_sync
    source=tmp_path/'source'/'config.json'; source.parent.mkdir()
    source.write_text('{"offline_mode":true}',encoding='utf-8')
    monkeypatch.setattr(settings,'key',lambda p:'synthetic-device-secret' if p == 'openai' else '')
    copied=tmp_path/'drive'/'config.json'; copied.parent.mkdir()
    copied.write_bytes(source.read_bytes())
    usb_sync.keep_drive_keys(copied,None)
    assert 'synthetic-device-secret' not in copied.read_text(encoding='utf-8')
    keystore.export_readable(copied)  # only the explicit private export calls this
    assert json.loads(copied.read_text(encoding='utf-8'))['openai_key']=='synthetic-device-secret'
    assert 'openai_key' not in source.read_text(encoding='utf-8')
