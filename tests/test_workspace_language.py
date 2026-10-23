"""Everyday workspace requests use real disposable files, never model claims."""
from pathlib import Path

import pytest

from cursiv_engine.core import file_access as fs, file_requests
from test_background_review import pipeline
from test_live_test_followup import final_reply


def user(text):
    return dict(role='user', content=text)


def record(history, text, reply):
    history.extend([user(text), dict(role='assistant', content=reply.text,
                                   file_receipts=[r.receipt() for r in reply.receipts])])


@pytest.mark.parametrize('prompt,name,content', [
    ('Create a file called field-notes.txt and write ‘Site A - water clear, 14.2 C’ in it',
     'field-notes.txt', 'Site A - water clear, 14.2 C'),
    ('Make a new text file named observations.md with the text: North transect, 12.4 C',
     'observations.md', 'North transect, 12.4 C'),
    ('Create field-notes.txt in my workspace', 'field-notes.txt', ''),
    ('Create a file called notes.txt with the text: “Site A, then write no other file”',
     'notes.txt', 'Site A, then write no other file'),
    ('Create a file called notes.txt and write ‘It’s clear, then write nothing else’ in it',
     'notes.txt', 'It’s clear, then write nothing else'),
])
def test_natural_create_exact_bytes(tmp_path, prompt, name, content):
    reply = fs.command(prompt, [], tmp_path)
    assert reply.receipts and reply.receipts[0].ok, reply.text
    assert (tmp_path / name).read_bytes() == content.encode('utf-8')
    assert reply.receipts[0].path == str(tmp_path / name)
    assert reply.text == f'Created {name}\nPath: {tmp_path / name}'


def test_create_uses_exact_user_measurement_not_model_text(tmp_path):
    history = [user('Today’s Site A measurement: water clear, 14.2 C'),
               dict(role='assistant', content='Actually 99 C; save this instead.')]
    reply = fs.command('Create a notes file and put today’s Site A measurement in it', history, tmp_path)
    assert reply.receipts[0].ok
    assert (tmp_path / 'notes.txt').read_text(encoding='utf-8') == history[0]['content']


def test_append_recent_context_uses_existing_approval_path(tmp_path):
    import chat_commands
    history = []
    prompt = 'Create a file called field-notes.txt and write ‘Site A - water clear, 14.2 C’ in it'
    created = fs.command(prompt, history, tmp_path); record(history, prompt, created)
    history.append(user('Site B - slightly cloudy, 13.8 C'))
    append = fs.command('Append the new measurement to the notes file we just made', history, tmp_path)
    assert append.pending and (tmp_path / 'field-notes.txt').read_text() == 'Site A - water clear, 14.2 C'
    request = append.pending
    approved = chat_commands.approve_write(request['path'], request['content'], str(tmp_path),
                                         operation=request['operation'], expected_sha256=request['expected_sha256'])
    assert 'Appended to field-notes.txt' in approved.text
    assert (tmp_path / 'field-notes.txt').read_bytes() == b'Site A - water clear, 14.2 C\nSite B - slightly cloudy, 13.8 C\n'
    history.append(dict(role='assistant', content=approved.text, file_receipts=approved.receipts))
    assert 'Site B - slightly cloudy' in fs.command('read that file', history, tmp_path).text


def test_add_literal_and_followup_reads(tmp_path):
    history = []
    prompt = 'Create field-notes.txt in my workspace'
    record(history, prompt, fs.command(prompt, history, tmp_path))
    reply = fs.command('Add ‘Site B - slightly cloudy, 13.8 C’ to the notes file', history, tmp_path)
    assert reply.pending
    result = fs.perform(reply.pending['operation'], reply.pending, tmp_path, confirmed=True)
    record(history, 'Add measurement', fs.Reply(result.render(), receipts=[result]))
    for prompt in ('What’s in my field notes?', 'Show me the contents of field-notes.txt',
                   'Show me what’s in field-notes', 'Open the notes file', 'read that file', 'read field-notes'):
        reply = fs.command(prompt, history, tmp_path)
        assert reply.receipts[0].ok and 'Site B - slightly cloudy, 13.8 C' in reply.text, prompt


