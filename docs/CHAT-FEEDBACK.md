# Quiet chat feedback and notebook continuity

> Release follow-up: U85 is published, with verified Windows/Mac downloads
> and the website deployed. [U85 verification](U85-RELEASE-VERIFICATION.md) records
> actual release gates and results. The status, source fingerprint and test
> records below describe the completed pre-release implementation checkpoint.

## Status at the pre-release implementation checkpoint

Unreleased working-tree changes on `codex/maintainability-hardening`, based on
`d3922a48f74518997ccaea0390a771aed6f03513` (published U84 source/evidence).
No commit, push, installer bump, packaging or deployment for this follow-up.
No existing records, personal workspace files or historical benchmark results
are migrated, deleted or rewritten.

## Findings and changes

U84 already streams in 40 ms batches, caches unchanged conversation history,
updates the active message and finishes the draft before optional model review.
This follow-up keeps those paths. It fixes presentation gaps:

- The old “background check running” appeared before model availability was
  known. `Job.run(on_model_state=...)` now carries an observer in a copied
  context. Availability checks happen first; only the actual invocation/stream
  emits activity, balanced in `finally`. Qt signals update widgets on the GUI
  thread. A queued job shows “Draft ready” without animation. Cancellation and
  generation guards suppress stale results and progress.
- The small progress bar accompanies “Draft ready · checking answer…” or
  “reviewing wording…” only during reviewer calls. Clean results clear the line
  and retain bounded `background_review` metadata without changing/reparsing
  the message. Findings show “Checked · N notes” (structured issue count);
  unavailable checks say so. Suggested revisions remain explicitly labeled.
- A separate quiet line shows typed file/tool, notebook or memory receipts.
  Model prose cannot set it. File failures remain visible when generation ends;
  the existing hard stop still prevents model continuation after a failed tool.
  Full destinations and errors remain in the original execution result.
- Existing offline status remains in its pill. File access, configured workspace
  and current talk-only/read-only/memory restriction appear separately. Commands
  refresh status when their application result arrives, rather than waiting for
  the existing periodic settings refresh. No connectivity probe is added.
- Confirmed notebook receipts in this conversation provide the last recorded
  site across turns and on reopen. This is historical context, not a fresh
  existence check, a newly active project, or authorization to read that site.
  A new conversation clears notebook context; the configured workspace remains.
- Restriction confirmations are shorter and do not claim offline execution,
  deletion of history or “nothing saved.” Memory saves/automatic learning are
  blocked according to the existing gate; chat history follows its own settings.
  Dated recall leads with count and calendar scope while retaining limits on
  completeness, unreadable records, saved-date semantics and the 40-record cap.
- The regular model prompt and the retained compact-provider system block ask
  for a calm, precise, slightly warm voice without stock offers, decorative
  emoji or constant questions. Emergency instructions remain intact. Explicit
  persistent saves say “Saved to memory,” with the real record identifier;
  they are never relabeled as conversation-only.

## Notebook integrity and authorship

Native chat recording still accepts user-authored details only and uses the
existing allowlisted notebook backend. Short confirmations retain record IDs,
sample IDs where present, a 12-character fingerprint prefix and chain status.
The complete hash stays in the receipt/record and in notebook row tooltips.

The graphical notebook additionally reads its returned record back and checks
the chain before confirming a save/correction. An optional curiosity notification
cannot turn a completed verified save into a reported failure. Failure wording
does not promise that a partial append left no bytes. Check before retrying.

Notebook table wording/tooltips distinguish recorded observations from model
suggestions in chat. The interface does not claim authorship can be authenticated
from the observation text or that recording proves the observation is true.
No new author/source field is inserted into existing hash-covered records.

Team/phone imports reuse the existing signature, record-value, manifest and chain
checks. Each newly copied log is now independently read back and compared with
the checked source. Existing copies are chain-checked on repeat imports too.
The report includes a `chain_verified` device list; summaries say “chain intact”
only for covered devices and no rejected/conflicting logs. Repeats say zero new
entries. Unsigned devices, missing photos and clock warnings retain detailed
notes; chain integrity is distinct from device identity and photo availability.
The receiver counts verified new entries separately from received uploads.

Imports remain per-device copies in the team store; they do not merge into this
computer's own append-only log. A failed multi-device import can leave earlier
copies on disk; no automatic rollback or deletion is introduced. Errors surface
without claiming a complete import. The same limitations apply if a drive is
removed between a completed verification and later access.

## Validation record

- Baseline focused tests before edits: **203 passed in 25.73 s**.
  Isolated snapshot/log: `%TEMP%/cursiv-maintenance-4wiuglby`.
- First focused follow-up: **288 passed, 1 failed in 28.93 s** at
  `%TEMP%/cursiv-maintenance-stmxkcvy`. A new unavailable-model test carried
  prior arithmetic state into a mocked stream. Isolating its turn fixes the test.
- First full follow-up: **1,264 passed, 1 failed, 1 skipped in 143.04 s** at
  `%TEMP%/cursiv-maintenance-2bz37w04`. The saved-notes fake host lacked the
  new state signal. Its fixture now asserts state refresh before notes delivery.
- Feedback-specific isolated checks after the final memory/context additions:
  **19 passed in 5.58 s**, `%TEMP%/cursiv-maintenance-f4cueo58`.
- Next full run: **1,265 passed, 2 failed, 1 skipped in 158.99 s**, at
  `%TEMP%/cursiv-maintenance-01m05r3j`. The two failures expected old “remember”
  prose. Their assertions now require the precise save wording/record ID while
  retaining independent persisted-content/restart checks.
