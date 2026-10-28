"""U108 frozen failure probes: real native entry points and disposable evidence."""
import pytest

from cursiv_engine.core import file_access as fs, notebook_tools as nt, fieldlog, turn_policy
from test_background_review import pipeline
from test_live_test_followup import final_reply

SOURCE_QUESTIONS = [
    'Examine the repository and identify its architecture.',
    'Trace the message-processing pipeline.',
    'Find the implementation of the Field Notebook.',
    'Inspect Field Notebook retrieval code.',
]


@pytest.fixture
def source(tmp_path):
    files = {
        'ARCHITECTURE.md': '# Architecture\nMessages enter send then process_message.\n',
        'app.py': 'from worker import process_message\n\ndef send(message):\n    return process_message(message)\n',
        'worker.py': 'from notebook import retrieve\n\ndef process_message(message):\n    return retrieve(message)\n',
        'notebook.py': 'def retrieve(sample):\n    """Field Notebook retrieval implementation."""\n    return sample\n',
        'ordinary.txt': 'A harmless document.\n',
    }
    for name, body in files.items():
        (tmp_path / name).write_text(body, encoding='utf-8')
    return tmp_path


@pytest.mark.parametrize('question', [
    'Read-only: read ARCHITECTURE.md.',
    'Do not modify any files; read ARCHITECTURE.md.',
    'Inspect but do not modify: read ARCHITECTURE.md.',
])
def test_read_only_permission_does_not_disable_inspection(pipeline, monkeypatch, source, question):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model for file read'))
    policy = turn_policy.for_text(question)
    assert policy.inspect and not policy.change
    out = final_reply(pipeline, question, file_access=True, root_path=str(source))
    assert 'Messages enter send' in out


@pytest.mark.parametrize('question', SOURCE_QUESTIONS)
def test_analysis_uses_real_source_not_notebook(pipeline, monkeypatch, source, question):
    monkeypatch.setattr(nt, 'execute', lambda *a, **k: pytest.fail('No notebook lookup for implementation'))
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No unsupported model source analysis'))
    out = final_reply(pipeline, question, file_access=True, root_path=str(source))
    assert 'Source inspection' in out and '.py:' in out
    assert 'retrieve' in out or 'process_message' in out


def test_feature_discussion_is_not_observation():
    assert nt._request('Explain the difference between conversational memory and the Field Notebook.', []) is None
    assert nt._request('How does the Field Notebook save a record?', []) is None
    assert nt._request('Inspect Field Notebook retrieval code.', []) is None
    assert nt._request('Find the implementation of the Field Notebook.', []) is None


@pytest.mark.parametrize('question', [
    'Find sample WB-107 in my notebook.',
    'Find the Field Notebook record for sample WB-107.',
    'Retrieve my notebook observation for sample WB-107.',
])
def test_lookup_sample_does_not_search_the_instruction_words(question):
    row = fieldlog.add(site='Willow Basin', sample_id='WB-107', project='ORION-742', note='clear')
    result = nt.command(question, [])
    assert result and result.ok and [r['id'] for r in result.records] == [row['id']]


def test_record_id_is_exact_not_unfiltered_listing():
    wanted = fieldlog.add(site='Willow Basin', sample_id='WB-107', note='clear')
    fieldlog.add(site='Elsewhere', sample_id='WB-108', note='cloudy')
    result = nt.command(f"Find the Field Notebook record {wanted['id']}.", [])
    assert result and result.ok and [r['id'] for r in result.records] == [wanted['id']]


@pytest.mark.parametrize('question', [
    'Log site: Willow Basin; sample: WB-107; temp 18.6 C; Show me the parsed record and request confirmation before saving.',
    'Record field observation: site: Willow Basin; sample: WB-107; temp 18.6 C. Ask me before saving.',
])
def test_explicit_confirmation_prevents_native_write(question):
    result = nt.command(question, [])
    assert not fieldlog.log_file().exists(), 'No append before explicit confirmation'
    assert result is None or not result.ok


def test_first_available_message_is_not_claimed_as_complete_history():
    from cursiv_engine.core import conversation_recall
    out = conversation_recall.answer('What was my first message?', [dict(role='user', content='Later context')])
    assert 'available' in out.lower()


def test_original_concern_is_answered_from_user_history():
    from cursiv_engine.core import conversation_recall
    history = [dict(role='user', content='How do I know when my project is good enough?'),
               dict(role='assistant', content='Consider your goals.'),
               dict(role='user', content='I am developing an offline assistant.')]
    out = conversation_recall.answer('What was my original concern?', history)
    assert out and 'project is good enough' in out
    assert 'offline assistant' not in out


@pytest.mark.parametrize('question', ['Convert 5 meters to kilograms.', 'What is 2 m + 3 kg?'])
def test_calculator_decline_cannot_become_model_verified(pipeline, monkeypatch, question):
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model substitutes for refused arithmetic'))
    out = final_reply(pipeline, question)
    assert any(word in out.lower() for word in ('incompatible', 'cannot', 'unsupported', 'not supported'))
    assert 'verified calculation' not in out.lower()


def test_enabled_workspace_persists_across_turns(source):
    from cursiv_engine.core import workspace
    workspace.save('synthetic', str(source), True)
    for _ in range(3):
        root, enabled, error = workspace.load('synthetic')
        assert enabled and not error
        assert 'Messages enter send' in fs.command('read ARCHITECTURE.md', [], root).text
    workspace.save('synthetic', str(source), False)
    root, enabled, error = workspace.load('synthetic')
    assert not enabled and not error and fs.command('read ARCHITECTURE.md', [], None).receipts == []
