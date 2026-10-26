"""Beginner descriptions retain confirmation, user evidence and append-only writes."""
import threading

import pytest

from cursiv_engine.core import fieldlog, notebook_proposals, turn_policy
from cursiv_engine.memory import semantic
from test_chat_feedback import panel, _APP


def test_unknown_scale_and_reported_time_are_not_invented():
    said = 'Water temperature was 21.4 degrees at Willow Basin around 2:15.'
    proposal = notebook_proposals.observation(said)
    assert proposal.needs_confirm and not proposal.ok
    assert 'Celsius or Fahrenheit' in proposal.problems[0]
    fields = fieldlog.parse(proposal.slots['details'])
    assert fields['site'] == 'Willow Basin'
    assert fields['measurements'] == [dict(name='Water temperature', value='21.4', unit='')]
    assert fields['note'] == 'Reported observation time: 2:15'
    assert 'recorded_local' not in fields and fields['sample_id'] == ''
    assert proposal.edit_text == said


@pytest.mark.parametrize('said', [
    'Is water temperature of 21.4 C normal at Willow Basin?',
    'Imagine water temperature was 21.4 C at Willow Basin.',
    'Do not save this: water temperature was 21.4 C at Willow Basin.',
    'The report says water temperature was 21.4 C at Willow Basin.',
    'Water temperature was 21.4 C at Willow Basin; project: SECRET.',
    'Water temperature was 21.4 C at Willow Basin at 29:90.',
])
def test_non_observations_never_become_previews(said):
    assert notebook_proposals.observation(said) is None


def test_ordinary_observation_waits_for_confirmation_then_readback_matches(panel, monkeypatch):
    import chat_commands
    from cursiv_engine.ui import chat_app
    monkeypatch.setattr(chat_app, '_local_model_ready', lambda: False)
    panel._run_turn('Water temperature was 21.4 degrees Celsius at Willow Basin around 2:15.', [])
    _APP[0].processEvents()
    assert fieldlog.entries() == []
    key, proposal = next(iter(panel._intents.items()))
    assert proposal.ok
    # Run the actual confirmed native route synchronously; no model or fake save.
    result = chat_commands.notebook_command(proposal.command, [], scope='u106-confirmation')
    assert result.receipt['ok']
    row = fieldlog.entries()[0]
    assert row['site'] == 'Willow Basin'
    assert row['measurements'][0]['value'] == '21.4' and row['measurements'][0]['unit'] == '°C'
    assert row['note'] == 'Reported observation time: 2:15'
    assert fieldlog.verify() == []


def test_edit_unknown_scale_returns_original_language(panel):
    said = 'Water temperature was 21.4 degrees at Willow Basin around 2:15.'
    panel._show_intent_card(notebook_proposals.observation(said))
    panel._answer_intent('edit', next(iter(panel._intents)))
    assert panel._input.toPlainText() == said
    assert fieldlog.entries() == []


def test_confirmation_cards_do_not_cross_conversations(panel, monkeypatch):
    import conversations
    proposal = panel._memory_confirmation('Remember the lake study uses weekly sampling.', [])
    panel._show_intent_card(proposal)
    key = next(iter(panel._intents))
    panel.new_conversation()
    panel._answer_intent('save', key)
    assert semantic.list_facts() == []
    panel._show_intent_card(proposal)
    key = next(iter(panel._intents))
    monkeypatch.setattr(conversations, 'load', lambda _: dict(messages=[], html='Other conversation'))
    assert panel.open_conversation('another-conversation')
    panel._answer_intent('save', key)
    assert semantic.list_facts() == []


def test_reported_day_is_not_part_of_the_site():
    preview = notebook_proposals.observation('Water temperature was 18.2 C at Quarry Inlet yesterday.')
    fields = fieldlog.parse(preview.slots['details'])
    assert fields['site'] == 'Quarry Inlet'
    assert fields['note'] == 'Reported observation date: yesterday'


@pytest.mark.parametrize('suffix', ['at noon', 'on Tuesday', 'last night', 'this morning'])
def test_unsupported_time_qualifiers_cannot_be_saved_as_part_of_a_place(suffix):
    preview = notebook_proposals.observation('Water temperature was 18.2 C at Quarry Inlet ' + suffix + '.')
    assert preview is not None and not preview.ok
    assert any('place and reported time' in problem for problem in preview.problems)


