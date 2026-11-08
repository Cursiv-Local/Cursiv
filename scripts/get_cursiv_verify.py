"""
Build the robot evidence verifier (cursiv-verify, from Cursiv Robotics) into tools/ for a release.

    py -3.13 scripts/get_cursiv_verify.py

Needs Rust (free, https://rustup.rs). Builds from a pinned commit of the public Cursiv-Robotics
repository with its locked dependencies, copies the binary to tools/, and prints its SHA-256 for
the release record. launcher/build.spec bundles tools/cursiv-verify when it is there.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = "https://github.com/Cursiv-Local/Cursiv-Robotics"
COMMIT = "1814b971dd6f16c838436eb7e405f1b6536a07dc"   # Cursiv-Robotics main after PR #6 (importer hardening, general profile)
ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if not shutil.which("cargo"):
        print("Rust is not installed (https://rustup.rs); robot evidence import will be unavailable in this build.")
        return 1
    exe = "cursiv-verify.exe" if os.name == "nt" else "cursiv-verify"
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["cargo", "install", "--git", REPO, "--rev", COMMIT, "--locked", "--root", tmp, "cursiv-verify"], check=True)
        built = Path(tmp) / "bin" / exe
        (ROOT / "tools").mkdir(exist_ok=True)
        dest = ROOT / "tools" / exe
        shutil.copy2(built, dest)
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    print(f"{dest}  sha256 {digest}  (Cursiv-Robotics {COMMIT[:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
