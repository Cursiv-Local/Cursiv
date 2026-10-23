# Native replies and hard execution boundaries — local follow-up

Historical local checkpoint: these repairs are now included in U86. See
[U86 release verification](U86-RELEASE-VERIFICATION.md) for the combined source,
version and actual publication outcomes. The local status below describes the
checkpoint before the owner authorized publication.

## Status and decisions

Unreleased work on `codex/u85-live-test-followup`, preserving the earlier local
[live-session repairs](LIVE-TEST-FOLLOWUP.md). No commit, push, version bump,
installer rebuild or website deployment was performed. Published U85 evidence
is unchanged. Personal transcripts and `test_internals/` are excluded from test
snapshots and commits.

The owner explicitly chose: **read-only permits requested reads and blocks
writes; talk-only blocks all tools and saved-source lookup.** Neither permits
automatic memory formation. Separate chat-history settings still govern history
retention. Encryption, signing and physical USB persistence remain separate.

## Audit and changes

| Gap found in the current source | Repair and evidence |
|---|---|
| Native replies covered a few notebook FAQs, but broader own-feature questions still reached the model. | A reviewed feature-answer module handles files, memory, offline/online behavior, USB, updates, checks, notebook basics and capabilities. Unknown recognized Cursiv workflows return an honest native unavailable answer. Unrelated questions and explicit philosophy/hypotheticals decline to the conversation pipeline. Actual notebook/file reads keep their execution routes rather than being replaced with help. |
| A restricted memory request could miss ordinary intent parsing and continue as model prose. GUI also attempted legacy adapters before core chat. | A pure pre-dispatch action gate classifies notebook, filesystem, memory, explicit allowlisted tool names and command-family operations under the effective policy. Blocked actions stop before model generation, backend calls, source lookup or formation. GUI restricted turns bypass legacy command adapters and reach that shared gate. `requested_operations()` is a pure memory-intent interface; it does not inspect pending records or storage. |
| Detected non-unit calculation conflicts could remain beneath a conflicting draft. | A deterministic-override module withdraws the model calculation and shows the code result first. Existing in-place unit-conversion correction is retained. Known contradictory history is explicitly reported alongside the correct code result. Reference/dose withdrawals now share the focused module. Unsupported execution/provenance claims get an application-authored withdrawal instead of preserving their authority in the final replacement. |
| `adv-011` supplies incompatible bleach instructions. The benchmark runner embeds them directly in the chat message, so checking only imported-library passages misses the actual case. Broad notebook intent parsing can also mistake the quoted “old notebook” for a destination. | A narrow same-condition/concentration conflict check examines both user-supplied text and actual library passages before provider generation. The real benchmark message shape is tested on both provider modes. Inline text is labeled “This message”, without inventing a filename/page or reference lookup. Explicit file/notebook/memory payloads keep their selected destination; a verified file-write regression checks exact bytes. A final-draft guard handles alternate pipelines. Different concentrations or clear/cloudy conditions are not automatically equated. No replacement dose is invented. |
| Simple flow questions were still model arithmetic. | A full-match calculator supports explicit volume/rate/time requests, L and mL, seconds/minutes/hours, positivity and finite-result checks. Native results include units, a constant-flow/no-loss assumption and application source label. Recognized incomplete/changing-flow requests get native clarification rather than model arithmetic; unmatched calculators decline. Existing per-person supply duration, clock and proportion logic remains. |
| A short offline/workspace question read memory status unnecessarily. | Native state routing runs before file dispatch, and pure state questions use session grants/network state without reading memory records. Full memory/status questions retain their authorized read path. Legacy desktop status explicitly labels its application source and describes a resolved local model as a selection candidate, not proof of the engine that answered. |
| A leading “Done.” could hide a fabricated file acknowledgement. | The existing prose guard recognizes sentence-prefixed acknowledgements and explicit common filenames. Model text remains prose, never a receipt. Real denied/unconfirmed tool results still stop model continuation. |
| `check full` could still skip a low-risk answer because the fast eligibility test ran unconditionally. | Full mode now explicitly queues review even for an ordinary answer. Fast mode retains bounded risk-based eligibility, code-check failures remain deterministic, and crises retain their no-slow-review path. Extracted pure eligibility rules preserve the `verify.should_verify` compatibility import. Token budgets, cancellation, local-only background review and post-draft scheduling are unchanged. |

Execution paths:

- Desktop: `_run_turn()` → restricted-turn adapter bypass → scoped core chat →
  `action_gate.refusal()` → native help/state/operations or explicit model fallthrough.
- Backend operations continue through `file_access`, `notebook_tools` and memory
  intents. The gate only narrows authorization and never grants access.
- Documents: actual supplied passages → `conflicting_doses()` → native refusal
  before a model is allowed to pick a dose.
- Inline supplied instructions: exact message text → the same pure conflict
  check, with no saved-source lookup. Literal native-action payloads remain data.
- Completion: streamed draft → cheap code checks → deterministic withdrawal or
  optional review preparation. Desktop review remains queued after the draft,
  with no model review call before first visible tokens.

## Files changed in this round

New production modules:

