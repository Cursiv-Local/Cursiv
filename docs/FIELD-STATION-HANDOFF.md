# HANDOFF FOR CHATGPT (or any assistant): CURSIV FIELD STATION / RASPBERRY PI SETUP

**Read this first if you are picking up the Raspberry Pi "Field Station" work on Cursiv.** It is kept up to
date after every step by the assistant doing the work (Claude), in case that session runs out of usage.
The owner is Joshua Winkler. Repository: https://github.com/Cursiv-Local/Cursiv (local checkout:
`C:\Users\joshu\OneDrive\Documents\GitHub\Cursiv-v3`, Windows 11, Git Bash and PowerShell).

Last updated: 2026-10-26, step 3 of 7 done (sessions, setup, unlock).

## What this work is

Turn Cursiv (an offline-first field research app for Windows) into a "Field Station" that also runs on a
Raspberry Pi 5, served to phones/tablets/laptops over the Pi's own Wi-Fi, without breaking the Windows
desktop app. Full spec and audit: `docs/FIELD-STATION-PLAN.md` (read it). The owner approved phases 2–5 with
these choices (2026-10-26):

1. **Encryption:** the notebook stays encrypted on the Pi. After each boot it is locked until someone signed
   in enters the **encryption passphrase** in the browser (the desktop asks for the same passphrase at
   start; it is separate from the sign-in password, see `launcher/encryption_dialog.py` `startup()` and
   `cursiv_engine/core/vault.py` `unlock()`). Until unlocked, only telemetry is shown. A fresh Pi needs a
   first-run setup: create the administrator account (`guardian/access_gate.py`) and set the encryption
   passphrase (`core/vault_migration.py` `migrate(passphrase)`).
2. **HTTP, not HTTPS, for now**, protected by the Pi's unique WPA Wi-Fi password. The UI and docs must say
   plainly that local HTTP is not encrypted.
3. **Accounts:** reuse existing Cursiv accounts (`access_gate.verify_credentials`). One notebook per
   station plus team views; private memory per account.
4. **Ships as a "Field Station preview" alongside U104** (U104 = fixes from an outside review: drive-key
   passphrase, strict photo import, Vosk checksum + safe unzip limits, release-doc consistency test).

## Hard rules (from the owner and the spec)

- Don't break or slow the Windows desktop app (`launcher/`). The station is a new package
  `cursiv_engine/station/`; it reuses `cursiv_engine` (which has no Qt imports).
- Never invent readings: no battery %, no temperature without a real sensor. Every value is labelled
  real / derived / simulated / unavailable, plus stale. Simulated values never appear as real.
- Don't claim anything works on a Pi until it has run on one and results are recorded. Label status as:
  implemented and tested / implemented, awaiting hardware validation / planned / unsupported.
- Don't weaken the field notebook (append-only, SHA-256 chained, corrections as new entries). One server
  process so `fieldlog`'s lock serializes writes.
- No new web framework: use the standard library (`http.server.ThreadingHTTPServer`), like
  `cursiv_engine/core/phone_receive.py` (private networks only, one-time code, lockout, size limits).
- Owner's standing rules: upward progression only (never ship something that makes Cursiv worse); never
  delete user data; never touch the untracked files `docs/CURSIV-LEGAL-HANDOFF.md`, `field-notes.txt`,
  `test_internals/` (stage files by name, never `git add -A`); commit/push/release only when asked.
- Version names: `3.14-U104` style (U-suffix), never bump the minor version.

## Environment notes

- Tests: `"$LOCALAPPDATA/Temp/cursiv-u88-build-39c0ad1699b74be8bab5385ce1b281d8/Scripts/python.exe" -m pytest -q -p no:cacheprovider tests/...`
  (a locked venv; never pip-install into it). Full suite ~2,140 tests, ~8 min on this PC.
- Mandatory USB gate: `pytest -m usb` (44 tests). Website: `node cloudflare/publish.mjs --build-only` then
  `node --test cloudflare/tests/*.test.mjs` (22 tests).
