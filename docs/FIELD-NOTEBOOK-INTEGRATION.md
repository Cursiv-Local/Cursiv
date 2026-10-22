# Native Field Notebook integration repair

Date: 2026-10-21. Branch: `codex/native-field-notebook`.

Follow-up: the subsequently approved filesystem, memory and related-store findings
were repaired on `codex/verified-local-actions`; see
[Verified local actions](VERIFIED-LOCAL-ACTIONS.md). The audit/results below describe
the earlier notebook patch and remain its historical evidence.

## Read-only audit and root cause

The native backend is `cursiv_v215/core/fieldlog.py`. Confirmed callable APIs:

- `add(**fields)`: returns an actual observation dict after append, flush and fsync.
- `entries()` / `current()`: load all records / the current view after corrections.
- `correct(id, reason, **fields)`: appends a linked correction; never edits the original.
- `verify()`: checks the existing SHA-256 fingerprints, previous-record links and sequence.
- `parse(text)`: parses explicit observation fields and retains other text as notes.
- `field_recall.query()`: bounded, integrity-checked retrieval and filtering.

The graphical `FieldNotebookDialog._save_entry()` already called `add()` or
`correct()`, and `refresh()` read `current()` from the same backend. Normal storage
is `Path.home()/.cursiv/fieldlog/observations.jsonl`. Portable activation redirects
HOME before importing modules, so that path is under the portable drive's Home.
Demo mode retains its existing separate notebook. The generic workspace and an
invented `field_log.txt` are not the native notebook's storage interface.

Before this repair, the desktop path was:

1. ChatPanel snapshots history and calls `chat_commands.handle_command()`.
2. Only explicit `log ...` / `field log ...` commands reached `fieldlog.command()`.
3. Natural notebook requests could fall through to `chat_app.chat()` and generic
   file classification/planning. Some `save ... file ...` requests were captured
   by the generic filesystem parser before the notebook command handler.
4. The local Ollama path uses `/api/generate`, streams ordinary response text,
   and does not execute textual `file_create` descriptions. The generic planner's
   built-in file tools are read-only; there is no built-in `file_create` there.
5. That prose used the ordinary assistant renderer. Existing tool-note filtering
   only protects the specific "Checked on this computer" status format.
6. Command TextResults were excluded from saved conversation history. This also
   lost notebook instruction/details needed by subsequent "add it" requests.

Source inspection establishes this routing/presentation defect; it does not
establish that any invented notebook file was written. No live qwen inference
was used as proof of execution during this repair.

## Production changes and execution path

`core/notebook_tools.py` provides three explicit application-owned operations:

- `notebook_create_observation`: validates structured fields and a request ID,
  checks the existing chain, calls `fieldlog.add()`, reads the stored ID back,
  compares the stored data with both the requested fields and returned record,
  validates its record shape, and verifies the chain again.
- `notebook_read_entries`: uses the existing bounded `field_recall.query()`.
- `notebook_verify_chain`: uses the existing chain and photo verification APIs.

Unknown operations, file paths, invented permission flags and unsupported photo
arguments are refused. Existing-entry edits/deletions are not chat operations;
the response points to the notebook window's append-only correction workflow.
This is an allowlisted Python application interface, not a parser that executes
model-written tool-call text. It does not expose arbitrary filesystem writes.

Deterministic routing now precedes generic files, memory, model selection,
answer checking and automatic learning in both desktop commands and the public
`chat_app.chat()` entry point. Explicit provider prefixes cannot bypass it.
Native notebook operations work with file access off and network access off.

Supported requests include:

```text
record a field observation: site: Pond 2; water temp 12.40 C; pH 7.20; note: turbid
add it to the field log
add it to the field notebook section
No, in the field notebook, not a file.
read the field notebook entry <actual record ID>
verify the field notebook SHA-256 chain
```

Follow-ups use bounded, consecutive **user** observation details. Assistant prose,
claimed paths/permissions, conversational memories and forged receipts never
supply observation data or evidence of a save. More recent explicit structured
values replace earlier values of the same field/measurement before recording.
Ambiguous references ask for details rather than reconstructing a model's draft.

The Result object is created by application code. Only a verified save includes
the actual record ID, fingerprint and a positive acknowledgement. Errors are
shown directly. If fsync/read-back fails, the response explicitly allows that
data may already exist; it never deletes an uncertain append or falsely states
that nothing reached disk. Retrying a valid completed append reuses its ID.

ChatPanel displays native results as command text and saves their user context
plus structured `notebook_receipt` metadata. On reopening the Field Notebook,
its existing `refresh()` reads these same records. Conversation JSON remains
backward compatible; metadata is optional and is not treated as execution proof.

## Append-only compatibility and duplicate handling

`fieldlog.add()` has one optional `request_id` argument. A new chat-created entry
may contain `chat_request_id`, which is covered by the existing fingerprint.
No migration, schema version bump, rewrite, renumbering or deletion is performed.
Old entries remain byte-for-byte unchanged. Existing correction, import/export,
signature and chain checks continue to use the original backend and hash logic.

