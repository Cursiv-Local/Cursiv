"""Command result API shared by dispatch, providers and the Qt adapter.

TextResult is ready to display; receipt subclasses carry native backend
evidence. NotesResult requests a GUI view; StreamResult owns a generator
and optional completion callback. chat_commands re-exports these classes.
"""
from __future__ import annotations
from typing import Callable, Generator, Optional


class TextResult:
    """A complete, ready-to-show result -- no streaming."""
    def __init__(self, text: str, image_path: str = ""):
        self.text = text
        self.image_path = image_path   # set for image-generation/paste results


class NotebookResult(TextResult):
    """An application-owned notebook receipt, never an LLM's save claim."""
    def __init__(self, result):
        super().__init__(result.render())
        self.receipt = result.receipt()


class FileActionResult(TextResult):
    def __init__(self, result):
        super().__init__(result.render())
        self.receipts = [result.receipt()]


class MemoryResult(TextResult):
    def __init__(self, result):
        super().__init__(result.render())
        self.receipt = result.receipt()


class NotesResult(TextResult):
    """UI request; the chat panel opens/focuses the viewer on its GUI thread."""
    def __init__(self, category: str = '', query: str = ''):
        super().__init__('Opening saved notes…')
        self.category, self.query = category, query


class StreamResult:
    """An intro line shown immediately, then a generator streamed in."""
    def __init__(
        self,
        intro: str,
        generator: Generator[str, None, None],
        on_complete: Optional[Callable[[str], None]] = None,
    ):
        self.intro = intro
        self.generator = generator
        self.on_complete = on_complete