- Every code module must be listed in `docs/CODE-MAP.md` (`tests/test_code_map.py`).
- Storage code may not swallow errors silently: a `pass`/`continue`-only `except` in core storage,
  guardian or memory modules needs `# best-effort: <why>` (`tests/test_silent_errors.py`).
- Heredocs in Git Bash mangle `\n` and `\s`; edit Python files with an editor tool or a script file.

## Plan for phases 2–5 (this session)

| # | Step | Status |
|---|---|---|
| 1 | Check the engine functions the station calls (vault, accounts, notebook) | done |
| 2 | `station/telemetry.py` (temperature via discovered thermal zone, `vcgencmd get_throttled` parsing, CPU/RAM via psutil, disk, board model, battery providers: Linux `power_supply`, unavailable, simulated) + `station/simulation.py` (scenarios A–E from the spec, plus F undervoltage) | done: `tests/test_station_telemetry.py` 25 passed |
| 3 | `station/sessions.py`: sign-in with existing accounts, session cookie (HttpOnly, SameSite=Strict, idle + absolute expiry), CSRF token, login rate limit, encryption unlock | done: `tests/test_station_sessions.py` 7 passed |
| 4 | `station/server.py`: stdlib server; private/loopback clients only; Host + Origin checks; security headers; API: session, login/logout, unlock, status, health, notebook list/add/correct/verify/export, workspaces, safe shutdown (state machine; real OS shutdown only if configured) | next |
| 5 | `station/web/` browser UI (dashboard, notebook, health, workspaces, settings), phone-first, Cursiv dark-and-gold look | planned |
| 6 | `station/storage.py` Linux drive discovery by filesystem UUID (lsblk JSON / psutil), recognizes Cursiv workspaces (`Home/.cursiv/fieldlog/notebook.json`, `cursiv-field-share/`); ARM64 CI job (`ubuntu-24.04-arm`) | planned |
| 7 | Tests for all of the above, `docs/CODE-MAP.md` lines, update `FIELD-STATION-PLAN.md` status labels, full suite, PR | planned |

Phases 6–9 (install script + systemd, Wi-Fi access point, local AI benchmark on ARM, SSD/USB mounting) come
later and need a real Pi 5 to validate.

## Progress log (newest first)

- 2026-10-26 step 3: `station/sessions.py`: `Sessions` (token + per-session CSRF, idle 30 min, absolute 12 h),
  `Limiter` (5 free tries, then 30 s doubling to 15 min, per client address and per account), `Gate`
  (`sign_in` via `access_gate.verify_credentials`; `first_setup` needs the 8-digit setup code printed on the
  station console, runs `vault_migration.migrate(passphrase)` then `access_gate.setup_credentials`;
  `encryption()` status; `unlock()` = `vault.unlock` + `vault_migration.adopt_new_stores()`). The server must
  hold `core/data_lease.DataLease` for its whole life, as `launcher/main.py` does. Tests 7 passed. Committed.
  Next: step 4 `station/server.py`.
- 2026-10-26 step 2: `cursiv_engine/station/__init__.py`, `telemetry.py` (Reading with source real/derived/
  simulated/unavailable + stale; CPU sensor found by thermal-zone type, implausible values rejected;
  `parse_throttled` bits 0-3 now / 16-19 since boot; battery providers `SysfsBattery` (/sys/class/power_supply),
  `NoBattery` (says telemetry unavailable, invents nothing), simulated; advisory thresholds configurable),
  `simulation.py` (scenarios A-F via `CURSIV_STATION_SIMULATE` or `simulation.activate()`), tests 25 passed.
  Committed on `claude/field-station`. Next: step 3 `station/sessions.py`.
- 2026-10-26: Branch `claude/field-station` created from `main` at `21ddd1a`. `docs/FIELD-STATION-PLAN.md`
  written (not committed yet). Started `cursiv_engine/station/`. Nothing committed yet on this branch.
