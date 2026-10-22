# U82 release verification

## Published source and Windows installer

- Public release: [Cursiv v3.14-U82](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U82).
- Published: 2026-10-22 at 17:54:16 UTC, marked Latest, not draft/prerelease.
- Source: [f14c033103aba27d3b9993912f29c2a6b618974a](https://github.com/Cursiv-Local/Cursiv/commit/f14c033103aba27d3b9993912f29c2a6b618974a).
- Tag: v3.14-U82, resolving to that exact source commit. Earlier published tags
  and assets were preserved. U80's preexisting draft was not published.
- Windows files: Cursiv-Setup-3.14-U82.exe and Cursiv-Setup-latest.exe, each
  **53,343,967 bytes** (about 53 MB), with identical contents.
- Windows SHA-256:
  b5dc52f8bff98dfae098141dc950e7f6b05e1b1a1dacd608d75b66cc8175098b
- SHA256SUMS.txt lists both Windows names. Its normal Windows CRLF line endings
  are supported by the verification check.

The unauthenticated GitHub latest-release API returned v3.14-U82. An independent,
unauthenticated full download through the stable latest-installer URL returned
the actual executable with exactly the size/hash above. The installer reports
product version 3.14-U82.

The existing updater comparison was checked: U82 is newer than U81; U81 is not
newer than itself. No updater or networking policy was changed. Offline mode must
be off for an online check. This publication does not install the update on the
owner's computer.

## Source and packaged checks

[Release-commit CI](https://github.com/Cursiv-Local/Cursiv/actions/runs/39820518992):

- Windows: **1,080 passed, 1 skipped**.
- Mac: **1,070 passed, 11 skipped**.
- Local isolated release-preparation run: **1,080 passed, 1 skipped**.

The Windows executable built from the tag passed its frozen self-test with
disposable home/data paths:

- Chat engine, commands, launcher/window code and PDF imports.
- Writable disposable data directories.
- 112 bundled offline reference entries.
- Unit/coordinate calculations.
- Notebook append, integrity chain, exports and signature verification.
- Document search.
- Offscreen chat window construction.

The self-test did not start/download an AI engine or change the owner's real
data. No live-model quality test or installation on the owner's computer is claimed.

## Windows build environment correction

The first package candidate was rejected by its self-test because QtCore and
QtWidgets could not load. A minimal packaged Qt probe reproduced the problem.
Its dependency analysis identified ICU/UCRT libraries collected from unrelated
Poppler/libheif directories inherited in the build environment's PATH.

Isolating those libraries made the same Qt probe pass. The final installer was
rebuilt using only the repository's declared requirements and a process PATH
restricted to Python, Git and Windows system directories. Its dependency list
contains no libraries from those unrelated tool directories, and its complete
packaged self-test passed. The failed candidate was never published.

Final build tools: Python 3.13.13, PyInstaller 6.22.3, PyQt6 6.11.0 and Qt 6.11.2.
The existing tagged-source builder was used; application source/storage formats
were unchanged by this build-environment correction. Future builds should use an
isolated requirements environment and exclude unrelated native-tool PATH entries.

## Mac release automation

[U82 Mac package workflow](https://github.com/Cursiv-Local/Cursiv/actions/runs/39826720885)
builds this same tag. Its tests, native app build and packaged self-test gate the
DMG upload. Consult that run and the release's actual asset list for platform
package availability and its SHA256SUMS-mac.txt. Windows checksums do not apply to
Mac packages.

## Repository and data preservation

README, changelog, implementation report, release notes and handoff record the
changes. This verification record is documentation after the tagged source
commit; it does not move the release tag or change installer contents.
The owner's preexisting test_internals/u81_test.txt is preserved and excluded from
commits and build inputs. No website deployment or production DNS change occurred.