- Final full Windows suite: **1,267 passed, 1 skipped in 154.66 s**.
  Snapshot/manifest/log: `%TEMP%/cursiv-maintenance-4ko8bgh7`.
  The only skip requires a real Mac Keychain. This run includes offline-network
  enforcement, complete-launcher construction, streaming/Markdown/scroll/copy,
  model-check cancellation, notebook append/correction/read-back, signed phone
  transfer, failed writes and independent persistence/restart checks.
- Final diff/inventory: **31 intended files**, clean whitespace check, valid
  Python syntax/no undefined names in changed modules, valid documentation links.
  Production and test files match the final passing snapshot; replay production
  matches the same application tree. `test_internals/u81_test.txt` retains its
  original SHA-256. HEAD remains `d3922a48f74518997ccaea0390a771aed6f03513`.
- Offscreen chat/notebook previews inspected with real disposable records:
  `%TEMP%/cursiv-feedback-preview-fhc0m8ys/{chat,notebook}.png`.
  Preview-only system-font registration made text readable; application fonts
  are unchanged. A direct-repository preview stalled during startup and was
  stopped; the disposable-source preview completed. No root cause for that
  startup stall is claimed and no owner application process was interrupted.

The tests use disposable source copies, isolated homes, temporary logs/signing
keys, offscreen Qt, deterministic provider stubs and no model startup. Existing
local-network phone tests use localhost. No pass implies physical installed-PC,
USB removal, current Mac packaging or live-model tone validation.

## Exact files

Production:

- `cursiv_engine/core/feedback.py` (new factual presentation helpers/voice)
- `cursiv_engine/chat/review.py`, `launcher/chat_review.py`
- `launcher/chat_feedback.py` (new UI feedback mixin)
- `launcher/chat_controls.py`, `launcher/chat_panel.py`
- `cursiv_engine/chat/conversation.py`, `cursiv_engine/codex/system_prompt.md`
- `cursiv_engine/core/turn_policy.py`
- `cursiv_engine/memory/intents.py`, `cursiv_engine/memory/recall.py`
- `cursiv_engine/core/notebook_tools.py`, `launcher/field_notebook.py`
- `cursiv_engine/core/fieldsync.py`, `cursiv_engine/core/phone_receive.py`,
  `launcher/phone_receive_dialog.py`

Checks: new `tests/test_chat_feedback.py`; updated
`tests/test_background_review.py`, `tests/test_grounded_chat.py`,
`tests/test_phone_receive.py`, `tests/test_saved_notes_viewer.py`,
`tests/test_autonomous_memory.py`, `tests/test_persistence.py`.
Documentation: this report, `README.md`, `CHANGELOG.md`, `HANDOFF.md`,
`docs/VERIFICATION-POLICY.md`, `docs/ASYNC-ANSWER-REVIEW.md`.
Rendering artifacts are listed with the measurements below.

## Controlled rendering comparison

Raw reports: [before](../bench/results/chat-feedback-before-20261022.json) and
[after](../bench/results/chat-feedback-after-20261022.json).
Same unchanged replay script, three runs per size, 898-character Markdown
response (code, table, list, links), 16-character chunks every 8 ms, real local
autosave, 5 ms Qt heartbeat and RSS sampler. Both builds already use U84's
background scheduling. Only the 1,000 ms reviewer wait is simulated; no AI is
invoked. The fixture retains a deterministic `UNGROUNDED_KNOWN` note despite
the fake verifier's CLEAR, so these replays exercise the notes path. Separate
regressions assert that a clean review never calls the Markdown renderer.

Times are medians in milliseconds unless labeled otherwise; values show
**before → after**. Small timing differences are not isolated causal gains.

| Existing messages | Final token → ready | Final token → first completed render | Markdown parsing total | Worst GUI gap across 3 runs | Median peak RSS (MiB) |
|---|---:|---:|---:|---:|---:|
| 10 | 18.34 → 17.14 | 12.53 → 11.92 | 2.30 → 2.53 | 25.02 → 20.91 | 58.43 → 58.34 |
| 100 | 25.00 → 22.40 | 13.92 → 12.18 | 2.45 → 2.27 | 38.78 → 31.85 | 70.63 → 70.40 |
| 1,000 | 81.24 → 76.39 | 18.47 → 19.64 | 2.46 → 2.42 | 190.90 → 137.81 | 177.96 → 173.68 |

There were **zero full-document rebuilds** in all 18 runs. All individual
final-token-to-ready samples were below 250 ms (including initialization).
The largest after-change GUI gap was 137.81 ms in the 1,000-message case;
this is not a guarantee of a continuously 30–50 ms GUI cadence. Review completion
still includes the simulated second and subsequent follow-up work. These figures
are not measurements of Qwen generation/verifier speed or live-model behavior.

The reports include the complete run data and source-manifest hashes. Application
tree fingerprints use sorted compact JSON of application/launcher paths and
raw-byte hashes, as specified in each report:

- Before: `7ee75fd9b17f8751afb8dda2c6aa81fcda3155164146dff5ac3579f9f0d190fc`
- After: `2ccbcc32e18cc970cefa2220e59683ee70e6649ddb21ce2609b7e45233108b53`

The immutable truth benchmark cases/scorer and historical U-release results are
untouched. No new model-quality percentage is claimed for this UI follow-up.

## Remaining limits

The reviewer still consumes local compute and cancellation is cooperative during
an outstanding backend read. This follow-up does not make a small model faster,
guarantee a consistent voice, fix every factual error, or establish self-awareness.
The deterministic checks and finite model review retain their documented gaps.
Progress describes invocation activity, not percent complete or a reliable ETA.
Historical receipt context is not newly verified access. Existing authorization,
symlink protections, network policy and conversation storage settings remain
the enforcement boundaries; presentation text grants no permissions.
