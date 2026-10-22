# Trust-boundary follow-up

> Publication follow-up: the owner subsequently authorized commit/push,
> packaging, release and website deployment. U83 stayed an unpublished candidate
> after a full-window smoke failure; U84 repairs it and expands that gate.
> Earlier status statements below record audit checkpoints. See
> [U84 verification](U84-RELEASE-VERIFICATION.md) for current publication results.

## Scope and status

2026-10-22, `codex/maintainability-hardening`, uncommitted. The owner's latest
list prioritizes the policy gate, clean file intents, application-owned source
labels, deferred checks and exact transcript regressions. Most of that work was
already present; this follow-up audits it and closes the gaps below.

No commit, push, tag, version bump, installer build, release or deployment is
performed for this follow-up. Installed/public U82 does not contain these pending
desktop changes. The earlier general-purpose phone photo update was deployed as
Worker `784d34d9-56e8-4089-8244-1f2fb82b430b`; the additional phone/notebook
clarification here is **local only**, ready for a later website publication.

## Read-only findings before production changes

1. Source formatting still called `_memory_used(answer, question)`, a word-overlap
   heuristic. Identical supplied facts could produce different source labels
   depending on model wording. The streaming filter was case-sensitive, allowing
   lower-case or all-caps model-authored source footers through.
2. The central policy parser did not recognize “don't use any tools” / “do not
   call plugins.” Its descriptive-pronoun exclusion also missed leading
   second-person instructions such as “You must not save any memories.”
3. `task_text()` removed only one leading policy clause. A second recognized
   clause could prevent a clean native read intent from being parsed.
4. `file_access.command()` called `save_memory()` for `file remember` even when
   its file result was unsuccessful or path resolution raised an error. A failed
   file write could therefore cause a separate persistent side effect.
5. Deferred review copied raw `_MEMORY_CTX`. A recalled context subsequently
   withheld from the answering prompt could still be handed to the reviewer.
6. Dated recall caught every `ValueError` from date parsing **and retrieval** as
   a date-range clarification. A damaged store could receive the wrong error
   explanation, though it was not treated as a successful recall.
7. Explicit external Cross-check used 1,500-token limits on some providers,
   Claude's normal 4,096-token default, and no explicit OpenAI output cap. The
   automatic reviewer already had 180/300-token bounds and asynchronous display.
8. USB confirmation warned that copied data was readable, but did not explicitly
   explain the readable API-key export needed to use keys on other computers.
9. `/app` and `/notebook/` had separate implementations, but lacked an obvious
   reciprocal explanation of online AI versus offline capture.

## Repairs and execution paths

### Policy and file intent

`command_dispatch` → `turn_policy` → `completion` → native operations or guarded
conversation/provider dispatch remains the single policy path. The new variants
are recognized before lookup, tools, plugins and retention. Quoted examples,
literal payloads and descriptive “I don't read books” text remain data.

`task_text()` now removes a bounded sequence of recognized leading read-only
clauses. Authorization still uses the **original** request; filename/content
parsing never grants permission. Existing suffix handling preserves quoted
filenames and explicit `file ... :: ...` payloads. Traversal, symlink/junction,
workspace and protected-credential guards are unchanged.

`file remember` calls memory saving only after a successful filesystem result.
Both failed-result and resolution-error branches state that memory was not
attempted. A later memory failure does not roll back an already verified file
write: these remain two separately reported operations, not a transaction across
both stores. Existing confirmation-mediated writes retain their receipt checks.

### Source ownership and deferred review

`chat/provenance.py` owns source formatting and accepts **no answer text**.
It uses the application's supplied reference/document records, calculation,
confirmed execution records, web-search flag and supplied-memory record.
Compatibility `sources_line(answer, question)` arguments remain accepted but
cannot select the label. The old `_memory_used()` helper remains for compatibility
and is no longer an attribution/permission input.

Final system-prompt assembly records which recalled memory context actually
survived prompt replacement/withholding. The immutable fact tuple is scoped with
the turn's grounding state, cleared on a new stream and copied with deferred
review context. Source labels say **“saved memory context supplied (use by the
model is not established)”**, never infer use from matching words. Legacy saved
conversation context also records its supplied text. Evidence assessment and
the optional reviewer use this supplied-memory tuple, rather than raw recalled
facts that may have been withheld.

Model-authored source footer variants are filtered case-insensitively across
streamed chunks; literal examples in fenced code remain intact. This protects
the status-label channel, not every arbitrary assertion in model prose. A source
label records what Cursiv supplied, not whether the model understood it or every
sentence is correct. Provider context limits can still trim supplied material.

The existing asynchronous path remains: finish the draft/enable input, then run
eligible local review and append labeled results. Fast/full/off controls and
stale-result rejection remain. Explicit Cross-check now passes a **400-token**
cap to all five supported provider adapters and requests short sections. Normal
chat budgets are preserved. Automatic verdict/rewrite limits remain 180/300;
unchanged rewrites do not trigger a second verdict. See
[the earlier timing report](ASYNC-ANSWER-REVIEW.md) for controlled measurements;
no fresh live-model speed or accuracy claim is made here.

### State, memory, safety and presentation

Existing native operational answers use the current workspace/file-access/
offline/memory state packet; a grant is not proof that a particular write will
succeed. Existing memory opt-out notices identify blocked saves/automatic
learning while explaining that conversation history has separate settings.
No chat-history deletion or new private-session mode is implied.

Dated recall now validates date bounds separately, allowing retrieval failures
to become application-authored storage errors. Existing corrupt-line warnings,
empty-store handling and read-only legacy-repair guard are retained. This does
not guarantee retrieval of every saved fact or eliminate heuristic intent misses.

