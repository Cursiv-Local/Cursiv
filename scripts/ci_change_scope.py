"""Select full application CI unless every changed path is website/docs infrastructure.

Unknown paths, missing history and manual runs fail closed to the full suite. Git
renames are expanded into deletion/addition so moving app code cannot hide it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

PREFIXES = ('cloudflare/tests/', 'docs/', 'bench/results/', 'bench/discovery/')
STATIC = frozenset(('.html', '.css', '.png', '.ico', '.jpg', '.jpeg', '.svg', '.webp', '.txt', '.webmanifest', '.json'))
APP_PAGES = frozenset(('website/app.html', 'website/chat.html', 'website/profile.html'))
FILES = frozenset((
    'README.md', 'TECH.md', 'HANDOFF.md', '.github/workflows/website.yml', '.github/workflows/tests.yml',
    'scripts/discoverability_audit.py', 'scripts/generate_web_icons.py',
    'scripts/search_discovery_report.py', 'tests/test_discovery_measurement.py',
    'scripts/ci_change_scope.py', 'tests/test_ci_change_scope.py',
    'cloudflare/publish.mjs', 'website/assets/download-stats.js',
))


def website_only(paths):
    if not paths:
        return False
    def allowed(path):
        if not isinstance(path, str) or not path or path.startswith('/') or '\\' in path or '..' in PurePosixPath(path).parts:
            return False
        # Browser apps and new executable scripts keep their existing application gates.
        if path.startswith('website/notebook/') or path in APP_PAGES:
            return False
        return (path in FILES or path.startswith(PREFIXES) or
                path.startswith('website/') and PurePosixPath(path).suffix.lower() in STATIC)
    return all(allowed(path) for path in paths)


def changed_paths(base, head, *, cwd=None):
    if not all(re.fullmatch(r'[0-9a-f]{40}', value or '') for value in (base, head)):
        raise ValueError('Missing commit identity')
    ancestor = subprocess.check_output(['git', 'merge-base', base, head], cwd=cwd, text=True).strip()
    raw = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', '-z', ancestor, head], cwd=cwd)
    return [path for path in raw.decode('utf-8').split('\0') if path]


def main():
    only = False
    try:
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text(encoding='utf-8'))
        kind = os.environ.get('GITHUB_EVENT_NAME')
        if kind == 'pull_request':
            base, head = event['pull_request']['base']['sha'], event['pull_request']['head']['sha']
        elif kind == 'push':
            if event.get('forced'):
                raise ValueError('Rewritten history needs full validation')
            base, head = event['before'], event['after']
            if base == '0' * 40:
                branch = event['repository']['default_branch']
                base = subprocess.check_output(['git', 'rev-parse', '--verify',
                    'refs/remotes/origin/' + branch], text=True).strip()
        else:
            raise ValueError('Manual run: full application validation')
        only = website_only(changed_paths(base, head))
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError):
        pass  # Missing/ambiguous scope must never omit application tests.
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'website_only={str(only).lower()}\n')
    print('Website/docs-only: full app suite not run; focused website, USB, workspace and security checks remain.'
          if only else 'Application/unknown scope: full application suites required.')


if __name__ == '__main__':
    main()