- `cursiv_v215/core/action_gate.py`
- `cursiv_v215/core/feature_answers.py`
- `cursiv_v215/core/deterministic_overrides.py`
- `cursiv_v215/core/fieldmath.py`
- `cursiv_v215/core/review_policy.py`

Integration changes:

- `cursiv_v215/core/native_answers.py`, `presence.py`, `turn_policy.py`, `calc.py`,
  `file_access.py`, `verify.py`
- `cursiv_v215/memory/intents.py`
- `cursiv_v215/chat/completion.py`, `conversation.py`, `review.py`
- `launcher/chat_panel.py`, `commands_system.py`

Tests: new `tests/test_native_boundaries.py`; update `tests/test_verify.py` to
distinguish fast mode from explicitly full mode, and `tests/test_grounded_chat.py`
to keep exercising the model-output guard on an unrelated prompt now that
own-feature questions are native. Update `tests/test_answer_check.py` and
`tests/test_phase_a.py` to require the stronger withdrawal contract: preserve
the code-backed safety lead and remove the unsafe model claim, rather than
requiring the bad claim to remain beneath a warning. Existing source/input
checks remain.

Documentation: this report, LIVE-TEST-FOLLOWUP, README, CHANGELOG, ARCHITECTURE,
CLAIM-EVIDENCE and HANDOFF. The earlier notebook parser, verified receipts,
GUI correction read-back/chain checks and notebook integrity formats are retained.
No unrelated semantic-memory storage refactor was attempted.

## Actual regression runs

All runs used disposable source/home/data folders, offscreen Qt and controlled
providers. Logs and normalized Python manifests live under
`%TEMP%/cursiv-live-followup-<suffix>/`; ignored run summaries are in
`reports/live-followup/`.

| Run | Result | Snapshot suffix |
|---|---|---|
| Baseline before this round's edits | 251 passed, 12.71 s | _9r8uhgp |
| First focused integration | 9 failed, 273 passed, 15.16 s. Fixed a GUI test fixture and a native-help interception of an actual notebook read; clarified the old casual/full-mode contracts and preserved post-model guard coverage. | 3ehh6p2t |
| Expanded integration | 4 failed, 474 passed, 22.23 s. Stronger withdrawals initially lost useful calculation/history and execution-record detail. Restored application-owned detail while keeping disputed model prose withdrawn. | qfz91kvk |
| Incorrect test selection | No tests ran; selected nonexistent `test_commands.py`. Corrected the test paths. | befyprst |
| Expanded corrected selection | 487 passed, 23.04 s | jur9qkg7 |
| First full run | 6 failed, 1,403 passed, 1 skipped, 184.25 s. Fixed native-help interception of a compound live-network question and retention-only data. Preserved the code-backed lightning lead in withdrawals; two old note-only assertions were strengthened to the new withdrawal contract. | 2toy1emq |
| Full-run findings and filesystem regressions | 237 passed, 14.46 s | b5v69dus |
| Complete follow-up | 1,416 passed, 1 skipped, 176.43 s | 1_jpovls |
| Explicit allowlisted-tool-name denial | 138 passed, 8.18 s | xnwgrmzh |
| Complete source/status audit | 1,424 passed, 1 skipped, 169.22 s | si6_ulzj |
| Unavailable-reference safeguard included | 1,425 passed, 1 skipped, 168.18 s | 68baks6q |
| Exact benchmark message and literal-payload regression | 155 passed, 11.10 s | 21lkqoyr |
| Final current source, including exact inline benchmark inputs | **1,428 passed, 1 skipped, 168.62 s** | j3b9zcia |

The skip requires a real macOS Keychain. The final run contains 83 additional
cases over the previous round's 1,345 passes. The normalized application source
SHA-256, using the existing benchmark fingerprint algorithm, is
`2a6048bf01f3d34c925015112acd72d3d55d25ff11fcbdc6c778ea05bdc35220`.
Every current production/test Python file matches the final snapshot manifest;
none is missing. Python syntax checks, the existing 1,200-line production module
limit, local documentation links and `git diff --check` pass. The personal
`test_internals/u81_test.txt` hash remains unchanged; nothing is staged.

These tests include the actual `adv-011` case data; exact proportion/duration
regressions remain permanent in the preceding live-test suite. No benchmark
source/scorer or historical model results were altered.

## Limits and manual checks

- This is bounded native classification, not a guarantee for every possible
  wording. An unmatched operational request can require clarification. Reviewed
  workflow text must be maintained as the actual UI/backend changes.
- The dose-document comparison only proves a narrow conflict in supplied text;
  it neither establishes medical correctness nor resolves conflicting sources.
- Replacement-capable desktop clients remove detected unsupported drafts.
  Consumers without replacement support receive an explicit retraction after
  already-streamed prose; those bytes cannot be recalled from the consumer.
- No fresh live-model truth benchmark or packaged installer test was run in this
  round. Published U85's score and its documented retrieval/allergy failure stay
  historical; these changes do not certify general safety or perfect recall.
- Basic USB operation is owner-reported working. Physical memory persistence,
  restart and second-PC retrieval remain unverified. Windows signing is deferred
  until next month; approval is not assumed. Encryption remains the separately
  approved migration design, with no storage migration in this round.
