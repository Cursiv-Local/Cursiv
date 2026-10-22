"""Command media.

Functions receive the explicit CommandRuntime services from the compatibility
facade. They never import that facade, widgets, or install replacement globals.
Runtime owns call overrides, configuration and per-turn execution records.
Provider calls retain their existing offline gate and authorization checks.
Entry points: _looks_like_text_to_json_request, list_training_entries, add_training_entry_json, delete_training_entry, _run_llm_once, text_to_training_entry, _cloudflare_image, _image_request_prompt, _ollama_vision_model, _vision_describe, image_to_training_entry, describe_photo, analyze_pasted_image, postal_compose, approve_write.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Generator, Optional
from command_results import TextResult, NotebookResult, FileActionResult, MemoryResult, NotesResult, StreamResult
from command_runtime import CommandRuntime

def _looks_like_text_to_json_request(runtime: CommandRuntime, text: str) -> bool:
    """Fuzzy match for phrases like 'translate my notes into JSON for
    training' -- order-independent keyword co-occurrence rather than a
    rigid phrase, since there's no one fixed way to ask for this."""
    t = text.lower()
    return "json" in t and "train" in t and any(v in t for v in runtime._TEXT2JSON_VERBS)

def list_training_entries(runtime: CommandRuntime) -> list[dict]:
    """Read every entry in the training JSONL. Each dict gets a '_line'
    key (its 0-based line number) so the caller can select/delete it."""
    if not runtime._TRAINING_JSONL.exists():
        return []
    entries = []
    for i, line in enumerate(runtime._TRAINING_JSONL.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            d = runtime.json.loads(line)
        except Exception:
            continue
        if isinstance(d, dict):
            d["_line"] = i
            entries.append(d)
    return entries

def add_training_entry_json(runtime: CommandRuntime, raw_json: str) -> tuple[bool, str]:
    """Validate and append a manually-pasted JSON object."""
    raw_json = raw_json.strip()
    if not raw_json:
        return False, "Paste a JSON object first."
    try:
        entry = runtime.json.loads(raw_json)
    except Exception as e:
        return False, f"Invalid JSON: {e}"
    if not isinstance(entry, dict):
        return False, 'JSON must be an object, e.g. {"prompt": "...", "response": "..."}'
    entry.setdefault("timestamp", runtime.datetime.now().isoformat())
    entry.setdefault("source", "manual")
    entry.setdefault("quality", 1.0)
    runtime._TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with runtime._TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(runtime.json.dumps(entry) + "\n")
    return True, "Added to training data."

def delete_training_entry(runtime: CommandRuntime, line_index: int) -> tuple[bool, str]:
    """Remove one entry by its line number in the JSONL file."""
    if not runtime._TRAINING_JSONL.exists():
        return False, "No training data file yet."
    lines = runtime._TRAINING_JSONL.read_text(encoding="utf-8").splitlines()
    if not (0 <= line_index < len(lines)):
        return False, "Entry not found — the list may be out of date."
    del lines[line_index]
    runtime._TRAINING_JSONL.write_text(
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )
    return True, "Deleted."

def _run_llm_once(runtime: CommandRuntime, messages: list[dict], cfg: dict) -> str:
    """Collect one full (non-streaming) response, offline-first: Ollama
    before any cloud provider, matching Cursiv's always-works-air-gapped
    default -- cloud keys are only ever a fallback, never a requirement."""
    try:
        text = "".join(c for c in runtime._call_ollama(messages) if c and c != runtime.RATE_SENTINEL)
        if text.strip():
            return text
    except Exception:
        pass
    xai_key = cfg.get("api_key", "")
    if xai_key:
        try:
            text = "".join(c for c in runtime._call_xai_stream(messages, xai_key) if c and c != runtime.RATE_SENTINEL)
            if text.strip():
                return text
        except Exception:
            pass
    ant_key = cfg.get("anthropic_key", "")
    if ant_key:
        try:
            text = "".join(c for c in runtime._call_claude_direct(messages, ant_key) if c and c != runtime.RATE_SENTINEL)
            if text.strip():
                return text
        except Exception:
            pass
    oai_key = cfg.get("openai_key", "")
    if oai_key:
        try:
            text = "".join(c for c in runtime._call_openai_direct(messages, oai_key) if c and c != runtime.RATE_SENTINEL)
            if text.strip():
                return text
        except Exception:
            pass
    return ""

def text_to_training_entry(runtime: CommandRuntime, notes: str, cfg: dict) -> tuple[bool, str, Optional[dict]]:
    """Ask whatever model is available to turn free-form notes into a
    structured {prompt, response} JSON training example."""
    notes = notes.strip()
    if not notes:
        return False, "No notes to translate.", None

    sys_prompt = (
        "Convert the user's notes into a single JSON object with exactly two "
        'keys: "prompt" (a plausible question or instruction these notes '
        'would answer) and "response" (the notes, cleaned up, with all '
        "information preserved — do not drop or invent facts). Return ONLY "
        "the JSON object: no markdown fences, no extra commentary."
    )
    raw = runtime._run_llm_once(
        [{"role": "system", "content": sys_prompt}, {"role": "user", "content": notes}], cfg
    )
    if not raw.strip():
        return False, ("No model available to translate notes — start Ollama, "
                        "or set a cloud API key."), None

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    try:
        parsed = runtime.json.loads(cleaned)
    except Exception:
        parsed = None

    if isinstance(parsed, dict) and parsed.get("response"):
        entry = {
            "prompt":    str(parsed.get("prompt", "Notes")),
            "response":  str(parsed["response"]),
            "quality":   1.0,
            "agent_id":  "text_to_json",
            "timestamp": runtime.datetime.now().isoformat(),
            "source":    "text_to_json",
        }
    else:
        # Model didn't return clean JSON -- store the raw notes rather
        # than silently losing them.
        entry = {
            "prompt":    "Notes",
            "response":  notes,
            "quality":   1.0,
            "agent_id":  "text_to_json",
            "timestamp": runtime.datetime.now().isoformat(),
            "source":    "text_to_json_fallback",
        }

    runtime._TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with runtime._TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(runtime.json.dumps(entry) + "\n")
    return True, "Notes translated and added to training data.", entry

def _cloudflare_image(runtime: CommandRuntime, prompt: str, account_id: str, token: str) -> bytes:
    import base64 as _b64cf
    import urllib.request
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{runtime.CF_IMAGE_MODEL}"
    req = urllib.request.Request(
        url, data=runtime.json.dumps({"prompt": prompt, "steps": 4}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = runtime.json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore")[:200]
        if e.code == 429 or "neuron" in detail.lower():
            raise RuntimeError("Cloudflare's free daily image allowance is used up — it resets at midnight UTC.")
        raise RuntimeError(f"Cloudflare {e.code}: {detail}")
    img = (data.get("result") or {}).get("image")
    if not img:
        raise RuntimeError(f"Cloudflare returned no image: {str(data.get('errors'))[:200]}")
    return _b64cf.b64decode(img)

def _image_request_prompt(runtime: CommandRuntime, text: str) -> Optional[str]:
    """'image <prompt>' or a plain-English ask like 'make me a picture of a
    dog' -> the prompt ('' if the command had none). None if not an image ask."""
    t = text.strip()
    if t.lower() == "image":
        return ""
    if t.lower().startswith("image "):
        return t[6:].strip()
    # Whole sentence, not just the tail: "a logo for my bakery" needs "logo".
    return t.rstrip("?.!") if runtime._IMAGE_ASK_RE.match(t) else None

def _ollama_vision_model(runtime: CommandRuntime) -> str:
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as r:
            names = [m.get("name", "") for m in runtime.json.loads(r.read()).get("models", [])]
    except Exception:
        return ""
    for family in runtime.OLLAMA_VISION_MODELS:
        for n in names:
            if n.split(":")[0] == family:
                return n
    return ""

def _vision_describe(runtime: CommandRuntime, img_b64: str, mime: str, prompt_text: str, cfg: dict) -> tuple[str, str]:
    import urllib.request
    from cursiv_v215.ui.chat_app import _saved_key, GEMINI_URL, GEMINI_MODELS
    # Local first (a photo stays on this computer when the image model is installed);
    # online keys only when nothing local can read it and the internet isn't blocked.
    model = runtime._ollama_vision_model()
    if model:
        try:
            body = runtime.json.dumps({"model": model, "prompt": prompt_text,
                               "images": [img_b64], "stream": False}).encode()
            req = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                text = runtime.json.loads(r.read()).get("response", "")
            if text.strip():
                return text, f"{model} (local)"
        except Exception:
            pass
    try:
        from cursiv_v215.core import netgate as _ng
        if not _ng.allowed():
            return "", ""
    except Exception:
        return "", ""
    ant_key, oai_key = cfg.get("anthropic_key", ""), cfg.get("openai_key", "")
    gem_key = cfg.get("gemini_key", "") or _saved_key("gemini_key")

    if ant_key:
        try:
            import anthropic as _anth_v
            resp = _anth_v.Anthropic(api_key=ant_key).messages.create(
                model="claude-sonnet-4-6", max_tokens=600,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime, "data": img_b64}},
                    {"type": "text", "text": prompt_text},
                ]}],
            )
            return resp.content[0].text, "Claude"
        except Exception:
            pass

    if oai_key:
        try:
            import openai as _oai_v
            resp2 = _oai_v.OpenAI(api_key=oai_key).chat.completions.create(
                model="gpt-4o", max_tokens=600,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text", "text": prompt_text},
                ]}],
            )
            return resp2.choices[0].message.content, "GPT-4o"
        except Exception:
            pass

    if gem_key:
        body = runtime.json.dumps({"contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": mime, "data": img_b64}},
            {"text": prompt_text},
        ]}]}).encode()
        for model in GEMINI_MODELS:
            try:
                req = urllib.request.Request(
                    GEMINI_URL.format(model=model), data=body,
                    headers={"Content-Type": "application/json", "x-goog-api-key": gem_key})
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = runtime.json.loads(r.read())
                cand = (data.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                if text.strip():
                    return text, "Gemini"
            except Exception:
                continue

    return "", ""

def image_to_training_entry(runtime: CommandRuntime, image_bytes: bytes, cfg: dict, ext: str) -> tuple[bool, str, Optional[dict]]:
    """Run vision analysis on an uploaded image and store the description
    as a JSON training example. Mirrors analyze_pasted_image's vision call
    but writes to the training store instead of strand memory."""
    from cursiv_v215.core import atomic
    img_dir = runtime._image_folder(cfg)
    img_path = img_dir / f"train_{runtime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.{ext}"
    atomic.write_bytes(img_path, image_bytes)

    import base64 as _b64t
    img_b64 = _b64t.b64encode(image_bytes).decode()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "gif": "image/gif", "webp": "image/webp"}.get(ext.lower(), "image/png")
    prompt_text = ("Describe this image in detail — objects, text, layout, and anything "
                   "notable — as a single clear paragraph suitable for training data.")

    vision_result, vision_provider = runtime._vision_describe(img_b64, mime, prompt_text, cfg)
    if not vision_result:
        return False, runtime._NO_VISION_HELP, None

    entry = {
        "prompt":     prompt_text,
        "response":   vision_result,
        "quality":    1.0,
        "agent_id":   "image_upload",
        "timestamp":  runtime.datetime.now().isoformat(),
        "source":     "image_upload",
        "image_path": str(img_path),
    }
    runtime._TRAINING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with runtime._TRAINING_JSONL.open("a", encoding="utf-8") as f:
        f.write(runtime.json.dumps(entry) + "\n")
    return True, f"Image analyzed via {vision_provider} and added to training data.", entry

