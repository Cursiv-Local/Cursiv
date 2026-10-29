"""Shared command API: result types, runtime protocol and dispatch sentinel.

The desktop compatibility facade re-exports result classes. Ordered command
handlers consume this widget-free interface; model text cannot create receipts.
"""
from __future__ import annotations
from typing import Any, Callable, Generator, Optional, Protocol


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
        self.save_preview = result.save_preview
        self.update_preview = result.update_preview


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
        run=None,
    ):
        self.intro = intro
        self.generator = generator
        self.on_complete = on_complete
        self.run = run


class CommandRuntime(Protocol):
    CF_IMAGE_MODEL: Any
    FileActionResult: Any
    IMAGE_GEN_CLOUDFLARE_HOWTO: Any
    IMAGE_GEN_MODELS: Any
    IMAGE_GEN_NEEDS_KEY: Any
    MemoryResult: Any
    NotebookResult: Any
    NotesResult: Any
    OLLAMA_VISION_MODELS: Any
    Path: Any
    RATE_SENTINEL: Any
    StreamResult: Any
    TextResult: Any
    _ANSI_RE: Any
    _BABEL_DEFAULT_SET: Any
    _BABEL_MANY: Any
    _BABEL_OK: Any
    _BUILDER_TOPICS: Any
    _CHAT_ROOT: Any
    _CODEX_HELP: Any
    _FIELD_HELP_TEXT: Any
    _HELP_TEXT: Any
    _HELP_TOPICS: Any
    _HERMES_OK: Any
    _IMAGE_ASK_RE: Any
    _LANG_NAMES: Any
    _LAST_CODEX: Any
    _NO_LOCAL_VISION: Any
    _NO_VISION_HELP: Any
    _PACK_EXT: Any
    _PERSONAL_TOPICS: Any
    _PHOTO_CMD: Any
    _QUEUE_OK: Any
    _REF_OK: Any
    _RETIRED: Any
    _SFED_OK: Any
    _STRAND_OK: Any
    _TEXT2JSON_VERBS: Any
    _TRAINING_JSONL: Any
    _VOICE_CLEAN_SYS: Any
    _VOICE_OK: Any
    _agent_command: Any
    _babel_decode: Any
    _babel_encode: Any
    _babel_input: Any
    _babel_source: Any
    _babel_targets: Any
    _call_claude_direct: Any
    _call_ollama: Any
    _call_ollama_code_council: Any
    _call_openai_direct: Any
    _call_xai_stream: Any
    _cascade_gen: Any
    _cascade_stream: Any
    _chat: Any
    _cloudflare_image: Any
    _codex_command: Any
    _free_key_command: Any
    _gate: Any
    _hermes_avail: Any
    _hermes_run: Any
    _image_folder: Any
    _image_request_prompt: Any
    _is_builder: Any
    _looks_like_text_to_json_request: Any
    _notes_view_request: Any
    _obs_export: Any
    _obs_save_config: Any
    _ollama_vision_model: Any
    _personal: Any
    _probe_claude: Any
    _probe_openai: Any
    _probe_xai: Any
    _queue_enqueue: Any
    _queue_format: Any
    _ref_answer: Any
    _ref_avail: Any
    _run_llm_once: Any
    _save_key: Any
    _session_append: Any
    _sfed_export: Any
    _sfed_import: Any
    _sfed_summary: Any
    _strand_count: Any
    _strand_fmt: Any
    _strand_list: Any
    _strand_save: Any
    _strand_search: Any
    _strand_terr_counts: Any
    _strand_territories: Any
    _vision_describe: Any
    _voice_avail: Any
    _voice_record: Any
    _voice_transcribe: Any
    _web_search: Any
    datetime: Any
    describe_photo: Any
    help_text: Any
    json: Any
    memory_command: Any
    notebook_command: Any
    re: Any
    text_to_training_entry: Any


# Distinguishes an unknown command from an intentional return to chat.
UNHANDLED = object()
