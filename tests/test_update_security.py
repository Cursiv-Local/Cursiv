"""Publisher authentication fails closed; model/release prose cannot grant trust."""
from contextlib import nullcontext
from types import SimpleNamespace
import pytest
import update_security as security


def test_release_selection_checks_tag_name_url_and_size():
    tag = '3.14-U88'
    record = dict(name=f'Cursiv-Setup-{tag}.exe', size=20,
                  browser_download_url=f'{security.RELEASES}/download/v{tag}/Cursiv-Setup-{tag}.exe')
    assert security.asset(dict(tag_name='v'+tag, assets=[record])) == (tag, record)
    for field, value in [('browser_download_url', 'https://attacker.invalid/setup.exe'), ('size', 0)]:
        with pytest.raises(ValueError):
            security.asset(dict(tag_name='v'+tag, assets=[dict(record, **{field: value})]))
    with pytest.raises(ValueError):
        security.asset(dict(tag_name='../escape', assets=[]))


def test_unconfigured_signing_never_verifies_or_launches(tmp_path):
    with pytest.raises(PermissionError, match='not configured'):
        security.verify_installer(tmp_path / 'unsigned.exe')


@pytest.mark.skipif(security.os.name != 'nt', reason='Windows Authenticode adapter')
@pytest.mark.parametrize('status,thumb,accepted', [('Valid', 'ABC', True), ('NotSigned', '', False),
                                                  ('HashMismatch', 'ABC', False), ('Valid', 'OTHER', False)])
def test_authenticode_status_and_independent_publisher_allowlist(tmp_path, monkeypatch, status, thumb, accepted):
    import json
    path = tmp_path / 'candidate.exe'; path.write_bytes(b'test fixture')
    calls = []
    def run(argv, **kw):
        calls.append((argv, kw))
        return SimpleNamespace(stdout=json.dumps(dict(status=status, thumbprint=thumb)))
    monkeypatch.setattr(security.subprocess, 'run', run)
    if accepted:
        assert security.verify_installer(path, trusted=('ABC',))['status'] == 'Valid'
    else:
        with pytest.raises(PermissionError):
            security.verify_installer(path, trusted=('ABC',))
    assert calls and calls[0][1]['env']['CURSIV_VERIFY_INSTALLER'] == str(path)


@pytest.mark.parametrize('failure', ['interrupted', 'signature', 'offline'])
def test_failed_download_removes_partial_files(tmp_path, monkeypatch, failure):
    from cursiv_v215.core import netgate
    folder = tmp_path / 'download'; folder.mkdir()
    monkeypatch.setattr(security.tempfile, 'mkdtemp', lambda **kw: str(folder))
    monkeypatch.setattr(security, 'TRUSTED_PUBLISHERS', ('ABC',))
    monkeypatch.setattr(security, '_get_manifest', lambda tag: {})
    monkeypatch.setattr(security.release_identity, 'verify_manifest', lambda *a: dict(size=6))
    monkeypatch.setattr(netgate, 'allowed', lambda: failure != 'offline')
    monkeypatch.setattr(security, 'verify_installer', lambda path: (_ for _ in ()).throw(PermissionError('signature')))
    data = [b'MZ' if failure == 'interrupted' else b'MZ1234', b'']
    response = SimpleNamespace(headers={'Content-Length': '6'}, read=lambda _: data.pop(0))
    monkeypatch.setattr(security.urllib.request, 'urlopen', lambda *a, **kw: nullcontext(response))
    with pytest.raises((OSError, PermissionError)):
        security.download(f'{security.RELEASES}/download/v3.14-U88/Cursiv-Setup-latest.exe',
                          '3.14-U88', 6, lambda *a: None)
    if failure != 'offline':
        assert not folder.exists()
    else:
        assert list(folder.iterdir()) == []


def test_launch_rechecks_publisher_before_process_creation(monkeypatch):
    import cursiv_launcher
    monkeypatch.setattr(security, 'verify_installer', lambda _: (_ for _ in ()).throw(PermissionError('unsigned')))
    monkeypatch.setattr(cursiv_launcher.subprocess, 'Popen', lambda *a, **kw: pytest.fail('No unsigned execution'))
    with pytest.raises(PermissionError):
        cursiv_launcher._run_installer_and_quit('unsigned.exe')
