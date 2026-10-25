# U98 release verification — October 25, 2026

## Immutable source and gates

- Tag: `v3.14-U98`; source: `1bc1593152a91e3de4f40b26f5b4c1528506524a`.
- Source PRs: https://github.com/Cursiv-Local/Cursiv/pull/20 and
  https://github.com/Cursiv-Local/Cursiv/pull/21.
- Exact-main CI: https://github.com/Cursiv-Local/Cursiv/actions/runs/40168966310.
- Tagged Mac build: https://github.com/Cursiv-Local/Cursiv/actions/runs/40169427781.

All five protected checks passed on both PRs and on exact main, including the
"USB portability (end to end)" step inside both `test` jobs.

The first U98 tag (not published) pointed at the PR #20 merge. Its tagged Windows build
stopped at the new packaged "plugin isolation" self-test: inside `Cursiv.exe
--plugin-runner` the `socket` module was already loaded, so a plugin's `import socket`
didn't raise the import audit event (using a socket was still refused). PR #21 makes the
runner unload the blocked modules first; the tag was moved to that merge before anything
was published.

## Executed source checks

Full isolated Windows suite: **1,915 passed, 1 skipped** (on the tag, in the locked
environment). Hosted Windows: **1,915 / 1 skip**; Mac: **1,900 / 16 skips**. USB gate
(`-m usb`, 25 tests on Windows, 24 + 1 platform skip on Mac): passed in CI and in the
pre-commit hook. Required workspace gate: **63 passed**.

New in U98: `tests/test_plugin_isolation.py` (separate process, no secrets, network /
programs / native code / outside files refused, already-loaded modules still refused,
Forge tests in the runner), `tests/test_notebook_encryption.py`,
`tests/test_agents_vault.py` and `tests/test_chat_badges.py`.

## Tagged packages, USB start and owner proof

The Windows helper built a clean tagged checkout with the pinned dependencies and
required the frozen app's **ALL PASSED** result, which now includes "PASS plugin
isolation: a plugin ran in its own process; network access was refused". It then
started the built app from a USB layout (`verify_portable`), where the same checks
passed. The tagged Mac workflow passed its source suite and frozen **ALL PASSED** check,
including plugin isolation. Both aliases match their versioned installers. Checksums and
provenance (both recording source `1bc1593`) were checked before the eight assets were
signed locally with the existing owner key; the signing tools matched their stored hashes
first, and the signer verified the manifest independently.

Windows SHA-256: `1f62566b3af118ab816042b82a78f2bab31aece7fb79be28b6f3315c3998492a`.

Mac SHA-256: `4c7fc38bd30a4e476bb220e25172bd57aee45b2430e7ea1cb2bc3fadd35a1b3e`.

Owner fingerprint:
`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`.
No private key material entered the checkout, CI or packages.

## Remaining limits

No new model-accuracy benchmark is claimed. Plugin isolation is process separation with
a Python audit hook, not an operating-system sandbox: a plugin still runs as the same
Windows user, so plugins remain "review before you approve". The owner moved data
computer → USB → another computer on U97 hardware; a clean-machine first start and a
passphrase-recovery drill are not claimed.
