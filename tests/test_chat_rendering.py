"""Offline streaming, rich-text caching and ordered autosave regressions."""
from __future__ import annotations

import threading

import pytest
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QFont, QTextCursor, QTextDocument, QTextDocumentFragment
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from chat_rendering import MarkdownStream, TranscriptCache

_APP = []


@pytest.fixture
def panel(monkeypatch, tmp_path):
    import chat_panel
    import conversations
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    app = _APP[0]
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_backend', lambda self: None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_load_models', lambda self: None)
    monkeypatch.setattr(chat_panel.ChatPanel, '_refresh_status_pill', lambda self: None)
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: False)
    monkeypatch.setattr(conversations, 'DIR', tmp_path / 'conversations')
    original_title = conversations._smart_title
    monkeypatch.setattr(conversations, '_smart_title', lambda *a: None)
    p = chat_panel.ChatPanel()
    p._test_title = original_title
    p.resize(900, 600)
    p.show()
    app.processEvents()
    p._transcript.clear()
    p._empty_shown = False
    p._begin_turn()
    p._reply_is_chat = True
    yield p
    conversations.wait_for_save()
    app.processEvents()
    p.close()
    p.deleteLater()


def bold(document, word):
    return document.find(word).charFormat().fontWeight() >= QFont.Weight.Bold


def settle():
    QTest.qWait(65)


def test_chunks_are_batched_on_the_gui_thread(panel, monkeypatch):
    calls = []
    original = panel._append_reply_chunk

    def append(text):
        assert QThread.currentThread() == panel.thread()
        calls.append(text)
        original(text)
    monkeypatch.setattr(panel, '_append_reply_chunk', append)
    for _ in range(100):
        panel._on_chunk('word ')
    assert 'word' not in panel._transcript.toPlainText()
    assert panel._chunk_timer.interval() == 40
    # Wait for delivery rather than assuming Windows schedules a coarse Qt
    # timer within exactly 65 ms on a busy machine. The production interval
    # and single-batch/GUI-thread assertions remain unchanged.
    for _ in range(25):
        if calls:
            break
        QTest.qWait(10)
    assert calls == ['word ' * 100]
    panel._on_done()
    assert not panel._chunk_timer.isActive()


def test_completed_paragraphs_are_formatted_during_streaming(panel):
    panel._on_chunk('**Already bold**\n\nUnfinished **')
    panel._flush_reply_chunks()
    assert bold(panel._transcript.document(), 'Already bold')
    assert panel._transcript.toPlainText().endswith('Unfinished **')
    panel._on_chunk('now complete**')
    panel._on_done()
    assert bold(panel._transcript.document(), 'now complete')
    assert 'Unfinished now complete' in panel._transcript.toPlainText()


@pytest.mark.parametrize('fence', ['```', '~~~~'])
def test_incomplete_fenced_blocks_wait_for_the_closing_fence(fence, panel):
    stream = MarkdownStream()
    for chunk in [fence[:1], fence[1:] + 'python\n', 'x = 1\n\n', 'print(x)\n']:
        stream.push(chunk)
        assert stream.take_ready() == ''
    stream.push(fence + '\n\nlast')
    ready = stream.take_ready()
    assert ready == fence + 'python\nx = 1\n\nprint(x)\n' + fence + '\n\n'
    assert stream.tail == 'last'
    panel._on_chunk(ready + 'last')
    panel._flush_reply_chunks()
    panel._on_done()
    assert 'x = 1\n\nprint(x)' in panel._transcript.toPlainText()
    assert fence not in panel._transcript.toPlainText()


def test_fence_like_text_inside_code_does_not_close_the_block():
    stream = MarkdownStream()
    stream.push('````python\n```\n\n')
    assert stream.take_ready() == ''
    stream.push('````\n\n')
    assert stream.take_ready().endswith('````\n\n')


RICH = ('## Notes\n\n**bold** and *italic*, with [a link](https://cursiv.us/).\n\n'
        '1. First\n   - Nested\n2. Second\n\n'
        '| Sample | Value |\n| --- | --- |\n| North | 12.4 |\n| South | 14.1 |\n\n'
        '```python\nprint("not **bold**")\n\n# keep this blank line\n```\n\n'
        '> Quoted text\n\n[Reference][site]\n\n[site]: https://cursiv.us/\n\n'
        'Known: observed readings\nInferred: none\nAssumed: none\nUnknown: calibration\n\n'
        '*[Answered by Ollama · test-model]*')


