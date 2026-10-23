"""Authorized text operations and model-independent local dispatch."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from cursiv_engine.core import file_access as fs


def test_read_create_list_and_atomic_append(tmp_path):
    p = tmp_path / 'notes.txt'
    result = fs.command('file create notes.txt :: first\r\n', [], tmp_path)
    assert 'Saved and verified' in result.text
    original = p.read_bytes()
    assert 'first' in fs.command('file read notes.txt', [], tmp_path).text
    assert 'notes.txt' in fs.command('file list .', [], tmp_path).text
    request = fs.command('file append notes.txt :: second', [], tmp_path).pending
    assert request and p.read_bytes() == original
    fs.execute(request['operation'], request, tmp_path, confirmed=True)
    assert p.read_bytes() == original + b'second'


def test_overwrite_requires_confirmation_and_rechecks_original(tmp_path):
    p = tmp_path / 'notes.txt'
    p.write_text('original', encoding='utf-8')
    with pytest.raises(PermissionError, match='Confirmation'):
        fs.execute('write_file', {'path': str(p), 'content': 'new'}, tmp_path)
    request = fs.command('file replace notes.txt :: new', [], tmp_path).pending
    p.write_text('edited externally', encoding='utf-8')
    with pytest.raises(PermissionError, match='changed'):
        fs.execute('write_file', request, tmp_path, confirmed=True)
    assert p.read_text() == 'edited externally'


def test_approved_overwrite_and_fresh_process_read(tmp_path):
    p = tmp_path / 'notes.txt'
    p.write_text('old', encoding='utf-8')
    request = fs.command('file replace notes.txt :: permanent research notes', [], tmp_path).pending
    fs.execute('write_file', request, tmp_path, confirmed=True)
    script = ('from pathlib import Path; from cursiv_engine.core.file_access import execute; '
              'print(execute("read_file", {"path":"notes.txt"}, Path(__import__("sys").argv[1])))')
    r = subprocess.run([sys.executable, '-B', '-c', script, str(tmp_path)], capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    assert 'permanent research notes' in r.stdout


@pytest.mark.parametrize('name', ['../escape.txt', '.env', '.env.local', '.ssh/id_rsa', 'key.pem',
                                 'credentials.txt', '.cursiv/config.json', '.git/config', 'notes.txt:secret'])
def test_protected_paths_and_traversal_are_denied(tmp_path, name):
    with pytest.raises((PermissionError, ValueError)):
        fs.execute('write_file', {'path': name, 'content': 'no'}, tmp_path, confirmed=True)


def test_outside_workspace_is_denied_even_with_confirmation(tmp_path):
    root = tmp_path / 'authorized'
    root.mkdir()
    outside = tmp_path / 'outside.txt'
    outside.write_text('private', encoding='utf-8')
    for op in ('read_file', 'write_file', 'list_directory'):
        with pytest.raises(PermissionError):
            fs.execute(op, {'path': str(outside), 'content': 'no'}, root, confirmed=True)
    assert outside.read_text() == 'private'


def test_symbolic_link_cannot_escape(tmp_path):
    root = tmp_path / 'authorized'
    outside = tmp_path / 'outside'
    root.mkdir(); outside.mkdir()
    (outside / 'notes.txt').write_text('private', encoding='utf-8')
    try:
        (root / 'link').symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f'Symlink privilege unavailable: {exc}')
    with pytest.raises(PermissionError):
        fs.execute('read_file', {'path': 'link/notes.txt'}, root)


@pytest.mark.skipif(os.name != 'nt', reason='Windows directory junction regression')
def test_windows_junction_cannot_escape(tmp_path):
    root = tmp_path / 'authorized'
    outside = tmp_path / 'outside'
    root.mkdir(); outside.mkdir()
    (outside / 'notes.txt').write_text('private', encoding='utf-8')
    link = root / 'junction'
    # Fixed fixture paths, one shell; no deletion or user data is involved.
    result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(outside)],
                            capture_output=True, text=True, timeout=20)
    if result.returncode:
        pytest.skip('Junction creation unavailable: ' + result.stderr)
    try:
        with pytest.raises(PermissionError):
            fs.execute('read_file', {'path': 'junction/notes.txt'}, root)
    finally:
        os.rmdir(link)                       # remove only the junction itself


def test_hardlinked_file_is_denied(tmp_path):
    root = tmp_path / 'authorized'
    root.mkdir()
    original = tmp_path / 'outside.txt'
    original.write_text('private', encoding='utf-8')
    try:
        os.link(original, root / 'linked.txt')
    except OSError:
        pytest.skip('Hard links unavailable')
    with pytest.raises(PermissionError):
        fs.execute('read_file', {'path': 'linked.txt'}, root)


def test_failed_atomic_replace_preserves_original(tmp_path, monkeypatch):
    p = tmp_path / 'notes.txt'
    p.write_text('original', encoding='utf-8')
    def fail(*_):
        raise OSError('disk full')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError):
        fs.execute('write_file', {'path': str(p), 'content': 'new'}, tmp_path, confirmed=True)
    assert p.read_text() == 'original'
    assert not list(tmp_path.glob('.cursiv-write-*'))


def test_both_explicit_memory_and_file_save_report_independent_outcomes(tmp_path, monkeypatch):
    from cursiv_engine.memory import semantic
    monkeypatch.setattr(semantic, 'embed', lambda _: None)
    out = fs.command('file remember project.txt :: The project is Cursiv', [], tmp_path)
    assert 'Saved and verified' in out.text and 'Conversational memory: saved and verified' in out.text
    assert any(f['text'] == 'The project is Cursiv' for f in semantic.list_facts())
    long = 'x' * 450
    out = fs.command('file remember long.txt :: ' + long, [], tmp_path)
    assert (tmp_path / 'long.txt').read_text() == long
    assert 'Conversational memory: not confirmed' in out.text


def test_save_conversation_uses_actual_transcript(tmp_path):
    history = [{'role': 'user', 'content': 'The project is Cursiv'},
               {'role': 'assistant', 'content': 'This is an unverified draft'}]
    out = fs.command('file save conversation project.md', history, tmp_path)
    assert 'Saved and verified' in out.text
    assert 'assistant: This is an unverified draft' in (tmp_path / 'project.md').read_text()


def test_file_access_off_and_missing_paths_report_actual_errors(tmp_path):
    assert 'File access is off' in fs.command('file read notes.txt', [], None).text
    assert 'FileNotFoundError' in fs.command('file read missing.txt', [], tmp_path).text
    assert 'Which file do you mean?' in fs.command('Save everything to a file on my desktop', [], tmp_path).text


def test_credentials_inside_an_ordinary_named_file_are_protected(tmp_path):
    p = tmp_path / 'notes.txt'
    p.write_text('api_key = "supersecret123456"', encoding='utf-8')
    with pytest.raises(PermissionError, match='credentials'):
        fs.execute('read_file', {'path': str(p)}, tmp_path)
    with pytest.raises(PermissionError, match='credentials'):
        fs.execute('write_file', {'path': str(p), 'content': 'overwrite'}, tmp_path, confirmed=True)


def test_confirmed_gui_dispatch_reports_file_and_memory_failures_separately(tmp_path, monkeypatch):
    import chat_commands as cc
    from cursiv_engine.memory import semantic
    monkeypatch.setattr(semantic, 'embed', lambda _: None)
    text = cc.approve_write('../outside.txt', 'A project fact', str(tmp_path), remember=True).text
    assert text.startswith('Error:') and 'Conversational memory: saved and verified' in text


def test_full_chat_file_result_does_not_call_a_cloud_verifier(tmp_path, monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    monkeypatch.setattr(ca, '_router_llm', lambda *_a, **_kw: pytest.fail('No model should see a file command'))
    out = ''.join(ca.chat('file create offline.txt :: private research notes', [], '', None,
                          file_access=True, root_path=str(tmp_path)))
    assert 'Saved and verified' in out


def test_filesystem_route_is_offline_and_needs_no_model_tools(tmp_path, monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import netgate
    monkeypatch.setattr(netgate, 'allowed', lambda: False)
    monkeypatch.setattr(ca, '_call_ollama', lambda *_a, **_k: pytest.fail('No native tool calling needed'))
    out = ''.join(ca._chat_inner('file create research.txt :: offline data', [], '', None,
                                file_access=True, root_path=str(tmp_path)))
    assert 'Saved and verified' in out
    assert (tmp_path / 'research.txt').read_text() == 'offline data'


def test_legacy_file_tools_share_workspace_checks(tmp_path):
    from cursiv_engine.core import tools
    (tmp_path / 'notes.txt').write_text('data', encoding='utf-8')
    calls = [{'tool': 'read_file', 'args': {'path': str(tmp_path / 'notes.txt')}}]
    assert 'File access is off' in tools.run(calls)[0][1]
    assert 'data' in tools.run(calls, root=tmp_path)[0][1]
    calls[0]['args']['root'] = str(tmp_path)
    assert 'Invalid file arguments' in tools.run(calls, root=tmp_path)[0][1]


def test_native_file_dispatch_cannot_bypass_confirmation_or_protection(tmp_path):
    from cursiv_engine.ui import chat_app as ca
    assert 'delete_file' not in {t['function']['name'] for t in ca.FILE_TOOLS}
    (tmp_path / 'notes.txt').write_text('original', encoding='utf-8')
    assert 'Confirmation' in ca.execute_tool('write_file', {'path': 'notes.txt', 'content': 'new'}, tmp_path)
    assert (tmp_path / 'notes.txt').read_text() == 'original'
    assert ca.execute_tool('read_file', {'path': '../outside.txt'}, tmp_path).startswith('Error:')
    assert 'must be an object' in ca.execute_tool('write_file', [], tmp_path)
    pending = ca._pending_file({'path': 'notes.txt', 'content': 'new', 'remember': True}, tmp_path)
    assert pending['remember'] is False


def test_file_commands_work_in_a_fresh_process_with_external_sockets_blocked(tmp_path):
    script = '''
import sys
from pathlib import Path
def deny_network(event, args):
    if event in ('socket.connect', 'socket.getaddrinfo', 'socket.sendto'):
        raise OSError('No network permitted by this test')
sys.addaudithook(deny_network)
from cursiv_engine.core.file_access import command
root = Path(sys.argv[1])
assert 'Saved and verified' in command('file create offline.txt :: offline content', [], root).text
print(command('file read offline.txt', [], root).text)
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(tmp_path)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert 'offline content' in result.stdout
