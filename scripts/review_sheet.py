"""
A printable sheet for a professional review of Cursiv's offline reference
(research roadmap R7; docs/PROFESSIONAL-REVIEW.md says how the review runs).

    py -3.13 scripts/review_sheet.py                       # medical and survival entries
    py -3.13 scripts/review_sheet.py --category medical
    py -3.13 scripts/review_sheet.py --out review.html

Every entry is printed word for word, with its source and the date it was last
checked, and boxes for the reviewer: correct as written / needs a change /
remove. The sheet carries the commit and a fingerprint (SHA-256) of the exact
text shown, so a review is tied to the words reviewed: if an entry changes
afterwards, the fingerprint no longer matches and it needs reviewing again.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def entry_fingerprint(e) -> str:
    return hashlib.sha256(f"{e.id}\n{e.text}".encode("utf-8")).hexdigest()


def render(categories: tuple[str, ...] = ("medical", "survival")) -> tuple[str, str]:
    """(html, fingerprint of everything on the sheet)."""
    sys.path[:0] = [str(REPO)]
    from cursiv_engine.core import reference as ref
    rows = sorted((e for e in ref.entries() if e.category in categories), key=lambda e: (e.category, e.title))
    whole = hashlib.sha256("".join(entry_fingerprint(e) for e in rows).encode()).hexdigest()
    try:
        commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        commit = ""
    cards = []
    for n, e in enumerate(rows, 1):
        src = ref.source(e.title)
        where = (f'<a href="{html.escape(src.get("url", ""))}">{html.escape(src.get("source", ""))}</a>, '
                 f'checked {html.escape(src.get("checked", ""))}' if src else
                 "<b>No published source</b>: written for Cursiv")
        held = " · <b>held back from chat until reviewed</b>" if e.title in ref.NOT_IN_CHAT else ""
        cards.append(
            f'<section class="entry"><h2>{n}. {html.escape(e.title)} <span>({e.category})</span></h2>'
            f'<p class="src">{where}{held} · <code>{entry_fingerprint(e)[:16]}</code></p>'
            f'<p class="text">{html.escape(e.text)}</p>'
            '<p class="boxes">☐ Correct as written &nbsp; ☐ Needs a change &nbsp; ☐ Remove &nbsp; ☐ Outside my expertise</p>'
            '<div class="notes">Changes or comments:</div></section>')
    page = f"""<!doctype html><meta charset="utf-8"><title>Cursiv reference review</title>
<style>
body{{font-family:Georgia,serif;margin:16mm;color:#111;line-height:1.45}}
h1{{font-size:20pt;margin:0 0 4mm}} .meta td{{padding:1mm 4mm 1mm 0;vertical-align:top}}
.entry{{border-top:1px solid #999;padding:3mm 0;break-inside:avoid}}
.entry h2{{font-size:13pt;margin:0}} .entry h2 span{{font-weight:normal;color:#555;font-size:10pt}}
.src{{font-size:9pt;color:#444;margin:1mm 0}} .text{{margin:2mm 0}}
.boxes{{font-family:Arial,sans-serif;font-size:10pt}} .notes{{border:1px solid #bbb;height:22mm;padding:1mm;font-size:9pt;color:#666}}
code{{font-size:8.5pt}} .sign td{{padding:3mm 4mm 3mm 0}} .line{{border-bottom:1px solid #333;width:70mm;display:inline-block}}
</style>
<h1>Cursiv offline reference: professional review</h1>
<p>Each entry below is shown to people in Cursiv when no internet is available, often in an
emergency. Please mark each one. Cursiv will say an entry was reviewed only if you marked it
"correct as written", and will name you only if you agree below.</p>
<table class="meta">
<tr><td>Entries</td><td>{len(rows)} ({", ".join(categories)})</td></tr>
<tr><td>Printed</td><td>{date.today().isoformat()} from commit {html.escape(commit or "unknown")}</td></tr>
<tr><td>Fingerprint</td><td><code>{whole}</code></td></tr>
</table>
<table class="sign">
<tr><td>Reviewer</td><td><span class="line"></span></td></tr>
<tr><td>Qualification and licence</td><td><span class="line"></span></td></tr>
<tr><td>Date</td><td><span class="line"></span></td></tr>
<tr><td>May Cursiv name you as the reviewer?</td><td>☐ Yes &nbsp; ☐ No, record the qualification only</td></tr>
</table>
{"".join(cards)}
"""
    return page, whole


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--category", default="medical,survival", help="comma-separated: medical, survival, science")
    ap.add_argument("--out", default="", help="where to save (default: Cursiv-reference-review-<date>.html here)")
    a = ap.parse_args()
    page, whole = render(tuple(c.strip() for c in a.category.split(",") if c.strip()))
    out = Path(a.out or f"Cursiv-reference-review-{date.today().isoformat()}.html")
    out.write_text(page, encoding="utf-8")
    print(f"saved {out.resolve()}\nfingerprint {whole}")


if __name__ == "__main__":
    main()
