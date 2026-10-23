"""
LoRA training — fine-tunes a small local base model on your own collected
training data (.cursiv/training_data.jsonl -- what "Save to Training" and the
Training Data dialog's image/notes/manual-JSON entries all feed into).

Deliberately scoped small: Qwen2.5-1.5B-Instruct, LoRA r=8 alpha=16 (mirrors
the checkpoint convention already referenced in
cursiv_engine/codex/system_prompt.md). Produces a portable PEFT adapter folder
under .cursiv/lora_checkpoints/<timestamp>/ -- not merged into a full model
or converted to GGUF/Ollama, to keep the dependency surface and the number
of steps that can fail to a minimum for a first working version.

Heavy ML packages (torch, transformers, peft, accelerate, datasets) are NOT
bundled in the installer -- same reasoning as Winkler-Codex's Ollama models:
multi-GB, best installed on demand into a real system Python, in a visible
terminal, not silently inside the frozen app. check_requirements() below is
pure stdlib + psutil (already bundled) specifically so the GUI can show real
disk/RAM/package numbers before anything heavy is imported or downloaded.

Run standalone once requirements are met:
    python -m cursiv_engine.training.lora_trainer [--epochs N]
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from cursiv_engine.training.paths import TRAINING_JSONL, CURSIV_DIR

BASE_MODEL   = "Qwen/Qwen2.5-1.5B-Instruct"
LORA_R       = 8
LORA_ALPHA   = 16
LORA_DROPOUT = 0.05
# Standard PEFT target modules for the Qwen2/Llama attention + MLP blocks.
LORA_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]

REQUIRED_PACKAGES = ("torch", "transformers", "peft", "accelerate", "datasets")

MIN_FREE_DISK_GB = 8.0     # ~3GB model download + tokenizer/cache + adapter + margin
MIN_FREE_RAM_GB  = 8.0     # bf16 base weights + LoRA optimizer state + activations
MIN_EXAMPLES     = 10      # below this, a fine-tune is unlikely to move the model much
DEFAULT_EPOCHS   = 1       # kept low by default -- see CPU_SECONDS_PER_EXAMPLE below

# Measured directly: a single forward+backward pass on this base model, on a
# CPU with no CUDA, at max_length=512, took ~360s/example in testing. That's
# ~30 hours for 100 examples at 3 epochs -- not something to default someone
# into without warning them first. check_requirements() uses this to show a
# real estimate before anything starts; a CUDA GPU is dramatically faster,
# so the estimate is skipped when one's detected rather than needlessly
# alarming a user who won't hit anywhere near this number.
CPU_SECONDS_PER_EXAMPLE = 360

CHECKPOINTS_DIR = CURSIV_DIR / "lora_checkpoints"


# ── Requirements check (no heavy imports -- safe to call any time) ─────────

def missing_packages() -> list[str]:
    import importlib
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except Exception:
            missing.append(pkg)
    return missing


def _python_candidates() -> list[str]:
    found: list[str] = []
    for cmd in ("python", "python3", "py"):
        p = shutil.which(cmd)
        if p:
            found.append(p)
    programs = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python"
    if programs.exists():
        for sub in sorted(programs.glob("Python3*"), reverse=True):
            exe = sub / "python.exe"
            if exe.exists():
                found.append(str(exe))
    seen, out = set(), []
    for p in found:
        key = os.path.normcase(os.path.abspath(p))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _no_window() -> int:
    return getattr(__import__("subprocess"), "CREATE_NO_WINDOW", 0)


def _runs(python_exe: str) -> bool:
    """The Microsoft Store 'App Execution Alias' python.exe exists on PATH
    even when no Python is installed -- it just opens the Store. Only count
    an interpreter that actually runs code."""
    import subprocess
    try:
        r = subprocess.run([python_exe, "-E", "-c", "print('ok')"],
                           capture_output=True, text=True, timeout=20,
                           creationflags=_no_window())
        return r.returncode == 0 and r.stdout.strip() == "ok"
    except Exception:
        return False


def probe_python(python_exe: str) -> dict:
    """Ask the interpreter that will actually run training which packages it
    has and whether torch sees a GPU. Must run out-of-process: inside the
    frozen Cursiv.exe torch is never importable, so an in-process check
    always reported 'missing' and the button never got past installing.
    -E keeps a stray PYTHONPATH from shadowing that Python's own stdlib."""
    import subprocess
    code = (
        "import importlib.util, json\n"
        f"pk = {list(REQUIRED_PACKAGES)!r}\n"
        "miss = [p for p in pk if importlib.util.find_spec(p) is None]\n"
        "gpu = ''\n"
        "if 'torch' not in miss:\n"
        "    try:\n"
        "        import torch\n"
        "        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''\n"
        "    except Exception as e:\n"
        "        miss.insert(0, 'torch')\n"
        "print(json.dumps({'missing': miss, 'gpu': gpu}))\n"
    )
    try:
        r = subprocess.run([python_exe, "-E", "-c", code],
                           capture_output=True, text=True, timeout=120,
                           creationflags=_no_window())
        d = json.loads(r.stdout.strip().splitlines()[-1])
        return {"missing": list(d["missing"]), "gpu": d["gpu"]}
    except Exception:
        return {"missing": list(REQUIRED_PACKAGES), "gpu": ""}


