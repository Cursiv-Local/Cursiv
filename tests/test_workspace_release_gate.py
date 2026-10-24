"""Release preparation fails closed before tag creation; no real GitHub calls."""
import subprocess

import pytest

from scripts import prepare_release as gate

COMMIT = 'a' * 40


def checks():
    return [dict(id=i, name=name, status='completed', conclusion='success', head_sha=COMMIT,
                 app=dict(slug='github-actions')) for i, name in enumerate(gate.REQUIRED_CHECKS, 1)]


@pytest.mark.parametrize('failure', ['missing', 'failed', 'pending', 'wrong-source', 'wrong-app', 'newer-failure'])
def test_missing_or_failing_native_checks_block_release(monkeypatch, failure):
    rows = checks()
    if failure == 'missing': rows.pop(0)
    elif failure == 'failed': rows[0]['conclusion'] = 'failure'
    elif failure == 'pending': rows[0].update(status='in_progress', conclusion=None)
    elif failure == 'wrong-source': rows[0]['head_sha'] = 'b' * 40
    elif failure == 'wrong-app': rows[0]['app']['slug'] = 'untrusted'
    else: rows.append(dict(rows[0], id=100, conclusion='failure'))
    monkeypatch.setattr(gate, 'api', lambda path: dict(object=dict(sha=COMMIT)) if path.startswith('git/') else dict(check_runs=rows))
    with pytest.raises(RuntimeError, match='Release blocked'):
        gate.require_ci(COMMIT)


def test_exact_source_all_checks_pass(monkeypatch):
    monkeypatch.setattr(gate, 'api', lambda path: dict(object=dict(sha=COMMIT)) if path.startswith('git/') else dict(check_runs=checks()))
    gate.require_ci(COMMIT)


def test_non_main_source_cannot_be_tagged(monkeypatch):
    monkeypatch.setattr(gate, 'api', lambda path: dict(object=dict(sha='b' * 40)))
    with pytest.raises(RuntimeError, match='current main'):
        gate.require_ci(COMMIT)


@pytest.mark.parametrize('fail_at', ['ci', 'local-tests'])
def test_no_tag_command_if_a_gate_fails(monkeypatch, fail_at):
    from scripts import build_release
    monkeypatch.setattr(gate, 'git', lambda *args: '' if args[0] == 'status' else COMMIT)
    monkeypatch.setattr(build_release, 'versions_at', lambda _: {'one': '3.14-U91'})
    called = []
    def ci(*args):
        called.append('ci')
        if fail_at == 'ci': raise RuntimeError('Release blocked')
    def run(args, **kwargs):
        called.append('tests' if 'check_workspace_files.py' in str(args) else 'tag')
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(gate, 'require_ci', ci)
    monkeypatch.setattr(gate.subprocess, 'run', run)
    with pytest.raises((RuntimeError, subprocess.CalledProcessError)):
        gate.prepare('v3.14-U91')
    assert 'tag' not in called


def test_tag_created_only_after_both_gates(monkeypatch):
    from scripts import build_release
    monkeypatch.setattr(gate, 'git', lambda *args: '' if args[0] == 'status' else COMMIT)
    monkeypatch.setattr(build_release, 'versions_at', lambda _: {'one': '3.14-U91'})
    called = []
    monkeypatch.setattr(gate, 'require_ci', lambda *args: called.append('ci'))
    monkeypatch.setattr(gate.subprocess, 'run', lambda args, **kw:
                        called.append('tests' if 'check_workspace_files.py' in str(args) else 'tag'))
    gate.prepare('v3.14-U91')
    assert called == ['ci', 'tests', 'tag']


def test_workspace_gate_is_in_pr_main_and_build_paths():
    root = gate.ROOT
    workflow = (root / '.github/workflows/tests.yml').read_text(encoding='utf-8')
    triggers = workflow.split('jobs:')[0]
    # Every push (main included, since U96 every branch) and every pull request.
    assert 'pull_request:' in triggers and 'push:' in triggers
    assert 'branches:' not in triggers or 'branches: [main]' in triggers
    assert 'workspace-files:' in workflow and 'python scripts/check_workspace_files.py' in workflow
    assert "'tests/test_workspace_release_gate.py'" in (root / 'scripts/check_workspace_files.py').read_text(encoding='utf-8')
    assert 'require_ci' in (root / 'scripts/build_release.py').read_text(encoding='utf-8')
    assert 'Require exact-source main release gates' in (root / '.github/workflows/mac-build.yml').read_text(encoding='utf-8')
