"""Create a release tag only after local workspace tests and exact-source main CI.

Usage: python scripts/prepare_release.py v3.14-U91
No push, installer build, key access or publication is performed here.
"""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'Cursiv-Local/Cursiv'
REQUIRED_CHECKS = ('workspace-files (windows-latest)', 'workspace-files (macos-latest)',
                   'test (windows-latest)', 'test (macos-latest)', 'security')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, encoding='utf-8').strip()


def api(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', f'repos/{REPOSITORY}/{endpoint}'],
                                              cwd=ROOT, text=True, encoding='utf-8'))


def require_ci(commit, *, main_tip=True):
    main = api('git/ref/heads/main')['object']['sha']
    if main_tip and main != commit:
        raise RuntimeError('Release source must be the current main commit with passing checks. Merge the tested PR first.')
    if not main_tip and main != commit and api(f'compare/{commit}...main')['status'] != 'ahead':
        raise RuntimeError('Release source is not in main history.')
    checks = api(f'commits/{commit}/check-runs?filter=latest&per_page=100')['check_runs']
    latest = {}
    for check in sorted(checks, key=lambda row: row['id'], reverse=True):
        latest.setdefault(check['name'], check)
    for name in REQUIRED_CHECKS:
        check = latest.get(name, {})
        if (check.get('status') != 'completed' or check.get('conclusion') != 'success' or
                check.get('head_sha') != commit or check.get('app', {}).get('slug') != 'github-actions'):
            raise RuntimeError(f'Release blocked: {name} is missing, pending or unsuccessful for {commit}.')


def prepare(tag):
    if not re.fullmatch(r'v3\.14-U\d+', tag):
        raise ValueError('Use a versioned release tag, for example v3.14-U91.')
    if git('status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Commit the reviewed source and wait for main CI before creating a release tag.')
    from scripts.build_release import versions_at
    commit = git('rev-parse', 'HEAD')
    if any(value != tag[1:] for value in versions_at(commit).values()):
        raise RuntimeError('The three application version strings must match the proposed tag.')
    require_ci(commit)
    subprocess.run([sys.executable, str(ROOT / 'scripts/check_workspace_files.py')], cwd=ROOT, check=True)
    subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                    'tag', '-a', tag, '-m', f'Cursiv {tag} — required workspace/main gates passed'], cwd=ROOT, check=True)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    try:
        prepare(sys.argv[1])
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'Release tag not created: {exc}')
