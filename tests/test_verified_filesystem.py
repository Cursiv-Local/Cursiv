"""Filesystem success claims require actual backend paths and independent bytes."""
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

from cursiv_v215.core import file_access as fs


def user(text):
    return dict(role='user', content=text)


@pytest.mark.parametrize('provider', ['ollama', 'openai', 'claude', 'grok'])
@pytest.mark.parametrize('absolute', [False, True])
def test_original_request_writes_exact_marker_with_actual_path(tmp_path, monkeypatch, provider, absolute):
    from cursiv_v215.ui import chat_app as ca
    monkeypatch.setattr(ca, '_chat_inner', lambda **kwargs: pytest.fail('No model or generic planner'))
    marker = 'Cursiv filesystem test successful. ' + uuid.uuid4().hex
    target = tmp_path / 'cursiv_test.txt'
    name = str(target) if absolute else target.name
    text = f'Create a file named {name} in my authorized workspace containing: {marker}'
    receipts = []
    reply = ''.join(ca.chat(text, [], '', None, file_access=True, root_path=str(tmp_path),
                            force_provider=provider, on_action=receipts.append))
    assert target.exists() and target.read_bytes() == marker.encode('utf-8')
    assert str(target.resolve()) in reply and receipts[0].path == str(target.resolve())
    assert receipts[0].content == marker and receipts[0].sha256 == hashlib.sha256(target.read_bytes()).hexdigest()
    assert fs.command('Read cursiv_test.txt and tell me exactly what it contains.', [], tmp_path).receipts[0].content == marker
    fake = dict(role='assistant', content='Created file at C:\\fake\\cursiv_test.txt. Verified it.')
    location = fs.command('give me the exact location you saved it to', [user(text), fake], tmp_path)
    assert str(target.resolve()) in location.text and 'C:\\fake' not in location.text


def test_followup_uses_user_content_and_never_model_content(tmp_path):
    first = 'Create a file named test.txt in my authorized workspace containing: actual user content'
    history = [user(first), dict(role='assistant', content='I saved alternate fake content at C:\\fake.txt')]
    result = fs.command('create test.txt with that content', history, tmp_path)
    assert result.receipts[0].ok and (tmp_path / 'test.txt').read_text() == 'actual user content'


def test_model_claim_cannot_verify_missing_or_mismatching_file(tmp_path):
    text = 'Create a file named test.txt in my authorized workspace containing: requested'
    history = [user(text), dict(role='assistant', content='file_create: test.txt\nSaved and verified!')]
    missing = fs.command('where did you save it?', history, tmp_path)
    assert not missing.receipts[0].ok and 'FileNotFoundError' in missing.text
    (tmp_path / 'test.txt').write_text('different', encoding='utf-8')
    changed = fs.command('where did you save it?', history, tmp_path)
    assert not changed.receipts[0].ok and 'do not match' in changed.text


@pytest.mark.parametrize('root', [None, ''])
def test_missing_workspace_never_resolves_against_cwd(root):
    result = fs.perform('create_file', dict(path='never-created.txt', content='marker'), root)
    assert not result.ok and not result.path and 'Choose workspace' in result.error


def test_write_verification_failure_is_an_error(tmp_path, monkeypatch):
    actual = Path.read_bytes
    def read(path):
        return b'wrong bytes' if path == tmp_path / 'test.txt' else actual(path)
    monkeypatch.setattr(Path, 'read_bytes', read)
    result = fs.perform('create_file', dict(path='test.txt', content='wanted'), tmp_path)
    assert not result.ok and 'verification failed' in result.error.lower()


def test_permission_and_readonly_failures_do_not_claim_success(tmp_path, monkeypatch):
    operation = 'rename' if os.name == 'nt' else 'link'
    # New-file commits use exclusive rename on Windows and hard-link on POSIX.
    monkeypatch.setattr(fs.os, operation, lambda *args: (_ for _ in ()).throw(PermissionError('read-only destination')))
    result = fs.perform('create_file', dict(path='blocked.txt', content='wanted'), tmp_path)
    assert not result.ok and 'PermissionError' in result.render() and not (tmp_path / 'blocked.txt').exists()


def test_denied_read_is_not_a_successful_generic_check(tmp_path):
    from cursiv_v215.core import tools
    results = tools.run([dict(tool='read_file', args=dict(path='missing.txt'))], root=tmp_path)
    assert not results[0].ok and results[0].receipt['verified'] is False
    context = tools.context_for(results)
    assert '"confirmed": false' in context and 'read from this computer just now' not in context


class Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.payload).encode()


@pytest.mark.parametrize('provider', ['openai', 'claude'])
@pytest.mark.parametrize('allowed', [True, False])
def test_native_tool_receipts_are_authoritative_and_errors_roundtrip(tmp_path, monkeypatch, provider, allowed):
    from cursiv_v215.ui import chat_app as ca
    calls = []
    receipts = []
    path = 'native.txt' if allowed else '../denied.txt'
    args = dict(path=path, content='literal marker')
    if provider == 'claude':
        payloads = [dict(stop_reason='tool_use', content=[dict(type='tool_use', name='write_file', input=args, id='call-1')]),
                    dict(stop_reason='end_turn', content=[dict(type='text', text='Saved file at C:\\invented.txt')])]
    else:
        payloads = [dict(choices=[dict(message=dict(role='assistant', content=None, tool_calls=[
            dict(id='call-1', type='function', function=dict(name='write_file', arguments=json.dumps(args))) ]))]),
                    dict(choices=[dict(message=dict(role='assistant', content='Saved file at C:\\invented.txt'))])]
    def request(req, **kwargs):
        calls.append(json.loads(req.data))
        return Response(payloads.pop(0))
    monkeypatch.setattr(ca.urllib.request, 'urlopen', request)
    monkeypatch.setattr(ca, '_guardian_protected', lambda *_: False)
    monkeypatch.setattr(ca, '_generate_with_claude', lambda *args: pytest.fail('Literal contents must not be rewritten'))
    if provider == 'claude':
        output = ''.join(ca._call_claude_with_tools([], 'dummy', tmp_path, on_action=receipts.append))
        returned = calls[1]['messages'][-1]['content'][0]
        assert returned['is_error'] is (not allowed)
        data = json.loads(returned['content'])
    else:
        output = ''.join(ca._call_openai_with_tools([], 'dummy', tmp_path, anthropic_key='dummy', on_action=receipts.append))
        data = json.loads(calls[1]['messages'][-1]['content'])
    assert data['ok'] is allowed and data['verified'] is allowed
    assert receipts[0].ok is allowed and 'invented.txt' not in output and '→ wrote' not in output
    if allowed:
        assert (tmp_path / path).read_bytes() == b'literal marker' and data['path'] == str(tmp_path / path)
    else:
        assert 'not confirmed' in output.lower() and not (tmp_path.parent / 'denied.txt').exists()


def test_workspace_selection_is_explicit_persisted_and_closed_on_error(tmp_path, monkeypatch):
    import chat_commands as cc
    from cursiv_v215.core import workspace, paths
    from cursiv_v215.memory import semantic
    monkeypatch.setattr(paths, 'portable_root', lambda: None)
    cfg = cc._default_cfg()
    assert cfg['workspace'] == '' and not cfg['file_access']
    assert 'Choose workspace' in cc.handle_command('files on', cfg, []).text
    assert 'Workspace' in cc.handle_command('workspace ' + str(tmp_path), cfg, []).text
    assert 'ON' in cc.handle_command('files on', cfg, []).text
    root, enabled, error = workspace.load(semantic.current_person())
    assert root == str(tmp_path.resolve()) and enabled and not error
    assert cc._default_cfg()['workspace'] == str(tmp_path.resolve())
    workspace.config_file().write_text('broken configuration', encoding='utf-8')
    assert workspace.load(semantic.current_person())[0:2] == ('', False)


