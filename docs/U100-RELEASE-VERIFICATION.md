# U100 release verification — October 25, 2026

## Immutable source and gates

- Tag: `v3.14-U100`; source: `7c297d507596a055b8d679f6a50fdd643b6306f6`.
- Source PR: https://github.com/Cursiv-Local/Cursiv/pull/24 (memory you can see and steer, the
  audit of the owner's U99 test run, version 3.14-U100 and release notes).
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40221380586.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40222033037.

All protected checks passed on the PR and on exact main, including the
"USB portability (end to end)" step inside both `test` jobs.

## Executed source checks

Full isolated Windows suite: **2,021 passed, 14 skipped** (on the tag, in the locked
environment). Of the 14 skips, 13 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model) and 1 needs a Mac's Keychain. Hosted Windows: **2,021 / 14 skips**; Mac:
**2,006 / 29 skips**. USB gate (`-m usb`, 25 tests on Windows, 24 + 1 platform skip on
Mac): passed in CI. Required workspace gate: **63 passed** on both.

New in U100: `tests/test_notebook_audit.py`, `tests/test_conversation_audit.py` and
`tests/test_science_audit.py` (each test reproduces a failure from the owner's U99 test run),
`tests/test_session_notes.py`, `tests/test_memory_suggestions.py`,
`tests/test_memory_markdown.py` and `tests/test_guidance.py`.

Separate measured results, on qwen3:4b-instruct, recorded in [MEMORY-U100](MEMORY-U100.md):
suggested memories on a held-out set never used for tuning, 20% → 90% of lasting facts offered
on the first run (2 false cards, 0 sensitive), then 70–80% with 0 false cards after two rules
that run prompted. A live replay of the owner's notebook conversation
(`scripts/replay_notebook.py`) stores W-001 with its sample ID, finds it, verifies it and
corrects it with the original kept.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and
required the frozen app's **ALL PASSED** result, including plugin isolation. It then
started the built app from a USB layout (`verify_portable`), where the same checks
passed. The tagged Mac workflow passed its source suite and frozen **ALL PASSED** check,
including plugin isolation. Both aliases match their versioned installers. Checksums and
provenance (both recording source `7c297d5`) were checked before the eight assets were
signed locally with the existing owner key; the signer verified the manifest
independently.

Windows SHA-256: `b077eade44456aafc11bbd96db018175a02ac38d0286c873adfd0af98744ef9f`.

Mac SHA-256: `45ea92435efdf9032ed058b56ff6d769ef72cfd0b7918d67cb9b2e588c66f5b1`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

## Remaining limits

No new 158-case model-accuracy benchmark is claimed. Overconfident explanations (a 0.4 °C
thermometer difference called "normal") are addressed only by guidance to the model, which
the 4B model doesn't fully follow. Notebook entries saved wrongly by U99 stay as they are
(append-only); they can be corrected in the Field Notebook window. The owner tests U100 in the
installed app and on the portable SSD after release.
