"""U105 (outside review): release documents stay consistent, as part of the normal test run.

tests/test_versions.py already checks that the app, the updater and the installer carry one version. This
checks what went stale before: release notes for the current version, verification documents that every
release note links to, the README naming a current release, the signed manifests the website serves, and
the docs index. The current release's own verification document is written after it's built (in the
evidence PR), so only that one may still be missing."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def _current() -> int:
    v = re.search(r'VERSION\s*=\s*"3\.14-U(\d+)"', (ROOT / "cursiv_engine/core/selfknow.py").read_text(encoding="utf-8"))
    assert v, "selfknow.VERSION isn't a 3.14-U<n> version"
    return int(v.group(1))


def _verified() -> list[int]:
    return sorted(int(m.group(1)) for p in DOCS.glob("U*-RELEASE-VERIFICATION.md")
                  if (m := re.fullmatch(r"U(\d+)-RELEASE-VERIFICATION\.md", p.name)))


def test_the_current_version_has_release_notes_and_a_changelog_entry():
    n = _current()
    assert (DOCS / f"RELEASE-U{n}.md").is_file(), f"write docs/RELEASE-U{n}.md for this version"
    assert re.search(rf"(?m)^## 3\.14-U{n} ", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")), \
        f"CHANGELOG.md has no '## 3.14-U{n}' heading"


def test_every_linked_verification_document_exists():
    n = _current()
    missing = []
    for notes in sorted(DOCS.glob("RELEASE-U*.md")):
        for k in re.findall(r"U(\d+)-RELEASE-VERIFICATION\.md", notes.read_text(encoding="utf-8")):
            if int(k) != n and not (DOCS / f"U{k}-RELEASE-VERIFICATION.md").is_file():
                missing.append(f"{notes.name} links U{k}-RELEASE-VERIFICATION.md")
    assert not missing, missing


def test_the_readme_names_a_current_release():
    n = _current()
    named = {int(k) for k in re.findall(r"v3\.14-U(\d+)", (ROOT / "README.md").read_text(encoding="utf-8"))}
    assert named & {n, n - 1}, f"README.md names {sorted(named)}; it should name U{n} (or U{n - 1} until the evidence PR)"


def test_every_verified_release_has_its_signed_manifest_on_the_website():
    missing = [k for k in _verified() if k >= 89
               and not (ROOT / "website" / "assets" / f"cursiv-owner-release-U{k}.json").is_file()]
    assert not missing, f"website/assets lacks cursiv-owner-release-U<k>.json for {missing}"


def test_the_docs_index_lists_every_verified_release():
    index = (DOCS / "README.md").read_text(encoding="utf-8")
    missing = [k for k in _verified() if k >= 100 and f"[U{k}](U{k}-RELEASE-VERIFICATION.md)" not in index]
    assert not missing, f"docs/README.md has no row for {missing}"
