"""
Voice Agent — two-stage local pipeline.  No cloud at any step.

  Stage 1 (STT):   mic → PCM → faster-whisper → raw transcript
  Stage 2 (Clean): raw text → Babel binary encode → LLM → clean English

Stage 2 reuses the existing Babel binary system:
  - Non-English speech → full translation to English
  - English speech → filler-word removal, transcription error correction
  - The binary encoding forces careful character-level re-reading by the LLM

STT backend cascade (first available wins):
  1. faster-whisper   — best quality, CPU int8, multilingual, ~466 MB small model
  2. Vosk             — good offline, ~40 MB model
  3. SpeechRecognition + pocketsphinx — zero download, low quality last resort

Install for full pipeline:
  pip install faster-whisper sounddevice
"""
from __future__ import annotations

import io
import json
import tempfile
import urllib.request
import wave
from pathlib import Path
from cursiv_engine.core.paths import APP_DATA   # where program data lives (core/paths.py)

# ── Paths ─────────────────────────────────────────────────────────────────────
_ROOT      = Path(__file__).parent.parent.parent
_VOICE_DIR = APP_DATA / "voice"
SAMPLE_RATE = 16_000   # all backends expect 16 kHz mono

# Vosk small-en model (fallback)
_VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
_VOSK_MODEL_URL  = f"https://alphacephei.com/vosk/models/{_VOSK_MODEL_NAME}.zip"
_VOSK_MODEL_DIR  = _VOICE_DIR / _VOSK_MODEL_NAME
# U105 (outside review): the download is checked against this before it's unpacked. Measured 2026-10-26 from
# the file at _VOSK_MODEL_URL (41,205,931 bytes; 20 files, 70,898,967 bytes unpacked).
_VOSK_SHA256 = "30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498"

# faster-whisper uses HuggingFace hub cache by default (~/.cache/huggingface)
# Override with WHISPER_CACHE env var or pass download_root to WhisperModel.
_WHISPER_CACHE = _VOICE_DIR / "faster-whisper"

# ── Babel system prompt for voice cleaning ────────────────────────────────────
# Used in Stage 2: raw STT transcript → clean English.
VOICE_CLEAN_SYSTEM = """You are a voice transcription cleaner.

You receive raw speech-to-text output that has been decoded from binary.
Your job:
1. Remove filler words (um, uh, like, you know, so, actually)
2. Fix obvious transcription errors (homophones, cut-off words)
3. Add proper punctuation and capitalization
4. Preserve ALL meaning and intent — do not paraphrase or summarize
5. If the speech is in a non-English language, translate it to clear English

Reply with ONLY the cleaned text.  No labels, no headers, no explanation."""


# ── Audio capture ─────────────────────────────────────────────────────────────

def record(duration_s: float = 5.0, status_cb=None) -> tuple[bytes, object]:
    """
    Capture audio from the default microphone.

    Returns (pcm_int16_bytes, float32_array_or_None).
    float32_array is used by faster-whisper directly (no temp file needed).
    pcm_int16_bytes is used by Vosk.
    """
    if status_cb:
        status_cb(f"Listening… ({duration_s:.0f}s)")

    # ── sounddevice (preferred) ───────────────────────────────────────────────
    try:
        import sounddevice as _sd
        import numpy as _np

        # Capture float32 for faster-whisper, int16 for Vosk
        arr_f32 = _sd.rec(
            int(duration_s * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
        )
        _sd.wait()
        flat   = arr_f32.flatten()
        pcm    = (flat * 32767).astype(_np.int16).tobytes()
        return pcm, flat
    except ImportError:
        pass

    # ── pyaudio fallback ──────────────────────────────────────────────────────
    try:
        import pyaudio as _pa
        import numpy as _np

        pa     = _pa.PyAudio()
        stream = pa.open(
            format=_pa.paInt16,
            channels=1,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=1024,
        )
        n_frames = int(SAMPLE_RATE / 1024 * duration_s)
        frames   = [stream.read(1024) for _ in range(n_frames)]
        stream.stop_stream()
        stream.close()
        pa.terminate()
        raw = b"".join(frames)
        # float32 for faster-whisper
        arr = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
        return raw, arr
    except ImportError:
        pass

    raise RuntimeError(
        "No audio capture library.\n"
        "  pip install sounddevice   (recommended)\n"
        "  pip install pyaudio       (alternative)"
    )


# ── STT Stage 1: raw transcription ───────────────────────────────────────────

def _transcribe_whisper(
    audio,   # float32 numpy array or file path
    model_size: str = "small",
    status_cb=None,
) -> str:
    """faster-whisper transcription.  Downloads model on first use."""
    from faster_whisper import WhisperModel  # type: ignore

    _WHISPER_CACHE.mkdir(parents=True, exist_ok=True)
    if status_cb:
        status_cb(f"Transcribing with Whisper ({model_size})…")

    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        download_root=str(_WHISPER_CACHE),
    )
    segments, _info = model.transcribe(audio, beam_size=5, language=None)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _ensure_vosk_model(status_cb=None) -> Path:
    if _VOSK_MODEL_DIR.exists():
        return _VOSK_MODEL_DIR
    _VOICE_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = _VOICE_DIR / f"{_VOSK_MODEL_NAME}.zip"
    if status_cb:
        status_cb("Downloading Vosk model (~40 MB)…")
    urllib.request.urlretrieve(_VOSK_MODEL_URL, zip_path)
    return _install_vosk_zip(zip_path)