def find_system_python() -> Optional[str]:
    """Locate a real, standalone Python interpreter -- NOT sys.executable,
    which inside the frozen Cursiv.exe is the app itself, not a Python that
    can pip install torch/transformers/peft into its own site-packages.
    Prefers one that already has the training packages, so a second Python
    on PATH doesn't send the user back to the install step forever."""
    working = [p for p in _python_candidates() if _runs(p)]
    for p in working:
        if not probe_python(p)["missing"]:
            return p
    return working[0] if working else None


def check_requirements() -> dict:
    """Real, current numbers -- disk, RAM, packages, GPU, example count --
    for the GUI to show before anything heavy is downloaded or imported."""
    disk_free_gb = shutil.disk_usage(str(Path.home())).free / (1024 ** 3)

    ram_total_gb = 0.0
    try:
        import psutil
        ram_total_gb = psutil.virtual_memory().total / (1024 ** 3)
    except Exception:
        pass

    examples = load_examples()
    if getattr(sys, "frozen", False):
        python_exe = find_system_python()
        probe = probe_python(python_exe) if python_exe else {
            "missing": list(REQUIRED_PACKAGES), "gpu": ""}
        missing, gpu_name = probe["missing"], probe["gpu"]
    else:
        # Already running under the Python that will train (CLI path).
        python_exe = sys.executable
        missing = missing_packages()
        gpu_name = ""
        if not missing:
            try:
                import torch
                if torch.cuda.is_available():
                    gpu_name = torch.cuda.get_device_name(0)
            except Exception:
                missing = ["torch"] + [m for m in missing if m != "torch"]
    gpu_available = bool(gpu_name)

    est_cpu_seconds = len(examples) * DEFAULT_EPOCHS * CPU_SECONDS_PER_EXAMPLE

    return {
        "disk_free_gb":   round(disk_free_gb, 1),
        "disk_ok":        disk_free_gb >= MIN_FREE_DISK_GB,
        "ram_total_gb":   round(ram_total_gb, 1),
        "ram_ok":         ram_total_gb == 0.0 or ram_total_gb >= MIN_FREE_RAM_GB,
        "gpu_available":  gpu_available,
        "gpu_name":       gpu_name,
        "missing_packages": missing,
        "packages_ok":    not missing,
        "python_exe":     python_exe,
        "python_ok":      python_exe is not None,
        "example_count":  len(examples),
        "examples_ok":    len(examples) >= MIN_EXAMPLES,
        "base_model":     BASE_MODEL,
        "default_epochs": DEFAULT_EPOCHS,
        # Only meaningful for CPU training -- a CUDA GPU is dramatically
        # faster and this fixed per-example estimate doesn't apply to it.
        "est_cpu_hours":  round(est_cpu_seconds / 3600, 1),
    }


def module_launch_code(code_root: str, module: str) -> str:
    """One-liner for `python -E -c ...` that runs a cursiv_engine module from a
    system Python. Cursiv's install folder is APPENDED to sys.path rather
    than set as PYTHONPATH: it holds the frozen app's own Python 3.13
    _ctypes/numpy/etc., and putting it first made `import torch` crash on
    any other Python version -- which the trainer then reported as
    'missing packages', so training never started."""
    root = code_root.replace("\\", "\\\\").replace("'", "\\'")
    return (f"import sys, runpy; sys.path.append('{root}'); "
            f"runpy.run_module('{module}', run_name='__main__', alter_sys=True)")


def pip_install_torch_argv(python_exe: str) -> list[str]:
    """CPU-only torch by default -- the accessible, always-works path this
    feature is built around. A user with a CUDA GPU already has a driver
    and can swap the index URL themselves; auto-detecting CUDA reliably
    before torch is even installed isn't worth the extra failure surface.
    Kept as its own call (separate from pip_install_rest_argv) since torch's
    special --index-url shouldn't apply to the other packages."""
    return [
        python_exe, "-m", "pip", "install", "--upgrade",
        "torch", "--index-url", "https://download.pytorch.org/whl/cpu",
    ]


def pip_install_rest_argv(python_exe: str) -> list[str]:
    return [python_exe, "-m", "pip", "install", "--upgrade",
            "transformers", "peft", "accelerate", "datasets"]


# ── Data loading ────────────────────────────────────────────────────────────

def load_examples() -> list[dict]:
    if not TRAINING_JSONL.exists():
        return []
    examples = []
    for line in TRAINING_JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("prompt") and d.get("response"):
            examples.append(d)
    return examples


def format_example(entry: dict) -> str:
    return (
        f"### Instruction:\n{entry['prompt']}\n\n"
        f"### Response:\n{entry['response']}"
    )


