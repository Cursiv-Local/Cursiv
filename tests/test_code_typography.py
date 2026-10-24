"""Code typography uses normal chat size without changing stored text or history."""
import pytest
from PyQt6.QtGui import QFont, QTextCursor, QTextDocument

from chat_rendering import style_code
from test_chat_rendering import panel


def code_size(document, text):
    selected = document.find(text)
    assert not selected.isNull()
    fmt = selected.charFormat()
    assert fmt.fontFamilies()[0] == 'Consolas'
    font = fmt.font().resolve(document.defaultFont())
    base = document.defaultFont()
    if base.pixelSize() > 0:
        assert font.pixelSize() == base.pixelSize()
    else:
        assert font.pointSizeF() == base.pointSizeF()


@pytest.mark.parametrize('stream', [False, True])
def test_inline_and_fenced_code_match_normal_size(panel, stream):
    text = 'Normal prose and `field log`.\n\n```python\nprint(12.4)\n```\n\nEnd.'
    panel._on_chunk(text)
    if stream:
        panel._flush_reply_chunks()
        code_size(panel._transcript.document(), 'field log')
        code_size(panel._transcript.document(), 'print(12.4)')
    panel._on_done()
    document = panel._transcript.document()
    code_size(document, 'field log')
    code_size(document, 'print(12.4)')
    assert not document.find('Normal prose').charFormat().fontFixedPitch()
    assert 'field log' in document.toPlainText() and 'print(12.4)' in document.toPlainText()


def test_new_code_does_not_reformat_unchanged_history(panel):
    document = panel._transcript.document()
    document.clear()
    QTextCursor(document).insertMarkdown('Previous `old_command`.')
    previous = document.find('old_command').charFormat()
    panel._begin_turn()
    panel._reply_is_chat = True
    panel._on_chunk('New `new_command`.\n\nTail')
    panel._flush_reply_chunks()
    panel._on_done()
    assert document.find('old_command').charFormat() == previous
    code_size(document, 'new_command')


def test_old_saved_html_is_restyled_without_rewriting_loaded_data(panel, monkeypatch):
    import conversations
    old = QTextDocument()
    old.setDefaultFont(panel._transcript.document().defaultFont())
    old.setMarkdown('Saved `field log` and **bold**.\n\n```text\nold code\n```')
    saved_html = old.toHtml()
    messages = [{'role': 'assistant', 'content': 'Saved field log'}]
    record = {'html': saved_html, 'messages': messages}
    monkeypatch.setattr(conversations, 'load', lambda _: record)
    assert panel.open_conversation('synthetic-font-preview')
    document = panel._transcript.document()
    assert document.toPlainText() == old.toPlainText()
    code_size(document, 'field log')
    code_size(document, 'old code')
    assert record['html'] == saved_html and record['messages'] == messages
    assert panel._history == messages and not panel._dirty
    assert panel._transcript_cache.html is None
    exported = panel._transcript_cache.capture()
    assert 'Consolas' in exported
    restored = QTextDocument()
    restored.setHtml(exported)
    assert restored.toPlainText() == document.toPlainText()


@pytest.mark.parametrize('pixels', [False, True])
def test_code_respects_document_point_or_pixel_units(panel, pixels):
    document = QTextDocument()
    font = QFont('Segoe UI')
    if pixels:
        font.setPixelSize(18)
    else:
        font.setPointSizeF(12.5)
    document.setDefaultFont(font)
    document.setMarkdown('Text `command` and\n\n```text\ncode block\n```')
    before = document.toPlainText()
    assert style_code(document, 0, document.characterCount() - 1)
    code_size(document, 'command')
    code_size(document, 'code block')
    assert document.toPlainText() == before


def test_code_styling_is_idempotent_and_preserves_other_formats(panel):
    document = QTextDocument()
    document.setDefaultFont(panel._transcript.document().defaultFont())
    document.setMarkdown('**bold** [link](https://cursiv.us/) and `command`')
    before = document.toPlainText()
    bold = document.find('bold').charFormat()
    link = document.find('link').charFormat()
    assert style_code(document, 0, document.characterCount() - 1)
    revision = document.revision()
    assert not style_code(document, 0, document.characterCount() - 1)
    assert document.revision() == revision
    assert document.find('bold').charFormat() == bold
    assert document.find('link').charFormat() == link
    assert document.toPlainText() == before
