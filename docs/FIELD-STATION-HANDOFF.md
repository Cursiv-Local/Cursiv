# HANDOFF FOR CHATGPT (or any assistant): CURSIV FIELD STATION / RASPBERRY PI SETUP

**Read this first if you are picking up the Raspberry Pi "Field Station" work on Cursiv.** It is kept up to
date after every step by the assistant doing the work (Claude), in case that session runs out of usage.
The owner is Joshua Winkler. Repository: https://github.com/Cursiv-Local/Cursiv (local checkout:
`C:\Users\joshu\OneDrive\Documents\GitHub\Cursiv-v3`, Windows 11, Git Bash and PowerShell).

Last updated: 2026-10-26, step 7 of 7: full suite passed, PR opened (see log).

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
| 4 | `station/server.py`: stdlib server; private/loopback clients only; Host + Origin checks; security headers; API: session, login/logout, unlock, status, health, notebook list/add/correct/verify/export, workspaces, safe shutdown (state machine; real OS shutdown only if configured) | done: `tests/test_station_server.py` 13 passed (live loopback server) |
| 5 | `station/web/` browser UI (dashboard, notebook, health, workspaces, settings), phone-first, Cursiv dark-and-gold look | done: walked through live (setup, restart -> locked -> unlock, record, correct, verify, health at phone width); 15 server tests |
| 6 | `station/storage.py` Linux drive discovery by filesystem UUID (lsblk JSON / psutil), recognizes Cursiv workspaces (`Home/.cursiv/fieldlog/notebook.json`, `cursiv-field-share/`); ARM64 CI job (`ubuntu-24.04-arm`) | done: `tests/test_station_storage.py` 5 passed; CI job `station-arm64` added (first run on the PR) |
| 7 | Tests for all of the above, `docs/CODE-MAP.md` lines, update `FIELD-STATION-PLAN.md` status labels, full suite, PR | done: full suite 2,175 passed, 14 skipped; PR opened, not merged |

Phases 6–9 (install script + systemd, Wi-Fi access point, local AI benchmark on ARM, SSD/USB mounting) come
later and need a real Pi 5 to validate.

## Progress log (newest first)

- 2026-10-26 (release, owner asked "release, commit, push, publish, and a webpage"): PR #40 merged to main
  (`cac12de`). Branch `claude/u104`: version 3.14-U104 (selfknow, launcher, installer), `docs/RELEASE-U104.md`,
  CHANGELOG. New page `website/field-station.html` (real screens from `scripts/station_shots.py` +
  `scripts/cdp_shots.mjs`: the station run against a throwaway folder, sample entries via the API, headless
  Edge over the DevTools protocol), social card, links from home / field-research / team-drives, sitemap.
  Interface fixes from the screenshots: one shared "unavailable" note per card, storage labels, wider label
  column. The outside-review items move to U105. Next: PR, CI, merge, tag v3.14-U104, build, sign, publish,
  evidence PR, publish the website.
- 2026-10-26 step 7: full suite 2,175 passed / 14 skipped (the usual live-model + Keychain skips). Committed and pushed `claude/field-station`; PR #40 (https://github.com/Cursiv-Local/Cursiv/pull/40) opened for the owner (not merged, not released). Earlier note: `docs/CODE-MAP.md` has a "Field Station preview" section (code-map test
  passes); `docs/FIELD-STATION-PLAN.md` gained section 8 (status of every deliverable, labelled) and section 9
  (API reference); CHANGELOG has "3.14-U104 — in progress". Full suite running. Not yet committed. Then: commit,
  push `claude/field-station`, open a PR (do NOT merge or release without the owner), watch the new
  `station-arm64` CI job.
- 2026-10-26 step 6: `tests/test_station_storage.py` (lsblk JSON parsed to UUID-identified mounted drives, swap
  and unmounted skipped; workspace recognition writes nothing; psutil fallback marked not stable; the station
  imports with `sys.modules['PyQt6'] = None`). `requirements-station.txt` (engine deps only, versions from
  `requirements-release.lock`, no Qt/PyInstaller). CI job `station-arm64` on `ubuntu-24.04-arm` runs 11 test
  files (113 tests locally with Qt blocked). A GitHub ARM server is not a Pi: hardware stays "awaiting
  validation". Committed. Next: step 7 (CODE-MAP lines for every station module, plan status labels, full
  suite, PR).
- 2026-10-26 step 5: `station/web/index.html`, `app.css`, `app.js` (views: setup with station name, sign in,
  unlock, dashboard, notebook with corrections/search/verify/export, health with source chips, workspaces,
  settings with two-step safe shutdown; textContent only, no inline code, CSP-clean). Walked through in a live
  preview: setup -> sign in -> server restart -> signed out and notebook locked -> unlock -> record (value
  "12.40" kept as typed, `<b>` in a note shown as text) -> correction kept the original -> integrity check;
  Health at 375 px wide without sideways scroll. Fixes from the walkthrough: setup names the station's notebook
  (`station_name`), HEAD /healthz, notes only for unavailable/stale readings. `scripts/station_dev.py` runs the
  server against `.station-dev/` (git-ignored); NEVER run `python -m cursiv_engine.station` on a development PC
  (it holds the data lease and setup encrypts `~/.cursiv`). `.claude/launch.json` config `field-station`
  (port 8090, scenario A). Committed. Next: step 6, storage tests (`parse_lsblk`) + ARM64 CI job.
- 2026-10-26 step 4: `station/server.py` (`Station` state + `make_handler`; `local_client()` = the inbound rule:
  loopback or RFC1918/ULA only; Host must be a station name; Origin must match; CSRF header `X-CSRF-Token` on
  every POST after sign-in; security headers + CSP; cookie `cursiv_station` HttpOnly SameSite=Strict (no
  Secure: plain HTTP, by the owner's choice). API: GET /healthz, /api/session, /api/health, /api/status,
  /api/notebook[?q=&limit=], /api/notebook/verify, /api/workspaces; POST /api/setup, /api/login, /api/logout,
  /api/unlock, /api/notebook, /api/notebook/correct, /api/export, /api/shutdown {confirm:true}. Locked data
  -> 423. Shutdown: running -> draining -> stopped, OS command only if `--shutdown-command` given.)
  `station/storage.py` (read-only drive discovery: lsblk UUIDs on Linux, psutil elsewhere marked not stable;
  recognises Cursiv workspaces). `station/__main__.py` (`python -m cursiv_engine.station --simulate A`, holds
  DataLease, offline on, prints the first-run setup code). Tests 13 passed. Committed. Next: step 5, the
  browser UI in `cursiv_engine/station/web/` (index.html, app.css, app.js; served at / and /static/<name>;
  CSP forbids inline scripts and styles, so keep JS and CSS in files).
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
