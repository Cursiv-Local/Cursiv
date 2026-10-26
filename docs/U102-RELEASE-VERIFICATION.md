# U102 release verification — October 25, 2026

## Immutable source and gates

- Tag: `v3.14-U102`; source: `36a2428905c125ee54c743806f9ee9a61f93ffda`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/32.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40248733315 (JUnit XML kept as
  artifacts `test-results-windows-latest`, `-macos-latest`, `-ubuntu-latest`).
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40249446666.

All protected checks passed on the PR and on exact main, including the
"USB portability (end to end)" step inside both `test` jobs. `test-linux` (experimental, not
release-blocking; see [SUPPORT-MATRIX](SUPPORT-MATRIX.md)) also passed.

## Executed source checks

Full isolated Windows suite: **2,073 passed, 14 skipped** (on the tag, in the locked
environment). Of the 14 skips, 13 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model) and 1 needs a Mac's Keychain. Hosted Windows: **2,073 / 14 skips**; Mac:
**2,056 / 31 skips**; Linux: **2,055 / 32 skips**. USB gate: 25 on Windows, 24 + 1 platform
skip on Mac and Linux, passed. Required workspace gate: **63 passed** on both.

New in U102:
- `tests/test_plugin_isolation.py`: the Windows Job Object stops, with no audit hook at all,
  starting a program, `os.system`, a 2 GB allocation, an endless loop and reading the clipboard;
  if the job can't be applied nothing runs; secrets in the environment never reach a code run.
- `tests/test_calc_bench.py`: the 237-case calculation benchmark (`bench/calc200`), 237/237.
  First run before fixes: 221/237 (six defects, all fixed; see CHANGELOG).
- `tests/test_notebook_integrity_matrix.py`: 13 notebook scenarios plus the rebuilt-chain limit
  ([results](NOTEBOOK-INTEGRITY.md)).
- `tests/test_encryption_recovery.py`: full disk, truncated and bit-flipped encrypted stores,
  writing a recovery copy to a new file, refusing a tampered copy.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and required the
frozen app's **ALL PASSED** result. Its plugin-isolation check now runs the plugin inside the
Windows Job Object (`Cursiv.exe --plugin-runner` as a confined child) and passed, in the installed
layout and in the USB layout (`verify_portable`). The tagged Mac workflow passed its source suite
and frozen **ALL PASSED** check. Both aliases match their versioned installers. Checksums and
provenance (both recording source `36a2428`) were checked before the eight assets were signed
locally with the existing owner key; the signer verified the manifest independently.

Windows SHA-256: `c7e0601f583f91eaeec66b18995913f395e28bbd32fb3148d725aa3a0d518321`.

Mac SHA-256: `d3ef3545de1c3dd2a5b67fd0a6b2d91da40f669df2414f67a8921fa125a4cc8e`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

The owner has run the physical tests (installed app, USB drive and external SSD across clean PCs)
on Windows. There is no physical testing on a Mac.

## Remaining limits

No new 158-case model-accuracy benchmark is claimed. Plugins and code runs still run as the same
Windows user: reading files the user can read is stopped by the audit hook, not the OS (no restricted
token or AppContainer). macOS/Linux confinement is resource limits only. Recovery copies can be
written out from Python, not yet from a menu. All results are the project's own testing; nothing has
been independently reviewed. See [THREAT-MODEL](THREAT-MODEL.md) and [RECOVERY](RECOVERY.md).
