"""
How fast Cursiv's models answer on this computer, with and without the graphics
card (research roadmap R5). Writes docs/HARDWARE.md: the machine, then for each
model the time to load, the speed reading the prompt and the speed writing the
answer, on the card (as Cursiv sets it up) and on the processor only (num_gpu 0,
as on a laptop with no graphics card).

    py -3.13 scripts/hardware_check.py                      # qwen3:4b-instruct and qwen2.5:1.5b
    py -3.13 scripts/hardware_check.py qwen3:4b-instruct

Needs Ollama running. Runs each case twice and reports the second (warm) run.
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
OLLAMA = "http://127.0.0.1:11434"
PROMPT = ("A field team needs to purify creek water. In about 120 words, explain settling, filtering and "
          "boiling, in order.")


def _post(path: str, body: dict, timeout: float = 900) -> dict:
    req = urllib.request.Request(OLLAMA + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def machine() -> dict:
    def ps(cmd: str) -> str:
        try:
            return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True,
                                  timeout=20).stdout.strip()
        except Exception:
            return ""
    from cursiv_engine.core import speed
    return {
        "cpu": ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name") or platform.processor(),
        "cores": os.cpu_count(),
        "ram_gb": ps("[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory/1GB)"),
        "gpu": ps("(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join ', '"),
        "vram_mb": speed.gpu_vram_mb(),
        "os": platform.platform(),
    }


def run(model: str, options: dict) -> dict:
    from cursiv_engine.core import speed
    speed.make_room(model)
    body = {"model": model, "prompt": PROMPT, "stream": False, "keep_alive": "5m",
            "options": {"num_predict": 220, "num_ctx": speed.num_ctx(), **options}}
    _post("/api/generate", {"model": model, "keep_alive": 0}, 60)          # start cold
    t0 = time.time()
    cold = _post("/api/generate", body)
    warm = _post("/api/generate", body)
    ev = warm.get("eval_count", 0) / max(warm.get("eval_duration", 1) / 1e9, 1e-9)
    pe = warm.get("prompt_eval_count", 0) / max(warm.get("prompt_eval_duration", 1) / 1e9, 1e-9)
    return {"load_s": round(cold.get("load_duration", 0) / 1e9, 1), "prompt_tps": round(pe),
            "gen_tps": round(ev, 1), "answer_s": round(warm.get("total_duration", 0) / 1e9, 1),
            "wall_s": round(time.time() - t0, 1)}


def main() -> int:
    from cursiv_engine.core import speed
    models = sys.argv[1:] or ["qwen3:4b-instruct", "qwen2.5:1.5b"]
    m = machine()
    rows = []
    for model in models:
        for label, opts in (("graphics card (as Cursiv sets it)", speed.gpu_options(model)),
                            ("processor only (no graphics card)", {"num_gpu": 0})):
            print(f"{model} · {label} …", flush=True)
            try:
                r = run(model, opts)
            except Exception as exc:
                r = {"error": str(exc)}
            rows.append((model, label, r))
            print("   ", r, flush=True)
    lines = ["# Hardware check", "",
             f"Measured {time.strftime('%Y-%m-%d')} with `scripts/hardware_check.py`: one fixed prompt "
             "(about 120 words out), second run reported (model already loaded). Load time is from cold.", "",
             "## This computer", "",
             f"- Processor: {m['cpu']} ({m['cores']} threads)", f"- Memory: {m['ram_gb']} GB",
             f"- Graphics: {m['gpu']} ({m['vram_mb']} MB)", f"- System: {m['os']}", "",
             "## Results", "",
             "| Model | Running on | Load (cold) | Reading the prompt | Writing the answer | Whole answer |",
             "|---|---|---|---|---|---|"]
    for model, label, r in rows:
        if "error" in r:
            lines.append(f"| {model} | {label} | error: {r['error']} | | | |")
        else:
            lines.append(f"| {model} | {label} | {r['load_s']} s | {r['prompt_tps']} tokens/s | "
                         f"{r['gen_tps']} tokens/s | {r['answer_s']} s |")
    lines += ["", "A token is about three quarters of a word. 'Processor only' is what a laptop without a "
              "usable graphics card gets; Cursiv falls back to it automatically."]
    out = REPO / "docs" / "HARDWARE.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"saved {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
