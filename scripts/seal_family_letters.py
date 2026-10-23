"""
Re-seal the family letters after editing them.

  1. Edit private/family_source.json  (git-ignored -- the only readable copy)
  2. python scripts/seal_family_letters.py
  3. Rebuild (scripts/build.bat) so the new sealed_letters.json ships.

Writes cursiv_engine/family/sealed_letters.json, which is safe to commit and ship:
each letter opens only with that person's name + birth date.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cursiv_engine.family.family_seal import SEALED_FILE, build_sealed  # noqa: E402

SOURCE = ROOT / "private" / "family_source.json"


def main() -> None:
    if not SOURCE.exists():
        sys.exit(f"Missing {SOURCE} -- the plaintext source lives only on the owner's machine.")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    sealed = build_sealed(source)
    SEALED_FILE.write_text(json.dumps(sealed, indent=1), encoding="utf-8")
    print(f"Sealed {len(source['members'])} members into {len(sealed['entries'])} entries -> {SEALED_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
