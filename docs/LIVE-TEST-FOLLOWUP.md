# U84 live-session follow-up on the U85 source

Historical local checkpoint: these repairs are now included in U86. See
[U86 release verification](U86-RELEASE-VERIFICATION.md) for the combined source,
version and actual publication outcomes. The local status below describes the
checkpoint before the owner authorized publication.

## Status and scope

Working branch: `codex/u85-live-test-followup`, based on published-source/evidence
commit `b2321f0f4a1e3ec120d9703cf0747bd0bf9b917d`. These are local, unreleased
repairs; the application/launcher/installer version remains 3.14-U85. The public
U85 installers and website have not been replaced by this follow-up.

The subsequent [native trust-boundary round](NATIVE-TRUST-BOUNDARIES.md) builds on
this checkpoint. The source fingerprint and final run below describe this first
round; consult the subsequent report for the current working source.

The owner supplied the U84 findings brief, the actual session transcript and the
additional thirteen-item request. Transcript commands are diagnostic examples,
not instructions to execute against the owner's records. Personal memory lists
and the full transcript were not copied into the repository. Tests use disposable
source/home/data folders, synthetic observations and controlled provider replies.

## Read-only findings and repaired execution paths

| Issue | Cause confirmed in source | Repair |
|---|---|---|
| Phone capture/import, duplicate sample IDs, correction/sharing help | Natural questions fell through to unrestricted model prose rather than built-in help. | `core/native_answers.py` answers the bounded help questions from actual notebook workflows before any model call. It names cursiv.us/notebook/, first-load/offline/browser-storage limits, .cursivsync import, append-only corrections and team sharing. Help never executes the described operation. |
| Duplicate sample IDs | The model incorrectly denied existing clash detection. | Help describes `fieldsync.sample_clashes()` and the team-log/import behavior: separate device chains, flags after import, no live disconnected check, no automatic merge or rename. Existing two-laptop synthetic import tests exercise the backend. |
| Comma-separated log rejected | `fieldlog.parse()` split only semicolons/newlines, so a greedy site field swallowed the observation, temperature and sample ID. `observation:` was not a field alias. | Recognize observation/note aliases and split commas only before explicit fields, measurement-shaped parts or coordinate pairs. Retain ordinary/quoted commas and exact measurement strings. Missing content gets a precise native clarification before an append. Semicolons remain the unambiguous format for complicated prose. |
| “Correct the last entry” invented a text-file workaround | The intent parser recognized explicit notebook names but missed last/previous/selected-entry wording; restrictions could bypass ordinary command dispatch. | Recognize that correction intent. Pure policy classification returns a short application refusal before a backend/model call. An unrestricted correction request points to Field Notebook → Correct selected; it does not edit an entry in chat. Earlier restrictions do not silently carry into a new turn. |
| Long save and empty-read messages | The native result renderer repeated entry details. | One-line `Logged. Sample …` receipts retain the actual record ID, fingerprint, read-back and chain result. Both native and legacy typed-log routes independently read back before that claim. Empty native reads return one clear line. |
| Write-error message could deny a record that exists | A write can reach storage before its final flush reports an error; the legacy message always said “Nothing was recorded”. | Report the append as not confirmed and advise inspection before retrying. A regression forces a real post-write flush failure and independently verifies the record bytes exist. The full/read-only failure tests still require existing bytes and chain integrity to remain unchanged. |
| Duration/rate/volume left to model arithmetic | The supply parser required a topic word such as “water”; the exact 20-liter question did not have one. | Allow an explicit per-person/day allocation with a duration question. Short, unambiguous questions return the existing code result directly, retaining the allocation-assumption warning. Ambiguous/compound inputs are not guessed. |
| Arrival time missed code calculation | Clock recognition covered “will/would” but not “what time do we arrive?” or “when do we arrive?”. | Extend the existing clock grammar. The transcript computes 18:15; the hike-plus-20-minute-break case computes 18:35, with an actual calculator receipt. No benchmark answers/cases were edited. |
| Proportion note left an unsupported “yes” first | `calc.check()` detected the contradiction but completion appended its note under the draft. | Direct simple comparisons use the application calculation. Detected overlap contradictions in longer answers withdraw the model comparison and replace it with the calculated summary; clients without replacement support receive an explicit withdrawal. Existing dose/reference withdrawal remains in force. |
| Version/workspace/model answers | Version was a self-knowledge model turn; “the current workspace” missed the native question pattern; “current model” dumped a state packet without a model name. | Version comes from `selfknow.VERSION`, with an application-state label. Workspace/network/file questions use short native state answers. Model questions report only the running application's recorded last engine identity, or unknown; an installed/configured model is not represented as the provider that answered. |
| Repetitive restrictions and routine source lines | The Qt renderer displayed policy paragraphs and routine evidence footers as normal content/chips. | Show current restrictions in the existing quiet badge. Keep the full policy and routine model/memory-source text in Show reasoning and checks and raw history. Keep reference cards, calculations, failures and real tool receipts visible. Preserve fenced/indented source examples as literal code. |
| Stock offers/emoji | Restrained general guidance alone did not stop small-model closing templates. | Add scoped prompt guidance and narrowly trim separate trailing stock-offer paragraphs for restricted/simple turns in replacement-capable chat. Preserve open dialogue, requested questions/closings, quoted/fenced examples and mixed warning paragraphs. This is bounded presentation handling, not a general semantic truth filter. |
| Session repetition | Existing receipt-derived context retained a site but no sample and appeared during unrelated questions. | Retain the confirmed site/sample in conversation metadata and show it only for relevant notebook/field turns or reopened context. The workspace indicator remains factual. Historical context does not create another observation, grant access or prove current storage availability. |
| Demo restoration could claim success after a failed write/cleanup | The generic key setter suppresses write errors and can treat corrupt JSON as empty; sample cleanup ignored errors. | Update only the demo flag with validated JSON, atomic write/read-back and unchanged unrelated settings. Restore the real view before cleanup. Report retained samples honestly, reject unexpected/linked cleanup roots, roll back a failed sample setup, and fail closed on unreadable mode settings. Add guided semicolon/comma prompts. |

