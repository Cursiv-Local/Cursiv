"""Research profile hides legacy operations without deleting existing user data."""
from types import SimpleNamespace
import pytest
from cursiv_engine.core import profile


@pytest.mark.parametrize('text', ['letters', 'open letter abc', 'legacy', 'legacy import example.legacypack',
                                 'postal setup Test', 'seal export abc', 'babel i am Example born 2000-01-01'])
def test_hidden_personal_commands_never_reach_backend(monkeypatch, text):
    import chat_commands as cc
    import command_dispatch
    monkeypatch.setattr(cc, '_personal', lambda: False)
    def unexpected(*a, **k): raise AssertionError('hidden personal backend was invoked')
    monkeypatch.setattr(command_dispatch._postal, 'handle', unexpected)
    result = cc.handle_command(text, cc._default_cfg(), [])
    assert result.text == profile.PERSONAL_NOTE


def test_enabled_personal_commands_keep_existing_route(monkeypatch):
    import chat_commands as cc
    monkeypatch.setattr(cc, '_personal', lambda: True)
    monkeypatch.setattr(cc, '_POSTAL_OK', True)
    monkeypatch.setattr(cc, '_postal_all', lambda: [])
    assert 'No sealed letters found' in cc.handle_command('letters', cc._default_cfg(), []).text


def test_hidden_gui_shortcuts_do_not_open_dialogs(monkeypatch):
    from chat_panel import ChatPanel
    notes = []
    fake = SimpleNamespace(_append_system=notes.append)
    monkeypatch.setattr(profile, 'personal', lambda: False)
    assert ChatPanel._try_dialog_command(fake, 'write to Example') is True
    ChatPanel._open_postal_compose(fake, 'Example')
    ChatPanel._open_legacy_vault(fake)
    assert notes == [profile.PERSONAL_NOTE] * 3


@pytest.mark.parametrize('text', ['file create notes.txt :: hello', 'write a file called notes.txt with hello',
                                 'field log', 'remember field measurement', 'help field',
                                 'how do I write to a file?'])
def test_research_features_are_not_personal_commands(text):
    assert not profile.personal_command(text)