def describe_photo(runtime: CommandRuntime, path: str, question: str, cfg: dict) -> TextResult:
    """Ask the image model about a photo. Local model first; the answer says where it was read."""
    import base64 as _b64p
    import io
    p = runtime.Path(path)
    if not p.is_file():
        return runtime.TextResult(f"No photo at {p}.")
    try:
        from PIL import Image
        with Image.open(p) as img:                      # smaller is much faster, and enough to read
            img = img.convert("RGB")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO(); img.save(buf, "JPEG", quality=88)
        data, mime = buf.getvalue(), "image/jpeg"
    except Exception:
        data, mime = p.read_bytes(), "image/jpeg"
    q = question.strip() or "Describe what this photo shows, as an observer in the field would: what, where, condition."
    prompt = (q + "\n\nSay only what is visible in the photo. If something can't be told from the photo "
              "(species, exact size, chemistry), say so instead of guessing.")
    text, provider = runtime._vision_describe(_b64p.b64encode(data).decode(), mime, prompt, cfg)
    if not text:
        try:
            from cursiv_v215.core import netgate as _ng
            offline = not _ng.allowed()
        except Exception:
            offline = True
        return runtime.TextResult(runtime._NO_LOCAL_VISION if offline or not runtime._ollama_vision_model() else runtime._NO_VISION_HELP)
    local = provider.endswith("(local)")
    where = (f"read by {provider[:-8]} on this computer" if local
             else f"sent to {provider} online: this photo left this computer")
    return runtime.TextResult(f"{text.strip()}\n\n*[Sources: your photo ({p.name}), {where}. The AI's reading of a photo can "
                      f"be wrong; check anything that matters.]*", image_path=str(p))