# ── Training (heavy imports happen only in here) ────────────────────────────

def run_training(
    epochs: int = DEFAULT_EPOCHS,
    output_dir: Optional[Path] = None,
    progress_cb: Optional[Callable[[str], None]] = None,
    max_steps: int = -1,
) -> dict:
    """Fine-tunes BASE_MODEL with LoRA on every example currently in
    training_data.jsonl. Blocking -- run on a background thread/process."""
    def log(msg: str) -> None:
        if progress_cb:
            progress_cb(msg)
        else:
            print(msg, flush=True)

    examples = load_examples()
    if not examples:
        raise RuntimeError("No training examples found in training_data.jsonl.")
    log(f"Loaded {len(examples)} training example(s).")

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer,
        DataCollatorForLanguageModeling, Trainer, TrainingArguments,
    )

    dtype = torch.bfloat16  # halves memory vs fp32; works on CPU and GPU alike
    log(f"Loading tokenizer and base model ({BASE_MODEL})...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(BASE_MODEL, dtype=dtype)

    lora_config = LoraConfig(
        r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES, bias="none", task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    log(f"LoRA adapter attached (r={LORA_R}, alpha={LORA_ALPHA}). "
        f"Trainable params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    texts = [format_example(e) + tokenizer.eos_token for e in examples]
    dataset = Dataset.from_dict({"text": texts})

    def _tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=512)

    dataset = dataset.map(_tokenize, batched=True, remove_columns=["text"])

    if output_dir is None:
        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = CHECKPOINTS_DIR / stamp
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    args = TrainingArguments(
        output_dir=str(output_dir / "_trainer_state"),
        num_train_epochs=epochs,
        max_steps=max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=1,
        save_strategy="no",
        report_to=[],
    )
    trainer = Trainer(
        model=model, args=args, train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    log(f"Starting training -- {epochs} epoch(s) over {len(examples)} example(s). "
        f"This can take a while on CPU.")
    trainer.train()

    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    log(f"Adapter saved to {output_dir}")

    return {"output_dir": str(output_dir), "example_count": len(examples), "epochs": epochs}


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Cursiv LoRA training")
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS,
                         help=f"Default {DEFAULT_EPOCHS} -- CPU training is slow "
                              f"(~{CPU_SECONDS_PER_EXAMPLE}s/example/epoch measured), "
                              f"so this stays low unless you raise it deliberately.")
    parser.add_argument("--force", action="store_true",
                         help="Skip the requirement pre-flight check.")
    parser.add_argument("--max-steps", type=int, default=-1,
                         help="Stop after N optimizer steps (quick smoke test).")
    args = parser.parse_args()

    print("")
    print("  Cursiv — LoRA Training")
    print(f"  Base model: {BASE_MODEL}  (LoRA r={LORA_R} alpha={LORA_ALPHA})")
    print("")

    if not args.force:
        req = check_requirements()
        print(f"  Free disk:     {req['disk_free_gb']} GB  "
              f"({'OK' if req['disk_ok'] else f'need {MIN_FREE_DISK_GB}+ GB'})")
        if req["ram_total_gb"]:
            print(f"  Total RAM:     {req['ram_total_gb']} GB  "
                  f"({'OK' if req['ram_ok'] else f'need {MIN_FREE_RAM_GB}+ GB'})")
        print(f"  GPU:           {req['gpu_name'] if req['gpu_available'] else 'none detected (CPU training)'}")
        print(f"  Examples:      {req['example_count']}  "
              f"({'OK' if req['examples_ok'] else f'fewer than the recommended {MIN_EXAMPLES}'})")
        if not req["gpu_available"] and req["example_count"]:
            est_hours = round(req["example_count"] * args.epochs * CPU_SECONDS_PER_EXAMPLE / 3600, 1)
            print(f"  Estimated time: ~{est_hours} hour(s) on CPU at "
                  f"{args.epochs} epoch(s) (measured ~{CPU_SECONDS_PER_EXAMPLE}s/example/epoch -- "
                  f"a GPU would be dramatically faster)")
        print("")
        if req["missing_packages"]:
            print(f"  Missing packages: {', '.join(req['missing_packages'])}")
            print("  Install them first, or re-run with --force to try anyway.")
            sys.exit(1)
        if not req["disk_ok"]:
            print("  Not enough free disk space. Free some up and try again, "
                  "or re-run with --force.")
            sys.exit(1)
        if req["example_count"] == 0:
            print("  No training examples yet -- add some in the Training Data "
                  "dialog first (upload an image, paste JSON, or type notes and "
                  "ask to translate them).")
            sys.exit(1)

    def progress(msg: str) -> None:
        print(f"  {msg}", flush=True)

    result = run_training(epochs=args.epochs, progress_cb=progress,
                          max_steps=args.max_steps)
    print("")
    print(f"  Done. Adapter saved to: {result['output_dir']}")
    print("")


if __name__ == "__main__":
    main()
