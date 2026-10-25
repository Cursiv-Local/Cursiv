"""Integration checks for extracted modules and retained entry points."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_complete_launcher_constructs_titlebar_and_chat(monkeypatch):
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication
    import cursiv_launcher as launcher
    import shell_dialogs
    app = QApplication.instance() or QApplication([])
    # Build the real shell without running delayed setup/sync/model jobs.
    monkeypatch.setattr(QTimer, 'singleShot', lambda *args: None)
    window = launcher.CursivLauncher('Regression test')
    try:
        assert window.findChild(shell_dialogs.TitleBar) is not None
        assert window._chat_panel._net_pill.text()
    finally:
        window._phone_sync_timer.stop()
        window._tray.hide()
        window.deleteLater()


def test_extracted_notes_json_command_serializes_success_result():
    import json
    from types import SimpleNamespace
    from cursiv_engine.core.command_api import TextResult
    import commands_system
    entry = {'instruction': 'Explain the sample', 'output': 'A "quoted" answer'}
    runtime = SimpleNamespace(
        _looks_like_text_to_json_request=lambda text: True,
        text_to_training_entry=lambda text, cfg: (True, 'Converted', entry),
        TextResult=TextResult)
    result = commands_system.handle(runtime, 'convert notes to json', 'convert notes to json', {}, [])
    assert json.loads(result.text.split('```json\n', 1)[1].split('\n```', 1)[0]) == entry


def test_production_python_module_size_budget():
    oversized = []
    for package in ('cursiv_engine', 'launcher'):
        for path in (ROOT / package).rglob('*.py'):
            count = len(path.read_text(encoding='utf-8').split('\n'))
            if count > 1200:
                oversized.append((str(path.relative_to(ROOT)), count))
    assert oversized == []


def test_extracted_chat_modules_import_without_widgets():
    code = ('import sys; from cursiv_engine.chat import context, routing, completion, '
            'local_provider, cloud_providers, provider_tools, conversation, streaming, provenance; '
            'assert not any(n.startswith("PyQt6") for n in sys.modules)')
    subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, check=True)


def test_runtime_overrides_reach_provider_boundaries(monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    monkeypatch.setattr(ca, '_ollama_running', lambda: True)
    monkeypatch.setattr(ca, '_resolve_ollama_model', lambda: 'test-local')
    monkeypatch.setattr(ca, '_call_ollama', lambda *a, **kw: iter(['provider boundary']))
    assert ca._local_llm([{'role': 'user', 'content': 'hello'}], 20) == 'provider boundary'
    assert 'test-local' in ca._ollama_label('engine')


def test_command_domain_order_preserves_intentional_chat_fallback(monkeypatch):
    import chat_commands as cc
    import command_dispatch as dispatch
    from cursiv_engine.core.command_api import UNHANDLED
    called = []
    for name in ('system', 'research', 'credentials', 'extensions', 'notes', 'services', 'images'):
        module = getattr(dispatch, '_' + name)
        monkeypatch.setattr(module, 'handle', lambda *a, name=name: called.append(name) or
                            (None if name == 'research' else UNHANDLED))
    monkeypatch.setattr(cc, 'notebook_command', lambda *a, **k: None)
    monkeypatch.setattr(cc, 'memory_command', lambda *a: None)
    assert cc.handle_command('ordinary conversation', {}, []) is None
    assert called == ['system', 'research']


def test_command_api_keeps_facade_result_identity():
    import chat_commands
    from cursiv_engine.core import command_api
    for name in ('TextResult', 'NotebookResult', 'FileActionResult', 'MemoryResult', 'NotesResult', 'StreamResult'):
        assert getattr(chat_commands, name) is getattr(command_api, name)


def test_extracted_view_classes_are_reexported():
    import cursiv_launcher as launcher
    import shell_dialogs
    from chat_panel import ChatPanel
    from chat_transcript import ChatTranscriptMixin
    from chat_controls import ChatControlsMixin
    assert launcher.FleetDialog is shell_dialogs.FleetDialog
    assert launcher.CommandAccessDialog is shell_dialogs.CommandAccessDialog
    assert issubclass(ChatPanel, ChatTranscriptMixin)
    assert issubclass(ChatPanel, ChatControlsMixin)