def analyze_pasted_image(runtime: CommandRuntime, png_bytes: bytes, cfg: dict, width: int, height: int) -> TextResult:
    import base64 as _b64img

    from cursiv_v215.core import atomic
    import uuid
    img_dir = runtime._image_folder(cfg)
    img_path = img_dir / f"paste_{runtime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.png"
    atomic.write_bytes(img_path, png_bytes)

    img_b64 = _b64img.b64encode(png_bytes).decode()
    vision_result, vision_provider = runtime._vision_describe(
        img_b64, "image/png",
        "Describe what you see in this image. Be specific and useful. "
        "Flag anything relevant to code, design, architecture, or ongoing work.", cfg)

    if runtime._STRAND_OK:
        body = vision_result or f"Image pasted: {img_path} ({width}x{height}px)"
        runtime._strand_save(f"paste: image {img_path.stem}", body, tags=["image", "paste", "vision"],
                     score=0.72, territory_tag="worldmodel", source="paste", model=vision_provider or "none")

    header = f"Image pasted — {width}×{height}px\n\n"
    if vision_result:
        return runtime.TextResult(f"{header}Vision analysis (via {vision_provider}):\n\n{vision_result}", image_path=str(img_path))
    return runtime.TextResult(f"{header}Image saved, no analysis. {runtime._NO_VISION_HELP}", image_path=str(img_path))