def test_stream_and_single_final_parse_have_identical_formatting(panel):
    import chat_badges
    chat_badges.seen_once("tour_shown")      # the one-time tour card is tested on its own
    for i in range(0, len(RICH), 7):
        panel._on_chunk(RICH[i:i + 7])
        panel._flush_reply_chunks()
    panel._on_done()
    rendered = panel._transcript.toHtml()
    # Reconstruct that same active message once; final output must not depend
    # on chunk boundaries, previously incomplete tables, fences, or links.
    panel._render_cache = None
    panel._render_reply()
    assert panel._transcript.toHtml() == rendered
    text = panel._transcript.toPlainText()
    assert '12.4' in text and 'Local · test-model' in text
    assert 'Known:' not in text and 'Show reasoning and checks' in text
    assert '<table' in rendered and '<pre' in rendered and 'href="https://cursiv.us/"' in rendered


def test_finished_message_cache_skips_repeat_parsing(panel, monkeypatch):
    calls = []
    original = QTextCursor.insertMarkdown

    def parse(cursor, text, *a):
        calls.append(text)
        return original(cursor, text, *a)
    monkeypatch.setattr(QTextCursor, 'insertMarkdown', parse)
    panel._on_chunk('**One parse**')
    panel._on_done()
    panel._render_reply()
    panel._render_reply()
    assert calls == ['**One parse**']


@pytest.mark.parametrize('count', [10, 100, 1000])
def test_streaming_never_rebuilds_or_parses_unchanged_history(count, panel, monkeypatch):
    history = '\n'.join(f'History {i} — untouched 😀' for i in range(count))
    panel._transcript.setPlainText(history)
    panel._begin_turn()
    panel._reply_is_chat = True
    parses = []
    original = QTextCursor.insertMarkdown
    monkeypatch.setattr(QTextCursor, 'insertMarkdown',
                        lambda cursor, text, *a: (parses.append(text), original(cursor, text, *a))[1])
    monkeypatch.setattr(panel._transcript, 'setHtml', lambda *a: pytest.fail('Full HTML rebuild'))
    monkeypatch.setattr(panel._transcript, 'setMarkdown', lambda *a: pytest.fail('Full Markdown rebuild'))
    panel._on_chunk('**New answer**\n\nTail')
    panel._flush_reply_chunks()
    panel._on_done()
    assert panel._transcript.toPlainText().startswith(history)
    assert parses and all('History' not in text for text in parses)


def test_replacement_drains_pending_text_without_leaking_the_old_draft(panel):
    panel._on_chunk('old draft **wrong**\n\n')
    panel._on_replace('**Correct answer**')
    panel._on_chunk('\n\nA check note.')
    panel._flush_reply_chunks()
    panel._pending_history_append = [('assistant', '**Correct answer**\n\nA check note.')]
    panel._on_done()
    assert 'old draft' not in panel._transcript.toPlainText()
    assert panel._transcript.toPlainText().count('Correct answer') == 1
    assert 'A check note.' in panel._transcript.toPlainText()
    assert panel._history[-1]['content'] == '**Correct answer**\n\nA check note.'


def test_scrolled_history_and_selected_text_are_preserved(panel):
    view = panel._transcript
    view.setPlainText('\n'.join(f'History line {i}' for i in range(200)))
    panel._begin_turn()
    panel._reply_is_chat = True
    selected = view.document().find('History line 4')
    view.setTextCursor(selected)
    view.verticalScrollBar().setValue(0)
    for text in ['**new**\n\n', 'last paragraph']:
        panel._on_chunk(text)
        panel._flush_reply_chunks()
    panel._on_done()
    assert view.verticalScrollBar().value() == 0
    assert view.textCursor().selectedText() == 'History line 4'
    view.copy()
    assert QApplication.clipboard().text() == 'History line 4'


