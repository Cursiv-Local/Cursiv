"""Family letters, the legacy vault and personal letters were removed from the public app (U97)."""
import importlib.util

import pytest

from cursiv_engine.core import profile


@pytest.mark.parametrize('text', ['letters', 'open letter abc', 'legacy', 'legacy import example.legacypack',
                                 'postal setup Test', 'seal export abc', 'write to Example',
                                 'babel i am Example born 2000-01-01'])
def test_removed_letter_commands_say_so(text):
    import chat_commands as cc
    assert cc.handle_command(text, cc._default_cfg(), []).text == profile.REMOVED_NOTE


def test_gui_letter_shortcuts_say_so():
    from types import SimpleNamespace
    from chat_panel import ChatPanel
    notes, typed = [], []
    fake = SimpleNamespace(_append_system=notes.append, _append_user=typed.append)
    assert ChatPanel._try_dialog_command(fake, 'write to Example') is True
    assert ChatPanel._try_dialog_command(fake, 'legacy') is True
    assert notes == [profile.REMOVED_NOTE] * 2
    assert typed == ['write to Example', 'legacy']      # each note sits under what was typed (U98)


def test_family_code_and_names_are_not_shipped():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ('cursiv_engine.family', 'cursiv_engine.postal'):
        assert importlib.util.find_spec(name) is None, name
    assert not (root / 'cursiv_engine' / 'family' / 'sealed_letters.json').exists()
    assert '_FAMILY_FIRST' not in (root / 'launcher' / 'main.py').read_text(encoding='utf-8')


@pytest.mark.parametrize('text', ['file create notes.txt :: hello', 'write a file called notes.txt with hello',
                                 'field log', 'remember field measurement', 'help field',
                                 'how do I write to a file?'])
def test_research_features_are_not_letter_commands(text):
    assert not profile.letters_command(text)
