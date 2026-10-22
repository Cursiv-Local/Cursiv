"""Saved-note presentation never changes note storage, classification or scoring."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from PyQt6.QtWidgets import QApplication, QFileDialog, QPlainTextEdit, QWidget
from cursiv_v215.core import strand_store, strand
import saved_notes as notes
from saved_notes_dialog import SavedNotesDialog


@pytest.fixture
def archive(tmp_path, monkeypatch):
    folder = tmp_path / 'data'
    folder.mkdir()
    path = folder / 'strands.jsonl'
    records = []
    for i in range(17):
        territory = 'general' if i < 3 else 'worldmodel' if i < 16 else 'architecture'
        full = f'Full note {i}: ' + 'complete research content ' * 90 + f' END-OF-RECORD-{i}'
        records.append(dict(id=f'{i:08x}', query=f'Question {i}', synthesis=full[:1000],
            strand=strand.encode(dict(query=f'Question {i}', synthesis=full, territory=territory)),
            territory_tag=territory, source='anchor', score=.85, timestamp=1700000000 + i,
            provenance={'original': True}, custom_metadata={'untouched': i}))
    path.write_text(''.join(json.dumps(row) + '\n' for row in records), encoding='utf-8')
    monkeypatch.setattr(strand_store, 'CURSIV_DIR', folder)
    monkeypatch.setattr(strand_store, 'STRANDS_FILE', path)
    monkeypatch.setattr(strand_store, 'TERRITORIES_FILE', folder / 'territories.json')
    monkeypatch.setattr(strand_store, '_mx', strand_store._StrandMatrix())
    before = path.read_bytes()
    yield records, path, tmp_path
    assert path.read_bytes() == before, 'Viewing/managing presentation changed the archive'
    assert not (folder / 'territories.json').exists(), 'Viewer created category definitions'


@pytest.fixture
def app():
    from PyQt6.QtGui import QFont, QFontDatabase
    application = QApplication.instance() or QApplication([])
    font = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'Fonts' / 'segoeui.ttf'
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
        application.setFont(QFont('Segoe UI', 10))
    return application


def test_all_notes_and_real_category_counts(archive, app):
    dialog = SavedNotesDialog()
    assert dialog._title.text() == 'Saved Notes (17)'
    assert dialog._tree.topLevelItemCount() == 17
    assert [dialog._categories.item(i).text() for i in range(dialog._categories.count())] == [
        'All notes (17)', 'Architecture (1)', 'General (3)', 'Worldmodel (13)']
    dialog.close()


def test_full_payload_expand_and_metadata_preserved(archive, app):
    records, path, _ = archive
    dialog = SavedNotesDialog()
    item = dialog._tree.topLevelItem(0)
    dialog._expand(item)
    editor = dialog._tree.itemWidget(item.child(0), 0)
    assert 'END-OF-RECORD-16' in editor.toPlainText()
    assert len(editor.toPlainText()) > 2000
    metadata = item.child(1)
    dialog._expand(metadata)
    raw = json.loads(dialog._tree.itemWidget(metadata.child(0), 0).toPlainText())
    assert raw == records[-1]
    assert path.read_bytes().count(b'\n') == 17
    dialog.close()


def test_search_full_content_filters_and_sorting(archive, app):
    dialog = SavedNotesDialog(category='worldmodel')
    assert dialog._tree.topLevelItemCount() == 13
    dialog._search.setText('END-OF-RECORD-14')
    assert dialog._tree.topLevelItemCount() == 1
    dialog.apply_request()
    assert dialog._tree.topLevelItemCount() == 17
    dialog._sort.setCurrentIndex(1)
    assert dialog._tree.topLevelItem(0).text(0) == 'Question 0'
    dialog._sort.setCurrentIndex(2)
    assert dialog._tree.topLevelItem(0).text(1) == 'Architecture'
    dialog.close()


def test_copy_and_export_selected_without_rewriting(archive, app, monkeypatch):
    records, _, folder = archive
    dialog = SavedNotesDialog()
    dialog._tree.setCurrentItem(dialog._tree.topLevelItem(0))
    dialog._copy_selected()
    assert 'END-OF-RECORD-16' in app.clipboard().text()
    output = folder / 'selected.json'
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *args: (str(output), 'JSON'))
    dialog._export_selected()
    assert json.loads(output.read_text())['notes'] == [records[-1]]
    assert 'verified' in dialog._status.text()
    assert not dialog._delete.isEnabled()  # No supported delete API: no unsafe rewrite added.
    assert 'no supported deletion API' in dialog._delete.toolTip()
    dialog.close()


def test_export_cannot_replace_internal_store(archive):
    records, path, root = archive
    with pytest.raises(ValueError, match='internal data'):
        notes.export_selected(records, str(path))
    with pytest.raises(ValueError, match='internal data'):
        notes.export_selected(records, str(root / '.CURSIV' / 'memory_settings.json'))


@pytest.mark.parametrize('message,category,query', [
    ('Show my saved notes.', '', ''), ('What notes do you have?', '', ''),
    ('Open my notes.', '', ''), ('Show your worldmodel notes.', 'worldmodel', ''),
    ('notes architecture', 'architecture', ''), ('strands general', 'general', ''),
    ('notes search calibration', '', 'calibration')])
def test_browse_requests_are_ui_actions(archive, message, category, query):
    import chat_commands as cc
    result = cc.handle_command(message, cc._default_cfg(), [])
    assert isinstance(result, cc.NotesResult)
    assert (result.category, result.query) == (category, query)
    assert len(result.text) < 100 and 'score:' not in result.text


def test_specific_note_and_existing_retrieval_remain_available(archive):
    import chat_commands as cc
    result = cc.handle_command('note show 00000010', cc._default_cfg(), [])
    assert not isinstance(result, cc.NotesResult) and 'END-OF-RECORD-16' in result.text
    assert strand_store.get_strand('00000010')['id'] == '00000010'
    assert strand_store.search_strands('Question research', top_k=3)
    assert cc.handle_command('notes from the meeting', cc._default_cfg(), []) is None


def test_dialog_is_focused_and_reused(archive, app):
    from chat_panel import ChatPanel
    host = QWidget()
    errors = []
    host._append_system = errors.append
    ChatPanel._open_saved_notes(host, 'worldmodel', '')
    first = host._notes_dialog
    ChatPanel._open_saved_notes(host, '', '')
    assert host._notes_dialog is first
    assert first._tree.topLevelItemCount() == 17 and not errors
    first.close()
    host.close()


def test_worker_delivers_action_via_signal(archive, monkeypatch):
    import chat_commands as cc
    import chat_panel
    monkeypatch.setattr(chat_panel, 'cc', cc)  # the real panel sets this when its backend is ready
    from chat_panel import ChatPanel
    emitted = []
    class Signal:
        def __init__(self, name): self.name = name
        def emit(self, *args): emitted.append((self.name, args))
    class Host:
        _pending_history_append = ['old']
        class _signals:
            state_changed = Signal('state')
            notes_view = Signal('notes')
            chunk = Signal('chunk')
            done = Signal('done')
    host = Host()
    ChatPanel._deliver_result(host, cc.NotesResult('worldmodel', 'rain'), [])
    assert emitted[:2] == [('state', ()), ('notes', ('worldmodel', 'rain'))]
    assert host._pending_history_append is None


def test_read_errors_are_visible(archive, app, monkeypatch):
    def denied(): raise PermissionError('drive unavailable')
    monkeypatch.setattr(notes, 'read_notes', denied)
    dialog = SavedNotesDialog()
    assert 'unavailable' in dialog._title.text()
    assert 'drive unavailable' in dialog._status.text()
    assert dialog._tree.topLevelItemCount() == 0
    dialog.close()


def test_light_and_dark_previews(archive, app, monkeypatch):
    import theme
    theme.install()
    folder = Path.cwd().parent
    original = theme.CURRENT
    try:
        for mode in ('light', 'dark'):
            monkeypatch.setattr(theme, 'CURRENT', mode)
            dialog = SavedNotesDialog(category='worldmodel')
            dialog.show()
            dialog._tree.topLevelItem(0).setExpanded(True)
            app.processEvents()
            assert len(dialog.findChildren(QPlainTextEdit)) >= 1
            assert theme.LIGHT['BG'] in dialog.styleSheet() if mode == 'light' else theme.DARK['BG'] in dialog.styleSheet()
            assert dialog.grab().save(str(folder / f'saved-notes-{mode}.png'))
            dialog.close()
    finally:
        theme.CURRENT = original


def test_restart_portable_relocation_offline(archive):
    records, source, folder = archive
    drive = folder / 'portable'
    data = drive / 'Home' / '.cursiv'
    data.mkdir(parents=True)
    shutil.copyfile(source, data / 'strands.jsonl')
    env = dict(os.environ, CURSIV_APP_DATA=str(data), HOME=str(drive / 'Home'), USERPROFILE=str(drive / 'Home'))
    code = """import sys, pathlib, socket
sys.path.insert(0,str(pathlib.Path.cwd()/'launcher'))
socket.create_connection=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network'))
from saved_notes import read_notes,full_text
rows,warnings=read_notes(); assert len(rows)==17 and not warnings
assert 'END-OF-RECORD-16' in full_text(rows[-1])
print(len(rows))
"""
    assert subprocess.check_output([sys.executable, '-B', '-c', code], env=env, text=True).strip() == '17'
    moved = folder / 'other-drive-letter'
    shutil.move(drive, moved)
    env.update(CURSIV_APP_DATA=str(moved / 'Home' / '.cursiv'), HOME=str(moved / 'Home'), USERPROFILE=str(moved / 'Home'))
    assert subprocess.check_output([sys.executable, '-B', '-c', code], env=env, text=True).strip() == '17'
    assert hashlib.sha256((moved / 'Home' / '.cursiv' / 'strands.jsonl').read_bytes()).digest() == hashlib.sha256(source.read_bytes()).digest()