def test_following_the_bottom_still_follows_streamed_and_final_text(panel):
    panel._transcript.setPlainText('\n'.join(f'History {i}' for i in range(100)))
    panel._begin_turn()
    panel._reply_is_chat = True
    bar = panel._transcript.verticalScrollBar()
    bar.setValue(bar.maximum())
    for part in ['**more words**\n\n' * 4, 'last paragraph\n' * 4]:
        panel._on_chunk(part)
        panel._flush_reply_chunks()
    panel._status_stage('Checking the answer…')
    panel._on_done()
    settle()
    assert panel._at_bottom()


@pytest.mark.parametrize('completion', ['_on_cancelled', '_on_error'])
def test_stop_and_error_flush_queued_text_and_stop_the_timer(panel, completion):
    panel._on_chunk('Keep these final tokens')
    getattr(panel, completion)(*(['synthetic failure'] if completion == '_on_error' else []))
    assert 'Keep these final tokens' in panel._transcript.toPlainText()
    assert not panel._chunk_timer.isActive()
    panel.new_conversation()
    settle()
    assert 'Keep these final tokens' not in panel._transcript.toPlainText()


def test_plain_commands_are_never_interpreted_as_markdown(panel):
    panel._reply_is_chat = False
    panel._on_chunk('  <file> **literal**\n    indented')
    panel._flush_reply_chunks()
    panel._on_done()
    assert '<file> **literal**\n    indented' in panel._transcript.toPlainText()


def test_export_cache_only_exports_new_blocks_and_roundtrips_rich_text(panel, monkeypatch):
    import conversations
    panel._on_chunk(RICH)
    panel._on_done()
    first_html = panel._transcript_cache.capture()
    panel._begin_turn()
    panel._reply_is_chat = True
    panel._on_chunk('**Another message**\n\n```text\ncode\n```')
    panel._on_done()
    exported = []
    original = QTextDocumentFragment.toHtml

    def export(fragment):
        exported.append(fragment.toPlainText())
        return original(fragment)
    monkeypatch.setattr(QTextDocumentFragment, 'toHtml', export)
    html = panel._transcript_cache.capture()
    assert len(exported) == 1 and 'Another message' in exported[0]
    assert 'Local · test-model' not in exported[0]
    assert 'Local · test-model' in first_html
    reloaded = QTextDocument()
    reloaded.setHtml(html)
    assert reloaded.toPlainText() == panel._transcript.toPlainText()
    assert bold(reloaded, 'Another message')
    assert '<table' in html and '<pre' in html and 'cursiv://details/' in html
    conv_id = conversations.queue_save(None, [{'role': 'assistant', 'content': RICH}], html)
    conversations.wait_for_save(conv_id)
    assert conversations.load(conv_id)['html'] == html


def test_loaded_html_seeds_cache_and_older_edits_invalidate_it():
    doc = QTextDocument()
    doc.setMarkdown('**history**')
    cache = TranscriptCache(doc)
    cache.reset(doc.toHtml())
    cursor = QTextCursor(doc)
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertBlock()
    cursor.insertText('new')
    assert 'new' in cache.capture()
    doc.setHtml(doc.toHtml().replace('history', 'changed'))
    assert cache.html is None
    loaded = QTextDocument()
    loaded.setHtml(cache.capture())
    assert loaded.toPlainText() == doc.toPlainText()


def test_autosave_returns_before_disk_write_and_uses_no_gui_objects_in_worker(panel, monkeypatch):
    import chat_panel
    import conversations
    entered, release = threading.Event(), threading.Event()
    original = conversations._save
    calls = []

    def slow(*a, **kw):
        calls.append(threading.get_ident())
        entered.set()
        assert release.wait(5)
        return original(*a, **kw)
    monkeypatch.setattr(conversations, '_save', slow)
    monkeypatch.setattr(chat_panel, 'autosave_enabled', lambda: True)
    panel._on_chunk('**Persist this**')
    panel._pending_history_append = [('user', 'Question'), ('assistant', '**Persist this**')]
    panel._on_done()
    try:
        assert not panel._streaming and panel._send_btn.isEnabled()
        assert entered.wait(2) and len(calls) == 1
        assert calls[0] != threading.get_ident()
    finally:
        release.set()
    conversations.wait_for_save(panel._conv_id)
    settle()
    assert not panel._dirty
    saved = conversations.load(panel._conv_id)
    doc = QTextDocument()
    doc.setHtml(saved['html'])
    assert doc.toPlainText() == panel._transcript.toPlainText()
    assert saved['messages'] == panel._history


