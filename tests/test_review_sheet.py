"""The professional-review sheet (scripts/review_sheet.py) prints every entry word for word."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import review_sheet  # noqa: E402

from cursiv_engine.core import reference as ref  # noqa: E402


def test_every_medical_entry_is_on_the_sheet_with_its_fingerprint():
    page, whole = review_sheet.render(("medical",))
    medical = [e for e in ref.entries() if e.category == "medical"]
    assert page.count('class="entry"') == len(medical)
    for e in medical:
        assert review_sheet.entry_fingerprint(e)[:16] in page
    assert whole in page and "Correct as written" in page
    assert review_sheet.render(("medical",))[1] == whole           # the same text, the same fingerprint
