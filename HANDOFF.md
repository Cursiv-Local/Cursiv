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

Complex / high-stakes questions (`needs_ledger`) get this block appended to the system prompt, after the coding-brain swap so it is not dropped:

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
