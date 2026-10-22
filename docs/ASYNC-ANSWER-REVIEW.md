# Answer review without a post-generation wait

> Publication follow-up: the owner subsequently authorized commit/push,
> packaging, release and website deployment. U83 stayed an unpublished candidate
> after a full-window smoke failure; U84 repairs it and expands that gate.
> Earlier status statements below record audit checkpoints. See
> [U84 verification](U84-RELEASE-VERIFICATION.md) for current publication results.

## Status and confirmed cause

Unreleased source changes on `codex/maintainability-hardening`, 2026-10-22.
The installed U82 application is unchanged. No commit, push, version bump,
installer build, release or deployment is authorized for this work.

The previous completion generator called `core/verify.py::run_pass()` before
the desktop worker emitted `done`. It could request a ledger, a verdict, a
rewrite and another verdict. The window could still scroll, but Send remained
disabled. This is model inference after generation, separate from Markdown
formatting. The previous selector admitted any digit, generic recommendations,
memory-update wording and the previous turn's failure.

## New behavior

1. Keep the existing pure-code evidence, calculation, citation, dose, action
   and contradiction checks in the foreground worker. A detected unsafe
   dose/reference contradiction still withdraws the draft immediately and
   displays the supplied reference. Model prose cannot authorize an operation.
2. Default to **fast** mode. Ordinary chat/factual replies, years, dates, list
   numbering and generic recommendations do not request a model review merely
   because they contain those features. Concrete safety/dosing language,
   numerical quantities/arithmetic, conflicting claims, action assertions or
   explicit check requests remain eligible. These are finite heuristics.
3. Fast mode reports deterministic problems directly. For eligible turns without
   those findings, it permits one short model verdict, with no model rewrite.
4. The desktop queues a review job, finalizes the draft, saves it through the
   existing autosave path and enables input. Only then does a daemon worker
   begin the optional model request. Results arrive as a labeled follow-up on
   that same message; an accepted full-mode revision is a **suggested revision**,
   rather than a silent replacement of the draft.
5. Each job captures supplied history/memory, copied calculation/document/tool
   evidence, and scoped grounding/policy state. It does not recall another saved
   memory, read later turns' facade evidence, change session ledgers or authorize
   assistant-derived memory retention from a pending review.
6. New turns, conversation switches, cancellation and errors invalidate older
   jobs. A result also checks its conversation generation, message position and
   original content before touching the latest message. Widget/history updates
   occur in the Qt result slot. One model-review slot prevents a cancelled-job
   backlog. The original incremental renderer, message cache and themes remain.
   An explicit Cross-check result also invalidates an automatic review before
   appending its separate block, so a late automatic result cannot erase it.

### Controls and limits

| Command | Model review | Pure-code checks |
|---|---|---|
| `check` / `check status` | Show the current setting | Always on |
| `check off` | None | Always on |
| `check fast` | Default; at most one eligible short verdict | Always on |
| `check full` | Eligible verdict, at most one rewrite, then recheck if changed | Always on |

The mode is saved as `answer_check_mode` in the existing configuration. The
setter preserves other fields and refuses corrupt settings. It creates no
additional copies of key configuration. There is no new settings screen.

Verdicts use at most **180 output tokens**; a full-mode rewrite uses at most
**300**. Full mode no longer makes a separate ledger-only request. An unchanged
rewrite receives no second model verdict. Review input is bounded to a
4,000-character question, an 8,000-character answer, 1,600 characters of supplied
context and 2,400 characters of evidence; oversized turns receive an unverified
review-limit note after the pure-code checks.

Desktop background review uses the existing `standard=True` installed-local-model
selector, even when Deep Think is on. It never starts/downloads a model or falls
back to an external provider. If no local model is available, the draft remains
available with a review-unavailable note. This applies to cloud-generated drafts
too. The selector can honor an advanced user's configured standard model; it is
not a new speed-ranking mechanism.

Programmatic callers without `on_review` retain a synchronous bounded check.
`chat()` defaults to fast mode; direct `verify.run_pass()` keeps its full-mode
default for API compatibility. Deterministic errors are never cleared by a
model's `CLEAR`. A bounded clear verdict is not proof of factual or clinical
correctness, or evidence of a completed tool action.

## Measurements actually taken

The original pre-change source is retained at
`%TEMP%/cursiv-maintenance-5ebnl5c5/src` (1,177 passed, 1 skipped baseline).
The comparison used its original render replay and the updated replay from
`%TEMP%/cursiv-maintenance-eme3y4as/src`. Each replay used three runs per history
size, an 898-character rich Markdown response streamed in 16-character chunks
every 8 ms, real local autosave, offscreen Qt, a 5 ms heartbeat and native RSS
sampling. The two comparison processes overlapped on this Windows host.
The replay source fingerprints were
`fae05d03e8eec1929adf395555b018fdd1029c0affddb945cb3e06bd8654d634`
(before) and
`02281188b4cf4e750d99f4e4e7fb8c75ba6d817a3d479f7a226290ccb3738f60`
(after). The subsequent explicit Cross-check cancellation guard does not change
this replay path.

**The model wait was simulated at 1,000 ms. No live inference timing or new
Truth Benchmark accuracy is claimed by these measurements.** The updated replay
uses the real review job, result signal, targeted rendering and persistence path.
It measures desktop completion sequencing; it does not replay every foreground
intent/retrieval/learning operation inside `chat()`. Separate integration tests
exercise that generator and confirm ordinary turns issue no verifier request.

Median values, rounded:

