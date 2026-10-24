"""ChatTranscriptMixin: focused ChatPanel view methods.

Only the GUI thread calls these methods; background results arrive through
the panel signals. The host supplies transcript/widgets/config and callbacks.
No model, filesystem authorization or conversation-storage policy lives here.
"""
from __future__ import annotations
import threading
from pathlib import Path
import re as _re
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QComboBox, QMenu, QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QPlainTextEdit,
    QPushButton, QLabel, QSizePolicy,
)
from theme import BG, BG2, BORDER, GOLD, LGOLD, SILVER, SILV2
import theme
from chat_rendering import MarkdownStream, style_code


class ChatTranscriptMixin:
    # Replies are Markdown, not trusted HTML. Literal <file>/<folder> otherwise
    # become open HTML elements and can swallow the rest of an instruction.
    _MARKDOWN = (QTextDocument.MarkdownFeature.MarkdownDialectGitHub |
                 QTextDocument.MarkdownFeature.MarkdownNoHTML)
    _STATUS_LINE = _re.compile(r"^\s*\*([\[(])(.*)[\])]\*\s*$")

    _LEDGER_LINE = _re.compile(r"^[\s>*_-]*(Known|Inferred|Assumed|Unknown)[*_]*\s*:", _re.I)

    @classmethod
    def split_details(cls, body: list[str]) -> tuple[list[str], str]:
        """The answer, and what goes behind "Show reasoning and checks": the
        Known / Inferred / Assumed / Unknown lines and the check's notes. The
        answer and the reference card stay in view."""
        main, details = [], []
        notes_at = next((i for i, ln in enumerate(body)
                         if ln.strip().startswith("**Checked, with notes**")), None)
        if notes_at is not None:
            details.extend(ln for ln in body[notes_at:] if ln.strip())
            body = body[:notes_at]
            while body and body[-1].strip() in ("", "---"):
                body = body[:-1]
        ledger: list[str] = []
        try:
            # The same reader the check uses: "✅ Known:" and items on the lines below count too.
            from cursiv_engine.core import verify
            text = "\n".join(body)
            found = verify._ledger_span(text)
            if found:
                start, end, parts = found
                ledger = [f"{k}: {parts[k] or 'none'}" for k in ("Known", "Inferred", "Assumed", "Unknown")]
                body = (text[:start].rstrip() + "\n" + text[end:]).split("\n")
        except Exception:
            pass
        if not ledger:
            ledger = [ln.replace("**", "").strip().strip("*_-> ") for ln in body if cls._LEDGER_LINE.match(ln)]
            body = [ln for ln in body if not cls._LEDGER_LINE.match(ln)]
        main = list(body)
        while main and main[-1].strip() in ("", "---"):
            main.pop()
        if ledger:
            details = ["**What this answer is based on**", *("- " + ln for ln in ledger)] + (
                [""] + details if details else [])
        return main, "\n".join(details)

    def _chip_html(self, inner: str) -> str:
        """One of Cursiv's own status lines, as a small line under (or above) the answer."""
        esc = self._escape(inner)
        if inner.startswith("Answered by "):
            engine = inner[len("Answered by "):]
            local = engine.startswith(("Ollama", "Code Council", "Cursiv local"))
            col = theme.GREEN if local else theme.AMBER
            label = ("Local · " + self._escape(engine.split("·", 1)[-1].strip())) if local else ("Online · " + self._escape(engine))
            return f'<p style="margin:6px 0 0 0; font-size:12px; color:{col};">● {label}</p>'
        if inner.startswith("Cursiv's check:"):
            return f'<p style="margin:8px 0 0 0; font-size:13px; color:{theme.AMBER};">⚠ {esc}</p>'
        if inner.startswith("From Cursiv's offline reference"):
            urgent = "[medical/" in inner or "[survival/" in inner
            style = (f"font-size:13px; color:{theme.TEXT};" if urgent else f"font-size:12px; color:{theme.MUTED};")
            return (f'<table width="100%" cellpadding="10" cellspacing="0" style="margin:2px 0 10px 0;'
                    f' background-color:{theme.SURFACE2}; border:1px solid {theme.BORDER};"><tr><td>'
                    f'<span style="{style}">{esc}</span></td></tr></table>')
        return f'<p style="margin:4px 0; font-size:12px; color:{theme.MUTED};">{esc}</p>'

    @staticmethod
    def _keep_line_breaks(md: str) -> str:
        """In Markdown a single newline joins lines; the model's single newlines
        (Known: / Inferred: lines, addresses, short steps) are meant as line breaks."""
        out, fence, under_item = [], '', False
        lines = md.split("\n")
        item = _re.compile(r"\s*([-*+]|\d+[.)])\s")
        for i, line in enumerate(lines):
            marker = _re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
            if marker:
                run, rest = marker.groups()
                if not fence:
                    fence = run
                elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                    fence = ''
                out.append(line)
                continue
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if fence or not line.strip():
                under_item = False if not line.strip() else under_item
                out.append(line)
                continue
            if item.match(line):
                under_item = False
                if nxt.strip() and not _re.match(r"\s*([-*+]|\d+[.)]|#|>|\|)", nxt):
                    # "1. Step\nWhat to do" — Qt numbers a line break inside an item as a new
                    # item (4 steps showed as 7), so the text under it becomes its own
                    # indented paragraph.
                    out += [line, ""]
                    under_item = True
                    continue
                out.append(line)
                continue
            if under_item:
                line = "   " + line.lstrip()
            if nxt.strip() and not line.endswith("  ") and not _re.match(r"\s*([-*+]|\d+[.)]|#|>|\|)", nxt):
                line += "  "
            out.append(line)
        return "\n".join(out)

    def _render_reply(self) -> None:
        """Swap the plain streamed text of a finished chat answer for rendered Markdown,
        with Cursiv's status lines as small chips. Only for chat answers: command output
        (help, status) keeps its plain, aligned text."""
        text = self._reply_text or ""
        start = getattr(self, "_reply_start", None)
        if start is None or not text.strip():
            return
        document = self._transcript.document()
        key = (text, theme.CURRENT, document.revision())
        if self._render_cache == key:
            return                    # the live document is the cache for completed messages
        at_bottom = self._at_bottom()
        scroll = self._transcript.verticalScrollBar().value()
        top, body, bottom, extra_details = [], [], [], []
        fence = ''
        for line in text.splitlines():
            marker = _re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
            if marker:
                run, rest = marker.groups()
                if not fence:
                    fence = run
                elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                    fence = ''
                body.append(line)
                continue
            if fence or line.startswith(('    ', '\t')):
                body.append(line)
                continue
            if line.startswith('This turn: ') and line.endswith('Conversation history still follows your chat-history settings.'):
                # A badge shows current limits; retain the full historical note
                # on demand instead of repeating a paragraph under every answer.
                extra_details.append(line)
                continue
            m = self._STATUS_LINE.match(line)
            if m:
                inner = m.group(2)
                if (inner == 'Source: model knowledge (not checked against a source)' or
                        inner.startswith('Sources: saved memory context supplied (use by the model is not established)')):
                    extra_details.append(inner)
                else:
                    (top if not body else bottom).append(inner)
            else:
                body.append(line)
        body, details = self.split_details(body)
        details = '\n\n'.join(part for part in (details, *extra_details) if part)
        md = self._keep_line_breaks("\n".join(body).strip())
        cursor = QTextCursor(self._transcript.document())
        cursor.beginEditBlock()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        for inner in top:
            cursor.insertHtml(theme.live(self._chip_html(inner)))
        if md:
            if top:
                cursor.insertBlock()
            markdown_start = cursor.position()
            cursor.insertMarkdown(md, self._MARKDOWN)
            style_code(document, markdown_start, cursor.position())
        if details:
            from urllib.parse import quote
            self._plain_block(cursor)
            cursor.insertHtml(f'<p style="margin:6px 0 0 0; font-size:12px;"><a href="cursiv://details/'
                              f'{quote(details)}" style="color:{theme.MUTED};">Show reasoning and checks</a></p>')
        for inner in bottom:
            self._plain_block(cursor)
            cursor.insertHtml(theme.live(self._chip_html(inner)))
        self._plain_block(cursor)               # the next turn starts outside any list
        cursor.endEditBlock()
        self._render_cache = (text, theme.CURRENT, document.revision())
        bar = self._transcript.verticalScrollBar()
        bar.setValue(bar.maximum() if at_bottom else scroll)

    @staticmethod
    def _plain_block(cursor: QTextCursor) -> None:
        """A new block that isn't part of the list an answer may end with. Qt carries the
        list on, so the "Local" line became item 5 and the next "You" was indented."""
        cursor.insertBlock(QTextBlockFormat(), QTextCharFormat())
        lst = cursor.currentList()
        if lst is not None:
            lst.remove(cursor.block())
        fmt = cursor.blockFormat()
        fmt.setIndent(0)
        cursor.setBlockFormat(fmt)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    def _force_new_block(self) -> None:
        # A fresh <p>...</p> fragment inserted via insertHtml() doesn't
        # reliably start a new QTextBlock when appended after existing
        # content -- Qt's rich text engine can merge it into the previous
        # block with a   line-separator standing in for the paragraph
        # break, which renders as glued onto the end of the last line
        # instead of a proper new block with its own margin. Every method
        # below that starts a new visual turn (system message, "You", a
        # fresh AI reply) calls this first; Qt's actual document-structure
        # API (insertBlock) doesn't have that ambiguity the way inserted
        # HTML fragments do.
        if self._transcript.document().isEmpty():
            return
        cursor = self._transcript.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertBlock()
        self._transcript.setTextCursor(cursor)

    def _append_html_block(self, html: str) -> None:
        self._transcript.moveCursor(QTextCursor.MoveOperation.End)
        self._transcript.insertHtml(theme.live(html))
        self._transcript.moveCursor(QTextCursor.MoveOperation.End)

    def _append_system(self, text: str) -> None:
        self._force_new_block()
        self._append_html_block(
            f'<p style="color:{SILV2}; font-size:12px; margin:4px 0 12px 0;">{self._escape(text)}</p>'
        )

    def _append_user(self, text: str) -> None:
        self._force_new_block()
        self._append_html_block(
            f'<p style="margin:10px 0 4px 0;">'
            f'<span style="color:{theme.MUTED}; font-weight:600;">You</span><br>'
            f'<span style="color:{SILVER};">{self._keep_shape(text)}</span></p>'
        )

    @classmethod
    def _keep_shape(cls, text: str) -> str:
        """Escaped text that keeps its line breaks, indents and spacing, so a pasted
        list or table doesn't run together into one paragraph."""
        out = cls._escape(text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    "))
        out = out.replace("  ", "&nbsp; ")
        return out.replace("\n", "<br>")

    def _begin_ai_reply(self) -> None:
        # Insert the reply heading and remember where its body begins. Qt closes
        # each HTML fragment immediately; there is no open tag state to maintain.
        self._force_new_block()
        self._append_html_block(
            f'<p style="margin:4px 0 4px 0;">'
            f'<span style="color:{theme.ACCENT}; font-weight:600;">Cursiv</span><br>'
            f'<span style="color:{theme.TEXT}; white-space:pre-wrap;">'
        )
        cursor = QTextCursor(self._transcript.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._reply_start = cursor.position()
        self._stream_tail_start = self._reply_start
        self._render_cache = None

    def _at_bottom(self) -> bool:
        sb = self._transcript.verticalScrollBar()
        return sb.value() >= sb.maximum() - 4

    def _append_reply_chunk(self, chunk: str) -> None:
        # Streamed chunks come from the model, not markup -- insert as plain
        # text so partial HTML never lands mid-tag. Insert through a cursor
        # tied to the document, not the widget's own moveCursor/textCursor,
        # so a user who scrolled up mid-generation to reread earlier text
        # doesn't get yanked back to the bottom on every chunk -- only
        # auto-follow if they were already at the bottom.
        at_bottom = self._at_bottom()
        cursor = QTextCursor(self._transcript.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        if at_bottom:
            self._transcript.verticalScrollBar().setValue(self._transcript.verticalScrollBar().maximum())

    def _end_ai_reply(self) -> None:
        # Qt parses insertHtml fragments immediately; there are no open HTML
        # tags to close here. Moving the widget cursor would steal scroll/selection.
        self._chunk_timer.stop()

    def _reset_rendering(self) -> None:
        self._chunk_timer.stop()
        self._pending_chunks.clear()
        self._markdown_stream = MarkdownStream()
        self._render_cache = None

    def _flush_reply_chunks(self, *, format_blocks: bool = True) -> None:
        if not self._pending_chunks:
            self._chunk_timer.stop()
            return
        chunk = ''.join(self._pending_chunks)
        self._pending_chunks.clear()
        if not self._reply_is_chat or not format_blocks:
            self._append_reply_chunk(chunk)
            return
        stream = self._markdown_stream
        stream.push(chunk)
        ready = stream.take_ready()
        if not ready.strip():
            self._append_reply_chunk(chunk)
            return
        at_bottom = self._at_bottom()
        bar = self._transcript.verticalScrollBar()
        scroll = bar.value()
        cursor = QTextCursor(self._transcript.document())
        cursor.setPosition(self._stream_tail_start)
        cursor.movePosition(QTextCursor.MoveOperation.End, QTextCursor.MoveMode.KeepAnchor)
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        markdown_start = cursor.position()
        cursor.insertMarkdown(self._keep_line_breaks(ready.strip()), self._MARKDOWN)
        style_code(self._transcript.document(), markdown_start, cursor.position())
        self._plain_block(cursor)
        self._stream_tail_start = cursor.position()
        cursor.insertText(stream.tail)        # unfinished fences/tables stay literal and intact
        cursor.endEditBlock()
        bar.setValue(bar.maximum() if at_bottom else scroll)

    def _append_image(self, path: str) -> None:
        import base64
        try:
            data = Path(path).read_bytes()
        except Exception:
            return
        b64 = base64.b64encode(data).decode()
        ext = Path(path).suffix.lstrip(".").lower() or "png"
        self._append_html_block(
            f'<p style="margin:4px 0 12px 0;">'
            f'<img src="data:image/{ext};base64,{b64}" style="max-width:480px; border-radius:8px;" />'
            f'</p>'
        )
