# HANDOFF FOR CHATGPT (or any assistant): CURSIV U105 (OUTSIDE-REVIEW FIXES)

**Read this first if you are picking up U105.** Kept current by Claude after every step, in case that session
runs out of usage. Owner: Joshua Winkler. Repo: https://github.com/Cursiv-Local/Cursiv (local checkout
`C:\Users\joshu\OneDrive\Documents\GitHub\Cursiv-v3`, Windows 11, Git Bash + PowerShell). Branch:
**`claude/u105`** (from `main` at `b5d457d`, after the U104 release). For the separate Raspberry Pi work see
`docs/FIELD-STATION-HANDOFF.md`.

Last updated: 2026-10-26, 3 of 4 items done.

## What U105 is

Four fixes from an outside review (the owner approved "Start U105" with exactly these):

| # | Item | Status |
|---|---|---|
| 1 | Drive signing-key passphrase, and a warning when a drive is made | **done**, commits `1c13882` + `14065aa` (fix) |
| 2 | Strict, photo-complete team import | **done**, commit `9eb3161` |
| 3 | Vosk model checksum + safe unzip limits (also for the Ollama zip) | **done**, commit `9b9089c` |
| 4 | Release-document consistency test | **not started** |

Then: full suite, CHANGELOG + `docs/RELEASE-U105.md`, version bump, PR, CI, merge, release (runbook below).

## Done so far

1. `cursiv_engine/core/devicekey.py`: `protect(passphrase)` re-stores the SAME Ed25519 key as
   `"pp1:" + base64(salt) + ":" + Fernet(scrypt via vault.derive)` so its key_id and every main computer's
   pin stay valid; `unlock(passphrase)`, `lock()`, `protected()`, `unlocked()`; `load()` raises
   `KeyLocked` (a ValueError) for a locked protected key and NEVER makes a new key in that case (a new key =
   a new identity that main computers refuse). `MIN_PASSPHRASE = 10`. Field Notebook (`launcher/
   field_notebook.py`): "Signing key…" button (protect with passphrase typed twice / unlock / status) and a
   status line when the key is locked. Make USB (`launcher/usb_ops.py`, named drives) warns the key is
   readable until protected. Tests: `tests/test_signing_key_passphrase.py` (5 passed), including a main
   computer still accepting a protected drive's shares.
2. `cursiv_engine/core/fieldsync.py`: `import_folder(folder, *, strict=False)`; strict checks every photo
   first (`_import_photos(..., copy=False)`) and refuses the whole notebook if any photo is missing, too big
   or doesn't match its SHA-256 name, copying nothing. Command `field log import --strict <folder>`; Field
   Notebook Import menu "From a USB stick or shared folder, every photo required…". Test in
   `tests/test_team_drives.py` (`test_strict_import_...`), part of the mandatory USB gate.

## How to do item 3 (Vosk checksum + safe unzip)

- Where: `cursiv_engine/agents/voice_agent.py` `_ensure_vosk_model()` (~line 148) downloads
  `https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip` with `urlretrieve` and runs
  `zipfile.ZipFile(...).extractall(_VOICE_DIR)` with no checksum. `launcher/usb_ops.py` `_download_ollama()`
  checks Ollama's SHA-256 (from GitHub's release digest) but also uses plain `extractall`.
- Plan: new module `cursiv_engine/core/safe_zip.py` with `extract(zip_path, dest, *, max_files, max_bytes,
  max_file_bytes)`: refuse absolute paths, `..`, drive letters, symlinks (external_attr mode 0o120000);
  count real uncompressed bytes while reading (sizes in a zip can lie) and stop past the limit; extract
  into a temporary folder next to `dest`, then `os.replace` into place; never overwrite an existing folder.
  Limits: Vosk 2,000 files / 200 MB; Ollama 20,000 files / 8 GB (check the real unpacked size first).
- Pin the Vosk zip: MEASURED 2026-10-26 by downloading it: SHA-256
  `30f26242c4eb449f948e42cb302dd7a686cb29a3423a8367f99ff41780942498`, 41,205,931 bytes, 20 files, 70,898,967
  bytes unpacked, one top folder `vosk-model-small-en-us-0.15/`. Store it as `_VOSK_SHA256` and check before
  extracting (delete the zip and raise on mismatch, like `_download_ollama`). Do NOT guess the hash.
- Tests (`tests/test_safe_zip.py`): traversal names, absolute names, symlink entries, too many files, a zip
  whose declared sizes understate the data, a good zip extracted completely, checksum mismatch refused,
  and that nothing is left half-extracted after a refusal. Add the module to `docs/CODE-MAP.md`.

## How to do item 4 (release-document consistency test)

