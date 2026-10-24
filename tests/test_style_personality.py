"""One personality, no tones: the retired tone command and old tone values are inert."""
import json

from cursiv_engine.core import style


def test_tone_command_explains_the_single_personality(tmp_path, monkeypatch):
    monkeypatch.setattr(style, 'DIR', tmp_path)
    reply = style.command('tone playful', 'dana')
    assert 'one personality' in reply and 'style add' in reply
    assert not (tmp_path / 'dana.json').exists()
    assert not hasattr(style, 'TONES') and not hasattr(style, 'set_tone')


def test_old_tone_value_is_ignored_and_rules_are_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(style, 'DIR', tmp_path)
    (tmp_path / 'dana.json').write_text(json.dumps(
        {'tone': 'playful', 'rules': [{'text': 'Call her Dana', 'source': 'manual', 't': 0}]}))
    block = style.prompt_addendum('dana', 'What time is it in Tokyo?')
    assert 'Call her Dana' in block and 'playful' not in block.lower() and 'tone' not in block.lower()
    assert 'Tone' not in style.describe('dana')


def test_no_rules_means_no_style_block(tmp_path, monkeypatch):
    monkeypatch.setattr(style, 'DIR', tmp_path)
    assert style.prompt_addendum('dana', 'Hello') == ''


def test_personality_and_hypotheticals_reach_the_compact_persona():
    from cursiv_engine.core import speed
    from cursiv_engine.ui import chat_app
    compact = speed.compact_persona(chat_app.SYSTEM_PROMPT_FILE)
    assert 'one personality' in compact and 'Curious.' in compact
    assert 'thought experiments, hypotheses, fiction and creative writing are welcome' in compact