def test_queued_saves_and_manual_rename_preserve_the_latest_messages(panel):
    import conversations
    fragment = '<html><body><p>one</p></body></html>'
    first_messages = [{'role': 'user', 'content': 'first'}]
    conv_id = conversations.queue_save(None, first_messages, fragment)
    first_messages[0]['content'] = 'mutation after capture'
    conversations.queue_save(conv_id, [{'role': 'user', 'content': 'latest'}], fragment)
    conversations.rename(conv_id, 'My name')
    saved = conversations.load(conv_id)
    assert saved['messages'][0]['content'] == 'latest' and saved['title'] == 'My name'
    conversations.delete(conv_id)
    assert conversations.load(conv_id) is None


@pytest.mark.parametrize('renamed', [False, True])
def test_delayed_title_does_not_overwrite_newer_history_or_a_manual_name(panel, monkeypatch, renamed):
    import conversations
    from cursiv_engine.ui import chat_app as ca
    entered, release = threading.Event(), threading.Event()
    messages = [{'role': 'user', 'content': 'First subject'}]
    conv_id = conversations.save(None, messages, '<p>First</p>')

    def title(*a, **kw):
        entered.set()
        assert release.wait(5)
        return 'New Topic'
    monkeypatch.setattr(ca, '_quick_llm', title)
    worker = threading.Thread(target=panel._test_title, args=(conv_id, messages, None))
    worker.start()
    try:
        assert entered.wait(2)
        newer = messages + [{'role': 'assistant', 'content': 'Latest response'}]
        conversations.queue_save(conv_id, newer, '<p>Latest</p>')
        conversations.wait_for_save(conv_id)
        if renamed:
            conversations.rename(conv_id, 'My title')
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive()
    saved = conversations.load(conv_id)
    assert saved['messages'] == newer
    assert saved['title'] == ('My title' if renamed else 'New Topic')


def test_failed_autosave_is_visible_and_manual_save_can_retry(panel, monkeypatch):
    import conversations
    panel._history = [{'role': 'user', 'content': 'Do not lose this'}]
    original = conversations._save
    with monkeypatch.context() as patch:
        patch.setattr(conversations, '_save', lambda *a, **kw: (_ for _ in ()).throw(OSError('disk full')))
        panel.save_conversation(background=True)
        # The notification is queued to the GUI thread, including immediate failures.
        settle()
    assert panel._dirty
    assert 'could not be saved' in panel._status.text()
    assert panel.has_unsaved()
    panel.save_conversation()
    assert conversations.load(panel._conv_id)['messages'] == panel._history
    assert not panel._dirty and conversations._save is original


