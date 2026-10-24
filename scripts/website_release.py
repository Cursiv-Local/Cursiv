"""
Point the website and release docs from one published release to the next.

    py -3.13 scripts/website_release.py --old U95 --new U96 \
        --old-hash <previous Windows SHA-256> --new-hash <new Windows SHA-256> \
        --windows 1865 --old-windows 1819 --mac 1850 --mac-skips 16 \
        --summary "One sentence for the Start page." --section "<p>…</p> text for the test page"

Edits only the lines a release changes (download links, Mac link, hash and its id,
signed-manifest link, current-release sentence, software counts, the new test-page
section) in README.md, TECH.md, docs/CLAIM-EVIDENCE.md and website/*.html. Every
replacement must match exactly once (or the stated number of times); otherwise the
script stops before writing anything, so a changed page is never half-updated.
Run `node cloudflare/publish.mjs --build-only` and the website tests afterwards.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("old", "new", "old-hash", "new-hash", "windows", "old-windows", "mac", "mac-skips", "summary",
                 "section", "title"):
        a.add_argument("--" + name, required=name != "title")
    x = a.parse_args()
    old, new = x.old, x.new
    lo, ln = old.lower(), new.lower()
    fmt = lambda n: f"{int(n):,}"
    link = (f"releases/download/v3.14-{old}/Cursiv-Setup-3.14-{old}.exe",
            f"releases/download/v3.14-{new}/Cursiv-Setup-3.14-{new}.exe")
    plan = {
        "README.md": [(f"**[{old}](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-{old})**. See the [release notes](docs/RELEASE-{old}.md)",
                       f"**[{new}](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-{new})**. See the [release notes](docs/RELEASE-{new}.md)", 1)],
        "TECH.md": [(f"{old} source and package checks are recorded in the [verification report](docs/{old}-RELEASE-VERIFICATION.md);",
                     f"{new} source and package checks are recorded in the [verification report](docs/{new}-RELEASE-VERIFICATION.md);", 1)],
        "docs/CLAIM-EVIDENCE.md": [(f"| [{old} verification]({old}-RELEASE-VERIFICATION.md), successful",
                                    f"| [{new} verification]({new}-RELEASE-VERIFICATION.md), successful", 1)],
        "website/index.html": [(*link, None),
                               (f"{old} source passed {fmt(x.old_windows)} software regression tests on Windows",
                                f"{new} source passed {fmt(x.windows)} software regression tests on Windows", 1),
                               (f'href="/ai-reliability-testing#{lo}"', f'href="/ai-reliability-testing#{ln}"', None)],
        "website/testers.html": [(*link, None)],
        "website/vision.html": [(f"{old} source passed {fmt(x.old_windows)} Windows software regression tests",
                                 f"{new} source passed {fmt(x.windows)} Windows software regression tests", 1),
                                (f"neither is a new {old} accuracy result", f"neither is a new {new} accuracy result", 1),
                                (f'href="/ai-reliability-testing#{lo}"', f'href="/ai-reliability-testing#{ln}"', None)],
        "website/start.html": [(*link, None),
                               (f"releases/download/v3.14-{old}/Cursiv-3.14-{old}-mac-arm64.dmg",
                                f"releases/download/v3.14-{new}/Cursiv-3.14-{new}-mac-arm64.dmg", 1),
                               (f'href="/ai-reliability-testing#{lo}"', f'href="/ai-reliability-testing#{ln}"', None),
                               (f'id="code-signing">{old} has an', f'id="code-signing">{new} has an', 1),
                               (f"<b>Windows {old} SHA-256:</b><br><code id=\"windows-{lo}-sha256\" style=\"overflow-wrap:anywhere\">{x.old_hash}</code>",
                                f"<b>Windows {new} SHA-256:</b><br><code id=\"windows-{ln}-sha256\" style=\"overflow-wrap:anywhere\">{x.new_hash}</code>", 1),
                               (f'<a href="/assets/cursiv-owner-release-{old}.json">Signed {old} manifest</a>',
                                f'<a href="/assets/cursiv-owner-release-{new}.json">Signed {new} manifest</a>', 1),
                               (f"Cursiv-Setup-3.14-{old}.exe -Algorithm SHA256", f"Cursiv-Setup-3.14-{new}.exe -Algorithm SHA256", 1),
                               (f"Open <code>Cursiv-Setup-3.14-{old}.exe</code>", f"Open <code>Cursiv-Setup-3.14-{new}.exe</code>", 1)],
        "website/ai-reliability-testing.html": [
            (f'<meta name="description" content="Cursiv {old} software regressions',
             f'<meta name="description" content="Cursiv {new} software regressions', 1),
            (f'<section id="{lo}">',
             f'<section id="{ln}"><div class="wrap"><h2>{new} software and release checks</h2><p>Updated '
             f'October 24, 2026. The full isolated Windows source suite passed <b>{fmt(x.windows)} passed; 1 platform '
             f'test skipped</b>. Hosted Mac source checks passed <b>{fmt(x.mac)} tests; {x.mac_skips} platform skips</b>. '
             f'Both tagged packages passed their frozen self-tests, and the Windows package also passed a start from a '
             f'USB layout. {x.section} <a href="https://github.com/Cursiv-Local/Cursiv/blob/main/docs/{new}-RELEASE-'
             f'VERIFICATION.md">Source, package and owner-signature evidence</a>.</p><p>These are software checks, not a '
             f'new model-accuracy score. No new full 158-case {new} model result is claimed. Historical results below are '
             f'unchanged. Windows CA signing and Mac notarization remain separate checks.</p></div></section>\n'
             f'<section id="{lo}">', 1)],
    }
    import re
    # Matched after the anchor links above were already moved to the new release.
    current = re.compile(r'<p class="fine">Current release: ' + old + r'\. [^<]*<a href="/ai-reliability-testing#' + ln + '">')
    staged = {}
    for rel, pairs in plan.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        for before, after, times in pairs:
            n = text.count(before)
            if n == 0 or (times is not None and n != times):
                raise SystemExit(f"{rel}: expected {times or 'at least 1'} of {before[:80]!r}, found {n}. Nothing written.")
            text = text.replace(before, after)
        if rel == "TECH.md" and x.title:
            row = re.search(r"(?m)^\| " + old + r": .*\|\s*$", text)
            if not row:
                raise SystemExit(f"TECH.md: no release-table row for {old}. Nothing written.")
            text = (text[:row.end()] + f"\n| {new}: {x.title} | [Release notes](docs/RELEASE-{new}.md), "
                    f"[verification](docs/{new}-RELEASE-VERIFICATION.md) |" + text[row.end():])
        if rel == "website/start.html":
            text, n = current.subn(f'<p class="fine">Current release: {new}. {x.summary} '
                                   f'<a href="/ai-reliability-testing#{ln}">', text)
            if n != 1:
                raise SystemExit("website/start.html: current-release sentence not found once. Nothing written.")
        staged[path] = text
    for path, text in staged.items():
        path.write_text(text, encoding="utf-8")
    print("Updated:", ", ".join(str(p.relative_to(ROOT)) for p in staged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
