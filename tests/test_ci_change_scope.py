"""CI selection must never hide an app change behind a website/docs change."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('ci_scope', Path(__file__).resolve().parents[1] / 'scripts/ci_change_scope.py')
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class ChangeScopeTests(unittest.TestCase):
    def test_website_and_documentation_paths_use_focused_checks(self):
        self.assertTrue(scope.website_only(['website/index.html', 'cloudflare/publish.mjs', 'docs/README.md',
            'bench/results/website-copy-live.json', 'HANDOFF.md', 'scripts/discoverability_audit.py',
            '.github/workflows/tests.yml', 'scripts/ci_change_scope.py', 'tests/test_ci_change_scope.py']))

    def test_application_dependencies_tests_and_unknown_paths_keep_full_suites(self):
        for path in ['cursiv_engine/chat/completion.py', 'launcher/main.py', 'requirements-release.lock',
                     'tests/test_verify.py', 'installer/setup.iss', 'scripts/build_release.py',
                     '.github/workflows/mac-release.yml', 'new-folder/file.py', '../website/a', '/website/a',
                     'website/../launcher/main.py', 'website\\index.html', 'cloudflare/worker.js',
                     'website/notebook/core.js', 'website/app.html', 'website/assets/new-runtime.js']:
            with self.subTest(path=path):
                self.assertFalse(scope.website_only(['website/index.html', path]))
        self.assertFalse(scope.website_only([]))

    def test_real_git_rename_out_of_app_still_requires_application_tests(self):
        with tempfile.TemporaryDirectory(prefix='cursiv-ci-scope-') as folder:
            root = Path(folder)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
            git('init', '-q')
            git('config', 'user.name', 'Scope regression')
            git('config', 'user.email', 'scope@example.invalid')
            (root / 'launcher').mkdir()
            (root / 'launcher/main.py').write_text('print(1)\n')
            git('add', 'launcher/main.py'); git('commit', '-qm', 'fixture')
            before = git('rev-parse', 'HEAD')
            (root / 'website').mkdir()
            git('mv', 'launcher/main.py', 'website/main.py')
            git('commit', '-qm', 'move')
            paths = scope.changed_paths(before, git('rev-parse', 'HEAD'), cwd=root)
            self.assertIn('launcher/main.py', paths)
            self.assertFalse(scope.website_only(paths))

    def test_forced_push_cannot_hide_application_reverts(self):
        with tempfile.TemporaryDirectory(prefix='cursiv-ci-forced-') as folder:
            event, output = Path(folder) / 'event.json', Path(folder) / 'output'
            event.write_text(json.dumps({'before': 'a' * 40, 'after': 'b' * 40, 'forced': True}))
            with patch.dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_OUTPUT=str(output),
                            GITHUB_EVENT_NAME='push'), patch.object(scope, 'changed_paths') as changed:
                scope.main()
                changed.assert_not_called()
                self.assertEqual(output.read_text(), 'website_only=false\n')

    def test_missing_history_and_manual_runs_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix='cursiv-ci-event-') as folder:
            event, output = Path(folder) / 'event.json', Path(folder) / 'output'
            event.write_text(json.dumps({'before': '0' * 40, 'after': 'a' * 40}))
            for kind in ['workflow_dispatch', 'push', 'pull_request']:
                with self.subTest(kind=kind), patch.dict(os.environ, GITHUB_EVENT_PATH=str(event),
                        GITHUB_OUTPUT=str(output), GITHUB_EVENT_NAME=kind):
                    scope.main()
                    self.assertTrue(output.read_text().endswith('website_only=false\n'))


if __name__ == '__main__':
    unittest.main()
