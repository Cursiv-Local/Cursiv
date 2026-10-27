# Handoff — Cursiv verification overhaul

Current rules and the latest releases. Everything older (each release from U61 to
U96, past plans, the 2026-10-21/22 reviews) is unchanged in
[docs/HANDOFF-HISTORY.md](docs/HANDOFF-HISTORY.md).

## Website general-search discoverability (Codex, 2026-10-26)

Continuing handoff: [DISCOVERABILITY-HANDOFF](docs/DISCOVERABILITY-HANDOFF.md); measurements and exact
Search Console exclusion classifications: [DISCOVERABILITY-REPORT](docs/DISCOVERABILITY-REPORT.md).
The website update leads with free/open-source local AI, retains notebook integrity as its distinction,
and adds local-AI/comparison/evidence pages, official favicons, canonical www handling and an experimental
llms.txt guide. Checks: 31 website tests and 6 aggregate-measurement tests passed. Published pages/icons
and redirects were checked live; Google reported the homepage available and Schema.org reported zero
errors/warnings. The owner chose manual discovery checks; no recurring monitor was created.
Publication proof and future measurements are in that handoff. Intentional private/noindex exclusions remain;
no app behavior, station code, model defaults, installer bytes or release tag changes. Directory/review
drafts require owner approval before sending; no search ranking or AI endorsement is promised.

## U106 published (Codex, 2026-10-26)

