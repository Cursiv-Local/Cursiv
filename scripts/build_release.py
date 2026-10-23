"""
Build a release installer from a tagged commit, never from the working tree.

    py -3.13 scripts/build_release.py v3.14-U63

1. Checks the three version strings at that tag agree with the tag
   (core/selfknow.py, launcher/cursiv_launcher.py, installer/cursiv_setup.iss).
2. Checks out the tag into a temporary git worktree (uncommitted edits here can't
   get in), runs PyInstaller and Inno Setup there.
3. Requires the frozen app's self-test with isolated user data, then compiles Inno Setup.
4. Copies identical versioned/latest installers to installer/Output/, verifies their
   SHA-256 (SHA256SUMS-<version>.txt), and removes only the checked temporary worktree.

The audit found U59 built from an uncommitted tree; this is the fix.
"""
from __future__ import annotations

import hashlib
import os
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


def build_environment() -> dict[str, str]:
    """Exclude unrelated DLL directories inherited from an editor/runtime PATH.

    U82 packaging found a concrete collision with bundled ICU/UCRT DLLs. Child
    builds use Python, Git and Windows directories; the owner's environment is
    unchanged. This helper does not load certificates or sign an installer.
    """
    env = dict(os.environ)
    for name in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH',
                 'QT_QPA_PLATFORM_PLUGIN_PATH'):
        env.pop(name, None)
    if os.name == 'nt':
        windows = Path(env.get('SystemRoot', r'C:\Windows'))
        directories = [Path(sys.executable).resolve().parent, Path(sys.base_prefix),
                       Path(sys.base_prefix) / 'Scripts', windows / 'System32', windows]
        git_exe = shutil.which('git')
        if git_exe:
            directories.append(Path(git_exe).resolve().parent)
        env['PATH'] = os.pathsep.join(dict.fromkeys(str(p) for p in directories))
    return env


def verify_frozen(work: Path, env: dict[str, str]) -> Path:
    """Require the built application self-test before staging an installer."""
    private = work.parent / 'selftest-data'
    private.mkdir(exist_ok=True)
    report = work.parent / 'frozen-selftest.txt'
    checked_env = dict(env, HOME=str(private), USERPROFILE=str(private),
                       CURSIV_REAL_HOME=str(private), CURSIV_APP_DATA=str(private / 'app'),
                       CURSIV_NO_ENGINE_START='1', QT_QPA_PLATFORM='offscreen')
    subprocess.run([str(work / 'dist/Cursiv/Cursiv.exe'), '--selftest', str(report)],
                   cwd=work, env=checked_env, check=True,
                   creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if not report.is_file() or not re.search(r'(?m)^ALL PASSED\s*$', report.read_text(encoding='utf-8')):
        raise RuntimeError(f'Packaged application self-test did not pass: {report}')
    return report


def stage_installers(source: Path, output: Path, version: str) -> Path:
    """Versioned/stable installer aliases must contain identical verified bytes."""
    output.mkdir(parents=True, exist_ok=True)
    versioned = output / f'Cursiv-Setup-{version}.exe'
    stable = output / 'Cursiv-Setup-latest.exe'
    shutil.copy2(source, versioned)
    shutil.copy2(versioned, stable)
    digest = hashlib.sha256(versioned.read_bytes()).hexdigest()
    if not versioned.stat().st_size or hashlib.sha256(stable.read_bytes()).hexdigest() != digest:
        raise RuntimeError('Installer alias verification failed')
    sums = output / f'SHA256SUMS-{version}.txt'
    sums.write_text(f'{digest}  {versioned.name}\n{digest}  {stable.name}\n', encoding='utf-8')
    return sums


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

    temporary = Path(tempfile.mkdtemp(prefix="cursiv_release_")).resolve()
    work = temporary / "src"
    git("worktree", "add", "--detach", str(work), tag)
    try:
        print(f"building {tag} ({git('rev-parse', '--short', tag).strip()}) in {work}", flush=True)
        from release_provenance import check_lock, record
        check_lock(work)
        env = build_environment()
        subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "launcher/build.spec"],
                       cwd=work, env=env, check=True)
        report = verify_frozen(work, env)
        print(f'packaged checks: {report}')
        subprocess.run([str(ISCC), "installer/cursiv_setup.iss"], cwd=work, env=env, check=True)
        name = f"Cursiv-Setup-{want}.exe"
        out = REPO / "installer" / "Output"
        sums = stage_installers(work / 'installer/Output' / name, out, want)
        record(work, [out / name, out / 'Cursiv-Setup-latest.exe'], out / f'provenance-{want}.json')
        print(f"saved {out / name}")
        # Published with the release so anyone can check the download (installer/BEFORE-INSTALL.txt).
        digest = hashlib.sha256((out / name).read_bytes()).hexdigest()
        print(f"sha256 {digest}\nsaved {sums} (upload it to the release as SHA256SUMS.txt)")
    finally:
        if work.resolve().parent != temporary or work.name != 'src' or not temporary.name.startswith('cursiv_release_'):
            raise RuntimeError('Refusing to remove an unexpected release worktree')
        git("worktree", "remove", "--force", str(work))
    return 0


if __name__ == "__main__":
    sys.exit(main())
