# U104 release verification — October 26, 2026

## Immutable source and gates

- Tag: `v3.14-U104`; source: `47c4ceb9d7addfb78ac0f7a80b1c4992857fc359`.
- Source PRs: https://github.com/Cursiv-Local/Cursiv/pull/38 (team-drive demo fixes),
  https://github.com/Cursiv-Local/Cursiv/pull/40 (Field Station preview) and
  https://github.com/Cursiv-Local/Cursiv/pull/41 (release, /field-station page).
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40345137210 (JUnit XML kept as artifacts).
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40346827361.

All protected checks passed on the PRs and on exact main, including the "USB portability (end to end)" step
inside both `test` jobs. `test-linux` and the new `station-arm64` (both experimental, not release-blocking;
see [SUPPORT-MATRIX](SUPPORT-MATRIX.md)) also passed.

## Executed source checks

Full isolated Windows suite: **2,175 passed, 14 skipped** (on the tag, in the locked
environment). Of the 14 skips, 13 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model) and 1 needs a Mac's Keychain. Hosted Windows: **2,175 / 14 skips**; Mac:
**2,158 / 31 skips**; Linux: **2,157 / 32 skips**. USB gate: **44** on Windows, 43 + 1 platform skip on Mac and
Linux. Required workspace gate: **63 passed** on both.

New in U104:
- `station-arm64`: **113 passed** on GitHub's ARM64 Linux (`aarch64`), installing only the engine's own
  dependencies (`requirements-station.txt`) with the desktop's Qt toolkit blocked. This is the Raspberry Pi
  5's processor type; it is not a Raspberry Pi.
- `tests/test_station_*.py` (51 tests): telemetry from faked `/sys` folders, scenarios A–F, sessions and
  CSRF, first-run setup and unlock with real encryption, a live loopback server (Host and Origin checks,
  locked data, 20 concurrent notebook writes, safe shutdown, storage failing mid-write), static files with no
  inline code, drive discovery by filesystem UUID, a headless import with Qt blocked.
- The Field Station interface was walked through in a desktop browser and at phone width (setup, restart,
  unlock, record, correct, verify, health); the website's screenshots come from the real server
  (`scripts/station_shots.py`) with simulated hardware readings labelled as such.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and required the frozen
app's **ALL PASSED** result, including plugin isolation, in the installed layout and in the USB layout.
The tagged Mac workflow passed its source suite and frozen **ALL PASSED** check. Both aliases match their
versioned installers. Checksums and provenance (both recording source `47c4ceb`) were checked before the
eight assets were signed locally with the existing owner key; the signer verified the manifest
independently. Installers downloaded back from the published release match.

Windows SHA-256: `4dd5c3b4781e84fcb1cbf16dc662b10e55e6b5a4e8c6916106dc9ee489fd8b21`.

Mac SHA-256: `f2f9e23c0e45399e9f1d4a7f06d36537587fc60ba66687e8fb2220455de5298a`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

The owner has run physical tests (installed app, USB drive and external SSD across clean PCs) on Windows in
earlier releases. Team drives and the Field Station are tested automatically only. There is no physical
testing on a Mac or a Raspberry Pi.

## Remaining limits

The Field Station has not run on a Raspberry Pi: real temperature, throttling and battery readings, the
station's own Wi-Fi, SSD and USB workspaces, the installer and local AI on the Pi are untested or planned
(`docs/FIELD-STATION-PLAN.md`, section 8). It uses plain HTTP on its own network. The outside-review items
planned for U104 move to U105. All results are the project's own testing; nothing has been independently
reviewed. See [THREAT-MODEL](THREAT-MODEL.md) and [RECOVERY](RECOVERY.md).