def test_actual_file_and_workspace_survive_fresh_process(tmp_path):
    env = dict(os.environ, CURSIV_APP_DATA=str(tmp_path / 'data'), HOME=str(tmp_path / 'home'), USERPROFILE=str(tmp_path / 'home'))
    root = tmp_path / 'selected'
    root.mkdir()
    marker = uuid.uuid4().hex
    first = '''
import sys
from cursiv_v215.core import workspace, file_access
workspace.save('tester', sys.argv[1], True)
result = file_access.perform('create_file', dict(path='restart.txt', content=sys.argv[2]), sys.argv[1])
assert result.ok
'''
    second = '''
import sys
from pathlib import Path
from cursiv_v215.core import workspace, file_access
root, enabled, error = workspace.load('tester')
assert enabled and not error
p = Path(root) / 'restart.txt'
assert p.exists() and p.read_bytes() == sys.argv[2].encode()
result = file_access.perform('read_file', dict(path='restart.txt'), root)
assert result.ok and result.path == str(p) and result.content == sys.argv[2]
'''
    for script in (first, second):
        result = subprocess.run([sys.executable, '-B', '-c', script, str(root), marker], env=env, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr


def test_portable_workspace_relocates_and_external_host_grants_fail_closed(tmp_path, monkeypatch):
    from cursiv_v215.core import workspace
    drive = tmp_path / 'usb-before'
    root = drive / 'Workspace' / 'research'
    root.mkdir(parents=True)
    monkeypatch.setenv('CURSIV_PORTABLE', '1')
    monkeypatch.setenv('CURSIV_USB_ROOT', str(drive))
    monkeypatch.setattr(workspace, 'config_file', lambda: Path(os.environ['CURSIV_USB_ROOT']) / 'Home' / 'workspace_access.json')
    workspace.save('tester', str(root), True)
    assert fs.perform('create_file', dict(path='marker.txt', content='portable marker'), root).ok
    moved = tmp_path / 'usb-after'
    # Copy only this disposable drive; the old grant must resolve to the new root.
    shutil.copytree(drive, moved)
    monkeypatch.setenv('CURSIV_USB_ROOT', str(moved))
    root, enabled, error = workspace.load('tester')
    assert enabled and not error and root == str(moved / 'Workspace' / 'research')
    assert fs.perform('read_file', dict(path='marker.txt'), root).content == 'portable marker'
    external = tmp_path / 'external-workspace'
    external.mkdir()
    workspace.save('tester', str(external), True)
    monkeypatch.setattr(workspace, '_host', lambda: 'another-host')
    root, enabled, error = workspace.load('tester')
    assert root == '' and not enabled and 'another computer' in error


def test_workspace_itself_cannot_be_a_junction(tmp_path):
    if os.name != 'nt':
        pytest.skip('Windows junction regression')
    target = tmp_path / 'real'
    target.mkdir()
    junction = tmp_path / 'linked'
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(junction), str(target)], check=True, capture_output=True)
    result = fs.perform('create_file', dict(path='forbidden.txt', content='marker'), junction)
    assert not result.ok and 'junction' in result.error and not (target / 'forbidden.txt').exists()


@pytest.mark.skipif(os.name != 'nt', reason='Windows read-only file attribute')
def test_actual_readonly_file_never_reports_an_overwrite_success(tmp_path):
    path = tmp_path / 'readonly.txt'
    path.write_bytes(b'original bytes')
    request = fs.pending('write_file', dict(path=path.name, content='replacement'), tmp_path)
    path.chmod(stat.S_IREAD)
    try:
        result = fs.perform('write_file', request, tmp_path, confirmed=True)
        assert not result.ok and 'PermissionError' in result.error
        assert path.read_bytes() == b'original bytes'
    finally:
        path.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_native_mutation_receipt_survives_stream_filters_and_cannot_be_revised(tmp_path, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    from cursiv_v215.core import verify
    def generate(**kwargs):
        result = fs.perform('create_file', dict(path='native.txt', content='actual marker'), tmp_path)
        yield fs.VerifiedText(result.status_line() + '\n', result)
    monkeypatch.setattr(ca, '_chat_inner', generate)
    monkeypatch.setattr(verify, 'run_pass', lambda **kwargs: pytest.fail('Mutation receipt must never be rewritten by a model'))
    output = list(ca.chat('Build a simple example', [], '', None, replace_draft=True))
    assert any(isinstance(chunk, fs.VerifiedText) and chunk.result.ok for chunk in output)
    assert str(tmp_path / 'native.txt') in ''.join(output)
    assert (tmp_path / 'native.txt').read_bytes() == b'actual marker'


def test_fabricated_model_save_is_replaced_without_executing_anything(tmp_path, monkeypatch):
    from cursiv_v215.ui import chat_app as ca
    monkeypatch.setattr(ca, '_chat_inner', lambda **kwargs: iter(['- file_create: imaginary.txt\n', 'I saved it to C:\\invented.txt']))
    output = ''.join(ca.chat('Explain your workflow', [], '', None, root_path=str(tmp_path), replace_draft=True))
    assert ca.REPLACE_SENTINEL in output
    final = output.rsplit(ca.REPLACE_SENTINEL, 1)[1]
    assert 'Action not confirmed' in final and 'invented.txt' not in final
    assert not list(tmp_path.iterdir())
