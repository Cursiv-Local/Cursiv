# U103 release verification — October 26, 2026

## Immutable source and gates

- Tag: `v3.14-U103`; source: `5c821ca021c6d38bd27262454097d2a9daf13cd2`.
- Source PRs: https://github.com/Cursiv-Local/Cursiv/pull/35 (overconfidence check, silent-error lint,
  phone and USB safety) and https://github.com/Cursiv-Local/Cursiv/pull/36 (team field drives).
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40264814995 (JUnit XML kept as
  artifacts `test-results-windows-latest`, `-macos-latest`, `-ubuntu-latest`).
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40265454873.

All protected checks passed on both PRs and on exact main, including the "USB portability (end to end)"
step inside both `test` jobs. `test-linux` (experimental, not release-blocking; see
[SUPPORT-MATRIX](SUPPORT-MATRIX.md)) also passed.

## Executed source checks

Full isolated Windows suite: **2,122 passed, 14 skipped** (on the tag, in the locked
environment). Of the 14 skips, 13 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model) and 1 needs a Mac's Keychain. Hosted Windows: **2,122 / 14 skips**; Mac:
**2,105 / 31 skips**; Linux: **2,104 / 32 skips**. USB gate: **44** on Windows (25 in U102), 43 + 1
platform skip (a Windows junction test) on Mac and Linux, passed. Required workspace gate: **63 passed**
on both.

New in U103:
- `tests/test_team_drives.py`, in the mandatory USB gate: three scientists' named drives used on several
  PCs (the main computer included) arrive on the main computer one at a time, every entry and photo byte
  for byte, in each scientist's name, without touching the main notebook; 20 drives with 1,200 entries and
  photos; six kinds of damage on a drive refused whole; a drive pulled mid-import leaves nothing
  half-written; importing again changes no bytes; a new drive carries only the notebooks chosen.
  `tests/test_fieldsync.py` joined the gate, and `tests/test_usb_end_to_end.py` runs the real Make USB with
  a name and chosen notebooks.
- `tests/test_overconfidence.py` and `bench/overconfidence` (live run with qwen3:4b-instruct, 50 risk
  questions labelled by hand; [results](../bench/overconfidence/RESULTS.md)).
- `tests/test_silent_errors.py`: storage code may not ignore an error without saying why; it found three
  that were hiding real failures (all fixed).
- `tests/test_phone_sync.py`, `tests/test_problem_report.py`, `tests/test_confirm_cards.py`: code that had
  no tests. The security-answer attempt limit is in `tests/test_password_reset.py`.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and required the frozen
app's **ALL PASSED** result, including plugin isolation, in the installed layout and in the USB layout.
The tagged Mac workflow passed its source suite and frozen **ALL PASSED** check. Both aliases match their
versioned installers. Checksums and provenance (both recording source `5c821ca`) were checked before the
eight assets were signed locally with the existing owner key; the signer verified the manifest
independently. Installers downloaded back from the published release match.

Windows SHA-256: `9e71f353149491b1b2ec7a661824ea64e7d4deb8f028c41f419dcf28b59b5510`.

Mac SHA-256: `3b286f1b077562ba4afc35811cac61768cad73419ea1e2a224f6acce81aaa076`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

The owner has run physical tests (installed app, USB drive and external SSD across clean PCs) on Windows
in earlier releases. Team drives are tested automatically only; there is no physical multi-drive test yet,
and no physical testing on a Mac.

## Remaining limits

A drive already used on two different PCs before U103 labels entries by PC and is still refused at import.
On a drive, the team copy is refreshed at start, quit, notebook close and at most every 30 s while
recording, so pulling a drive with Cursiv open can leave the last entries for the next start. The
overconfidence note catches a settled verdict at the start of an answer, not one inside a structured
answer, and 50 questions from one model is a small sample. Plugins and code runs still run as the same
Windows user. All results are the project's own testing; nothing has been independently reviewed. See
[THREAT-MODEL](THREAT-MODEL.md) and [RECOVERY](RECOVERY.md).
