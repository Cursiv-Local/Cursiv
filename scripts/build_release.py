"""
Build a release installer from a tagged commit, never from the working tree.

    py -3.13 scripts/build_release.py v3.14-U63

1. Checks the three version strings at that tag agree with the tag
   (core/selfknow.py, launcher/cursiv_launcher.py, installer/cursiv_setup.iss).
2. Checks out the tag into a temporary git worktree (uncommitted edits here can't
   get in), runs PyInstaller and Inno Setup there.
3. Copies the installer to installer/Output/ and removes the worktree.

The audit found U59 built from an uncommitted tree; this is the fix.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ISCC = Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe"
VERSION_FILES = {
    "cursiv_v215/core/selfknow.py": r'VERSION\s*=\s*"([^"]+)"',
    "launcher/cursiv_launcher.py": r'_CURRENT_VERSION\s*=\s*"([^"]+)"',
    "installer/cursiv_setup.iss": r'#define AppVer\s+"([^"]+)"',
}


def git(*args: str, cwd: Path = REPO) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True).stdout


def versions_at(ref: str) -> dict[str, str]:
    out = {}
    for path, pattern in VERSION_FILES.items():
        m = re.search(pattern, git("show", f"{ref}:{path}"))
        out[path] = m.group(1) if m else "?"
    return out


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    tag = sys.argv[1]
    git("rev-parse", "--verify", f"refs/tags/{tag}")
    want = tag.removeprefix("v")
    found = versions_at(tag)
    wrong = {p: v for p, v in found.items() if v != want}
    if wrong:
        print(f"Version strings at {tag} don't match {want}:")
        for p, v in wrong.items():
            print(f"  {p}: {v}")
        return 1
    if not ISCC.exists():
        print(f"Inno Setup not found at {ISCC}")
        return 1

    work = Path(tempfile.mkdtemp(prefix="cursiv_release_")) / "src"
    git("worktree", "add", "--detach", str(work), tag)
    try:
        print(f"building {tag} ({git('rev-parse', '--short', tag).strip()}) in {work}", flush=True)
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "launcher/build.spec"],
                       cwd=work, check=True)
        subprocess.run([str(ISCC), "installer/cursiv_setup.iss"], cwd=work, check=True)
        name = f"Cursiv-Setup-{want}.exe"
        out = REPO / "installer" / "Output"
        out.mkdir(parents=True, exist_ok=True)
        shutil.copy2(work / "installer" / "Output" / name, out / name)
        print(f"saved {out / name}")
    finally:
        git("worktree", "remove", "--force", str(work))
    return 0


if __name__ == "__main__":
    sys.exit(main())
