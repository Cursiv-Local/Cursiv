# Handoff — Cursiv verification overhaul

Repo: `C:\Users\joshu\OneDrive\Documents\GitHub\Cursiv-v3`
Remote: `https://github.com/winklersllc2026-bit/Cursiv.git` (branch `main`)
This is the winklersllc checkout. Do not edit `Cursiv-v2`, Desktop `Cursiv-V3`, or `joshua1993winkler-jpg/Cursiv`.

Status: **implemented in the working tree, not committed.** Read this before changing chat, memory, phases, or tests.

## What the user asked for

A quick overhaul so Cursiv stops declaring an answer correct without checking. Five pieces, in this order:

1. A real verification pass after the draft exists.
2. An assumption / evidence ledger on complex turns, stored with the turn.
3. Memory origin tags, dates, safety precedence, and conflict surfacing.
4. A small benchmark suite in `tests/`.
5. Proportional triggering so casual chat stays fast.

## Where the draft actually comes from

`chat()` in `cursiv_v215/ui/chat_app.py` does **not** call `cascade_stream()`. The desktop window streams `_chat_inner` via `_chat_stream`, which collects the draft in the `reply` list while yielding tokens. `cascade_stream()` is the one-shot helper used by Babel, council, and other commands.

The verification pass runs in `chat()` **after** `_chat_stream` returns and after `speed.chat_finished()`, so the local model is free. The user already sees the streamed draft. The pass then appends either nothing, a revised answer, or notes.

Verifier calls go through `_router_llm`: the local model when one is ready, no idle wait. The user's free Groq/Gemini key is used only when there is no local model, and a local call that fails does not fall back to the cloud (C-008, 2026-10-17; `_quick_llm` for learning follows the same order). The check runs before `chat_finished()`, so background learning cannot take the local model in the middle of it. Paid keys and Cursiv Cloud are not used for the check.

Since 2026-10-17 (Lane 1, see `AUDIT-2026-10-17.md`), `run_pass` also receives:
- `context`: the last six messages and the memory block recalled for the question (`_check_context`). The checker, the rewrite and the ledger-fill call all see it (C-024).
- `sources`: text actually looked up this turn (web search, plugin context, local tool results), collected in `chat_app._RETRIEVED`.
- The draft is the model's text with Cursiv's status lines stripped (no `*[Answered by …]*`), so the footer no longer triggers the pass.

Two deterministic checks were added (C-025): `known_problems` (a Known item with a number nobody gave, or mostly words nobody used, is an inference or an assumption) and `citation_problems` (a named source such as the CDC, WHO or "the local government report" may only be cited when its text was looked up this turn, or the person brought it up).

## Files

| File | Role |
|---|---|
| `cursiv_v215/core/verify.py` | Triggers, ledger, deterministic checks, one revise, session ledgers |
| `cursiv_v215/ui/chat_app.py` | Prompt addendum at the end of prompt build; `chat()` runs `verify.run_pass` |
| `cursiv_v215/core/phases.py` | Grounding trace notes when a ledger is required |
| `cursiv_v215/memory/semantic.py` | `origin`, `date`, conflict surfacing, safety quarantine |
| `cursiv_v215/codex/system_prompt.md` | Hard rule in Section 2 (kept by the compact persona) |
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
- Do not let a saved preference override `cursiv_v215/core/constitution.py` or the Section 2 safety paragraph.
- The 8 phase names stay as they are. The ledger is an extra note on the Grounding trace, not a 9th phase.

## Not done

- Not committed or pushed.
- `cascade_stream()` callers (Babel, council, codex commands) are not wrapped. Only `chat()`.
- Conflict detection is lexical (shared content words + negation or different numbers). It will miss paraphrases embeddings would catch.
- No browser or Qt run of the memory window. `fact_subtitle()` is what the dialog renders; that function is tested.

## Network gate (Lane 2, 2026-10-17)

`cursiv_v215/core/netgate.py` is the one switch for connections off this computer (AUDIT C-009, C-010, C-011). Settings live in `.cursiv/config.json` next to the keys:

| Setting | Default | Command | What it does |
|---|---|---|---|
| `offline_mode` | off | `offline on/off` | Closes the gate. Persists across restarts. |
| `web_search_auto` | off | `websearch on/off` | Trigger words ("today", "right now", "this week") search the web. Off: only a message starting `search:` / `search ` does. |
| `update_check_auto` | off | `autoupdate on/off` | GitHub update check 10 s after login. The Check for Updates button always works (unless offline). |

All three are also checkboxes in Settings.

