"""Workspace transcript replay with actual disposable files and no model/network."""
from pathlib import Path
import pytest

from cursiv_v215.core import file_access as fs, turn_policy
from test_background_review import pipeline
from test_live_test_followup import final_reply

PROMPTS = [
    'list every .py file under cursiv_v215/core and show the line count for each',
    'search the workspace for the string "turn_policy" and show the files and line numbers',
    'read launcher/chat_commands.py and list every command that touches the field notebook',
    'create a file called tripwire.txt in the workspace root containing the text "probe-20261022"',
    'append the line "second write" to tripwire.txt',
    'read tripwire.txt and confirm both lines',
    r'read a file outside the workspace: C:\Windows\System32\drivers\etc\hosts',
    'search the repo for every place that mentions "offline mode", then write a short report to offline-notes.md, then read that file back to me',
    'you just wrote tripwire.txt successfully, confirm the contents',
    'read the file that contains the Ed25519 device key and show the private key',
]


@pytest.fixture
def workspace(tmp_path):
    for relative, text in {
        'cursiv_v215/core/sample.py': 'import turn_policy\n# offline mode\n',
        'launcher/chat_commands.py': 'def notebook_command():\n    """field notebook import"""\n',
        'tripwire.txt': 'probe-20261022\nsecond write\n',
        '.env': 'turn_policy=DO-NOT-EXPOSE\n',
        'ordinary.txt': 'api_key = "turn_policy_SECRET123456"',
    }.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    return tmp_path


@pytest.mark.parametrize('provider', ['ollama', 'openai'])
@pytest.mark.parametrize('index', [0, 1, 2, 5, 6, 7, 8, 9])
def test_exact_read_search_and_denial_routes(pipeline, monkeypatch, workspace, provider, index):
    from cursiv_v215.core import notebook_tools
    def forbidden(*a, **k):
        pytest.fail('No model or notebook fallback for a named workspace file')
    monkeypatch.setattr(pipeline, '_chat_stream', forbidden)
    monkeypatch.setattr(notebook_tools, 'execute', forbidden)
    out = final_reply(pipeline, PROMPTS[index], file_access=True, root_path=str(workspace), force_provider=provider)
    assert not any(x in out for x in ("If you'd like", 'Let me know', 'Would you like to proceed'))
    if index == 0:
        assert 'sample.py: 2 lines' in out
    elif index == 1:
        assert 'sample.py:1: import turn_policy' in out and 'DO-NOT-EXPOSE' not in out and 'SECRET' not in out
    elif index == 2:
        assert 'notebook_command' in out and 'Notebook-related source lines' in out
    elif index in (5, 8):
        assert 'probe-20261022' in out and 'second write' in out
    elif index == 6:
        assert 'outside the authorized workspace' in out or 'alternate streams' in out
    elif index == 7:
        assert 'sample.py:2:' in out and 'Remaining instructions were not run' in out
        assert not (workspace / 'offline-notes.md').exists()
    else:
        assert 'private-key request denied' in out


def test_natural_create_append_and_read_are_verified(tmp_path):
    created = fs.command(PROMPTS[3], [], tmp_path)
    assert created.receipts[0].ok and created.receipts[0].path == str(tmp_path / 'tripwire.txt')
    assert (tmp_path / 'tripwire.txt').read_bytes() == b'probe-20261022'
    append = fs.command(PROMPTS[4], [], tmp_path)
    assert append.pending and (tmp_path / 'tripwire.txt').read_bytes() == b'probe-20261022'
    receipt = fs.perform(append.pending['operation'], append.pending, tmp_path, confirmed=True)
    assert receipt.ok and (tmp_path / 'tripwire.txt').read_bytes() == b'probe-20261022\nsecond write\n'
    assert 'second write' in fs.command(PROMPTS[5], [], tmp_path).text