The existing append lock also guards request-ID duplicate detection. Reusing an
ID with different details fails. The desktop scopes IDs by saved conversation,
person, preceding user context and source observation; repeated "add it" requests
reuse the observation, while separate chats and new explicit observations remain
distinct. Non-GUI callers can pass `scope` to `notebook_tools.command()` or
`notebook_scope` to `chat_app.chat()`; they should use a stable conversation ID
when they need the same retry/isolation behavior as the desktop.

## Tests and evidence

Tests run on disposable snapshots with isolated HOME/USERPROFILE, application
data, memory and signing keys. Real notebook data is never a test fixture.

- Baseline full suite: **864 passed, 1 skipped, 1 failed**, 140.33 s.
  Failure: existing `test_chat_rendering.py::test_chunks_are_batched_on_the_gui_thread`
  did not observe the timer firing during its 65 ms wait. This occurred before
  any production edits in this repair. The timer test was not changed.
- An initial new-test collection error used pytest's reserved `request` parameter;
  it was corrected. A subsequent run had **114 passed, 1 failed** because the new
  offline test incorrectly blocked the local `socket.gethostname()` call used to
  label the device. Its guard now blocks actual network connection/resolution,
  send and bind operations while allowing that local hostname lookup.
- Focused run before the final scope/compatibility additions: **116 passed**,
  22.93 s. Log: `cursiv-check-c23krzrh/pytest.log` under this task's visualization
  workspace.
- Intermediate full suites: **913 passed, 1 skipped**, 149.66 s
  (`cursiv-check-xmby05cu/pytest.log`), and **914 passed, 1 skipped**, 138.92 s
  (`cursiv-check-txlc2jcn/pytest.log`).
- **Final exact-source full suite: 920 passed, 1 skipped, 140.34 s.**
  The only skip requires macOS Keychain; this run was on Windows. The earlier
  timer failure did not recur in any of these three full post-change runs.
  Final log: [pytest.log](C:/Users/joshu/.codex/visualizations/2026/10/21/01a15c12-fb2b-7d00-9f67-101caecdd403/cursiv-check-dhckjpb1/pytest.log).

The final full suite used Python 3.13 via `check_cursiv_memory.py` with no test
selection (all `tests`, pytest `-q -ra --disable-warnings --maxfail=10`). The
focused selection was `tests/test_notebook_integration.py`, `tests/test_fieldlog.py`,
`tests/test_file_access.py`, and `tests/test_portable_recall_curiosity.py`.
All six changed/new Python files match the final test snapshot byte-for-byte.
Syntax inspection and `git diff --check` also passed. A comparison with the
task-start snapshot found exactly the eight intended notebook/report files;
unrelated pending files and the previous handoff content were preserved.

Coverage includes native initial/follow-up recording; destination corrections;
structured precision and coordinate preservation; newest user values; forged
assistant filesystem/memory claims; retries and concurrent threads; distinct
conversation scopes; permission/fsync/read-back/API failures; actual Windows
read-only file attributes; retrieval; chain tampering; existing-record/export
compatibility; GUI visibility and saved receipt/context; sequential fresh-process
restart/read/retry; offline execution and a portable drive move.

Backend-selector tests cover Ollama/OpenAI/Claude/xAI paths with model and generic
filesystem calls set to fail if reached. They verify application routing, not
live model behavior or external service availability. Fresh-process tests check
the real disposable JSONL with Python `Path.read_bytes()` / `json.loads()` and the
original chain verifier. No installed executable was rebuilt or launched.

## Related findings, deliberately outside this repair

- Explicit memory commands call the real `semantic.add_fact()` pathway. Its
  `_write_facts()` performs an atomic write and read-back; `_save_reply()` also
  looks up the returned record. Natural-language misses can still reach an LLM,
  and model claims of remembering are not receipts. `claims.memory_notes()` adds
  warnings after prose; it does not make that prose authoritative or prevent all
  invented success claims. This broader memory routing repair remains separate.
- Generic filesystem adapters still serialize errors as ordinary strings and can
  emit a "wrote"/"Checked" status for a failed operation. The earlier filesystem
  audit identified that defect; this repair bypasses that path for native notebook
  requests rather than changing unrelated filesystem/updater/networking code.
- Other state-changing command results commonly use plain TextResult strings.
  For example, legacy letter saves return an ID after file/index writes, but their
  interface has no equivalent notebook receipt/read-back contract. No live letter
  or memory save was made, and no general tool-security audit is claimed here.

## Remaining limits

- The language router is intentionally bounded and deterministic. Ambiguous
  references or unusual wording can require a clarification. It never extracts
  observation facts from model prose or invents missing values.
- SHA-256 chaining supplies the existing integrity check, not a digital signature
  authenticating a person's identity. Receipts are backend-verified application
  results; this patch adds no authentication service or new permission system.
- The existing fieldlog append lock is process-local. Concurrent threads and
  sequential restarts are tested; simultaneous writes from multiple processes,
  physical drive loss and hardware power-failure durability are not certified.
- Existing damaged chains block native chat appends and are reported. This patch
  does not repair or delete damaged user records automatically.
- Installed Cursiv remains unchanged until the owner builds and installs a release.
  No installer/updater edits, release, commit, push or deployment were performed.
