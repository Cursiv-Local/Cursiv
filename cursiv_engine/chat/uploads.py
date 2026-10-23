"""Chat uploads.

Functions receive the explicit ChatRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _read_text_file, process_uploaded_files.
"""
from __future__ import annotations

from typing import Callable, Generator
from pathlib import Path
from .runtime import ChatRuntime

def _read_text_file(runtime: ChatRuntime, path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Could not read {path.name}: {e}]"

def process_uploaded_files(runtime: ChatRuntime, files: list | None) -> tuple[str, list[dict]]:
    """
    Returns (text_context, image_parts).
    text_context: injected into system prompt.
    image_parts: list of xAI image_url dicts for vision calls.
    """
    if not files:
        return "", []

    text_chunks  = []
    image_parts  = []
    text_exts    = {".txt", ".md", ".py", ".js", ".ts", ".html", ".css",
                    ".json", ".yaml", ".yml", ".csv", ".xml", ".toml", ".bat", ".sh"}
    image_exts   = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

    for f in files:
        p = runtime.Path(f if isinstance(f, str) else f.name)

        if p.suffix.lower() in image_exts:
            try:
                raw     = p.read_bytes()
                b64     = runtime.base64.b64encode(raw).decode()
                mime    = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                           ".png": "image/png",  ".gif":  "image/gif",
                           ".webp": "image/webp"}.get(p.suffix.lower(), "image/png")
                image_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                })
                text_chunks.append(f"[Image uploaded: {p.name}]")
            except Exception as e:
                text_chunks.append(f"[Image {p.name} could not be processed: {e}]")

        elif p.suffix.lower() in text_exts:
            content = runtime._read_text_file(p)
            cap     = 8000
            if len(content) > cap:
                content = content[:cap] + f"\n... [truncated at {cap} chars]"
            text_chunks.append(f"\n### Uploaded file: {p.name}\n```\n{content}\n```")

        elif p.suffix.lower() == ".pdf":
            text_chunks.append(
                f"[PDF uploaded: {p.name} — PDF parsing not installed. "
                "Install pypdf and I can extract the text automatically.]"
            )
        else:
            try:
                content = runtime._read_text_file(p)[:4000]
                text_chunks.append(f"\n### Uploaded file: {p.name}\n```\n{content}\n```")
            except Exception:
                text_chunks.append(f"[File uploaded: {p.name} — binary, cannot display as text]")

    return "\n".join(text_chunks), image_parts
