# Cursiv Field Station: audit and implementation plan

Status: **plan only.** Nothing below is built unless marked. Written 2026-10-26 from an audit of the
repository at `main` (U103 + PR #39). Every statement about current code was checked against it.

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
