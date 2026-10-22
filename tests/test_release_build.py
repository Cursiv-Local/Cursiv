"""Release preparation checks without compiling/signing or touching Git state."""
import hashlib
import os
from pathlib import Path

import pytest
from scripts import build_release as release


def test_child_build_environment_excludes_editor_dll_paths(monkeypatch):
    monkeypatch.setenv('PATH', r'C:\unrelated\poppler;C:\unrelated\libheif')
    monkeypatch.setenv('PYTHONPATH', 'unexpected')
    monkeypatch.setenv('QT_PLUGIN_PATH', 'unexpected')
    env = release.build_environment()
    assert 'PYTHONPATH' not in env and 'QT_PLUGIN_PATH' not in env
    if os.name == 'nt':
        assert 'unrelated' not in env['PATH']
        assert 'System32' in env['PATH']
    assert os.environ['QT_PLUGIN_PATH'] == 'unexpected'


def test_both_installer_names_and_checksums_match(tmp_path):
    source = tmp_path / 'candidate.exe'
    source.write_bytes(b'disposable installer marker')
    output = tmp_path / 'Output'
    sums = release.stage_installers(source, output, '3.14-TEST')
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    assert (output / 'Cursiv-Setup-3.14-TEST.exe').read_bytes() == source.read_bytes()
    assert (output / 'Cursiv-Setup-latest.exe').read_bytes() == source.read_bytes()
    assert all(line.startswith(expected+'  ') for line in sums.read_text().splitlines())


@pytest.mark.parametrize('text', ['', 'FAILED', 'ALL PASSED'])
def test_frozen_check_requires_actual_report_and_private_data(tmp_path, monkeypatch, text):
    work = tmp_path / 'src';work.mkdir()
    seen = []
    def run(args, **kwargs):
        seen.append((args, kwargs))
        if text:
            Path(args[-1]).write_text(text, encoding='utf-8')
    monkeypatch.setattr(release.subprocess, 'run', run)
    if text == 'ALL PASSED':
        assert release.verify_frozen(work, {}) == tmp_path / 'frozen-selftest.txt'
    else:
        with pytest.raises(RuntimeError):
            release.verify_frozen(work, {})
    env = seen[0][1]['env']
    assert Path(env['CURSIV_APP_DATA']).is_relative_to(tmp_path)
    assert env['CURSIV_NO_ENGINE_START'] == '1'
    assert env['QT_QPA_PLATFORM'] == 'offscreen'


def test_live_benchmark_fingerprint_uses_source_paths_and_normalizes_newlines(tmp_path):
    from scripts.truth_bench import source_fingerprint
    source = tmp_path / 'launcher';source.mkdir()
    path = source / 'example.py'
    path.write_bytes(b'print(1)\r\n')
    first = source_fingerprint(tmp_path)
    path.write_bytes(b'print(1)\n')
    assert source_fingerprint(tmp_path) == first
    path.write_bytes(b'print(2)\n')
    assert source_fingerprint(tmp_path) != first
