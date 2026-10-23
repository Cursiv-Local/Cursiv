"""The version in the app, the launcher's update check and the installer move together."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_version_strings_match():
    found = {
        "selfknow": re.search(r'VERSION\s*=\s*"([^"]+)"', (ROOT / "cursiv_engine/core/selfknow.py").read_text(encoding="utf-8")),
        "launcher": re.search(r'_CURRENT_VERSION\s*=\s*"([^"]+)"', (ROOT / "launcher/cursiv_launcher.py").read_text(encoding="utf-8")),
        "installer": re.search(r'#define AppVer\s+"([^"]+)"', (ROOT / "installer/cursiv_setup.iss").read_text(encoding="utf-8")),
    }
    versions = {k: m.group(1) for k, m in found.items() if m}
    assert len(versions) == 3 and len(set(versions.values())) == 1, versions
    iss = (ROOT / "installer/cursiv_setup.iss").read_text(encoding="utf-8")
    assert f"OutputBaseFilename=Cursiv-Setup-{versions['installer']}" in iss
