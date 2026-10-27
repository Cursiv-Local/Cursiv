"""Beginner entry points reuse real widgets/storage and never execute examples."""
from pathlib import Path

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton

from cursiv_engine.core import documents, fieldlog, netgate


@pytest.fixture
def app():
    application = QApplication.instance() or QApplication([])
    font = Path('C:/Windows/Fonts/segoeui.ttf')
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
        application.setFont(QFont('Segoe UI', 10))
    return application


@pytest.fixture
def workspace(app, tmp_path, monkeypatch):
    from cursiv_engine.chat import keys
    import chat_panel
    from research_workspace import ResearchWorkspace
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setattr(keys, 'KEYS_FILE', tmp_path / 'config.json')
    monkeypatch.setattr(netgate, 'CONFIG_FILE', tmp_path / 'config.json')
    monkeypatch.setattr(documents, 'lib_dir', lambda: tmp_path / 'documents')
    monkeypatch.setattr(documents._passages, 'cache', None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_backend', lambda self: None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_models', lambda self: None)
    panel = chat_panel.ChatPanel()
    monkeypatch.setattr(panel, '_send', lambda: pytest.fail('Navigation must never send'))
    window = QMainWindow()
    view = ResearchWorkspace(panel, panel, window)
    window.setCentralWidget(view)
    window.resize(1120, 740)
    window.show()
    app.processEvents()
    yield view
    window.hide()
    window.deleteLater()
    app.processEvents()


def test_four_actions_persist_and_preserve_message_without_saving(workspace, app):
    assert list(workspace._actions) == ['Record Observation', 'Ask Cursiv', 'Research Files', 'Field Notebook']
    panel = workspace._panel
    panel._input.setPlainText('An unfinished question about this site')
    panel._history = [{'role': 'user', 'content': 'Earlier question'}]
    original = list(panel._history)
    before = fieldlog.entries()
    for name in workspace._actions:
        workspace._actions[name].click()
        app.processEvents()
        assert panel._input.toPlainText() == 'An unfinished question about this site'
        assert panel._history == original
        assert fieldlog.entries() == before
        assert all(button.isVisible() for button in workspace._actions.values())
    workspace.show_chat()
    assert workspace._stack.currentWidget() is panel
    assert not workspace._back.isVisible()


def test_notebook_and_documents_stay_in_main_window(workspace, app):
    host = workspace.window()
    visible_before = {w for w in app.topLevelWidgets() if w.isVisible()}
    workspace.open_files()
    assert workspace._files.window() is host
    assert 'across workspaces' in workspace._files._scope.text()
    workspace.open_notebook()
    app.processEvents()
    assert workspace._notebook.window() is host
    assert not workspace._notebook.isWindow()
    assert workspace._notebook.windowFlags() & Qt.WindowType.WindowType_Mask == Qt.WindowType.Widget
    assert {w for w in app.topLevelWidgets() if w.isVisible()} == visible_before
    assert workspace._back.isVisible()


def test_onboarding_example_is_labelled_and_never_sent_or_recorded(workspace, app):
    before = fieldlog.entries()
    workspace.show_getting_started()
    assert workspace._guidance.isVisible()
    example = next(b for b in workspace._guidance.findChildren(QPushButton) if b.text() == 'Show an example')
    example.click()
    app.processEvents()
    assert workspace._sample.isVisible()
    assert 'Example only — not saved' in workspace._sample.text()
    assert workspace._panel._input.toPlainText() == ''
    assert workspace._panel._history == []
    assert fieldlog.entries() == before
    assert not fieldlog.log_file().exists()
    next(b for b in workspace._guidance.findChildren(QPushButton) if b.text() == 'Got it — continue').click()
    assert not workspace._guidance.isVisible()


def test_real_document_import_failure_and_confirmed_removal(workspace, tmp_path):
    workspace.open_files()
    files = workspace._files
    source = tmp_path / 'Willow protocol.txt'
    source.write_text('Willow Basin sampling protocol. Label each bottle with its site code.', encoding='utf-8')
    original = source.read_bytes()
    files.import_files([str(source)])
    assert files._list.count() == 1
    assert 'Document indexed: Willow protocol.txt' == files._status.text()
    assert len(documents.library()) == 1
    files.import_files([str(tmp_path / 'missing.pdf')])
    assert 'Not imported:' in files._status.text()
    assert 'Document indexed:' not in files._status.text()
    assert files._list.count() == 1
    files._propose_remove()
    assert len(documents.library()) == 1
    assert files._confirm_row.isVisible()
    files._cancel_remove()
    assert len(documents.library()) == 1
    files._propose_remove()
    files._confirm_remove.click()
    assert documents.library() == []
    assert source.read_bytes() == original
    assert 'Removed from the library.' in files._status.text()


def test_selected_document_prefills_only_and_keeps_existing_draft(workspace, tmp_path):
    source = tmp_path / 'Willow protocol.txt'
    source.write_text('A field protocol for recording stream temperature.', encoding='utf-8')
    workspace.open_files()
    workspace._files.import_files([str(source)])
    workspace._files._ask_btn.click()
    panel = workspace._panel
    assert panel._input.toPlainText() == 'What does "Willow protocol.txt" say about '
    assert panel._history == []
    assert workspace._stack.currentWidget() is panel
    panel._input.setPlainText('Keep this draft')
    workspace.open_files()
    workspace._files._ask_btn.click()
    assert panel._input.toPlainText() == 'Keep this draft'


def test_navigation_failure_keeps_chat_and_explains(workspace, monkeypatch):
    monkeypatch.setattr(documents, 'library', lambda: (_ for _ in ()).throw(OSError('test disk unavailable')))
    workspace._actions['Research Files'].click()
    assert workspace._files is not None
    assert 'Could not read the document library' in workspace._files._status.text()
    assert workspace._panel._history == []


def test_bad_document_parser_reports_failure_without_success(workspace, monkeypatch):
    workspace.open_files()
    monkeypatch.setattr(documents, 'add', lambda path: (_ for _ in ()).throw(RuntimeError('test damaged PDF')))
    workspace._files.import_files(['damaged.pdf'])
    assert workspace._files._status.text() == 'Not imported: damaged.pdf: test damaged PDF'
    assert documents.library() == []


def test_embedded_notebook_fits_minimum_window_without_horizontal_scroll(workspace, app):
    from PyQt6.QtWidgets import QScrollArea
    workspace.window().resize(780, 520)
    workspace.open_notebook()
    app.processEvents()
    scroll = workspace._notebook_page.findChild(QScrollArea)
    assert scroll.horizontalScrollBar().maximum() == 0
    assert workspace._notebook.width() <= scroll.viewport().width()
    for action in workspace._actions.values():
        assert action.isVisible()
        assert action.geometry().right() <= workspace.width()


def test_small_window_collapses_guide_but_can_reopen_it(workspace, app):
    workspace.show_getting_started()
    workspace.window().resize(780, 520)
    app.processEvents()
    assert not workspace._guidance.isVisible()
    assert workspace._compact_guide.isVisible()
    workspace._compact_guide.click()
    assert workspace._guidance.isVisible()
    workspace._dismiss_guidance()
    assert not workspace._guidance.isVisible()
    assert workspace._compact_guide.isVisible()
    workspace._actions['Record Observation'].click()
    assert not workspace._guidance.isVisible()
    assert workspace._panel._input.toPlainText() == ''
    assert fieldlog.entries() == []
