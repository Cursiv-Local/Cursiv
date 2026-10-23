"""Check the pinned build environment and record public artifact provenance."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys


def check_lock(root):
    from packaging.requirements import Requirement
    missing = []
    for line in (Path(root) / 'requirements-release.lock').read_text(encoding='utf-8').splitlines():
        if not line or line[0].isspace() or line.startswith('#'):
            continue
        req = Requirement(line.removesuffix('\\').strip())
        if req.marker and not req.marker.evaluate():
            continue
        try:
            installed = importlib.metadata.version(req.name)
        except importlib.metadata.PackageNotFoundError:
            installed = 'missing'
        if installed == 'missing' or installed not in req.specifier:
            missing.append(f'{req.name}: {installed}; required {req.specifier}')
    if missing:
        raise RuntimeError('Release lock mismatch: ' + '; '.join(missing))


def record(root, artifacts, output):
    root = Path(root)
    check_lock(root)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    data = dict(source_commit=commit, python=sys.version, platform=platform.platform(),
                lock_sha256=hashlib.sha256((root / 'requirements-release.lock').read_bytes()).hexdigest(),
                packages={d.metadata['Name']: d.version for d in importlib.metadata.distributions()}, assets={})
    for name in artifacts:
        path = Path(name)
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        data['assets'][path.name] = dict(size=path.stat().st_size, sha256=digest)
    Path(output).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    record(Path(__file__).resolve().parents[1], sys.argv[2:], sys.argv[1])