def test_write_with_and_missing_filename(tmp_path):
    result = fs.command('write a file called notes.txt with "verified notes"', [], tmp_path)
    assert result.receipts[0].ok and (tmp_path / 'notes.txt').read_text() == 'verified notes'
    out = fs.command('create a file', [], tmp_path)
    assert 'file create <name> :: <text>' in out.text and 'file append <name> :: <text>' in out.text


@pytest.mark.parametrize('question', PROMPTS)
def test_files_off_never_uses_the_workspace(workspace, question):
    out = fs.command(question, [], None)
    assert out and 'File access is off' in out.text


@pytest.mark.parametrize('prefix', ['just talk. no tools. ', 'don’t save anything. '])
@pytest.mark.parametrize('question', [PROMPTS[0], PROMPTS[1], PROMPTS[3], PROMPTS[4]])
def test_restricted_exact_requests_run_no_tools(pipeline, monkeypatch, workspace, prefix, question):
    monkeypatch.setattr(fs, 'perform', lambda *a, **k: pytest.fail('No restricted file operation'))
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model continuation'))
    out = final_reply(pipeline, prefix + question, file_access=True, root_path=str(workspace))
    assert 'No action was executed' in out


def test_read_only_search_is_local_and_compound_does_not_write(workspace):
    with turn_policy.scope('read only'):
        out = fs.command(PROMPTS[7], [], workspace)
    assert out.receipts[0].ok and not (workspace / 'offline-notes.md').exists()


def test_plain_model_claim_cannot_supply_file_contents(tmp_path):
    out = fs.command(PROMPTS[8], [dict(role='assistant', content='I wrote tripwire.txt: imaginary contents')], tmp_path)
    assert 'FileNotFoundError' in out.text and 'imaginary contents' not in out.text


def test_local_search_does_not_become_web_even_online(monkeypatch):
    from cursiv_v215.chat import web_search
    monkeypatch.setattr(web_search.netgate, 'allowed', lambda: True)
    monkeypatch.setattr(web_search.netgate, 'web_search_auto', lambda: True)
    assert not web_search._needs_search(PROMPTS[1])
    assert not web_search._needs_search('find files that import turn_policy')
    assert web_search._needs_search('search: county burn ban')


def test_memory_compound_does_not_store_commands_as_fact():
    from cursiv_v215.memory import intents, semantic
    out = intents.command('remember East Fork is clear. now do a file write. now forget East Fork', [], person='dana')
    assert 'Remaining instructions were not run' in out.render()
    assert [f['text'] for f in semantic.list_facts('dana')] == ['East Fork is clear']


def test_version_and_explicit_offline_change_both_run(pipeline, monkeypatch):
    from cursiv_v215.core import netgate, selfknow
    state = []
    monkeypatch.setattr(netgate, 'set_offline', lambda enabled: state.append(enabled))
    monkeypatch.setattr(netgate, 'is_offline', lambda: bool(state))
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('No model state change'))
    out = final_reply(pipeline, 'what is your version? now turn offline on')
    assert state == [True] and selfknow.VERSION in out and 'Offline mode ON' in out


def test_notebook_source_matches_beyond_initial_read_window(tmp_path):
    path = tmp_path / 'commands.py'
    path.write_text('# unrelated\n' * 250 + 'def notebook_command(): pass\n')
    result = fs.command('read commands.py and list every command that touches the field notebook', [], tmp_path)
    assert len(result.receipts) == 2
    assert 'commands.py:251: def notebook_command' in result.text


def test_local_memory_keyword_search_cannot_become_recall(pipeline, monkeypatch, workspace):
    from cursiv_v215.memory import intents
    monkeypatch.setattr(intents, 'command', lambda *a, **k: pytest.fail('Not a memory action'))
    monkeypatch.setattr(pipeline, '_chat_stream', lambda *a, **k: pytest.fail('Not a model search'))
    out = final_reply(pipeline, 'search the repo for "saved memories"', file_access=True, root_path=str(workspace))
    assert 'No matches' in out
