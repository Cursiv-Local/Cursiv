"""Fast deterministic workspace gate, with a disposable home and no real AI calls."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix='cursiv-workspace-gate-') as temporary:
        home = Path(temporary)
        env = dict(os.environ, HOME=str(home), USERPROFILE=str(home),
                   APPDATA=str(home / 'Roaming'), LOCALAPPDATA=str(home / 'Local'),
                   CURSIV_APP_DATA=str(home / 'app'), CURSIV_REAL_HOME=str(home),
                   QT_QPA_PLATFORM='offscreen', CURSIV_NO_ENGINE_START='1',
                   CURSIV_PORTABLE='0', CURSIV_USB_ROOT='',
                   PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
        return subprocess.run([sys.executable, '-B', '-m', 'pytest',
                               'tests/test_workspace_language.py', 'tests/test_workspace_release_gate.py', '-q', '--tb=short',
                               '-p', 'no:cacheprovider', '--basetemp', str(home / 'tests')],
                              cwd=ROOT, env=env).returncode


if __name__ == '__main__':
    sys.exit(main())