def test_classifier_and_numbered_memory_selection_also_wait_for_confirmation(panel, monkeypatch):
    from cursiv_engine.core import local_intent
    from cursiv_engine.memory import intents
    semantic.set_person('baseline')
    text = 'Make a mental note that our control plot is Pine Reach.'
    monkeypatch.setattr(local_intent, 'classify', lambda said, users: dict(
        operation=intents.SAVE, content='our control plot is Pine Reach.', source=text))
    panel._run_turn(text, [])
    _APP[0].processEvents()
    assert semantic.list_facts('baseline') == []
    assert next(iter(panel._intents.values())).action.name == 'memory.save'
    # Existing pending memory choices must also resolve to a preview, not a save.
    intents._pending[intents._key('baseline', panel._conv_id or '')] = (
        intents.Action(intents.SAVE, reference=True), ['Control plot Pine Reach'])
    panel._run_turn('1', [])
    _APP[0].processEvents()
    assert semantic.list_facts('baseline') == []
    assert any(p.slots.get('fact') == 'Control plot Pine Reach' for p in panel._intents.values())


def test_explicit_memory_preview_cancel_and_confirm_once(panel, monkeypatch):
    semantic.set_person('baseline')
    panel._run_turn("Remember that we're studying seasonal changes in this lake.", [])
    _APP[0].processEvents()
    assert semantic.list_facts('baseline') == []
    key = next(iter(panel._intents))
    panel._answer_intent('cancel', key)
    assert semantic.list_facts('baseline') == []
    panel._run_turn("Remember that we're studying seasonal changes in this lake.", [])
    _APP[0].processEvents()
    key = next(iter(panel._intents))
    ran = []
    class RunNow:
        def __init__(self, target, args, daemon):
            self.target, self.args = target, args
        def start(self):
            ran.append(self.args)
            self.target(*self.args)
    monkeypatch.setattr(threading, 'Thread', RunNow)
    panel._answer_intent('save', key)
    _APP[0].processEvents()
    panel._answer_intent('save', key)
    assert len(ran) == 1 and ran[0][2] is False
    facts = semantic.list_facts('baseline')
    assert len(facts) == 1 and 'seasonal changes' in facts[0]['text']
    assert facts[0]['origin'] == 'user_said'


def _receipt(row):
    return dict(role='assistant', content='Stored observation', notebook_receipt=dict(
        ok=True, status='saved', records=[row]))


def test_context_correction_uses_receipts_and_preserves_original():
    original = fieldlog.add(site='Willow Basin', measurements=[dict(name='temperature', value='21.4', unit='°C')])
    text = 'I recorded the wrong temperature earlier. It should have been 20.4.'
    assert not notebook_proposals.context_correction(text, [dict(role='assistant', content=f"Logged. Record {original['id']}")]).ok
    proposal = notebook_proposals.context_correction(text, [_receipt(original)])
    assert proposal.ok and proposal.needs_confirm and fieldlog.entries() == [original]
    out = fieldlog.command(proposal.command)
    assert 'original entry is unchanged' in out
    rows = fieldlog.entries()
    assert rows[0] == original and rows[1]['corrects'] == original['id']
    assert rows[1]['measurements'][0]['value'] == '20.4' and rows[1]['reason'] == text
    assert fieldlog.verify() == []


def test_ambiguous_and_stale_correction_cannot_run(panel, monkeypatch):
    original = fieldlog.add(site='Willow Basin', measurements=[dict(name='temperature', value='21.4', unit='°C')])
    other = fieldlog.add(site='Other', measurements=[dict(name='temperature', value='18', unit='°C')])
    text = 'I recorded the wrong temperature earlier. It should have been 20.4.'
    read = dict(role='assistant', notebook_receipt=dict(ok=True, status='read', records=[original, other]))
    assert not notebook_proposals.context_correction(text, [read]).ok
    proposal = notebook_proposals.context_correction(text, [_receipt(original)])
    fieldlog.correct(original['id'], 'Already corrected', measurements=[dict(name='temperature', value='20', unit='°C')])
    panel._show_intent_card(proposal)
    monkeypatch.setattr(panel, '_run_turn', lambda *a: pytest.fail('Stale correction must not execute'))
    panel._answer_intent('save', next(iter(panel._intents)))
    assert len(fieldlog.entries()) == 3
    assert 'changed since the preview' in panel._transcript.toPlainText()
