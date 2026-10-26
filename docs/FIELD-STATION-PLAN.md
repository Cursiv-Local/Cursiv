# Cursiv Field Station: audit and implementation plan

Status: **phases 2–5 built as a preview (2026-10-26); nothing validated on a Raspberry Pi yet.** See
section 8. Audit written 2026-10-26 against `main` (U103 + PR #39). Every statement about current code was
checked against it. Handoff for another assistant: `docs/FIELD-STATION-HANDOFF.md`.

The Field Station is a Raspberry Pi 5 running Cursiv's existing engine headless, serving a browser
interface over its own Wi-Fi. Phones, tablets and laptops are the screens; the Pi, its SSD and the
USB workspaces hold the data. The Windows desktop app stays as it is.

## 1. Audit: what exists

| Area | Today | Reuse for the Pi |
|---|---|---|
| Core engine | `cursiv_engine/` has no Qt imports. Chat (`chat/`, `ui/chat_app.chat`), notebook (`core/fieldlog.py`), team sync (`core/fieldsync.py`), memory (`memory/`), documents and retrieval, calculations (`core/calc.py`, `fieldsci.py`, `science_check.py`), network gate (`core/netgate.py`). | Directly. This is already the shared core the spec asks for. |
| Desktop | `launcher/` (PyQt6 windows, tray, login dialogs, USB maker UI). | Not used on the Pi. Unchanged. |
| Linux | Full suite passes on Linux x86-64 in CI (`test-linux`, experimental). | ARM64 untested. Engine dependencies (bcrypt, cryptography, numpy, Pillow, psutil, pypdf) publish aarch64 wheels; PyQt6 and pywin32 aren't needed headless. |
| Windows-only code | Saved AI keys: DPAPI (`core/keystore.py`; on Linux keys stay readable). USB drive discovery: `ctypes.windll` (`launcher/usb_ops.list_drives`). Code sandbox: Windows Job Object, resource limits elsewhere (`core/confined.py`). | Needs Linux adapters: drive discovery by filesystem UUID; a Linux key store (or a passphrase vault key); confinement stays as POSIX limits. |
| Encryption at rest | Passphrase vault (`core/vault.py`, Fernet, scrypt-derived) covers notebook, memory, conversations. Portable drives are readable by design. | Works on Linux as is. Unlock needs a human passphrase at start: a headless decision (section 5). |
| Accounts | `guardian/access_gate.py`: bcrypt logins, multiple accounts, security questions with an attempt limit. | Reuse for web sign-in. |
| Notebook integrity | Append-only JSONL, SHA-256 chain, atomic writes with read-back, one `threading.Lock` per process; corrections are new entries; 14 integrity scenarios tested. | Reuse. A single server process keeps the lock meaningful; never run two writers. |
| Workspaces | U103: each notebook has an identity (id + name), signed shares, verified imports into a team view, Make USB with chosen notebooks. | The basis for the five USB workspaces. |
| Local web serving | `core/phone_receive.py`: stdlib `ThreadingHTTPServer`, private networks only, one-time code, lockout, size limits, auto-stop. | The pattern for the station server. No new web framework. |
| Network gate | An audit hook refuses outgoing connections and DNS to anything but loopback while offline. It doesn't govern accepting connections. | Must add an explicit inbound rule: answer only on the station's own Wi-Fi interface and loopback. |
| Phone notebook | `website/notebook/` is an offline browser notebook (IndexedDB, signed send files). | Its screens are a starting point for the station's notebook page (same look). |
| Local AI | Ollama on loopback; qwen3:4b-instruct default; qwen2.5:1.5b in the fallback list. Ollama publishes Linux ARM64 builds. | Measure on a Pi 5 before choosing a default. The station must work with no model. |

## 2. Architecture

```
phone / tablet / laptop  --Wi-Fi (Cursiv-Field, WPA2/3)-->  Raspberry Pi 5
                                                            cursiv-station (systemd, user "cursiv")
                                                              station/server.py   stdlib HTTP, sessions, CSRF
                                                              station/api/*.py    thin handlers
                                                              cursiv_engine/      the same core as desktop
                                                              station/telemetry/  temp, CPU, power, storage
                                                            Ollama (optional, loopback only)
                                                            /srv/cursiv (internal) · SSD by UUID · USB workspaces
```

- New package `cursiv_engine/station/`: server, API handlers, telemetry, storage discovery, setup. Handlers
  call existing engine functions; business logic stays in the core.
- One server process (threaded), so notebook writes stay serialized by the existing lock.
- Static UI in `station/web/` (HTML, CSS, small vanilla JS), in Cursiv's dark-and-gold look. No build step.
- Every module imports on Windows too, so CI tests it everywhere; Pi-only parts sit behind provider
  interfaces with simulated and unavailable versions.

## 3. Phases

Order follows the spec, adjusted so that each step is testable without hardware. Effort is a rough count of
working sessions.

| Phase | Deliverable | Testable now? | Effort |
|---|---|---|---|
| 1 Audit | This document | done | – |
| 2 Portability | Linux drive discovery (UUID-based), headless entry point, ARM64 import test in CI (`ubuntu-24.04-arm` runner) | yes, CI | 1 |
| 3 Local API | `station/server.py`: sign-in with existing accounts, sessions (expiry, HttpOnly, SameSite), CSRF tokens, Origin checks, rate limits, private-network-only binding; notebook, search, verify, export, telemetry endpoints | yes | 2 |
| 4 Browser UI | Dashboard, Field Notebook, Station Health, Workspaces, Settings, safe shutdown; phone-first | yes, in a browser | 2 |
| 5 Telemetry | Providers: CPU temp (thermal zones, discovered), CPU/RAM (psutil), throttling/undervoltage (`vcgencmd get_throttled` when present), storage; battery provider interface with real, simulated and unavailable implementations; every reading labelled real / derived / simulated / unavailable / stale | yes (simulation); real readings need the Pi | 1–2 |
| 6 Deployment | `install-station.sh` (asks before each system change), systemd unit (dedicated user, restart, health check, journal logging), docs | script reviewable now; run needs the Pi | 1 |
| 7 Networking | Access point via NetworkManager (`nmcli` hotspot), unique Wi-Fi password generated at setup, `cursiv.local` via Avahi plus the IP shown on screen, inbound gate rule | config testable; behaviour needs the Pi | 1 |
| 8 Local AI | ARM64 benchmark script (load time, tokens/s, memory, temperature), model recommendation by RAM, inference never blocks notebook or telemetry | needs the Pi | 1 |
| 9 SSD and USB | Mount by UUID, read/write check, never format, safe eject; USB workspaces reuse U103 identities and verified import into the team view, no merge from unknown drives | logic yes; mounting needs the Pi | 1–2 |
| 10 Validation | Automated tests per subsystem; `docs/FIELD-STATION-ACCEPTANCE.md` (the spec's 25 checks) with blank result columns | yes | 1 |

Phases 2–5 and 10 can be built and tested now. 6–9 can be written now but are only *implemented, awaiting
hardware validation* until run on a Pi 5.

## 4. Simulation

`CURSIV_STATION_SIMULATE=<scenario>` switches every hardware provider to a named scenario (A normal 52 °C /
82 %, B 81 °C critical, C battery 12 %, D SSD removed mid-write, E no battery telemetry). The dashboard shows
a fixed "SIMULATED" banner and every simulated value carries a simulated label; the server refuses to start
in simulation unless it's a development install. Tests run all five scenarios.

## 5. Decisions for the owner

1. **Encryption on a headless Pi.** The vault needs a passphrase at start. Options: (a) the administrator
   unlocks it from the browser after each boot (strongest; nothing works until unlocked); (b) notebook stays
   readable on the station's SSD, like a USB drive today (simplest; anyone with the SSD can read it);
   (c) key in the Pi's storage (no real protection if the Pi is taken). Recommendation: (a), with Research
   Tools Mode showing only telemetry until unlocked.
2. **HTTP or HTTPS on the local network.** Plain HTTP is not encrypted; anyone on the Field Station Wi-Fi
   could read traffic. The Wi-Fi itself is WPA2/WPA3-encrypted with a unique password. Self-signed HTTPS
   shows browser warnings on every phone. Recommendation: HTTP behind the WPA password for the first
   version, said plainly in the UI and docs; HTTPS with a station-generated certificate as a later option.
3. **Accounts.** First version: the existing Cursiv accounts, one notebook per station plus team views,
   private memory per account. Per-project permissions come later.
4. **Release vehicle.** Build it on a branch as a "Field Station preview" alongside U104's review fixes, or
   as its own release after U104.

## 6. Status labels used in all station docs

- **Implemented and tested**: code exists and automated tests pass.
- **Implemented, awaiting hardware validation**: code exists, tested only with simulation or mocks.
- **Planned**: designed, not built.
- **Unsupported**: not planned for the first version.

## 7. What won't be claimed

No battery percentage without a device that reports it; no temperature without a sensor reading; nothing
marked validated until it runs on a Pi 5 and the acceptance results are recorded; no multi-station sync
until built and tested; no claim that HTTP on the local network is encrypted.

## 8. Status (2026-10-26, branch `claude/field-station`)

| Deliverable | Status |
|---|---|
| Repository audit and plan | done (this document) |
| Shared core | **implemented and tested**: the station uses `cursiv_engine` unchanged; it imports with Qt blocked (`tests/test_station_storage.py`) |
| ARM64 compatibility | **implemented, awaiting validation**: CI job `station-arm64` on GitHub's ARM64 Linux; not yet run on a Pi |
| Local API (`station/server.py`) | **implemented and tested** on loopback: 15 tests incl. CSRF, Origin, Host, locked data, 20 concurrent writes, safe shutdown, storage failing mid-write |
| Sign-in, sessions, setup, unlock (`station/sessions.py`) | **implemented and tested**: 7 tests with real accounts and real encryption |
| Browser interface (`station/web/`) | **implemented and tested** in a desktop browser at 1280 and 375 px; **awaiting validation** on iOS Safari, Android Chrome, Firefox, tablets |
| Telemetry (`station/telemetry.py`) | **implemented and tested** with faked /sys folders (25 tests); **awaiting hardware validation** of the Pi 5 thermal zone, `vcgencmd` and any UPS battery |
| Battery providers | Linux `power_supply`, unavailable (plain power bank), simulated: **implemented and tested**; real UPS boards **awaiting hardware** |
| Simulation (`station/simulation.py`) | **implemented and tested**: scenarios A-F, labelled SIMULATED everywhere |
| Drive discovery (`station/storage.py`) | **implemented and tested** (read-only, by UUID); mounting, import/export, eject: **planned** (phase 9) |
| Install script, systemd service | **planned** (phase 6) |
| Wi-Fi access point, cursiv.local | **planned** (phase 7) |
| Local AI on the Pi | **planned** (phase 8): the dashboard shows whether Ollama is running; no Pi benchmark yet |
| Research chat in the browser | **planned**: not in this preview |
| Hardware acceptance test plan | **planned** (`docs/FIELD-STATION-ACCEPTANCE.md`) |
| Multi-station sync | **unsupported** in the first version |

### Running it on a development PC

`python scripts/station_dev.py --port 8090 --simulate A` (data in `.station-dev/`, git-ignored). Never run
`python -m cursiv_engine.station` on a PC with real Cursiv data: it holds the data lease and first-run setup
encrypts `~/.cursiv`.

## 9. Local API (preview)

All responses are JSON. Every request must come from loopback or a private network and name the station in
`Host`. After sign-in, the `cursiv_station` cookie (HttpOnly, SameSite=Strict) identifies the session; every
POST except setup and login also needs `X-CSRF-Token` (from `/api/session` or the login response) and, if the
browser sends `Origin`, it must be this station. 401 = sign in first; 403 = refused; 423 = notebook locked
(enter the passphrase); 429 = too many wrong tries (`Retry-After`); 503 = shutting down or storage unavailable.

| Method and path | Needs | Does |
|---|---|---|
| GET/HEAD `/healthz` | nothing | `{"ok", "state"}`, no data (for systemd and monitors) |
| GET `/api/session` | nothing | signed in?, user, CSRF token, needs setup?, encryption state, simulated scenario, version |
| POST `/api/setup` | setup code | `{code, username, password, passphrase, station_name}`: only while no account exists |
| POST `/api/login` / `/api/logout` | — / session | sign in with a Cursiv account / end the session |
| POST `/api/unlock` | session | `{passphrase}`: unlocks the encrypted notebook after a restart |
| GET `/api/health` | session | the telemetry snapshot (works while locked) |
| GET `/api/status` | session | encryption, local AI engine, offline state, notebook summary |
| GET `/api/notebook?q=&limit=` | unlocked | entries, newest first, with whose notebook each came from |
| POST `/api/notebook` | unlocked | a new entry (`site, sample_id, project, observer, note, measurements[], lat, lon`) |
| POST `/api/notebook/correct` | unlocked | `{entry_id, reason, ...fields}`: a new entry that corrects one; the original stays |
| GET `/api/notebook/verify` | unlocked | integrity check, and what a pass does and doesn't show |
| POST `/api/export` | unlocked | team export (CSV, JSON, GeoJSON, report) on the station |
| GET `/api/workspaces` | unlocked | notebooks on the station and drives it can see |
| POST `/api/shutdown` | session | `{confirm: true}`: stop writes, finish running ones, lock, then the OS command if configured |
