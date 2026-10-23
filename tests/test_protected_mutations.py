"""Protected state and guardian code stay immutable through every tool adapter."""
import pytest

from cursiv_engine.core import file_access as fs


@pytest.mark.parametrize('operation', ['write_file', 'create_file', 'append_file', 'delete_file', 'create_directory'])
@pytest.mark.parametrize('name', ['cursiv_engine/guardian/access_gate.py',
                                 'cursiv_engine/guardian/protected.py',
                                 '.cursiv/config.json', '.cursiv/runtime/login.json',
                                 '.cursiv/device_key.json', 'secrets.bat'])
def test_shared_mutation_layer_denies_protected_locations(tmp_path, operation, name):
    from cursiv_engine.ui import chat_app as ca
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'original marker')
    args = {'path': name, 'content': 'must not replace'}
    direct = fs.perform(operation, args, tmp_path, confirmed=True)
    provider = ca._file_tool_result(operation, args, tmp_path, confirmed=True)
    assert not direct.ok and not provider.ok
    assert path.read_bytes() == b'original marker'


def test_native_request_cannot_edit_guardian_source(tmp_path):
    path = tmp_path / 'cursiv_engine/guardian/protected.py'
    path.parent.mkdir(parents=True)
    path.write_text('original marker', encoding='utf-8')
    result = fs.command('file replace cursiv_engine/guardian/protected.py :: changed', [], tmp_path)
    assert result is not None
    # Preparing a confirmation is also refused; no backend write is authorized.
    assert not result.pending
    assert path.read_text(encoding='utf-8') == 'original marker'


def test_security_source_can_still_be_inspected_read_only(tmp_path):
    path = tmp_path / 'cursiv_engine/guardian/protected.py'
    path.parent.mkdir(parents=True)
    path.write_text('source marker', encoding='utf-8')
    result = fs.perform('read_file', {'path': str(path)}, tmp_path)
    assert result.ok and result.content == 'source marker'
