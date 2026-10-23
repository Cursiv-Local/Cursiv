"""Closing the window during a background model lookup must not emit twice."""
from types import SimpleNamespace


def test_deleted_signal_is_ignored_after_model_lookup(monkeypatch):
    import chat_controls
    from cursiv_v215.chat import status
    calls = []
    def emit(models):
        calls.append(models)
        raise RuntimeError('wrapped C/C++ object has been deleted')
    box = SimpleNamespace(clear=lambda: None, addItem=lambda *a: None, setEnabled=lambda value: None)
    target = SimpleNamespace(_model_box=box, _signals=SimpleNamespace(models=SimpleNamespace(emit=emit)))
    monkeypatch.setattr(status, 'local_models', lambda: [])
    monkeypatch.setattr(chat_controls.threading, 'Thread', lambda target, **kw: SimpleNamespace(start=target))
    chat_controls.ChatControlsMixin._load_models(target)
    assert calls == [[]]