GUI path: `ChatPanel._run_turn()` → guarded native notebook/command handling →
`chat.completion.chat()`. Feature help stays in completion so it receives normal
Markdown rendering and conversation history; it is not a plain command result
that drops the exchange. Provider prefixes do not transfer native operations to
the model. Notebook writes still use `notebook_tools.execute()` → `fieldlog.add()`
→ independent entries/read-back/chain verification. Original append-only schemas,
record bytes, workspace authorization and symlink protections are preserved.

## Changed files

Production:

- `cursiv_v215/core/native_answers.py` — new bounded native help/version/calculation/model-record replies.
- `cursiv_v215/chat/response_style.py` — new scoped guidance and conservative closer cleanup.
- `cursiv_v215/chat/completion.py` — native routing, blocked-action stop, style replacement and proportion withdrawal.
- `cursiv_v215/chat/conversation.py` — keep scoped style guidance through provider compaction.
- `cursiv_v215/core/fieldlog.py` — parser aliases/delimiters and verified short legacy receipts.
- `cursiv_v215/core/notebook_tools.py` — correction intents, policy refusals, missing/empty results and short receipts.
- `cursiv_v215/core/turn_policy.py` — remove leading delimited policy clauses for intent parsing; authorization still uses the original message.
- `cursiv_v215/core/resources.py` — explicit volume/rate/duration coverage without a literal water keyword.
- `cursiv_v215/core/calc.py` — arrival-time phrasing.
- `cursiv_v215/core/presence.py` — short state replies and workspace/network variants.
- `cursiv_v215/core/feedback.py` — shared short verified save receipt.
- `cursiv_v215/core/demo.py` — verified mode switching, guarded cleanup, rollback and guided prompts.
- `launcher/chat_feedback.py` — relevant receipt-derived site/sample context.
- `launcher/chat_panel.py` — badge the streamed policy note while keeping raw evidence.
- `launcher/chat_transcript.py` — expandable routine evidence and literal code preservation.
- `launcher/chat_commands.py` — canonical phone-notebook link in help.

Tests: new `test_live_test_followup.py`, `test_notebook_workflows.py`; update
`test_fieldlog.py` and `test_chat_feedback.py` to assert the new short receipt
while retaining record-ID, read-back, chain and actual-storage assertions.
Update `test_storage_failures.py` to require honest unconfirmed-write wording;
its unchanged-byte and chain assertions remain in place.

Documentation: this report, README, CHANGELOG, HANDOFF, ARCHITECTURE,
CLAIM-EVIDENCE, PLATFORM-READINESS, FIELD-KIT-TEST, and the focused USB persistence
checklist. Existing published release/benchmark evidence remains historical.

## Test record

Every run below uses a disposable snapshot. Logs and per-Python-file normalized
SHA-256 manifests are under `%TEMP%/cursiv-live-followup-<id>/`. The ignored local
`reports/live-followup/` directory contains the runner and run manifests.

