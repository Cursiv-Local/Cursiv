"""docs/CODE-MAP.md lists every module, so it can't quietly go stale."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _modules() -> list[str]:
    out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard",
                          "cursiv_engine/*.py", "launcher/*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    return [f for f in out if not f.endswith("__init__.py")]


def test_every_module_is_on_the_code_map():
    text = (ROOT / "docs" / "CODE-MAP.md").read_text(encoding="utf-8")
    named = set(re.findall(r"`([\w/]+\.py)`", text))
    missing = []
    for f in _modules():
        engine = f.removeprefix("cursiv_engine/")
        launcher = f.removeprefix("launcher/")
        if not ({f, engine, launcher} & named):
            missing.append(f)
    assert not missing, "add these to docs/CODE-MAP.md: " + ", ".join(missing)


def test_the_map_names_no_module_that_is_gone():
    text = (ROOT / "docs" / "CODE-MAP.md").read_text(encoding="utf-8")
    real = set()
    for f in _modules():
        real |= {f, f.removeprefix("cursiv_engine/"), f.removeprefix("launcher/")}
    gone = [n for n in re.findall(r"`([\w/]+\.py)`", text)
            if n not in real and not (ROOT / n).exists()]
    assert not gone, "remove these from docs/CODE-MAP.md: " + ", ".join(gone)


def test_cursiv_can_find_where_things_live():
    from cursiv_engine.core import self_source
    reply = self_source.command("self map plugin process")
    assert "plugin_runner.py" in reply and "code map" in reply
    assert "Field work" in self_source.command("self map")
    assert "CODE-MAP.md (code map)" in self_source.excerpts("notebook hash chain photos")