While the gate is closed:
- `allowed()` is False. `_needs_search`, `_web_search`, `_is_online`, `_post_json`, `cloud_enabled`, `_free_key_llm`, the free-key fallback, `cascade_stream`, the forced providers (`grok`/`claude`/`openai`/`council` answer locally with a note), `_pull_ollama_model`, the Setup and USB model pulls, the embedding-model pull and the update check all stop first.
- An audit hook (installed when netgate is imported, which `chat_app` does at import) raises `NetworkBlocked` (an OSError) on any non-loopback `socket.connect`, `sendto` or DNS lookup. That's the backstop for anything that forgot to ask. Ollama is on 127.0.0.1, so it keeps working. Saved keys are kept; they're just not used.

The Connectivity phase no longer probes 8.8.8.8 on every message. `_connectivity_probe` returns None ("not checked") when the gate is closed, or when the local model is ready and no cloud key or `web_search_auto` is set. A None isn't cached.

Proof: `tests/test_netgate.py` (records and refuses every outside connection with an audit hook) and `py -3.13 scripts/net_audit.py --offline` (a fresh copy of the source, an empty home, real `chat()` against the real local Ollama, logs every connection).

Not changed: Cursiv Cloud is still on by default for people with no local model (`_cloud_settings` writes `enabled: True`). With the gate open and Ollama running, a missing `nomic-embed-text` is still pulled automatically. That's Ollama's traffic, not Cursiv's process.

## Answer quality (2026-10-17, U61 draft)

- `core/reference.py`: chat looks up `reference_data/` for each message. A match puts the entry in the prompt (cite `[category/slug]`), and first-aid and survival entries are shown word for word in a status line, because a 1.5B model misquoted the numbers live. Three unreviewed entries (`NOT_IN_CHAT`) are only shown by `ref`.
- `phases.emergency_kind`: "medical" keeps the normal prompt plus first-aid instructions; "crisis" and "danger" keep the care-first crisis prompt.
- `chat()` skips the verify pass on any emergency turn (`_EMERGENCY_TURN`), and shows failed-check notes compactly (`_compact_notes`: at most three one-line items, under "Checked, with notes"). `verify.py` itself is unchanged.
- `chat(replace_draft=True)` (the chat window only): a clean revision replaces the draft on screen and in history (`REPLACE_SENTINEL`).

## Answer safety (2026-10-18, U63)

From a review of real answers (a bleeding answer said not to bandage or use a tourniquet) and the first-time-user findings.

- `reference_data/sources.json`: source, URL, check date and `reviewed` (all false) per entry; `reference.source()`; `note_line` shows "Based on ... (checked ...)". Bleeding, tourniquet, water, hypothermia rewritten from Stop the Bleed / EPA / CDC.
- `reference.ALIASES` entries may be tuples: all words needed (`("bleach", "gallon")`), so cleaning questions don't get the water card.
- `agents/reference_brain._bundled_search` (the online-AI tool) uses `reference.lookup`. Its old any-shared-word scoring was the cause of unrelated cards.
- `phases._MEDICAL` covers spurting / pouring blood, bleeding out, won't stop bleeding. Persona rule 3 separates crisis care from medical emergencies.
- `core/answer_check.py`: no model call, runs on every turn including emergencies, from `chat()` right after the draft. `contradictions()` (a negated `KEY_STEPS` step for a shown entry; "unless trained") and `unsupported_actions()` (claimed database/web search when `_WEB_SEARCHED` is false). Lines start "Cursiv's check:" and render amber.
- `chat_panel.split_details`: ledger lines and "Checked, with notes" go behind a "Show reasoning and checks" link (`cursiv://details/<text>`, opens a dialog). Medical and survival cards render at normal size.
- `verify.py` changed only by adding `exact_format` / `FORMAT_RULE`; the pass itself is unchanged.
- Benchmark: suites 1.1 (new cases, 4 defective checks fixed) and 1.2 (checks only: curly apostrophes, ledger "Unknown:" lines no longer count as admitting it can't know, negations before unsafe phrases). `truth_bench.py --model / --source <ref>`, `truth_rescore.py`, `compare_models.py`. Open failures: `bench/FAILURES-U63-pre.md` (rea-009 arithmetic, ref-015 dose merge, amb-002 assumed "it").
- Not done: the six Phase 1 prompts need to be re-run once the owner supplies them; a dose-number comparison against the card; the model comparison run.

## Releases

Build every installer with `py -3.13 scripts/build_release.py <tag>`: it checks that the version in `core/selfknow.py`, `launcher/cursiv_launcher.py` and `installer/cursiv_setup.iss` matches the tag, builds in a fresh git worktree of the tag, and copies the installer to `installer/Output/`. Don't build from the working tree (U59 was built from uncommitted code; U63's first build picked up edits made during the build). `tests/test_versions.py` keeps the three version strings equal; CI runs the tests on every push to main and every PR. A release needs a GitHub release with `Cursiv-Setup-<version>.exe` and `Cursiv-Setup-latest.exe`, not just a push.