def postal_compose(runtime: CommandRuntime, sender_user: str, recipient_raw: str, hint: str, content: str) -> TextResult:
    if not runtime._POSTAL_OK:
        return runtime.TextResult("Postal module unavailable.")
    if not content.strip():
        return runtime.TextResult("Nothing written — letter not sent.")
    resolved = runtime._postal_resolve(recipient_raw)
    recipient_key = resolved[1] if resolved else recipient_raw.lower().replace(" ", "")
    recipient_disp = resolved[0] if resolved else recipient_raw.title()
    my_id = runtime._postal_my_id()
    sender_key = my_id.get("name", sender_user).lower() if my_id else sender_user
    sender_disp = my_id.get("name", sender_user).title() if my_id else sender_user.title()
    lid = runtime._postal_seal(
        sender_key=sender_key, sender_display=sender_disp,
        recipient_key=recipient_key, recipient_display=recipient_disp,
        content=content, hint=hint,
    )
    return runtime.TextResult(
        f"Sealed\nid: {lid}\nfor: {recipient_disp}\n"
        f"signed: {'yes — Ed25519' if my_id else 'no — run postal setup first'}\n"
        f"readable: on this machine only"
    )

def approve_write(runtime: CommandRuntime, path: str, content: str, workspace: str, *, operation: str, expected_sha256: str | None, remember: bool) -> TextResult:
    from cursiv_v215.core import file_access
    args = {'path': path, 'content': content}
    if expected_sha256 is not None:
        args['expected_sha256'] = expected_sha256
    from cursiv_v215.ui.chat_app import _file_tool_result
    receipt = _file_tool_result(operation, args, workspace, confirmed=True)
    result = runtime.FileActionResult(receipt)
    if remember:
        result.text += '\nConversational memory: ' + file_access.save_memory(content)
    return result
