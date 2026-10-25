# U99 release verification — October 25, 2026

## Immutable source and gates

- Tag: `v3.14-U99`; source: `3345d8b39416eb7453832b103625001e4fb30c6a`.
- Source PRs: https://github.com/Cursiv-Local/Cursiv/pull/23 (conversational actions and
  operational self-knowledge) and https://github.com/Cursiv-Local/Cursiv/pull/25
  (version 3.14-U99, changelog, release notes).
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40209332058.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40210037537.

All protected checks passed on both PRs and on exact main, including the
"USB portability (end to end)" step inside both `test` jobs.

## Executed source checks

Full isolated Windows suite: **1,979 passed, 13 skipped** (on the tag, in the locked
environment). Of the 13 skips, 12 are the live-model evaluation
(`tests/test_self_knowledge_live.py`, runs only with `CURSIV_LIVE=1` against a running
model) and 1 needs a Mac's Keychain. Hosted Windows: **1,979 / 13 skips**; Mac:
**1,964 / 28 skips**. USB gate (`-m usb`, 25 tests on Windows, 24 + 1 platform skip on
Mac): passed in CI. Required workspace gate: **63 passed** on both.

New in U99: `tests/test_self_knowledge.py` (capability registry, evidence records, claim
checks, writing-not-refused, fiction labels), `tests/test_self_knowledge_live.py`,
`tests/test_intent.py` (conversational actions: every value checked against the user's
words, confirm before change) and `tests/test_code_map.py`.

The conversational-action benchmark (`scripts/intent_bench.py`, qwen3:4b-instruct) is a
separate measured result, recorded in [CONVERSATIONAL-ACTIONS-U99](CONVERSATIONAL-ACTIONS-U99.md):
on the held-out set never used for tuning, 94.0% right action, 90.3% offered correctly,
0 of 19 trick messages produced a card.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and
required the frozen app's **ALL PASSED** result, including plugin isolation. It then
started the built app from a USB layout (`verify_portable`), where the same checks
passed. The tagged Mac workflow passed its source suite and frozen **ALL PASSED** check,
including plugin isolation. Both aliases match their versioned installers. Checksums and
provenance (both recording source `3345d8b`) were checked before the eight assets were
signed locally with the existing owner key; the signer verified the manifest
independently.

Windows SHA-256: `3aa2f8d5097bf8b1c680e8d12f5fe4203d74026a13d5c63762fb547c74778751`.

Mac SHA-256: `c91eb8c10a54a7edba72db0fb7fbb8553292393088881293e2e6809176b24525`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

## Remaining limits

No new 158-case model-accuracy benchmark is claimed. The local model can still write
absolute privacy lines ("no cloud") in posts about Cursiv; the deterministic correction
note under them is the protection, not the model. The owner is testing U99 in the
installed app after release.