def test_status_distinguishes_answer_checking_from_rendering(panel, monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    monkeypatch.setattr(ca, '_router_llm', lambda *a, **kw: pytest.fail('Renderer called an AI'))
    panel._status_stage('Checking the answer…')
    panel._on_chunk('**Visible while checking**\n\n')
    panel._flush_reply_chunks()
    assert bold(panel._transcript.document(), 'Visible while checking')
    assert panel._status.text() == 'Checking the answer…'
    panel._on_done()
    assert panel._status.text() == ''


def test_last_paragraph_finishes_formatting_before_slow_checks_return(panel, monkeypatch):
    parses = []
    original = QTextCursor.insertMarkdown
    monkeypatch.setattr(QTextCursor, 'insertMarkdown',
                        lambda cursor, text, *a: (parses.append(text), original(cursor, text, *a))[1])
    panel._on_chunk('**Final token without a blank line**')
    panel._status_stage('Checking the answer…')
    assert bold(panel._transcript.document(), 'Final token without a blank line')
    assert panel._streaming
    panel._on_done()
    assert len(parses) == 1     # final done reuses the same rendered message


def test_notes_and_revisions_after_the_finished_draft_stay_in_one_message(panel):
    panel._on_chunk('**Original answer**')
    panel._status_stage('Checking the answer…')
    panel._on_chunk('\n\nA later check note.\n\n')
    panel._flush_reply_chunks()
    assert panel._transcript.toPlainText().count('Original answer') == 1
    panel._on_replace('**Corrected answer**\n\nA correction note.')
    panel._on_done()
    text = panel._transcript.toPlainText()
    assert 'Original answer' not in text and 'later check note' not in text
    assert text.count('Corrected answer') == 1 and 'A correction note.' in text


def test_theme_switch_mid_stream_preserves_formatting_and_saved_history(panel, monkeypatch, tmp_path):
    import theme
    from cursiv_engine.chat import keys
    monkeypatch.setattr(keys, 'KEYS_FILE', tmp_path / 'keys.json')
    start = theme.CURRENT
    try:
        panel._on_chunk('**Before theme change**\n\n')
        panel._flush_reply_chunks()
        panel._transcript_cache.capture()
        theme.switch_live('light' if start == 'dark' else 'dark')
        panel._on_chunk('**After theme change**\n\nTail')
        panel._flush_reply_chunks()
        panel._on_done()
        doc = panel._transcript.document()
        assert bold(doc, 'Before theme change') and bold(doc, 'After theme change')
        reloaded = QTextDocument()
        reloaded.setHtml(panel._transcript_cache.capture())
        assert reloaded.toPlainText() == doc.toPlainText()
    finally:
        theme.switch_live(start)


def test_images_flush_earlier_chunks_and_survive_cached_export(panel, tmp_path):
    from PyQt6.QtGui import QImage, QColor
    path = tmp_path / 'sample.png'
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.fill(QColor('green'))
    assert image.save(str(path))
    panel._reply_is_chat = False
    panel._on_chunk('Text before the image')
    panel._on_image(str(path))
    panel._on_done()
    html = panel._transcript_cache.capture()
    assert html.index('Text before the image') < html.index('data:image/png;base64,')
    reloaded = QTextDocument()
    reloaded.setHtml(html)
    assert reloaded.toPlainText() == panel._transcript.toPlainText()


def test_core_announces_the_post_generation_stage_without_a_formatting_call(monkeypatch):
    from cursiv_engine.ui import chat_app as ca
    from cursiv_engine.core import curiosity_engine
    from cursiv_engine.core import verify
    verify.reset_session()
    stages = []

    def stream(*args):
        reply = args[-1]
        reply.append('Hello there!')
        yield 'Hello there!'
        stages.append('last token')
    monkeypatch.setattr(ca, '_chat_stream', stream)
    monkeypatch.setattr(ca, '_WORKED', None)
    monkeypatch.setattr(ca, '_learn_later', lambda *a, **kw: None)
    monkeypatch.setattr(ca, '_router_llm', lambda *a, **kw: pytest.fail('Unnecessary AI call'))
    monkeypatch.setattr(curiosity_engine, 'notify', lambda *a: None)
    monkeypatch.setattr(curiosity_engine, 'suggestion', lambda *a: '')
    assert ''.join(ca.chat('hello', [], '', None, on_stage=stages.append)).startswith('Hello there!')
    assert stages == ['last token', 'Checking the answer…']


def test_full_verification_makes_at_most_three_post_answer_calls():
    """Optional full review has no separate ledger-only model round trip."""
    from cursiv_engine.core import verify
    verify.reset_session()
    ledger = 'Known: none\nInferred: none\nAssumed: none\nUnknown: none'
    outputs = iter(['The explanation is unclear.', 'Inspect the input.\n\n' + ledger, 'CLEAR'])
    seen = []

    def ask(messages):
        seen.append(messages[0]['content'])
        return next(outputs)
    try:
        outcome = verify.run_pass('Explain this Python function.', 'Check the function input.', ask=ask)
        assert outcome.clear and len(seen) == 3
        assert seen[0].startswith('You are a strict checker')
        assert seen[1].startswith('Rewrite the draft')
        assert seen[2].startswith('You are a strict checker')
    finally:
        verify.reset_session()