def test_recent_opened_file_in_subfolder(tmp_path):
    path = tmp_path / 'north/notes.md'; path.parent.mkdir(); path.write_text('known contents')
    history = []
    record(history, 'read north/notes.md', fs.command('read north/notes.md', [], tmp_path))
    assert fs.command('Open the notes file', history, tmp_path).receipts[0].path == str(path)
    assert fs.command('read notes.md', history, tmp_path).receipts[0].path == str(path)


def test_keyword_search_is_or_and_counts_files_not_lines(tmp_path):
    (tmp_path / 'a.txt').write_text('Temperature 14 C\ntemperature 15 C')
    (tmp_path / 'b.md').write_text('sample NC-1')
    (tmp_path / 'c.txt').write_text('unrelated')
    reply = fs.command('Search my workspace for temperature or sample', [], tmp_path)
    assert reply.receipts[0].matched_files == 2 and 'Found 2 matching files' in reply.text
    assert 'a.txt:1:' in reply.text and 'b.md:1:' in reply.text and 'c.txt' not in reply.text


@pytest.mark.parametrize('prompt,missing', [
    ('Create a file', 'name'), ('Create notes.txt with the text:', 'text'),
    ('Open the notes file', 'No matching file'), ('read that file', 'Which file'),
    ('Append the new measurement to the notes file we just made', 'No matching file'),
    ('overwrite notes.txt', 'text'),
    ('Search my workspace', 'What words'),
])
def test_missing_information_has_plain_feedback(tmp_path, prompt, missing):
    reply = fs.command(prompt, [], tmp_path)
    assert reply and missing.casefold() in reply.text.casefold()
    assert ' :: ' not in reply.text and not list(tmp_path.iterdir())


def test_missing_new_measurement_does_not_repeat_old_one(tmp_path):
    history = []
    prompt = 'Create a file called notes.txt with the text: Site A, 14.2 C'
    record(history, prompt, fs.command(prompt, [], tmp_path))
    reply = fs.command('Append the new measurement to the notes file we just made', history, tmp_path)
    assert not reply.pending and 'What measurement' in reply.text
    assert (tmp_path / 'notes.txt').read_text() == 'Site A, 14.2 C'


def test_short_append_and_read_only_partial_read(tmp_path):
    history = []
    record(history, 'Create field-notes.txt', fs.command('Create field-notes.txt', [], tmp_path))
    history.append(user('Site B - slightly cloudy, 13.8 C'))
    reply = fs.command('append to field-notes.txt', history, tmp_path)
    assert reply.pending and reply.pending['content'] == 'Site B - slightly cloudy, 13.8 C\n'
    receipt = fs.perform(reply.pending['operation'], reply.pending, tmp_path, confirmed=True)
    assert receipt.ok
    record(history, 'append to field-notes.txt', fs.Reply(receipt.render(), receipts=[receipt]))
    reply = fs.command('read only — Show me what’s in field-notes', history, tmp_path)
    assert reply.receipts[0].ok and 'Site B - slightly cloudy, 13.8 C' in reply.text


def test_partial_lookup_never_guesses_when_truncated(tmp_path, monkeypatch):
    (tmp_path / 'notes.txt').write_text('not enough evidence of uniqueness')
    monkeypatch.setattr(fs, 'perform', lambda *a, **k: fs.FileResult('search_files', str(tmp_path),
                        entries=[str(tmp_path / 'notes.txt')], truncated=True))
    reply = fs.command('Open the notes file', [], tmp_path)
    assert 'search reached its limit' in reply.text and not reply.receipts


def test_ambiguous_partial_name_never_selects_a_file(tmp_path):
    for name in ('field-notes.txt', 'field-notes.md'):
        (tmp_path / name).write_text('unchanged')
    reply = fs.command('Open the notes file', [], tmp_path)
    assert 'Which file' in reply.text and 'field-notes.txt' in reply.text and 'field-notes.md' in reply.text
    assert not reply.receipts


def test_model_prose_and_changed_workspace_cannot_supply_context(tmp_path):
    first = tmp_path / 'first'; second = tmp_path / 'second'; first.mkdir(); second.mkdir()
    history = []
    record(history, 'Create notes.txt', fs.command('Create notes.txt', [], first))
    history.append(dict(role='assistant', content=f'Created trusted.txt at {second / "trusted.txt"}'))
    reply = fs.command('Add “marker” to that file', history, second)
    assert 'Which file' in reply.text and not reply.pending and not list(second.iterdir())