Existing restricted-turn tests prohibit reference/calculator/tool/plugin/memory
work. Restricted lightning requests receive a native availability response; the
limits notice explicitly disables built-in calculation/reference checks. Normal
turns retain code calculations/reference handling. Detected unsafe dose/reference
contradictions still withdraw the draft and display the supplied reference.
These checks are finite and do not establish medical/field safety.

USB maker uses its existing confirmation dialog and adds an explicit readable
API-key explanation, checkbox tooltip and warning when preserving a prior private
copy. Copy/export behavior and personal stores are unchanged. Phone pages add
small reciprocal notes/links: `/notebook/` is offline capture after first load,
with no AI chat; `/app` requires internet and online AI. Neither is the full
desktop AI. The notebook cache name advances to v3 so a later publication can
refresh cached HTML; field records and their IndexedDB storage are unchanged.

## Tests actually executed

All runs use isolated source/home/data snapshots, excluding personal
`test_internals/`. Numerical-library threads are capped in the test processes.
No real external model/provider call, physical USB export or paid API request is
used by the new regressions.

| Stage | Result | Snapshot/log |
|---|---|---|
| Pre-follow-up complete baseline | 1,209 passed, 1 skipped; 176.73 s | `%TEMP%/cursiv-maintenance-u7nhk2vp/pytest.log` |
| New tests against pre-repair production source | 10 failures reproduced; 4.86 s; stopped at the configured ten-failure limit | `%TEMP%/cursiv-maintenance-u41pbftm/pytest.log` |
| First focused repair run | 385 passed, 3 failed; 28.82 s. Exposed dated storage-error misclassification and two verifier tests dependent on ambient review/power settings. | `%TEMP%/cursiv-maintenance-gpbjxplc/pytest.log` |
| Focused repair run | 388 passed; 46.32 s. Date/storage errors separated; verifier tests explicitly enable review. | `%TEMP%/cursiv-maintenance-9yr8mxzt/pytest.log` |
| Final full suite | **1,246 passed, 1 skipped; 299.62 s**. Includes the expanded local/cloud restrictions and ordinary provider-budget compatibility tests; the skip requires a Mac's Keychain. | `%TEMP%/cursiv-maintenance-s8vnolr0/pytest.log` |

Final tested application/launcher fingerprint:
`15985868d5d3bcb9fbff8aad9955b5f46f05376a094573d9d016ed137683e278`.
The production Python matches the final isolated snapshot. AST parsing and the
1,200-line production-module budget passed. Website build-only packaging plus
inline phone and notebook service-worker syntax checks passed; no publication
command ran. Personal test data and frozen Truth Benchmark cases/scoring remain
unchanged. The combined pending inventory has 105 intended files, including the
pre-existing maintenance/website work, and excludes personal `test_internals/`.

The exact original transcript strings remain in `test_restricted_regressions.py`:
“don't inspect … photosynthesis,” “just chat … lightning 30-minute rule,”
“don't save any memories … favorite color,” “conversation only … sample ID,”
“read only — look at the current workspace …,” “read the file launcher/main.py
and summarize …,” and operational-state questions. Both local/cloud dispatch
paths are mocked and checked for forbidden calls. The suite also verifies actual
disposable file paths/content, persistence, receipts and failed-tool exits.

## Exact incremental files

- Application: `cursiv_v215/core/turn_policy.py`, `core/file_access.py`,
  `core/grounding.py`, `core/crosscheck.py`, `memory/intents.py`,
  `chat/provenance.py`, `chat/context.py`, `chat/conversation.py`,
  `chat/streaming.py`, `chat/review.py`, `chat/cloud_providers.py`,
  `ui/chat_app.py` (all under `cursiv_v215/`), and `launcher/usb_maker.py`.
- Website: `website/app.html`, `website/notebook/index.html`,
  `website/notebook/sw.js`. The prior general-vision Worker change is preserved.
- Tests: `tests/test_trust_boundary_followup.py`, `tests/test_restricted_regressions.py`,
  `tests/test_reliability.py`, `tests/test_verify.py`, `tests/test_replace_draft.py`,
  `tests/test_module_boundaries.py`.
- Documentation: this report, `README.md`, `CHANGELOG.md`, `HANDOFF.md`,
  `TECH.md`, `ARCHITECTURE.md`, `docs/CLAIM-EVIDENCE.md`,
  `docs/VERIFICATION-POLICY.md`, `docs/U82-RESTRICTED-TURN-REPAIR.md`,
  `docs/ASYNC-ANSWER-REVIEW.md`, `docs/MAINTENANCE-HARDENING.md`.

The maintenance report inventories the entire combined uncommitted branch.

## Draft wording for the next approved release

- Supported conversation-only/read-only prefixes are enforced before tools,
  saved-source lookup and automatic learning. A turn notice reports the limits;
  conversation-history settings are separate.
- File intents use clean paths and actual backend receipts. Failed file-memory
  operations stop before a secondary memory save.
- Source status is generated by Cursiv from supplied evidence. A supplied-memory
  label does not claim the answer used or independently verified those facts.
- Most ordinary turns skip model review. Eligible reviews appear after the draft
  is ready; `check off`, `check fast` and `check full` control optional model work.
- USB confirmations explain readable copied API keys. Language heuristics and
  model checks remain limited; validate important answers and operations.

The updater currently displays GitHub release-body text; there is no separate
local “what's new” copy to synchronize. Do not change published U82's release
claims to describe these unshipped edits. Reuse the draft only after a release is
explicitly authorized and its package is tested. Signing, current Mac build,
clean installed Windows/portable second-PC tests and physical-phone checks
remain separate gates. Heavy encryption, consumer features, a native mobile app
and large interface redesigns are deferred as requested.