def _install_vosk_zip(zip_path: Path) -> Path:
    """Check the downloaded model against its pinned SHA-256, unpack it safely (core/safe_zip.py) into a
    temporary folder, and move the model into place. Anything that doesn't check out is refused and removed."""
    import hashlib
    import os
    import shutil
    import uuid
    from cursiv_engine.core import safe_zip
    try:
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        if digest != _VOSK_SHA256:
            raise safe_zip.UnsafeZip("the Vosk model download doesn't match its published checksum, so it wasn't used")
        unpack = _VOICE_DIR / f".vosk-unpack-{uuid.uuid4().hex[:8]}"
        try:
            safe_zip.extract(zip_path, unpack, max_files=200, max_bytes=200 << 20, max_file_bytes=100 << 20)
            inner = unpack / _VOSK_MODEL_NAME
            if not inner.is_dir():
                raise safe_zip.UnsafeZip(f"the zip doesn't contain {_VOSK_MODEL_NAME}/")
            os.replace(inner, _VOSK_MODEL_DIR)
        finally:
            shutil.rmtree(unpack, ignore_errors=True)
    finally:
        zip_path.unlink(missing_ok=True)
    return _VOSK_MODEL_DIR


def _transcribe_vosk(pcm_bytes: bytes, status_cb=None) -> str:
    from vosk import Model, KaldiRecognizer, SetLogLevel  # type: ignore
    SetLogLevel(-1)
    path = _ensure_vosk_model(status_cb)
    rec  = KaldiRecognizer(Model(str(path)), SAMPLE_RATE)
    rec.AcceptWaveform(pcm_bytes)
    return json.loads(rec.FinalResult()).get("text", "").strip()


def _transcribe_sphinx(pcm_bytes: bytes) -> str:
    import speech_recognition as _sr  # type: ignore
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_bytes)
    buf.seek(0)
    r = _sr.Recognizer()
    with _sr.AudioFile(buf) as src:
        data = r.record(src)
    return r.recognize_sphinx(data)


def transcribe_raw(
    pcm_bytes: bytes,
    float32_arr=None,
    model_size: str = "small",
    status_cb=None,
) -> str:
    """
    Stage 1: audio bytes → raw text string.
    Tries faster-whisper → Vosk → Sphinx in order.
    """
    # ── faster-whisper ────────────────────────────────────────────────────────
    try:
        audio_in = float32_arr if float32_arr is not None else pcm_bytes
        return _transcribe_whisper(audio_in, model_size=model_size, status_cb=status_cb)
    except ImportError:
        pass
    except Exception as exc:
        if status_cb:
            status_cb(f"Whisper error ({exc}) — trying Vosk")

    # ── Vosk ──────────────────────────────────────────────────────────────────
    try:
        return _transcribe_vosk(pcm_bytes, status_cb)
    except ImportError:
        pass
    except Exception as exc:
        if status_cb:
            status_cb(f"Vosk error ({exc}) — trying Sphinx")

    # ── pocketsphinx ─────────────────────────────────────────────────────────
    try:
        return _transcribe_sphinx(pcm_bytes)
    except ImportError:
        pass
    except Exception as exc:
        if status_cb:
            status_cb(f"Sphinx error: {exc}")

    raise RuntimeError(
        "No STT backend available.\n"
        "  pip install faster-whisper sounddevice   (recommended)\n"
        "  pip install vosk sounddevice             (offline fallback)\n"
        "  pip install SpeechRecognition pocketsphinx pyaudio  (last resort)"
    )


# ── Availability ──────────────────────────────────────────────────────────────

def is_available() -> bool:
    for pkg in ("sounddevice", "pyaudio"):
        try:
            __import__(pkg)
            return True
        except ImportError:
            pass
    return False


def stt_backend() -> str:
    """Return the name of the best available STT library."""
    for pkg in ("faster_whisper", "vosk", "speech_recognition"):
        try:
            __import__(pkg)
            return pkg.replace("_", "-")
        except ImportError:
            pass
    return "none"


def capture_backend() -> str:
    for pkg in ("sounddevice", "pyaudio"):
        try:
            __import__(pkg)
            return pkg
        except ImportError:
            pass
    return "none"
