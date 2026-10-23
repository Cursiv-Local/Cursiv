"""Fail-closed Windows updater identity; release checksums are not publisher trust."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
from cursiv_engine.core import release_identity

RELEASES = 'https://github.com/Cursiv-Local/Cursiv/releases'
# Populate only from the owner's independently verified signing certificate.
# Optional Windows certificate pinning, in addition to the owner manifest.
TRUSTED_PUBLISHERS: tuple[str, ...] = ()


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+-U\d+', value):
        raise ValueError('Unsupported release version')
    return value


def asset(data):
    tag = version(str(data.get('tag_name', '')).removeprefix('v'))
    if data.get('draft') or data.get('prerelease'):
        raise ValueError('A stable published release is required')
    names = (f'Cursiv-Setup-{tag}.exe', 'Cursiv-Setup-latest.exe')
    for name in names:
        for item in data.get('assets', []):
            if item.get('name') == name:
                url = f'{RELEASES}/download/v{tag}/{name}'
                size = item.get('size')
                if item.get('browser_download_url') != url or type(size) is not int or not 0 < size <= 1_000_000_000:
                    raise ValueError('Unexpected installer URL or size')
                return tag, item
    return tag, None


def verify_installer(path, *, trusted=None):
    trusted = TRUSTED_PUBLISHERS if trusted is None else trusted
    if not trusted:
        manifest = Path(path).parent / 'owner-release.json'
        match = re.fullmatch(r'Cursiv-Setup-(\d+\.\d+-U\d+)\.exe', Path(path).name)
        if not manifest.is_file() or not match:
            raise PermissionError('Owner proof unavailable; publisher signing is not configured. Use Open Releases Page for manual installation.')
        if Path(path).is_symlink() or Path(path).stat().st_nlink > 1 or manifest.is_symlink():
            raise PermissionError('Linked installer or owner proof is not permitted')
        return release_identity.verify_file(path, json.loads(manifest.read_text(encoding='utf-8')), match[1])
    if os.name != 'nt':
        raise PermissionError('Windows Authenticode verification is unavailable on this platform')
    raw = Path(path)
    target = raw.resolve(strict=True)
    if target.suffix.lower() != '.exe' or raw.is_symlink() or target.stat().st_nlink > 1:
        raise PermissionError('A regular Windows installer is required')
    script = ('$ErrorActionPreference="Stop"; '
              '$s=Get-AuthenticodeSignature -LiteralPath $env:CURSIV_VERIFY_INSTALLER; '
              '@{status=$s.Status.ToString(); thumbprint=$s.SignerCertificate.Thumbprint} | ConvertTo-Json -Compress')
    env = dict(os.environ, CURSIV_VERIFY_INSTALLER=str(target))
    powershell = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    result = subprocess.run([str(powershell), '-NoProfile', '-NonInteractive', '-Command', script],
                            env=env, capture_output=True, text=True, timeout=30, check=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    record = json.loads(result.stdout)
    if record.get('status') != 'Valid' or str(record.get('thumbprint', '')).upper() not in {t.upper() for t in trusted}:
        raise PermissionError('Installer signature is missing, invalid or not from the configured trusted publisher')
    return record


def _get_manifest(tag):
    from cursiv_engine.core import netgate
    if not netgate.allowed():
        raise netgate.NetworkBlocked(netgate.OFFLINE_MESSAGE)
    req = urllib.request.Request(f'{RELEASES}/download/v{tag}/owner-release.json', headers={'User-Agent': 'Cursiv-Launcher'})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError('Owner manifest exceeds the size limit')
    return json.loads(raw)


def download(url, tag, size, progress):
    from cursiv_engine.core import netgate
    version(tag)
    permitted = {f'{RELEASES}/download/v{tag}/{name}' for name in
                 (f'Cursiv-Setup-{tag}.exe', 'Cursiv-Setup-latest.exe')}
    if url not in permitted or type(size) is not int or not 0 < size <= 1_000_000_000:
        raise ValueError('Unexpected installer URL or size')
    if not netgate.allowed():
        raise netgate.NetworkBlocked(netgate.OFFLINE_MESSAGE)
    envelope = _get_manifest(tag)
    filename = f'Cursiv-Setup-{tag}.exe'
    signed = release_identity.verify_manifest(envelope, tag, filename)
    if signed['size'] != size:
        raise ValueError('GitHub asset size differs from owner-signed metadata')
    folder = Path(tempfile.mkdtemp(prefix='cursiv-update-'))
    dest = folder / f'Cursiv-Setup-{tag}.exe'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Cursiv-Launcher'})
        with urllib.request.urlopen(req, timeout=30) as response, dest.open('xb') as stream:
            declared = response.headers.get('Content-Length')
            if declared and int(declared) != size:
                raise OSError('Installer size differs from release metadata')
            got = 0
            while True:
                if not netgate.allowed():
                    raise netgate.NetworkBlocked(netgate.OFFLINE_MESSAGE)
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                got += len(chunk)
                if got > size:
                    raise OSError('Installer exceeded the expected size')
                stream.write(chunk)
                progress(int(got * 100 / size), f'Downloading update… {got / (1 << 20):.0f} MB')
        if got != size:
            raise OSError('Installer download was incomplete')
        (folder / 'owner-release.json').write_text(json.dumps(envelope), encoding='utf-8')
        verify_installer(dest)
        return str(dest)
    except BaseException:
        dest.unlink(missing_ok=True)
        (folder / 'owner-release.json').unlink(missing_ok=True)
        folder.rmdir()
        raise
