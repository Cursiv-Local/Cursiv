# Reliability evidence: what was tested, what was fixed, what is still unproven

> Later releases: [U85 verification](U85-RELEASE-VERIFICATION.md) records current
> source, package and public-download gates. The sprint results below retain
> their original source/platform scope and do not describe U85 measurements.

Sprint of 2026-10-18 to 19, on branch `ui-redesign` (commits `22ce938` to the commit that adds this file),
from three briefs: field-record integrity and recovery; calculation integrity and self-auditing; memory,
provenance and untrusted documents. Everything below was run on **one Windows 11 Home laptop** (Python
3.13.13, Node v24.15.0), from source, not from an installed build. Nothing here was run on a phone, a
clean machine, a Mac, or by a field team.

Kinds of evidence, kept apart throughout:

- **Unit/integration test**: automated, in `tests/`, run in this sprint (counts below).
- **Inspection**: I read the code or data and report what it does; nothing was executed to prove it.
- **Not tested**: said so.

---

## B. Test results (as run)

| Command | Result |
|---|---|
| `py -3.13 -m pytest tests -q -rs` (whole suite, before any change) | 509 passed, 1 skipped |
| `py -3.13 -m pytest tests -q -rs` (whole suite, after) | **662 passed, 1 skipped** (skipped: `test_keychain.py`, needs a Mac's Keychain) |
| `tests/test_integrity_attacks.py` | 45 passed |
| `tests/test_end_to_end_field.py` | 10 passed |
| `tests/test_offline_process.py` | 3 passed |
| `tests/test_reliability.py` | 78 passed |
| `tests/test_storage_failures.py` | 14 passed |
| `tests/test_phone_notebook.py` | 16 passed |
| `tests/test_phone_receive.py` | 7 passed (5 consecutive runs after a flaky-connection fix) |

When first written, 26 of the 45 integrity tests and 13 of the first 65 reliability tests failed; the
failures were real defects (section C) except where a test itself was wrong, which is noted.

**False-alarm check of the new answer checks** (`core/claims.py`): run on 817 distinct saved model answers
from earlier benchmark runs (`bench/results/*.json`), with each answer's real record rebuilt from its
status lines. First pass: 40 flagged, mostly from my measurement method (fixed); second: 6, of which 4 were
false alarms ("follow evidence-based advice", "a tool you already have", a negated claim with a curly
apostrophe), fixed and turned into tests; final: **2 flagged, both genuine** (an invented citation ID
`survival/choking-adult-heimlich`; a citation the answer was never given). This measures false alarms on
old answers. It does not measure how many real problems the checks miss.

---

## C. Defects found

Fixed, each with a regression test:

| # | Defect | Where | Severity |
|---|---|---|---|
| 1 | An entry written after a power cut left a half line was glued onto it: **both unreadable, the new one lost** | `fieldlog.add` | High |
| 2 | **One damaged line in the memory file made every memory disappear, and the next save rewrote the file with only the new one** | `semantic.list_facts` | High |
| 3 | A memory save that failed (disk full, read-only) fell through to the AI model, which replied "Got it, I'll remember" | `chat_commands` → `memory_command` | High |
| 4 | A share whose chain was recomputed with impossible values (latitude 999, "yesterday" as a time, photo path `../../secret.txt`) imported as trusted | `fieldsync` | High |
| 5 | A photo changed on disk after it was stored went unnoticed, and **the next export signed it as genuine** | `fieldlog.export` | High |
| 6 | A phone's name wasn't checked against its key: anyone could import a file under a phone's name before Cursiv had seen that phone | `fieldsync._check_signature` | Medium |
| 7 | A damaged manifest, a non-entry line, or a text `seq` crashed the whole import partway through | `fieldsync` | Medium |
| 8 | Exports wrote straight into the target folder: an interrupted export half-overwrote the last good one | `fieldlog.export` | Medium |
| 9 | Field Notebook window: a failed save (disk full) escaped the Save button with no message; export and report had no error handling | `launcher/field_notebook.py` | Medium |
| 10 | Exports didn't flag files added after signing, didn't say whose key signed, and said "checks out" for an export made from a log with problems | `fieldlog.verify_export(_text)` | Medium |
| 11 | No calculator for supply × people × time × allocation: the model did that arithmetic (240 L "lasts 12 days"; it lasts 1) | new `core/resources.py` | High |
| 12 | Statistics with units ("12.4 g, 9.8 g ...") weren't calculated at all; **a request for the population SD silently got the sample SD** | `fieldcalc.stats` | Medium |
| 13 | Plain-prose claims were never checked: "I used a deterministic tool, no AI was involved", "retrieved from stored data", "compiled from field-tested guidelines", "safety is not at risk" | new `core/claims.py` | High |
| 14 | "your saved memories" was named as a source whenever any memory was offered, used or not | `chat_app.sources_line` | Medium |
| 15 | Unsourced reference entries were given to the model as "facts"; a loose match rule brought "water wheel power" and insect-eating entries into a water-planning question | `core/reference.py` | Medium |
| 16 | Two unsourced entries gave unsafe advice if read as authoritative ("All insects safe if cooked"; an antibiotic dose with no allergy warning): **withheld from chat** pending review | `reference.NOT_IN_CHAT` | High |
| 17 | Document text had no untrusted-data framing; instructions inside a document reached the model as plain context | `core/documents.py`, `chat_app` | Medium |
| 18 | NaN location accuracy was written into the log as invalid JSON | `fieldlog.add` | Low |
| 19 | One bad photo used by two entries was counted as two missing photos | `fieldsync._import_photos` | Low |
| 20 | Wi-Fi receiver: a refused upload could reset the connection instead of answering | `core/phone_receive.py` | Low |
| 21 | No-AI messages told people to run `ollama run llama3.1` (a 4.7 GB download of a model Cursiv doesn't use) | `chat_app` | Low |
| 22 | Building the chat window started the real AI engine, also in the self-test and tests | `launcher/chat_panel.py` | Low |
| 23 | Unsigned phone files were described as "shared by Cursiv before U73" | `fieldsync.report_text` | Low |
| 24 | Weekday shifts, dates, points along a transect and two proportions had no calculator (benchmark rea-008, num-027, rea-016) | new `core/datecalc.py` | Medium |

Found and not fixed (open):

- **Program data stays behind after uninstall.** Memories, settings and saved keys are in
  `%LOCALAPPDATA%\Programs\Cursiv\_internal\.cursiv` (and an older `Cursiv\.cursiv`); the uninstaller
  leaves non-empty folders. This keeps records safe, which is what the brief asked, but a person expecting
  "uninstall removes my data" would be wrong. Needs a line in the uninstaller or docs. (Inspection.)
- The laptop's own log isn't signed entry by entry; a signed export covers the log's head. Someone with the
  files **and** this computer's signing key could rewrite the whole chain. Tamper-evident, not tamper-proof.
- A laptop's first signed share is trusted on first sight (key pinned then). Phones are now bound to their
  key by name; laptops aren't, because a laptop's name is a hash of its computer name, not of its key.

My own test mistake, caught: a storage test undid its own redirection and briefly pointed at the real
`~/.cursiv`. It only read (the file didn't exist); timestamps confirm nothing was written. Every test now
fails if it creates or changes the real field log, signing key, memory file or config (`tests/conftest.py`).

---

## Root causes of the observed failures (from the code)

| Observed in the scenario tests | Cause found | Fix |
|---|---|---|
| 240 L "lasts 12 days" for 120 people at 2 L/person/day | No resource calculator existed, so the model did the arithmetic; nothing compared its numbers with anything | `core/resources.py`; `calc.check` flags "lasts N days", "enough" with a shortfall, a total read as a daily figure |
| "No prior answer conflicts" after contradicting a 12-day claim | Nothing compared answers with earlier turns | `claims.history_notes` |
| "I used a deterministic tool, no AI reasoning involved" | Only "I searched the web"-type claims were checked; Cursiv's own tool record existed but nothing compared prose with it | `calc.Worked.record()` (tool, inputs, result, ok); `claims.tool_notes` |
| FIELD-731: "retrieved from stored data", then "no persistent storage" | Cursiv **does** have persistent memory (`memory_facts.jsonl`), but a record typed into chat is never saved unless the person types `remember ...`; the model read the values from the conversation and called it storage | "save this record: ..." saves exactly and reports the real write; `recall ...` returns only what is stored; `claims.memory_notes` |
| "your saved memories" under unrelated answers | Named whenever memory was offered; with no embedding model, a 12% word overlap was enough to offer it | Named only when the answer used a memory |
| Dental and insect entries in a water/food/power plan | One topic word plus two text words matched; "water", "food", "emergency" are in many titles | A match needs the topic's distinctive words |
| "compiled from field-tested survival guidelines" | **Not in the data**: `survival/water-purification` is from U.S. EPA (https URL on file, checked 2026-10-18, not professionally reviewed), and already says boiling doesn't remove chemicals from floodwater. The model invented it | Each entry's evidence state is given to the model and shown; `claims.reference_notes` |
| Three ill residents: "safety is not currently at risk" | Nothing checked certainty drawn from missing information | `claims.certainty_notes` |
| Rainfall document: 42 mm kept, but "verified", and an unrelated medical entry | Documents had no untrusted framing; "verified" wasn't checked; the medical entry was the loose match above | Framing; instruction flags; memories withheld from a turn with a flagged document; `claims.document_notes` |

## Execution paths, before and after

**Calculations.** Before: `chat_app._chat_inner` → `calc.work_out` (clock, plain sums, then fieldcalc:
lightning, bleach, distance, coordinates, dilution, stats, units) → if a result, its statement goes into the
prompt and `calc.check` looks for one number in the answer. Anything else: the model alone. After: the same
path, plus `resources` (supplies), `datecalc` (dates, weekdays, spacing, proportions) and stats with units;
every result carries `tool`, `inputs` and `ok`; a refused calculation (0 people, mixed units, an impossible
date) is marked refused and the model is told not to give a result; `calc.check` also looks for
contradictions. A calculator that raises counts as nothing ran.

**Tool-use claims.** The answer's words are compared with `Worked.record()`, the reference entries actually
given (with their evidence), the memories actually given, whether a search ran, and the documents given
(`claims.Evidence`, built in `chat_app._evidence`). Every check is code; none asks a model.

**Limits of these checks.** They match specific phrasings. A claim worded differently passes unflagged; a
passing check means "not contradicted by the record", not "true". The model-based check in
`core/verify.py` is a second model call and is not independent proof of anything.

---

## D. Verified versus unverified

| Claim | Evidence |
|---|---|
| Changed, removed, reordered, duplicated, rechained or invalid records are refused; the laptop's records stay byte-identical | Unit/integration tests (45 + 10) |
| The phone's real `core.js` produces files the laptop's real import accepts, every field and photo intact | Integration test, **under Node, not a phone browser** |
| The program starts and runs its self-test with no connection off this computer | Process test with two observers (audit hook + OS socket table) and a control; **this build, this Windows laptop only** |
| Import, Wi-Fi receive and signed export work with offline mode on and no outside connection | Integration test, same laptop |
| Interrupted, full, read-only and pulled-drive writes lose nothing and never say "saved" | Tests that make the write calls fail with the OS's errors; **not a real full disk, write-protected stick or pulled drive** |
| Phone storage, durability, quota, persistence, Safari/Chrome crypto | **Not tested.** Message logic is tested under Node; the browser paths are not |
| Clean install, first launch, upgrade, uninstall | Inspection of `installer/cursiv_setup.iss`, `launcher/data_home.py` and the installed copy on this laptop. **No clean machine was used** |
| Reference content is accurate | **Not established.** 37 of 112 entries name a public source; 0 are professionally reviewed |
| The new answer checks on live answers | **Partly measured** (`bench/FAILURES-U75.md`): one 153-case run on U75 plus 5 new cases. New checks: 3 notes, 1 true, 2 false (fixed); 2 misses found and fixed. U75 98.7% vs U68 97.4% on suite 1.5, within run-to-run noise; rea-008, rea-016 and num-027 traceably fixed by the calculators. The older model-based check put notes under 28 correct answers. A full miss rate is not measured |

---

## E. The five most important remaining barriers to trustworthy field use

1. **No test on a real phone.** IndexedDB durability, iOS storage eviction, the share sheet, camera
   capture and Ed25519 support in Safari and Chrome are all unproven.
2. **No professional review of the medical and survival content.** 0 of 112 reviewed; 75 have no
   published source (43 of the 80 medical/survival entries).
3. **No clean-machine install test.** First launch needs internet once (Ollama and the model); the
   installer is unsigned, so SmartScreen warns; nobody non-technical has done it unaided.
4. **The answer checks are pattern checks, measured once on live answers.** On one run they were mostly silent,
   with about as many false notes as true ones (fixed since); the older model-based check adds noise under correct
   answers (`bench/FAILURES-U75.md`). A miss rate across all answers isn't measured.
5. **Data at rest isn't encrypted** (login isn't encryption; on a USB the signing key is readable), and a
   laptop's first share is trusted on first sight.

## F. Readiness, conservatively (out of 10)

| Area | Score | Why |
|---|---|---|
| Engineering quality | 6 | Small, tested modules and atomic writes; but `chat_app.py` is 3,000+ lines of global per-turn state, and checks are regex-based |
| Automated reliability evidence | 6 | 662 deterministic tests, attack cases, a process-level offline test with a control; no live-model run of the new checks, one OS |
| Data integrity and recovery (laptop) | 7 | 24 defects fixed with tests; refusals are whole and leave data untouched; real hardware failures not exercised |
| Offline behaviour | 7 | Two-observer process test with a control, plus in-process tests; one build, one OS; first install still needs internet |
| Phone notebook reliability | 3 | Format, signing and messages tested under Node; nothing on a phone |
| Overall field readiness | 4 | Suitable for a supervised pilot with daily sends to the laptop; not for unsupervised field use |

## G. Next actions that need hardware or people

- **Android and iPhone:** install the notebook from `/notebook`, record 20 entries with photos, force-close,
  reboot, airplane mode, low storage, then send by USB, AirDrop/Quick Share and Wi-Fi; import; compare.
  Check Ed25519 support (the page says when a browser can't sign).
- **Clean Windows machine** (a spare laptop or a fresh VM; Windows 11 Home has no Windows Sandbox):
  the procedure below.
- **Independent reviewer** (a medic or physician): the 80 medical/survival entries, starting with the five
  held back, using `docs/PROFESSIONAL-REVIEW.md`.
- **Field team:** a week of real use with daily sends; count lost, duplicated or refused records.

### Clean-install procedure (manual; not yet done)

1. Fresh Windows 11 user with no Python, Git or Ollama. Note the installer's SHA-256 against
   `SHA256SUMS.txt` (`Get-FileHash`).
2. Run the installer as that user (no admin). Record SmartScreen's wording and every click needed.
3. First launch: does Setup explain the Ollama and model download, its size, and that it's once?
   Cut the network mid-download: is the message plain, and does a retry work?
4. With no model installed, ask a question: the answer must say the local AI isn't available (not an error
   dump), and the field notebook, reference and calculations must still work.
5. Record 3 field entries, export, verify the export (`field log verify <folder>`).
6. Network off: restart, record, export again.
7. Install the next version over it: the 3 entries, memories and settings must still be there.
8. Uninstall: the field log (`%USERPROFILE%\.cursiv\fieldlog`) must remain; note what remains in
   `%LOCALAPPDATA%\Programs\Cursiv` (memories and settings currently do).

---

## A. Files changed

| File | Defect or risk | Benefit |
|---|---|---|
| `cursiv_v215/core/fieldlog.py` | 1, 5, 8, 10, 18 | No lost entry after a power cut; photos checked; exports swapped in only once verified; signer named |
| `cursiv_v215/core/fieldsync.py` | 4, 6, 7, 19, 23 | Invalid or impersonating shares refused whole; damaged team copies left out and named; atomic copies |
| `cursiv_v215/core/resources.py` (new) | 11 | Supplies, need, shortfall, time it lasts; contradictions found |
| `cursiv_v215/core/datecalc.py` (new) | 24 | Dates, weekdays, transect points, two proportions |
| `cursiv_v215/core/fieldcalc.py`, `calc.py` | 12; tool record | Stats with units, sample vs population; every result says what ran |
| `cursiv_v215/core/claims.py` (new) | 13 | Tool, memory, source, certainty, blanket, document and earlier-answer claims checked against the record |
| `cursiv_v215/core/reference.py` | 15, 16 | Evidence state per entry; relevance; unsafe entries withheld |
| `cursiv_v215/core/documents.py` | 17 | Untrusted framing; instruction flags |
| `cursiv_v215/memory/semantic.py`, `launcher/memory_dialog.py` | 2, 3 | Damaged lines kept aside; saves exact or refused with a reason; `recall` |
| `cursiv_v215/ui/chat_app.py` | 13, 14, 17, 21 | Checks wired in; honest sources line; memories withheld when a document is flagged |
| `cursiv_v215/core/phone_receive.py` | 20 | Refused uploads answered; size checked on the phone first |
| `launcher/field_notebook.py`, `chat_panel.py`, `selftest.py` | 9, 22 | Failures said plainly; no engine start in self-test or tests |
| `website/notebook/core.js`, `app.js`, `sw.js` | phone honesty | Storage never called permanent; failed saves, unsigned files and missing photos named |
| `website/index.html`, `docs/PILOT-INTERVIEW-NOTES.md` | claims | "can't be quietly changed" → tamper-evident, with the limit; five held-back entries |
| `tests/` (7 new or extended files), `tests/conftest.py` | evidence | 153 new tests; real-data guard |
