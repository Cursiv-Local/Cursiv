"""Streaming Markdown boundaries and a message export cache. No model calls.

Only complete paragraphs outside fenced blocks are candidates for incremental
formatting. The unfinished tail stays plain text. A final message-only parse
resolves cross-paragraph constructs (reference links, lists and check details).
The buffer is pure text; TranscriptCache is used only on the GUI thread.
"""
from __future__ import annotations

import re

_FENCE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')


class MarkdownStream:
    def __init__(self):
        self.tail = ''
        self._scan = 0
        self._ready = 0
        self._fence = ''

    def push(self, text: str) -> None:
        self.tail += text
        while (end := self.tail.find('\n', self._scan)) >= 0:
            line = self.tail[self._scan:end].rstrip('\r')
            match = _FENCE.match(line)
            if match:
                marker, rest = match.groups()
                if not self._fence:
                    self._fence = marker
                elif marker[0] == self._fence[0] and len(marker) >= len(self._fence) and not rest.strip():
                    self._fence = ''
            if not line.strip() and not self._fence:
                self._ready = end + 1
            self._scan = end + 1

    def take_ready(self) -> str:
        ready = self.tail[:self._ready]
        self.tail = self.tail[self._ready:]
        self._scan -= self._ready
        self._ready = 0
        return ready


class TranscriptCache:
    """The Qt document caches display; this caches per-message disk exports.

    Any edit to older content (including a theme switch) invalidates the prefix.
    Loading a saved conversation seeds it directly from the existing HTML.
    """
    def __init__(self, document):
        self.document = document
        self.reset()
        document.contentsChange.connect(self._changed)

    def reset(self, html=None):
        self.html = html
        self.end = self.document.characterCount() - 1 if html is not None else 0

    def _changed(self, position, removed, added):
        if self.html is not None and position < self.end:
            self.reset()

    def capture(self):
        from PyQt6.QtGui import QTextCursor, QTextDocumentFragment
        end = self.document.characterCount() - 1
        if self.html is not None and end == self.end:
            return self.html
        if self.html is not None and self.document.characterAt(self.end) == '\u2029':
            cursor = QTextCursor(self.document)
            cursor.setPosition(self.end + 1)   # skip the previous last block's separator
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            delta = QTextDocumentFragment(cursor).toHtml()
            # Clipboard fragment markers would make Qt's HTML reader discard
            # everything before the appended message when the chat is reopened.
            delta = delta.replace('<!--StartFragment-->', '').replace('<!--EndFragment-->', '')
            body_start = delta.find('>', delta.lower().find('<body')) + 1
            body_end = delta.lower().rfind('</body>')
            prefix_end = self.html.lower().rfind('</body>')
            if prefix_end >= 0 and body_start > 0 and body_end >= body_start:
                self.html = self.html[:prefix_end] + delta[body_start:body_end] + self.html[prefix_end:]
            else:
                self.html = self.document.toHtml()
        else:
            # First save, or an older block changed. Rebuild the export once;
            # never replace or reparse the displayed document.
            self.html = self.document.toHtml()
        self.end = end
        return self.html
