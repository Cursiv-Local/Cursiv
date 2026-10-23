"""
Merge a trained LoRA adapter (cursiv_engine/training/lora_trainer.py's output)
into an Ollama-usable model.

Converts the adapter directly to GGUF -- no full-model merge needed. llama.cpp's
convert_lora_to_gguf.py operates on the PEFT adapter directory alone, producing
a small GGUF adapter file (tens of MB, not a multi-GB merged model) -- and layers
it onto Ollama's own qwen2.5:1.5b via a Modelfile's ADAPTER directive. Verified:
qwen2.5:1.5b's Ollama manifest ships a ChatML template, confirming it's the same
Qwen2.5-1.5B-Instruct checkpoint lora_trainer.py fine-tunes against, so the
adapter is weight-compatible with it.

The GGUF conversion tooling (convert_lora_to_gguf.py + its gguf-py/conversion
sibling packages) isn't a pip-installable package -- it lives in the llama.cpp
repo and is meant to be run from a checkout. Cached locally via a shallow,
sparse git clone (source files only, no C++ build) under
.cursiv/llama_cpp_tools/ the first time this runs.

Run standalone once a LoRA adapter exists:
    python -m cursiv_engine.training.ollama_merge [--name cursiv-tuned]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

from cursiv_engine.training.paths import CURSIV_DIR
from cursiv_engine.training.lora_trainer import CHECKPOINTS_DIR, find_system_python

# Confirmed via Ollama's registry manifest: qwen2.5:1.5b ships a ChatML
# template (<|im_start|>/<|im_end|>), the signature of the Instruct variant --
# the same checkpoint lora_trainer.py's BASE_MODEL fine-tunes.
OLLAMA_BASE_TAG = "qwen2.5:1.5b"

LLAMA_CPP_REPO = "https://github.com/ggml-org/llama.cpp.git"
TOOLS_DIR = CURSIV_DIR / "llama_cpp_tools"
_SPARSE_PATHS = ["/*.py", "/gguf-py/*", "/conversion/*"]

# ollama pull qwen2.5:1.5b (~1 GB) + adapter GGUF (tens of MB) + tools clone
# (source only, a few MB) + margin.
MIN_FREE_DISK_GB = 3.0


def find_ollama_exe() -> Optional[str]:
    exe = shutil.which("ollama")
    if exe:
        return exe
    import os
    candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(candidate) if candidate.exists() else None


def list_adapters() -> list[Path]:
    """Every trained adapter under .cursiv/lora_checkpoints/, newest first."""
    if not CHECKPOINTS_DIR.exists():
        return []
    dirs = [
        d for d in CHECKPOINTS_DIR.iterdir()
        if d.is_dir() and (d / "adapter_config.json").exists()
    ]
    return sorted(dirs, key=lambda d: d.stat().st_mtime, reverse=True)


def gguf_tools_ready() -> bool:
    return (TOOLS_DIR / "convert_lora_to_gguf.py").exists()


def check_merge_requirements() -> dict:
    """Real, current numbers -- safe to call any time, no heavy imports."""
    disk_free_gb = shutil.disk_usage(str(Path.home())).free / (1024 ** 3)
    ollama_exe = find_ollama_exe()
    python_exe = find_system_python()
    adapters = list_adapters()

    return {
        "disk_free_gb":  round(disk_free_gb, 1),
        "disk_ok":       disk_free_gb >= MIN_FREE_DISK_GB,
        "ollama_exe":    ollama_exe,
        "ollama_ok":     ollama_exe is not None,
        "python_exe":    python_exe,
        "python_ok":     python_exe is not None,
        "adapters":      [str(a) for a in adapters],
        "adapter_count": len(adapters),
        "latest_adapter": str(adapters[0]) if adapters else None,
        "tools_cached":  gguf_tools_ready(),
        "base_tag":      OLLAMA_BASE_TAG,
    }


def ensure_gguf_tools(progress_cb: Optional[Callable[[str], None]] = None) -> Path:
    """Shallow, sparse clone of llama.cpp's conversion scripts -- source only,
    a few MB, no C++ build required. Cached so this only happens once."""
    def log(msg: str) -> None:
        (progress_cb or print)(msg)

    script = TOOLS_DIR / "convert_lora_to_gguf.py"
    if script.exists():
        return script

    log(f"Fetching GGUF conversion tools (one-time, small download) into {TOOLS_DIR}...")
    TOOLS_DIR.parent.mkdir(parents=True, exist_ok=True)
    if TOOLS_DIR.exists():
        shutil.rmtree(TOOLS_DIR)
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
         LLAMA_CPP_REPO, str(TOOLS_DIR)],
        check=True,
    )
    subprocess.run(
        ["git", "sparse-checkout", "set", "--no-cone", *_SPARSE_PATHS],
        cwd=str(TOOLS_DIR), check=True,
    )
    if not script.exists():
        raise RuntimeError("GGUF conversion tools were fetched but convert_lora_to_gguf.py is missing.")
    return script


def convert_adapter_to_gguf(
    adapter_dir: Path,
    outfile: Optional[Path] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> Path:
    """Runs llama.cpp's convert_lora_to_gguf.py against a trained adapter.
    Needs the adapter's own training packages (torch/transformers) already
    installed -- run through the same system Python lora_trainer.py uses."""
    def log(msg: str) -> None:
        (progress_cb or print)(msg)

    script = ensure_gguf_tools(progress_cb)
    adapter_dir = Path(adapter_dir)
    if outfile is None:
        outfile = adapter_dir / "adapter.gguf"

    log(f"Converting adapter to GGUF ({adapter_dir.name})...")
    result = subprocess.run(
        [sys.executable, str(script), "--outfile", str(outfile), "--outtype", "f16",
         str(adapter_dir)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GGUF conversion failed:\n{result.stdout}\n{result.stderr}")
    log(f"GGUF adapter written to {outfile}")
    return outfile


def write_modelfile(adapter_gguf: Path, base_tag: str = OLLAMA_BASE_TAG) -> Path:
    modelfile = Path(adapter_gguf).parent / "Modelfile"
    modelfile.write_text(f"FROM {base_tag}\nADAPTER {adapter_gguf}\n", encoding="utf-8")
    return modelfile


def create_ollama_model(
    model_name: str,
    modelfile: Path,
    ollama_exe: str,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> None:
    def log(msg: str) -> None:
        (progress_cb or print)(msg)

    log(f"Pulling base model {OLLAMA_BASE_TAG} if not already present (first time only)...")
    subprocess.run([ollama_exe, "pull", OLLAMA_BASE_TAG], check=True)
    log(f"Creating Ollama model '{model_name}'...")
    subprocess.run([ollama_exe, "create", model_name, "-f", str(modelfile)], check=True)
    log(f"Done. Chat with it: ollama run {model_name}")


def merge_latest_to_ollama(
    model_name: str = "cursiv-tuned",
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    def log(msg: str) -> None:
        (progress_cb or print)(msg)

    adapters = list_adapters()
    if not adapters:
        raise RuntimeError("No trained adapters found. Run LoRA training first.")
    adapter_dir = adapters[0]
    log(f"Using most recent adapter: {adapter_dir}")

    ollama_exe = find_ollama_exe()
    if not ollama_exe:
        raise RuntimeError("Ollama not found. Install it first.")

    gguf_path = convert_adapter_to_gguf(adapter_dir, progress_cb=progress_cb)
    modelfile = write_modelfile(gguf_path)
    create_ollama_model(model_name, modelfile, ollama_exe, progress_cb=progress_cb)
    return {"adapter_dir": str(adapter_dir), "gguf_path": str(gguf_path), "model_name": model_name}


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Merge the latest LoRA adapter into an Ollama model")
    parser.add_argument("--name", default="cursiv-tuned", help="Ollama model name to create")
    args = parser.parse_args()

    print("")
    print("  Cursiv — Merge LoRA Adapter into Ollama")
    print("")
    req = check_merge_requirements()
    print(f"  Adapters found: {req['adapter_count']}")
    print(f"  Ollama:         {('found at ' + req['ollama_exe']) if req['ollama_ok'] else 'NOT FOUND'}")
    print(f"  Free disk:      {req['disk_free_gb']} GB  "
          f"({'OK' if req['disk_ok'] else f'need {MIN_FREE_DISK_GB}+ GB'})")
    print("")
    if not req["ollama_ok"]:
        print("  Install Ollama first, then try again.")
        sys.exit(1)
    if req["adapter_count"] == 0:
        print("  No trained adapters yet -- run LoRA training first "
              "(python -m cursiv_engine.training.lora_trainer).")
        sys.exit(1)
    if not req["disk_ok"]:
        print("  Not enough free disk space. Free some up and try again.")
        sys.exit(1)

    def progress(msg: str) -> None:
        print(f"  {msg}", flush=True)

    result = merge_latest_to_ollama(model_name=args.name, progress_cb=progress)
    print("")
    print(f"  Done. Chat with your fine-tuned model: ollama run {result['model_name']}")
    print("")


if __name__ == "__main__":
    main()