| Checkpoint | Actual result | Snapshot suffix |
|---|---|---|
| Existing focused regressions before production edits | 242 passed, 20.21 s | ny43bqg8 |
| New first-round tests before repair | 24 failed, 1 passed, 3.48 s; includes absent helper entry points | me4ue4zz |
| First focused repair | 202 passed, 13.27 s | k96j9ghl |
| Expanded notebook/import/security/rendering | 271 passed, 21.90 s | lk0hfcs6 |
| Additional transcript state questions | 224 passed, 13.02 s | 7lage88h |
| First full snapshot | 1,314 passed, 1 skipped, 175.12 s | eqogir97 |
| GUI/history/ambient-policy follow-up | 116 passed, 9.02 s | hcb9mlcv |
| Full follow-up with code-example guards | 1 failed, 1,320 passed, 1 skipped, 169.46 s; an existing refusal assertion required “No action”. Kept that wording and the refusal. | vnlfo8te |
| Completed first-round regressions | 187 passed, 10.38 s | j3yev5u0 |
| Added workflows/demo | 1 fixture failed, 169 passed, 19.61 s; the new fixture omitted its temporary config parent directory. Fixed fixture setup. | gsqv_6xj |
| Expanded final workflows/portable/grounding | 348 passed, 26.27 s | g1j_t8wz |
| Full storage-message review | 2 failed, 1,342 passed, 1 skipped, 175.09 s; two existing assertions required “Nothing was recorded” even though a post-write flush can fail. Updated that message contract, retaining independent storage assertions. | 3jqc3t65 |
| Storage regressions, including actual post-write flush failure | 38 passed, 8.51 s | 5s9ugx6d |
| Final complete source snapshot | **1,345 passed, 1 skipped, 182.03 s** | gh94nzr4 |

The first reproduction log printer also hit the Windows cp1252 emoji limit; the
disposable runner now explicitly prints UTF-8. No application behavior was
changed to make that log print. The skip requires a real macOS Keychain. These
are deterministic regressions, not a new live-model score or a physical
portable-drive validation.

Final normalized application Python SHA-256, using the existing benchmark
fingerprint algorithm:
`62a1505b5b8b03715957c2390500b3ce79251a09194b31d8cd33a50f556b5098`.
At that checkpoint every production/test Python file matched the snapshot manifest;
none was missing. All Python files parsed, no production module exceeded the
existing 1,200-line limit, and `git diff --check` passes. The personal
`test_internals/u81_test.txt` hash is unchanged. Nothing is staged, committed,
pushed, packaged or deployed by this follow-up.

## Packaging, USB and encryption

The owner reports basic physical USB operation works, but has not yet checked
memory saves/persistence on that drive. That report is recorded separately from
automated portable regressions. See [USB persistence checks](USB-PERSISTENCE-CHECK.md)
for independent file, memory, notebook, restart and second-PC checks. No completed
second-PC/full-day/persistence result is inferred from basic USB operation.

The current-user certificate store has zero valid code-signing certificates with
private keys. The owner confirms signing is deferred until next month, hoping
for approval then; no signing credential or physical second PC is available to
this execution session. Packages remain unsigned. No fake certificate, signing
claim, network-default change, installer rebuild or public-release replacement is
part of these source repairs.

Encryption remains the separately approved
[migration design](ENCRYPTION-MIGRATION-PLAN.md). Conversations/memories and their
backups/derived copies remain plaintext. No partial encryption or storage-format
migration was introduced. Existing bounded modules were reused; the two new
helpers keep native replies and presentation separate without splitting unrelated
verification, memory or dialog modules.

## Remaining limits and review points for Claude

- Parsers and FAQ routing intentionally cover bounded wording, not every possible
  utterance. Complex/ambiguous text may require a clarification or the documented
  semicolon format. A context badge is not a new save or authorization.
- Restricted-turn limits govern tools/retention, not whether separately enabled
  conversation history persists. Model prose that says “no history” is still
  untrusted; collapsing routine source text does not certify that prose.
- Native help does not test actual phone caching, pairing or a physical import.
  The physical USB persistence and cross-machine checks remain owner actions.
- General self-description/online privacy claims, historical-source questions,
  inferred-memory quality and missed allergy retrieval in the published U85
  benchmark need additional focused work. No new 158-case model run was made,
  and published U85's documented 153/158 score is not relabeled as this branch's.
- A checker only withdraws contradictions it detects against supplied evidence;
  unrecognized reference/dose/model errors remain possible. Existing medical
  material remains unreviewed by a medical professional.
- Review demo read/modify/write concurrency with other settings writers before
  supporting concurrent command sessions. The demo lock serializes demo switches;
  it is not a cross-module settings transaction. An unavailable/corrupt flag
  blocks a notebook destination rather than guessing the real store.
- Inspect the final diff and test manifests; preserve personal `test_internals/`.
  No owner application/data migration, commit, push or new publication is implied
  by this local follow-up report.
