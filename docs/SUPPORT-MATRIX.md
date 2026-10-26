# Supported platforms (U102)

| Platform | Package | Release-blocking CI | Physical testing | Code-run isolation |
|---|---|---|---|---|
| Windows 10/11 x64 | Installer and USB drive (`Cursiv-Setup-*.exe`) | Yes: `test (windows-latest)`, `workspace-files (windows-latest)`, packaged self-test, USB start | Owner: installed app, USB and external SSD across clean PCs (2026-10-25) | Job Object + audit hook |
| macOS 13+ Apple Silicon | `.dmg` (early) | Yes: `test (macos-latest)`, `workspace-files (macos-latest)`, packaged self-test in the Mac build | **None**: the project has no Mac to test on | Resource limits + audit hook |
| Linux x64 | None (source only) | **No** (experimental): `test-linux` runs on every push but doesn't block | None | Resource limits + audit hook |

Every test job uploads JUnit XML (`test-results-<os>`) as a workflow artifact.

"Physical testing" means the owner ran it on real hardware; CI is GitHub's hosted machines. Mac
packages are built and self-tested in CI only, and say so in each release's verification report.
Authenticode (Windows) and notarization (Apple) are not in place; packages are authenticated by the
owner signature instead.
