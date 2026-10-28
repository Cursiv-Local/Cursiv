"""Expanded U108 acceptance: boundaries, source citations and notebook approval."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

from cursiv_engine.core import fieldlog, file_access as fs, notebook_tools as nt, notebook_proposals as np
from cursiv_engine.core import source_inspection as si, turn_policy
from test_u108_reliability import source, SOURCE_QUESTIONS
from test_chat_feedback import panel, _APP


@pytest.mark.parametrize('question', SOURCE_QUESTIONS)
def test_citations_refer_to_real_lines_and_declared_names(source, question):
    out = fs.command(question, [], source)
    assert out and out.receipts
    citations = re.findall(r'([\w/.-]+\.(?:py|md)):(\d+)', out.text)
    assert citations
    for path, line in citations:
        lines = (source/path).read_text(encoding='utf-8').splitlines()
        assert 1 <= int(line) <= len(lines)
    for path, line, name in re.findall(r'([\w/.-]+\.py):(\d+) — declaration `([^`]+)`', out.text):
        tree = ast.parse((source/path).read_text())
        assert any(getattr(n,'name',None) == name and n.lineno == int(line) for n in ast.walk(tree))
    assert 'runtime target not verified' in out.text or 'Not verified: runtime dispatch' in out.text


def test_bounded_follow_of_real_cross_file_call(source):
    out = si.investigate('Trace the message-processing pipeline.', source).text
    assert 'app.py:4' in out and 'worker.py:3' in out and 'process_message' in out
    assert 'worker.py:4' in out and 'notebook.py:1' in out and 'retrieve' in out
    assert 'Possible static link' in out


def test_same_named_functions_in_unrelated_modules_are_not_linked(tmp_path):
    (tmp_path/'app.py').write_text('import unavailable\n\ndef send():\n    return unavailable.answer()\n')
    (tmp_path/'worker.py').write_text('def answer():\n    return "unrelated"\n')
    out = si.investigate('Trace the message-processing pipeline.', tmp_path).text
    assert 'calls `unavailable.answer`' not in out


def test_response_guidance_survives_real_provider_compaction():
    from cursiv_engine.chat import cloud_providers
    from cursiv_engine.ui.chat_app import _runtime
    from cursiv_engine.chat.response_style import guidance, GUIDANCE_HEADING
    rule = GUIDANCE_HEADING + guidance('One short reply, no advice. It is a joke.')
    messages = [dict(role='system', content='Persona '*5000),
                dict(role='system', content='state '*1000), dict(role='system', content=rule),
                dict(role='user',content='One short reply, no advice. It is a joke.')]
    slim = cloud_providers._slim(_runtime(), messages, 4000)
    assert sum(len(m['content']) for m in slim) <= 4000
    assert any('Playful personification' in m['content'] for m in slim)
    again = cloud_providers._slim(_runtime(), slim, 4000)
    assert sum(m['content'].startswith(GUIDANCE_HEADING) for m in again) == 1


def test_late_declarations_have_correct_window_offsets(tmp_path):
    body = ('# A padding line with enough harmless text to exceed the first excerpt.\n'*600 +
            'def _run_turn(message):\n    return message\n')
    (tmp_path/'chat_panel.py').write_text(body)
    out = si.investigate('Trace the message-processing pipeline.', tmp_path).text
    assert 'chat_panel.py:601 — declaration candidate `_run_turn`' in out
    receipt = fs.perform('read_file', dict(path='chat_panel.py', start_line=601, max_lines=2), tmp_path)
    assert receipt.start_line == 601 and receipt.content.startswith('def _run_turn') and receipt.truncated


@pytest.mark.parametrize('grant', [None, 'no-tools', 'read-only'])
def test_inspection_gates_and_no_writes(source, monkeypatch, grant):
    original = {p.name:p.read_bytes() for p in source.iterdir()}
    if grant == 'no-tools':
        with turn_policy.scope('No tools. Inspect the repository.'):
            out = si.investigate('Inspect the repository.', source)
        assert 'No action' in out.text and not out.receipts
    elif grant is None:
        out = si.investigate('Inspect the repository.', None)
        assert 'File access is off' in out.text and not out.receipts
    else:
        with turn_policy.scope('Read-only: inspect the repository.'):
            out = si.investigate('Inspect the repository.', source)
        assert 'Source inspection' in out.text and out.receipts
    assert original == {p.name:p.read_bytes() for p in source.iterdir()}


def test_current_workspace_only_no_secret_or_repository_metadata(tmp_path):
    left, right = tmp_path/'one', tmp_path/'two'
    left.mkdir(); right.mkdir()
    (left/'app.py').write_text('def only_left():\n    pass\n')
    (right/'app.py').write_text('def only_right():\n    pass\n')
    (right/'.env').write_text('PRIVATE_MARKER')
    (right/'unsafe.py').write_text('api_key = "SECRET_MARKER_123456"')
    out = si.investigate('Examine the repository and identify its architecture.', right).text
    assert 'only_right' in out and 'only_left' not in out and 'SECRET_MARKER' not in out and 'PRIVATE_MARKER' not in out


def test_explicit_budgets_and_malformed_source(tmp_path):
    for n in range(8):
        (tmp_path/f'app{n}.py').write_text('def broken(:\n    pass\n')
    out = si.investigate('Inspect repository source.', tmp_path, limits=si.Limits(files=2,calls=2,characters=1000))
    assert len(out.receipts) <= 2 and 'limits reached' in out.text
    assert 'runtime dispatch' in out.text
    with pytest.raises(ValueError):
        si.Limits(files=10000)


def test_javascript_declaration_has_real_reference(tmp_path):
    (tmp_path/'app.mjs').write_text('export function send(message) { return message; }\n')
    out = si.investigate('Inspect the repository source.', tmp_path).text
    assert 'app.mjs:1 — declaration `send`' in out


def test_desktop_preview_then_confirm_keeps_instructions_out_of_record(panel, monkeypatch):
    question = ('Log site: Willow Basin; project: ORION-742; sample: WB-107; temp 18.6 C; '
                'Show me the parsed record and request confirmation before saving.')
    panel._run_turn(question, [])
    _APP[0].processEvents()
    assert not fieldlog.log_file().exists()
    proposal = next(iter(panel._intents.values()))
    assert proposal.ok and proposal.needs_confirm
    assert 'confirmation' not in proposal.slots['details'].lower()
    assert 'parsed record' not in proposal.command.lower()
    result = nt.command(proposal.command, [], observer='Synthetic', scope='test-conversation')
    assert result.ok and len(fieldlog.entries()) == 1
    row = result.records[0]
    assert row['sample_id'] == 'WB-107' and row['project'] == 'ORION-742'
    assert not row['note'] and fieldlog.verify() == []
    for prompt in ('Find sample WB-107 in my notebook.', f"Find the Field Notebook record {row['id']}."):
        read = nt.command(prompt, [])
        assert read.ok and [r['id'] for r in read.records] == [row['id']]


def test_preview_rejected_under_read_only_and_cancel_does_not_write(panel):
    question = 'Log sample: TEST-108; temp 12 C; Ask me before saving.'
    result = nt.command('Read-only: '+question, [])
    assert not result.ok and not fieldlog.log_file().exists()
    proposal = np.confirmation(question)
    assert proposal.ok
    panel._intents = {'test':proposal}
    panel._streaming = False
    panel._answer_intent('cancel', 'test')
    assert not fieldlog.log_file().exists()


@pytest.mark.parametrize('verb', ['Save', 'Add', 'Record', 'Log', 'Prepare field observation:'])
def test_confirmation_with_decimal_measurement_is_not_mistaken_for_filename(verb):
    question = verb+' site: Willow Basin; sample: WB-107; temp 18.6 C; Ask me before saving.'
    proposal = np.confirmation(question)
    assert proposal is not None and proposal.ok
    result = nt.command(question, [])
    assert result is None or not result.ok
    assert not fieldlog.log_file().exists()


def test_filename_in_observation_note_does_not_remove_confirmation():
    question = 'Log site: Pond; temp 18.6 C; note: cross-reference protocol.md; Ask me before saving.'
    proposal = np.confirmation(question)
    assert proposal and proposal.ok and 'protocol.md' in proposal.command
    result = nt.command(question, [])
    assert result and not result.ok and not fieldlog.log_file().exists()


def test_restart_read_by_identifier_and_append_correction(tmp_path):
    saved = nt.command('log site: Willow Basin; sample: WB-107; temp 18.6 C', [], observer='Synthetic')
    row = saved.records[0]
    folder = fieldlog.log_dir()
    script = ('import sys; from pathlib import Path; from cursiv_engine.core import fieldlog, notebook_tools; '
              'fieldlog.log_dir=lambda:Path(sys.argv[1]); '
              'r=notebook_tools.command("Find sample WB-107 in my notebook.", []); '
              'print(r.records[0]["id"] if r and r.ok and len(r.records)==1 else "MISS")')
    process = subprocess.run([sys.executable,'-B','-c',script,str(folder)], capture_output=True,text=True,timeout=30)
    assert process.returncode == 0 and row['id'] in process.stdout, process.stderr
    original = fieldlog.entries()[0]
    fixed = fieldlog.correct(row['id'], 'Synthetic calibration correction', measurements=[dict(name='temp',value='18.9',unit='C')])
    assert fieldlog.entries()[0] == original and fixed['corrects'] == original['id'] and not fieldlog.verify()


def test_tone_feedback_is_current_thread_and_safety_keeps_precedence():
    from cursiv_engine.chat.response_style import guidance
    history = [dict(role='user',content='Keep it light; no pep talk.')]
    assert 'Playful personification' in guidance('My coffee is judging me.', history)
    assert 'Playful personification' not in guidance('Is this insulin dose safe?', history)
    assert 'Playful personification' not in guidance('My coffee is judging me.', [])


def test_unknown_unit_refusal_without_fake_result():
    from cursiv_engine.core.native_answers import answer
    out = answer('Convert 4 cubits to smoots.')
    assert 'not supported' in out and 'no numerical result' in out
    assert 'Cursiv calculation (' not in out
