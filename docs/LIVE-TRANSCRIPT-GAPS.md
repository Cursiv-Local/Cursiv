# Remaining 2026-10-22 live-transcript gaps

Historical local checkpoint: based on published U87 on `codex/live-transcript-gaps`.
The owner subsequently authorized publication; these changes are included in U89.
The results below retain the earlier checkpoint's counts. Current combined
release evidence is recorded separately in the U89 verification report.

## Read-only audit and causes

- `chat/completion.py` runs the action gate, native answers, status, notebook,
  memory and authorized file routes before streaming a model draft.
- `core/fieldmath.py` lacked cubic-metre flow conversion and the consumption
  question form. `core/calc.py` did not recognize the trailing “arrival time?”
  question. These missed the existing native calculation route.
- `core/native_answers.py` recognized phone imports only when the question
  contained “import”; “get observations ... into the notebook” fell through.
- `memory/intents.py` matched the entire forget query as a literal substring.
  “the algae issue note” does not occur in the saved East Fork fact.
- Existing policy recognition already understood the punctuation and curly
  apostrophe in the requested restriction prefixes. `core/action_gate.py` missed
  a mutation preceded by “ignore previous instructions and”. The file parser
  lacked “summarize the first N lines of filename”.
- The source line described evidence used in a turn, but desktop history did not
  retain a structured calculation/reference pair for a later source question.
- Combined version/offline requests reached the network-only answer. The exact
  emergency-action and medical-advice questions had no short native reply.

## Production files changed

Paths below are relative to the repository root.

| File | Change |
| --- | --- |
| `cursiv_engine/core/fieldmath.py` | Full-match conversion/consumption forms; cubic metres to litres; existing positive/finite checks. |
| `cursiv_engine/core/calc.py` | Recognize arrival-time questions in the existing clock calculator. |
| `cursiv_engine/core/native_answers.py` | Native receipts for the exact hiking form, shared phone help, concise denials. |
| `cursiv_engine/core/phone_help.py` | Shared reviewed phone URLs and wording. |
| `launcher/phone_help.py` | Reexport shared wording; preserve clickable help formatting. |
| `cursiv_engine/memory/intents.py` | Descriptive forget fallback requires all meaningful tokens and one visible match; ambiguity lists IDs; existing deletion/read-back pathway retained. |
| `cursiv_engine/core/action_gate.py` | Strip the explicit override wrapper before classifying a forbidden imperative. |
| `cursiv_engine/core/file_access.py` | Recognize explicit first-N-line requests, authorize the actual path, return a limited excerpt and typed read receipt. |
| `cursiv_engine/core/presence.py` | Combined version/offline question uses the short native state path without memory lookup. |
| `cursiv_engine/core/answer_evidence.py` | Typed application evidence receipt and native prior-bleach-source reply; never parse model citation prose. |
| `cursiv_engine/chat/completion.py` | Source follow-up dispatch and capture of calculations/references actually supplied during a streamed turn. |
| `launcher/chat_feedback.py` | Accept typed answer evidence; ignore plain dictionaries/model text. |
| `launcher/chat_panel.py` | Reset pending evidence each turn and save it on the completed assistant history row. |

Also changed: `tests/test_u86_remaining_gaps.py`, `README.md`, `CHANGELOG.md`,
`HANDOFF.md`, and this report. No notebook backend or data format changes.

## Behavior and limits

- The three requested calculations return approximately 13.3333 L/min,
  480 minutes (8 hours), and 11:05, with application calculation labels.
- Phone guidance is the same application-owned text as field help. Offline capture
  requires first loading/caching the page online; this reply performs no import.
- Forget matching does not use an LLM, embeddings or approximate spelling. A
  multi-match request removes nothing and returns IDs. Existing permissions,
  correction-history deletion and read-back verification remain in force.
- Read-only permits authorized reads, while talk-only/no-save prefixes block the
  requested actions and memory formation. The existing quiet GUI restriction badge
  and expandable full policy explanation remain intact.
- The README request returns a verified excerpt, explicitly labeled as an excerpt,
  rather than claiming an AI summary. Output is limited to 1–200 lines and the
  existing 12,000-character cap. Existing text-file size/credential checks apply;
  bytes/hash describe the underlying checked file, and `truncated` marks the excerpt.
- Prior sources come from application history metadata, not the answer’s prose or
  a new calculation. Old answers without receipts are explicitly unconfirmed.
  Integrations that call the generator directly must retain the typed `on_action`
  evidence alongside their own assistant history; the desktop does this itself.
- Offline-off reports that connectivity is unproven. Native denials do not claim
  a call or provide professional medical advice and do not append model closers.
- No actual local-model quality score is claimed; the tests use controlled
  providers to prove dispatch and application behavior. No hosted Mac or packaged
  installer validation has been run for these local changes.

## Regression evidence

Tests run against copied sources with temporary HOME, application data, Qt
offscreen and no engine startup. Personal `test_internals/` is excluded.

- Before edits: 216 existing focused tests passed in 9.83 s.
- First focused implementation run: 288 passed, one assertion failed because the
  fixture expected LF rather than the actual Windows CRLF file bytes. The test now
  compares line contents while preserving the receipt’s real bytes/hash.
- Final full suite: **1,523 passed, 1 skipped in 157.29 seconds**, Python 3.13 on
  Windows. Existing append-only notebook, sample-ID collision, distance/proportion
  withdrawal, bleach-dose and offline-gate regressions passed in the same run.
  Source snapshot/log: `%TEMP%/cursiv-live-followup-rnkliu9u`.
- `git diff --check` passed. The untracked personal test file retains SHA-256
  `efb67cb4aa306cbe3daf6dafd432fa918fa91f7e21dd3278cdf2489b84e0cac7`;
  it was not edited or included in the isolated source copy.

New coverage includes both requested provider modes for native calculations and
blocked actions; phone wording equality; actual deletion, subsequent recall and
fresh-process persistence; ambiguous deletion; read bounds and path authorization;
native state and denials; actual bleach/reference evidence; missing-provenance
refusal; restricted source lookup; typed GUI capture and completed history storage.
