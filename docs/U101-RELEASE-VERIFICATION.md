# U101 release verification — October 25, 2026

## Immutable source and gates

- Tag: `v3.14-U101`; source: `df74806ad87e2b33e2bc34bf2ae3d98758d67d94`.
- Source PRs: https://github.com/Cursiv-Local/Cursiv/pull/28 (starter profiles, version 3.14-U101),
  https://github.com/Cursiv-Local/Cursiv/pull/29 (codex sandbox, Linux CI, field formulas,
  contributor guide) and https://github.com/Cursiv-Local/Cursiv/pull/30 (data safety).
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40241877304.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40242465036.

All protected checks passed on the PRs and on exact main, including the
"USB portability (end to end)" step inside both `test` jobs. The new `test-linux` job
(not yet a required check) also passed.

## Executed source checks

Full isolated Windows suite: **2,048 passed, 14 skipped** (on the tag, in the locked
environment). Of the 14 skips, 13 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model) and 1 needs a Mac's Keychain. Hosted Windows: **2,048 / 14 skips**; Mac:
**2,033 / 29 skips**; Linux: **2,032 / 30 skips**. USB gate (`-m usb`, 25 tests on Windows,
24 + 1 platform skip on Mac and Linux): passed in CI. Required workspace gate: **63 passed**
on both.

Before the tag, one of four local full-suite runs on the release branch had a single failure
that didn't recur in the next three runs, in CI, or on the tag; which test it was wasn't
captured. It is recorded here rather than assumed away.

New in U101: `tests/test_starter_profiles.py`, `tests/test_login_files.py`,
`tests/test_damaged_lines.py`, field-formula tests in `tests/test_science_audit.py`, codex sandbox
tests in `tests/test_plugin_isolation.py` and import-privacy tests in
`tests/test_notebook_encryption.py`.

Separate measured result, qwen3:4b-instruct: `scripts/fieldcalc_bench.py` (14 field calculations
and 4 trick questions through the full chat path, offline): **9/14 right before, 14/14 after**,
0 trick questions calculated by code.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and
required the frozen app's **ALL PASSED** result, including plugin isolation. It then
started the built app from a USB layout (`verify_portable`), where the same checks
passed; that packaged copy contains the five starter profiles
(`cursiv_engine/agents/starters/*.md`) and the code-run guard (`core/plugin_runner.py`). The
tagged Mac workflow passed its source suite and frozen **ALL PASSED** check. Both aliases match
their versioned installers. Checksums and provenance (both recording source `df74806`) were
checked before the eight assets were signed locally with the existing owner key; the signer
verified the manifest independently.

Windows SHA-256: `adea1b166b683ab61e3bf5f803081d8d1161b87ce736be5431890e3789a08bc8`.

Mac SHA-256: `af9844903475e370c14d9af54c10ecec5ddfd49a2a6ea81596af62a465cd80ce`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

The owner validated the encrypted-vault USB round trip across clean PCs (2026-10-25).

## Remaining limits

No new 158-case model-accuracy benchmark is claimed. Overconfident explanations are still
addressed only by guidance to the model. A Linux app is not packaged (only the tests run on
Linux). Phone uploads over 64 MB are still stored readable on an encrypted computer (set apart
and listed by the receiver).