Tag `v3.14-U106` = `10b40d6` (source PR #45): four visible desktop research actions, notebook and imported
library in the main window, confirmed observation/memory previews, receipt-backed linked corrections and
verified dated notebook retrieval. Evidence: [U106-RELEASE-VERIFICATION](docs/U106-RELEASE-VERIFICATION.md);
continuing handoff: [U106-HANDOFF](docs/U106-HANDOFF.md). Tagged Windows suite: 2253 passed / 15 skipped;
Mac: 2236 / 32. Both frozen packages and Windows USB start passed; eight public assets signed with the
existing owner identity. This is the approved first researcher-experience increment. Project isolation,
broader report comparisons/exports, aggregate-date statistics and human usability studies remain open;
science/overconfidence logic and experimental Field Station code are unchanged.

## U100 (on `claude/u100`, built on U99): memory you can see and steer

- Session notes, suggested memories, the readable memory folder and guidance files:
  [docs/MEMORY-U100.md](docs/MEMORY-U100.md). The memory store stays the source of truth; the markdown
  folder is a readable copy (a decision for the owner to review). Inferred guesses go to
  `memory/suggestions.py`; don't route them back into `add_fact` without a confirmation.

## U99 (on `claude/u99`, one squashed commit): conversational actions and operational self-knowledge

- `core/capabilities.py` is THE inventory of what Cursiv supports; add a feature there (with its code and
  tests) and every reader follows. A failed live read is "unknown", never "off". Disabled != missing.
- `core/evidence_log.py` records what Cursiv itself read or checked; `core/claim_evidence.py` flags
  verification claims without a record and answers "have you inspected…" / "you said… check it".
  Never let the model write evidence records; keep "supplied to the model" separate from "inspected".
- Writing is not doing: persona rules, `response_style.writing_guidance`, the refusal retry, and the
  `turn_policy` "without …," fix. Session memory is left out of writing/creative requests (it caused the
  repetition, measured). Report: [docs/SELF-KNOWLEDGE-U99.md](docs/SELF-KNOWLEDGE-U99.md).
- `core/intent.py` (conversational actions): the model only proposes one native command; Cursiv checks it
  against the person's words and confirms changes. Publish the held-out score
  (`scripts/intent_bench.py --set heldout`): [docs/CONVERSATIONAL-ACTIONS-U99.md](docs/CONVERSATIONAL-ACTIONS-U99.md).
- Live-model checks: `CURSIV_LIVE=1 pytest tests/test_self_knowledge_live.py` (12/12 on qwen3:4b-instruct).

## U101 starter profiles (Claude, 2026-10-25, released in U101)
Profiles are markdown files in `agents/starters/`; `agents/profile_context.py` fetches what `reads:` allows
(never a tool call); `answer_note` flags numbers/units not in the records. Live on qwen3:4b: @checker found all
4 planted problems; @protocol gave both holding times with pages 3/3 after the "every condition" rule; the
Report writer invented a unit, methods and a model name before the code check and rules were added. No First
aid profile (medical stays with the reviewed reference). Owner rule: no self-editing agents.

## U102 published (Claude, 2026-10-25)
Tag `v3.14-U102` = `36a2428` (PR #32): Windows Job Object isolation (`core/confined.py`; a venv/py launcher
is resolved to the real interpreter because the job allows one process), 237-case calc benchmark (six
defects fixed), notebook integrity matrix, encryption recovery tests + `write_recovery_copy`, threat model /
support matrix / recovery / notebook docs, JUnit artifacts. Evidence: [U102-RELEASE-VERIFICATION](docs/U102-RELEASE-VERIFICATION.md).
Next: website repositioning toward field research (owner approved), then U103 (USB/FS matrix, sync, exports
sidecar metadata, retrieval) and U104 (performance/UX). A recovery menu item is planned, not built.

## U105 published (Claude, 2026-10-26)
Tag `v3.14-U105` = `501d94e` (PR #43): signing-key passphrase (`core/devicekey.py` protect/unlock/KeyLocked),
strict photo-complete import (`fieldsync.import_folder(strict=True)`), `core/safe_zip.py` + Vosk SHA-256 pin,
`tests/test_release_docs.py`. Evidence: [U105-RELEASE-VERIFICATION](docs/U105-RELEASE-VERIFICATION.md).
Handoffs for other assistants: docs/U105-HANDOFF.md, docs/FIELD-STATION-HANDOFF.md. Next: Field Station
phases 6-9 when a Raspberry Pi 5 arrives.

## U104 published (Claude, 2026-10-26)
Tag `v3.14-U104` = `47c4ceb` (PRs #38, #40, #41). Field Station preview (`cursiv_engine/station/`, plan and
status in docs/FIELD-STATION-PLAN.md, handoff for other assistants in docs/FIELD-STATION-HANDOFF.md) and
team-drive demo fixes. Evidence: [U104-RELEASE-VERIFICATION](docs/U104-RELEASE-VERIFICATION.md). Website:
/field-station and /team-drives. Next (U105): the outside-review items (drive-key passphrase, strict
photo-complete import, Vosk checksum + safe unzip limits, release-doc consistency test); Field Station phases
6-9 when a Pi 5 arrives.

## U103 published (Claude, 2026-10-26)
Tag `v3.14-U103` = `5c821ca` (PRs #35, #36). Evidence: [U103-RELEASE-VERIFICATION](docs/U103-RELEASE-VERIFICATION.md).
Next (owner asked): a demo with real screenshots, leading with three named SSDs brought back into one main
computer and a new drive sent out with chosen notebooks. Open: physical multi-drive test by the owner.

## U103 team drives (Claude, 2026-10-25, PR #36)
Notebook identity: `fieldlog/notebook.json` {id, name}; `_device()` returns the notebook id (an existing
notebook keeps its first entry's label; nothing is written until it's named). Shares carry the name;
imports keep `team/<id>.identity.json` (written only when it changes, so re-import is byte-identical).
A log may hold only its own notebook's label (strict, signed or not: the team view attributes by it; a drive used on two PCs before U103 is refused). On a drive,
`fieldsync.auto_share()` keeps `cursiv-field-share` at the drive top (start, quit, notebook close, and at most
every 30 s while recording). `usb_sync.team_notebook` routes another person's notebook to the team view
(action "team"), never a file copy over this computer's. `make_usb(workspace_name, team_ids)`: a named drive
gets its own notebook and key; `fieldsync.copy_notebooks_to` puts only chosen notebooks on it.
Mandatory gate: tests/test_team_drives.py (+ test_fieldsync.py) under `-m usb`.

## U103 work (Claude, 2026-10-25, merged in PR #35)
Finishes the review list. `science_check.overconfidence_note` (wired in chat/completion.py beside the other
science notes) judges the verdict lines only (first sentence, lines starting Yes/No/So); measured with
`scripts/overconfidence_bench.py`, results and hand labels in bench/overconfidence/RESULTS.md. Re-run
`--heldout` after changing the rule and report numbers as measured. `do_note` now ignores readings.
tests/test_silent_errors.py: pass/continue-only handlers in core storage, guardian and memory need
`# best-effort: <why>`. Phone sync drops secret-bearing memories (problem_report.has_secret). Kept on purpose:
sigil.py (saved files use its encodings) and agents/offline_queue.py (live chat tool). usb_ops.wipe_private_copy
removed (unused since U83). Icons: launcher/resources/gen_icons.py builds from icons/cursiv-logo-source.png.
Website (already published): new logo everywhere, social preview 20261025, notebook screenshot full width,
notebook service-worker cache v4.

## U101 published (Claude, 2026-10-25)
Tag `v3.14-U101` = `df74806` (PRs #28, #29, #30). Evidence: [U101-RELEASE-VERIFICATION](docs/U101-RELEASE-VERIFICATION.md).
Next from the review: tests for problem_report / login_recovery / chat_actions, one notebook read path,
overconfidence benchmark, dead modules, silent-except lint; profile form window; Settings reorganisation.

## U101 data safety (Claude, 2026-10-25, branch `claude/u101-data-safety` on top of hardening)
From the codebase review: login files atomic + accounts backup + `AccountsUnreadable` (tests/test_login_files.py);
`fieldlog/received/` and `fieldlog/.import-*` are now vault-covered, oversized uploads go to `received-large/`,
and `vault_migration.set_aside_large_uploads` moves (never deletes) old oversized readable uploads so they can't
stop an unlock (tests in test_notebook_encryption.py); strand/session loaders report damaged lines in `status`
(tests/test_damaged_lines.py). Writers already kept damaged lines; nothing was being lost, only unreported.
Still open from the review: tests for problem_report/login_recovery/chat_actions, one notebook read path,
overconfidence benchmark, dead modules (sigil, quality_scorer, offline_queue), silent-except lint.

## U101 hardening (Claude, 2026-10-25, released in U101)
- Codex run-and-fix: `coding/runner.py` runs `python -I <copy of core/plugin_runner.py> --script main.py`; the
  audit hook blocks what the word check misses (getattr(builtins, ...), importlib). Refusals -> "SANDBOX:".
- CI: `test-linux` job (Ubuntu): first run 2,017 passed / 30 skipped. Not a required check yet.
- `core/fieldsci.py` + `scripts/fieldcalc_bench.py` (bench/fieldcalc/cases.py written before the code; two
  hand-worked expected values were wrong and were recomputed): qwen3:4b 9/14 -> 14/14, 0 trap claims. The U100
  saturation answer had been answering "percent saturation" questions; it now steps aside.
- CONTRIBUTING: the rule behind the code; docs/GOOD-FIRST-ISSUES.md drafts five issues (not posted).
- Owner validated the encrypted USB round trip across clean PCs (2026-10-25).

## U100 published (Claude, 2026-10-25)
Tag `v3.14-U100` = `7c297d5` (PR #24). First three-digit U number: the updater compares
versions as numbers (`launcher/cursiv_launcher.py` `_version_key`), so U100 > U99.
Evidence: [U100-RELEASE-VERIFICATION](docs/U100-RELEASE-VERIFICATION.md).

## U100 audit of the owner's U99 test run (Claude, 2026-10-25, released in U100)
Root causes found and fixed with tests (`tests/test_notebook_audit.py`, `test_conversation_audit.py`,
`test_science_audit.py`): the fieldlog parser read codes as negative measurements; SESSION MEMORY carried
other conversations into ongoing ones; the stats tool always checked answers against the mean; the units tool
ignored requested decimal places. `scripts/replay_notebook.py` and `scripts/suggest_bench.py` run on the real
code in throwaway folders (APP_DATA too: HOME alone leaks into the checkout's `.cursiv`). Prompt-only items
(overconfidence, experiment design) are NOT shown fixed: live, the thermometer answer still says "normal".
Document questions measured at ~8 s here, search ~60 ms; no speed change made.

## U99 published (Claude, 2026-10-25)
Tag `v3.14-U99` = `3345d8b` (PRs #23, #25). Conversational actions (confirm cards) and
operational self-knowledge (capability registry, evidence records, writing not refused).
`scripts/website_release.py` now takes `--windows-skips` and `--date` (U99 skips 13 on
Windows: 12 live-model, 1 Keychain). Evidence: [U99-RELEASE-VERIFICATION](docs/U99-RELEASE-VERIFICATION.md).

## U98 published (Claude, 2026-10-25)

Tag `v3.14-U98` = `1bc1593` (PRs #20, #21). Plugins isolated in their own process, field
notebook and custom agents encrypted, chat look part 1. The first (unpublished) tag was
moved after its own packaged self-test caught an already-loaded `socket` in the runner.
Evidence: [U98-RELEASE-VERIFICATION](docs/U98-RELEASE-VERIFICATION.md).

## U97 published (Claude, 2026-10-25)

Tag `v3.14-U97` = `c7554a7` (PRs #17, #18). Trust fixes from the U96 live run, encryption
always on for a computer (a Cursiv USB drive stays readable; `usb_sync` decrypts and
re-encrypts), and the family letters, legacy vault, board, mailbox and council removed.
Evidence: [U97-RELEASE-VERIFICATION](docs/U97-RELEASE-VERIFICATION.md).

## U98 (2026-10-25, one squashed commit on `claude/u98`)

- Custom agents are covered by the vault (`agents` in `vault.FOLDERS`); their prompt no longer says "his family".
- Plugins never run inside Cursiv: every registration, command, tool and hook call runs
  in its own process (`core/plugin_runner.py`; `Cursiv.exe --plugin-runner`, dispatched
  at the very top of `launcher/main.py`) with a cleaned environment, a time limit and a
  PEP 578 audit hook refusing network, other programs, native code and files outside the
  plugin's data folder. Forge's test runs use the same runner. The packaged self-test
  checks it ("plugin isolation").
- The field notebook is encrypted with the vault (`vault.notebook_covered`); computers
  already on U97 adopt it at unlock (`vault_migration.adopt_new_stores`).
- Chat look part 1 (`launcher/chat_badges.py`): starter cards, worked-by-Cursiv badges,
  receipt cards, one-time offline note and tour, plain-words error cards.
- Tests never touch the real conversations folder (conftest): with a real vault on this
  PC they failed "locked".
- Do not reintroduce in-process plugin loading (`exec_module`) or Forge's external-Python
  harness.

## What the user asked for

A quick overhaul so Cursiv stops declaring an answer correct without checking. Five pieces, in this order:

1. A real verification pass after the draft exists.
2. An assumption / evidence ledger on complex turns, stored with the turn.
3. Memory origin tags, dates, safety precedence, and conflict surfacing.
4. A small benchmark suite in `tests/`.
5. Proportional triggering so casual chat stays fast.

## Where the draft actually comes from

`chat()` in `cursiv_engine/ui/chat_app.py` does **not** call `cascade_stream()`. The desktop window streams `_chat_inner` via `_chat_stream`, which collects the draft in the `reply` list while yielding tokens. `cascade_stream()` is the one-shot helper used by Babel, council, and other commands.

The verification pass runs in `chat()` **after** `_chat_stream` returns and after `speed.chat_finished()`, so the local model is free. The user already sees the streamed draft. The pass then appends either nothing, a revised answer, or notes.

Verifier calls go through `_router_llm`: the local model when one is ready, no idle wait. The user's free Groq/Gemini key is used only when there is no local model, and a local call that fails does not fall back to the cloud (C-008, 2026-10-17; `_quick_llm` for learning follows the same order). The check runs before `chat_finished()`, so background learning cannot take the local model in the middle of it. Paid keys and Cursiv Cloud are not used for the check.

Since 2026-10-17 (Lane 1, see `docs/AUDIT-2026-10-17.md`), `run_pass` also receives:
- `context`: the last six messages and the memory block recalled for the question (`_check_context`). The checker, the rewrite and the ledger-fill call all see it (C-024).
- `sources`: text actually looked up this turn (web search, plugin context, local tool results), collected in `chat_app._RETRIEVED`.
- The draft is the model's text with Cursiv's status lines stripped (no `*[Answered by …]*`), so the footer no longer triggers the pass.

Two deterministic checks were added (C-025): `known_problems` (a Known item with a number nobody gave, or mostly words nobody used, is an inference or an assumption) and `citation_problems` (a named source such as the CDC, WHO or "the local government report" may only be cited when its text was looked up this turn, or the person brought it up).

## Files

| File | Role |
|---|---|
| `cursiv_engine/core/verify.py` | Triggers, ledger, deterministic checks, one revise, session ledgers |
| `cursiv_engine/ui/chat_app.py` | Prompt addendum at the end of prompt build; `chat()` runs `verify.run_pass` |
| `cursiv_engine/core/phases.py` | Grounding trace notes when a ledger is required |
| `cursiv_engine/memory/semantic.py` | `origin`, `date`, conflict surfacing, safety quarantine |
| `cursiv_engine/codex/system_prompt.md` | Hard rule in Section 2 (kept by the compact persona) |
| `launcher/memory_dialog.py` | “What I remember” shows the origin tag |
| `tests/test_verify.py` | Benchmarks. No network. |

`tests/test_core.py` and `tests/test_honesty.py` were not rewritten. They still pass.

## Behavior

### 1. Verification pass

`verify.run_pass(user_text, draft, ask)`:

- Deterministic checks always run when the pass is triggered: number/definition drift, assumed items stated as facts, missing ledger on a complex turn.
- Then one verifier call. The instruction is exactly: “List concrete problems only: unsupported claims, changed definitions, contradictions, assumptions presented as facts, answers to the wrong question. If none, say CLEAR.”
- A model reply of `CLEAR` does **not** erase a deterministic problem. That is the “declared itself correct” fix.
- If anything is wrong, **one** rewrite is requested, then the same checks run again.
- If the rewrite is clean, `chat()` yields `Revised after check:` plus the rewrite. Learning treats extracted facts as `verified`.
- If the rewrite is missing or still wrong, the original draft stays, and `chat()` yields `Draft + notes:` with the original problems. Learning is skipped for that turn so the bad draft is not stored as memory.
- If no model is available, deterministic problems are still surfaced. There is no fake `CLEAR`.

### 2. Ledger

Complex / high-stakes questions (`needs_ledger`) get this block appended (since U63 the persona no longer asks for it on every answer, and `verify.exact_format()` requests skip it and get `FORMAT_RULE` instead) to the system prompt, after the coding-brain swap so it is not dropped:

```
Known: ...
Inferred: ...
Assumed: ...
Unknown: ...
```

Known is only what the person stated. Inferred is a conclusion. Assumed is a gap the model filled. Those must not be stated as facts.

`extract_ledger` pulls the block off the draft or the rewrite and stores it in process (`verify._ledgers`). The next turn’s prompt includes `prior_ledger_block()`. The block is also part of the assistant text, so the chat window stores it in conversation history (`launcher/chat_panel.py` saves the full streamed reply).

If the only problem is a missing ledger, the pass tries one short “fill the ledger only” call before a full rewrite.

Emergency / crisis text does not get a ledger and is not verified.

### 3. Memory

Every new fact has:

- `origin`: `user_said` (manual / “remember”), `inferred` (learned, plugins), or `verified` (learned from a turn the pass cleared)
- `date`: `YYYY-MM-DD`
- `created`: unchanged `YYYY-MM-DD HH:MM`
- `source`: unchanged (`manual`, `learned`, `verified`, `plugin:…`)

Old rows with no `origin` are labeled from `source` by `origin_of()`. A duplicate save does not upgrade origin. Repeating a claim does not turn `user_said` into `verified`.

`build_context` (what the model actually reads):

- Prefixes the safety line: preferences and repeated claims never outrank safety and are not known facts.
- Tags each fact `[you said]`, `[inferred]`, or `[verified]`.
- If two recalled facts conflict (one negates the other, or they give different numbers on the same topic), both are included with an explicit conflict note. Retrieval does not drop one.
- A fact that tells Cursiv to ignore or override safety / the constitution is listed under “Not applied” and is not given as a usable memory.

The memory window (`launcher/memory_dialog.py`) and `what do you remember` use `fact_subtitle()`, which shows date, origin, and family.

### 4. Benchmarks

`python -m pytest tests/test_verify.py tests/test_core.py tests/test_honesty.py`

Ran with Python 3.13 on 2026-10-16: `tests/test_verify.py` and `tests/test_honesty.py` passed. `tests/test_core.py` has one failure that was already there and is not part of this change: `test_portable_mode_points_home_models_and_ollama_at_the_drive`. The test sets `CURSIV_REAL_HOME` to an empty string, and `launcher/portable.py` uses `setdefault`, so it stays empty. Do not “fix” that while working on verification.

`tests/test_verify.py` covers constraint drift, definition drift, assumption-vs-fact, self-correction that introduces a new number, memory conflict, safety precedence, origin not upgrading, seeded `CLEAR` that still loses to the deterministic check, proportional triggers, crisis skip, ledger stored for the next turn, and one `chat()` pass with `_chat_stream` and `_router_llm` faked. The memory window was not opened; `fact_subtitle()` is what it renders.

### 5. Proportional trigger

`should_verify` is true when any of these hold:

- The draft contains a digit, a recommendation (“I recommend”, “you should”, “I suggest”), or a technical claim (API, retry, server, dosage, and the other words in `_TECH`).
- The user asks “is this correct?” / for a review (`_REVIEW`).
- The user is stating a memory (`remember that`, `my name is`, `I prefer`, `from now on`, `I always want`).
- The previous pass failed (`verify._previous_failed`). The next turn is checked even if it looks casual. A clean pass clears the flag.

Casual chat (“hey how are you”) does not call the verifier.

Not every turn that background-learning might touch is verified. Learning still runs on those turns, and the facts stay `inferred`. A failed pass skips learning. Do not “fix” this by verifying every message; the user asked for casual chat to stay fast.

## What not to change

- Do not route verification through paid xAI / OpenAI / Claude or Cursiv Cloud.
- Do not buffer the whole answer before the first token. The check is after the draft.
- Do not auto-revise more than once.
- Do not let a `CLEAR` string override number drift, a changed definition, or an assumption stated as fact.
- Do not let a saved preference override `cursiv_engine/core/constitution.py` or the Section 2 safety paragraph.
- The 8 phase names stay as they are. The ledger is an extra note on the Grounding trace, not a 9th phase.

## Not done

- `cascade_stream()` callers (Babel, council, codex commands) are not wrapped. Only `chat()`.
- Conflict detection is lexical (shared content words + negation or different numbers). It will miss paraphrases embeddings would catch.
- No browser or Qt run of the memory window. `fact_subtitle()` is what the dialog renders; that function is tested.

## U97 (2026-10-24): removals, trust fixes from the U96 live run, encryption always on

- Removed: family letters, legacy vault, personal letters, postal/board/mailbox and the
  council (copies kept in the git-ignored `private/`). `core/profile.REMOVED_NOTE`
  answers the old commands; `council`, `/full`, `/deliberate` point to `agents ask`.
  The phases module lost its council branch only. Plain MIT license.
- "What day is it?" is answered from the computer's clock (`core/clock.py`), and the
  date is in the live status block.
- Faked file actions: "Add a line to notes.txt saying …" is a real append that asks
  first; "Delete notes.txt" gets Cursiv's own answer (it never deletes files).
  `file_access.unverified_claim` also catches "File deleted", "Updated and verified",
  "Now executing:" and model-printed SHA-256 lines. Tests: `tests/test_file_claims.py`.
- Plain unit conversions and speed × time questions are answered by the calculator
  (`native_answers`, `fieldcalc.travel`); compound questions still go to the model with
  the worked result. Field-log averages/min/max come from the notebook
  (`field_recall.stats_command`). `response_style.drop_self_certification` removes the
  model's own "✅ Verified: …" / "No model was used" lines (part of the polish step in
  `chat/completion.py`; "Fact:" / "Speculation:" labels the person asked for stay).
- Encryption is always on for a computer (`launcher/encryption_dialog.py`): the first
  start asks for a passphrase and migrates; an unfinished migration resumes at the next
  start. A Cursiv USB drive (portable mode) stays readable by the owner's choice.
  `usb_sync` decrypts covered stores going to a drive and re-encrypts them coming back;
  staged imports stay encrypted; the vault marker and `.vault-recovery/` never travel.
  `vault_migration.require_closed` exempts this process's own launchers.