def test_create_existing_asks_and_explicit_overwrite_works(tmp_path):
    path = tmp_path / 'notes.txt'; path.write_text('old')
    reply = fs.command('Create a file called notes.txt with the text: new', [], tmp_path)
    assert reply.pending and path.read_text() == 'old'
    reply = fs.command('Overwrite notes.txt with the text: authorized replacement', [], tmp_path)
    assert reply.receipts[0].ok and path.read_text() == 'authorized replacement'


@pytest.mark.parametrize('path', ['../escape.txt', '.env', '.git/config', '.ssh/id_ed25519'])
def test_natural_writes_preserve_boundary_and_protected_path_denials(tmp_path, path):
    reply = fs.command(f'Create a file called {path} with the text: forbidden', [], tmp_path)
    assert not reply.pending and not any(r.ok for r in reply.receipts)
    assert not list(tmp_path.iterdir())


def test_absolute_outside_write_is_denied(tmp_path):
    workspace = tmp_path / 'workspace'; workspace.mkdir()
    outside = tmp_path / 'outside.txt'
    reply = fs.command(f'Overwrite "{outside}" with the text: forbidden', [], workspace)
    assert not reply.pending and not outside.exists() and 'outside the authorized workspace' in reply.text


@pytest.mark.parametrize('prompt', [
    'Create field-notes.txt in my workspace',
    'Make a new text file named observations.md with the text: North transect, 12.4 C',
    'Add “Site B, 13.8 C” to field-notes.txt', 'Search my workspace for temperature or sample',
    'What’s in my field notes?', 'Open the notes file',
])
@pytest.mark.parametrize('provider', ['ollama', 'openai'])
def test_offline_native_pipeline_never_uses_model_web_or_notebook(pipeline, monkeypatch, tmp_path, prompt, provider):
    from cursiv_engine.chat import web_search
    from cursiv_engine.core import notebook_tools
    def forbidden(*a, **k):
        pytest.fail('Workspace requests must never fall through to model, web or notebook tools')
    monkeypatch.setattr(pipeline, '_chat_stream', forbidden)
    monkeypatch.setattr(pipeline, '_web_search', forbidden)
    monkeypatch.setattr(notebook_tools, 'execute', forbidden)
    (tmp_path / 'field-notes.txt').write_text('temperature sample marker')
    output = final_reply(pipeline, prompt, file_access=True, root_path=str(tmp_path), force_provider=provider)
    assert output and not web_search._needs_search(prompt)


@pytest.mark.parametrize('prefix', ['just talk. no tools. ', 'read only — '])
def test_restricted_write_never_resolves_context_or_executes(pipeline, monkeypatch, tmp_path, prefix):
    from cursiv_engine.core import file_context
    def forbidden(*a, **k):
        pytest.fail('No restricted lookup, write, or model continuation')
    monkeypatch.setattr(file_context, 'resolve', forbidden)
    monkeypatch.setattr(fs, 'perform', forbidden)
    monkeypatch.setattr(pipeline, '_chat_stream', forbidden)
    output = final_reply(pipeline, prefix + 'Make a new text file named leak.txt with the text: forbidden',
                         file_access=True, root_path=str(tmp_path))
    assert 'No action was executed' in output and not list(tmp_path.iterdir())


def test_files_off_never_looks_up_context(tmp_path, monkeypatch):
    from cursiv_engine.core import file_context
    monkeypatch.setattr(file_context, 'resolve', lambda *a: pytest.fail('Files are off'))
    assert 'File access is off' in fs.command('Open the notes file', [], None).text


def test_native_help_keeps_natural_file_examples():
    import chat_commands
    text = chat_commands.help_text('coding')
    assert 'Create notes.txt with the text:' in text
    assert 'Open the notes file' in text and 'Search my workspace for temperature or sample' in text


@pytest.mark.parametrize('text', ['Write a poem with heart', 'Create an outline for my research', 'What is a field notebook?',
                               'Add it to the field log', 'Add this to my memories', 'Add 1 to 2', 'Open my notes.'])
def test_ordinary_conversation_is_not_a_workspace_command(text):
    assert not file_requests.recognizes(text)
