"""
Run the Field Station server for development against a separate, throwaway data folder, never this
computer's real Cursiv data (the server takes the data lease and first-run setup encrypts its folder).

    python scripts/station_dev.py [folder] [--port 8090] [--simulate A]

The folder defaults to .station-dev/ inside the checkout (git-ignored). Delete it to start over.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
args = sys.argv[1:]
folder = Path(args.pop(0)) if args and not args[0].startswith("-") else REPO / ".station-dev"
folder = folder.resolve()
(folder / "home").mkdir(parents=True, exist_ok=True)
os.environ["HOME"] = os.environ["USERPROFILE"] = str(folder / "home")
os.environ["CURSIV_APP_DATA"] = str(folder / "home" / ".cursiv")
sys.path.insert(0, str(REPO))
print(f"Field Station development data: {folder}", flush=True)

from cursiv_engine.station.__main__ import main  # noqa: E402

sys.exit(main(args))
