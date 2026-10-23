"""Signed export tree inspection rejects substitutions before file contents are read."""
import json
import pytest
from cursiv_v215.core import fieldlog, export_paths
from test_fieldlog import log


def test_valid_export_round_trip_and_uncovered_file(log, tmp_path):
    log.add(site='Creek', note='fixture')
    folder = tmp_path / 'export'
    log.export(folder)
    assert log.verify_export(folder) == []
    (folder / 'unexpected.txt').write_text('added')
    assert any("isn't covered" in p for p in log.verify_export(folder))


@pytest.mark.parametrize('directory', [False, True])
def test_unexpected_symlink_is_rejected_even_when_not_signed(log, tmp_path, directory):
    log.add(note='fixture')
    folder = tmp_path / 'export'; log.export(folder)
    outside = tmp_path / 'outside'
    if directory:
        outside.mkdir()
    else:
        outside.write_text('never included')
    try:
        (folder / 'substitution').symlink_to(outside, target_is_directory=directory)
    except OSError as exc:
        pytest.skip(str(exc))
    assert any('link' in p.lower() for p in log.verify_export(folder))


@pytest.mark.parametrize('name', ['../outside', '/absolute', 'C:/outside', 'dir\\escape'])
def test_manifest_path_names_are_lexically_contained(name):
    assert not export_paths.valid_name(name)