New `tests/test_release_docs.py`: version = `cursiv_engine/core/selfknow.VERSION` (e.g. `3.14-U105`);
`launcher/cursiv_launcher.py _CURRENT_VERSION` and `installer/cursiv_setup.iss` (`AppVer`,
`OutputBaseFilename`) must equal it; `docs/RELEASE-U<n>.md` and a CHANGELOG `## 3.14-U<n>` heading must
exist for it; every older `docs/RELEASE-U*.md` that links `U*-RELEASE-VERIFICATION.md` must have that file;
`README.md` must name the current release or the one before (it moves after the release, in the evidence
PR); `website/assets/cursiv-owner-release-U<k>.json` must exist for every verified release since U99. Check
what already exists first (`git grep -l "_CURRENT_VERSION" tests`).

## Release runbook (as used for U100-U104)

1. Bump `selfknow.VERSION`, `launcher/cursiv_launcher.py _CURRENT_VERSION`, `installer/cursiv_setup.iss`
   (title line, AppVer, output name); write `docs/RELEASE-U105.md`; CHANGELOG heading with date.
2. Full suite: `"$LOCALAPPDATA/Temp/cursiv-u88-build-39c0ad1699b74be8bab5385ce1b281d8/Scripts/python.exe" -m
   pytest tests -q -p no:cacheprovider -rfs` (expect ~2,190 passed, 14 skipped). Never pip-install into that venv.
3. Stage files BY NAME (never `git add -A`: untracked `docs/CURSIV-LEGAL-HANDOFF.md`, `field-notes.txt`,
   `test_internals/` must never be committed). PR to `main`, wait for CI (all jobs incl. `station-arm64`),
   merge, wait for main CI.
4. `git tag -a v3.14-U105 -m "..." <full merge sha>`; push tag; `gh workflow run mac-build.yml -f
   ref=v3.14-U105 -f upload=false`; `python scripts/build_release.py v3.14-U105` (Windows build, ALL PASSED
   required); full suite on the tag in a detached worktree.
5. Assets in `release-u105/assets`: versioned + `-latest` Windows exe, `provenance-3.14-U105.json`,
   `SHA256SUMS.txt`, Mac dmg + `Cursiv-mac-latest.dmg`, `SHA256SUMS-mac.txt`, `provenance-mac.json`. Verify
   checksums. Owner-sign (the signer needs the FULL 40-char commit and must run with LOCALAPPDATA pointed at
   the signing folder; it never copies the key):
   `S="$LOCALAPPDATA/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/CursivReleaseSigning"; LOCALAPPDATA="$(cygpath -w "$S/..")" <venv python> -I "$S/signer/scripts/owner_release.py" sign --version 3.14-U105 --commit <full sha> --output owner-release.json <the 8 files>`
   then copy `website/assets/cursiv-owner-release-key.json` in, write `u105-release-verification.json`.
6. `gh release create v3.14-U105 --verify-tag --latest --title "..." --notes-file docs/RELEASE-U105.md
   release-u105/assets/*`; cancel the release-triggered Mac run; download the installers back and compare hashes.
7. Evidence PR: `py -3.13 scripts/website_release.py --old U104 --new U105 --old-hash 4dd5c3b4781e84fcb1cbf16dc662b10e55e6b5a4e8c6916106dc9ee489fd8b21 --new-hash <new> --windows <n> --windows-skips 14 --old-windows 2175 --mac <n> --mac-skips <n> --title ... --summary ... --section ...`,
   `docs/U105-RELEASE-VERIFICATION.md`, `docs/README.md` row, HANDOFF note,
   `website/assets/cursiv-owner-release-U105.json`; then `node cloudflare/publish.mjs --build-only`,
   `node --test cloudflare/tests/*.test.mjs` (22), merge, `node cloudflare/publish.mjs`, check cursiv.us.

Owner rules: upward progression only; never delete user data; don't claim live-model results from mocks;
commit/push/release only when the owner asks (he asked for U105 work; ask before releasing if unsure).

## Progress log (newest first)

- 2026-10-26: item 3 committed (`9b9089c`): `cursiv_engine/core/safe_zip.py` (`extract(zip, dest, max_files,
  max_bytes, max_file_bytes)`, raises `UnsafeZip`), `voice_agent._install_vosk_zip()` checks `_VOSK_SHA256`
  then unpacks via safe_zip into a temp folder and moves `vosk-model-small-en-us-0.15/` into place;
  `usb_ops._download_ollama` uses safe_zip (20,000 files / 12 GB / 4 GB per file). `tests/test_safe_zip.py`
  (16; the real-download pin check runs when `CURSIV_VOSK_ZIP` points at the downloaded zip, otherwise
  skipped). Next: item 4 `tests/test_release_docs.py`, then the release runbook.
- 2026-10-26: items 1 and 2 committed on `claude/u105` (`1c13882`, `14065aa`, `9eb3161`); branch pushed.
  Next: item 3 (safe_zip + Vosk pin), item 4 (release-doc test), then the release runbook.