| Existing messages | Old final token → ready | New final token → ready | Old/new Markdown parsing | Old/new full-document rebuilds |
|---|---:|---:|---:|---:|
| 10 | 1,014 ms | 21 ms | 2.19 / 2.62 ms | 0 / 0 |
| 100 | 1,021 ms | 25 ms | 1.90 / 2.50 ms | 0 / 0 |
| 1,000 | 1,076 ms | 83 ms | 1.55 / 2.53 ms | 0 / 0 |

| Existing messages | New final token → follow-up finished | New heartbeat p95 / median maximum gap | Old/new median peak RSS | Old/new median RSS growth |
|---|---:|---:|---:|---:|
| 10 | 1,041 ms | 7.3 / 19.8 ms | 58.0 / 58.3 MiB | 0.59 / 0.80 MiB |
| 100 | 1,068 ms | 7.2 / 46.2 ms | 70.5 / 70.5 MiB | 3.75 / 3.90 MiB |
| 1,000 | 1,263 ms | 7.8 / 173.1 ms | 173.0 / 176.5 MiB | 25.79 / 30.31 MiB |

The largest individual heartbeat gap in the new 1,000-message runs was **263 ms**.
The extra follow-up save/render is included; long-history persistence is not
free. Median final persistence including the follow-up was 1,083 / 1,133 /
1,592 ms. Ready time met 250 ms in every replay run (largest 97 ms), independent
of the simulated review wait. This does not guarantee that latency on every PC.

Raw results:

- [Original blocking path](../bench/results/answer-review-blocking-20261022.json)
- [Background path](../bench/results/answer-review-background-20261022.json)

Reproduce with the repository's Python environment:

```powershell
python scripts/benchmark_chat_rendering.py --repeats 3 --check-delay-ms 1000 --output blocking.json
python scripts/benchmark_chat_rendering.py --repeats 3 --check-delay-ms 1000 --background-check --output background.json
```

The first command simulates the blocking architecture on current source; the
retained baseline result above used the original pre-change source. The script
creates a disposable home and uses synthetic history without provider calls.

## Test coverage and remaining risks

Focused review/rendering/policy suite: **208 passed in 12.49 s**; log and source
manifest at `%TEMP%/cursiv-maintenance-eme3y4as/`. Coverage includes selectors,
settings persistence/corruption, fast/off/full call limits, unchanged rewrites,
short standard-model requests, evidence isolation, no learning from pending
assistant claims, unavailable models, cancellation/stream closing, busy review
slots, input bounds, Qt buttons while the reviewer is blocked, late-result
rejection and conversation switching. Existing rendering, replacement,
cross-check, safety, restricted-turn and module-boundary checks also ran.

After the persistence and false-capability rewrite tests, the focused
review/grounding/rendering suite passed **118 tests in 9.41 s** in
`%TEMP%/cursiv-maintenance-112oap7s`. Final complete Windows suite, including the
subsequent explicit Cross-check cancellation guard: **1,209 passed, 1 skipped
in 176.73 s**, log/manifest at `%TEMP%/cursiv-maintenance-u7nhk2vp`.
The only skip needs a real Mac's Keychain. Application/launcher fingerprint:
`2ea2f061cd06916a76ada19d72a92dcaa974207b1070f735041aec36cf65663e`;
this identifies the source at that checkpoint. The subsequent
[trust follow-up](TRUST-BOUNDARY-FOLLOWUP.md) records later supplied-memory/source
changes and their tests. The initial full
attempt had **1,205 passed, 1 failed, 1 skipped in 162.90 s**, retained at
`%TEMP%/cursiv-maintenance-mye4hr41`. Its old grounding regression mocked a review
for generic conversation; the repaired test explicitly requests full review and
retains its requirement to reject false memory-capability claims.

Cancellation is cooperative: a blocked backend read can wait until its next
token/response or existing provider timeout. That request may still compete with
a new answer for local compute in the meantime. No new hard HTTP-abort mechanism
or separate model service is introduced. An unavailable/busy review is labeled,
never treated as a successful check. Switching away discards a pending review;
returning does not automatically re-run it.

Follow-up notes persist as part of the same conversation message, with optional
`background_review` status/problem metadata. They can inform later conversation
context as labeled review prose, but are not tool receipts or verified memories.
The old global facade still prevents a claim of safe concurrent server chats;
this desktop review isolates its own evidence rather than refactoring all turn
state. Physical installed/portable-PC and current Mac checks remain pending.

## Exact files for this follow-up

- Production: `cursiv_v215/core/verify.py`, `cursiv_v215/chat/review.py`,
  `cursiv_v215/chat/completion.py`, `cursiv_v215/ui/chat_app.py`,
  `launcher/chat_review.py`, `launcher/chat_panel.py`,
  `launcher/commands_system.py`, `launcher/chat_commands.py`.
- Checks: `tests/test_background_review.py`, `tests/test_verify.py`,
  `tests/test_replace_draft.py`, `tests/test_verification_hardening.py`,
  `tests/test_chat_rendering.py`, `tests/test_grounded_chat.py`,
  `scripts/benchmark_chat_rendering.py`,
  and the two new raw benchmark JSON files above.
- Documentation: this report, `README.md`, `CHANGELOG.md`, `TECH.md`,
  `ARCHITECTURE.md`, `HANDOFF.md`, `docs/VERIFICATION-POLICY.md`,
  `docs/MAINTENANCE-HARDENING.md`.

The master maintenance report inventories the entire pre-existing uncommitted
branch. This follow-up does not edit application storage backends, installer,
updater, website, benchmark source cases or historical benchmark results.
