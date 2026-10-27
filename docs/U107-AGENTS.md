# Research profiles and deferred tasks

Instructions for the U107 research profiles. Tagged release status is recorded in U107-HANDOFF.md.

Use `@field <question>`, `@checker <question>`, `@protocol <question>`, `@report <question>` or
`@writer <message>`. `agents ask <question>` selects relevant profiles using code. The alias
`agent council <question>` remains supported; it is unrelated to the removed general council.
Choose names explicitly with `agents ask @field,@writer: <question>`. A run supports at most three
distinct profiles and explains how to split larger requests. Personal overrides win over starters.
An ambiguous question asks for a profile instead of launching all five.

Profiles are read-only. Their saved `reads` fields permit notebook, matching imported documents and
code calculations; a saved `tools` field grants nothing. Teaching is user-provided context, not verified
fact. Current conversation history, saved teaching and writing style may be supplied when applicable;
they are accounted for separately from notebook/document facts. Automatic personal-memory recall is
withheld. Retrieved instructions are untrusted data; detected instructions withhold teaching, history
and saved writing style from every model stage in that run. Native notebook/file actions
and restricted-turn rules still take precedence; an agent answer cannot create a save receipt.

Notebook checks inspect every current matching record after corrections. Statistics scan a single
verified snapshot bounded at 100,000 rows/64 MB; larger or damaged sources return unavailable.
Dates mean recorded local dates. Site/sample/date/measurement/entry scopes and numeric coverage appear
in the result. Explicit latest-N/offset requests select records before calculating. Correction-history
requests use the native notebook command; research reports use current records after corrections.
Means/medians/ranges use finite numeric measurements with recorded units (or explicitly unitless
measures such as pH). Missing units/non-numeric values are counted, never silently filled. Mixed units
are not averaged together. Regression, significance and other unsupported analyses return a limitation.
Model context has bounded excerpts, separate from full-scope code calculations. Document search has
bounded passages and does not claim that all pages were read. Known missing evidence for any selected
profile stops the run before model stages. Protocol misses therefore use no model, including when
another named profile precedes the protocol role. A full narrative exceeding the excerpt budget asks
for a narrower scope; it does not substitute a recent slice or a numerical-only answer.

Code checks inspect supplied citations, record IDs, critical quantities/units, computed statistics and
unexecuted action/source claims. A failed draft is withdrawn and later stages stop. Passing these
particular checks does not establish general truth. Optional final review retains `check off`,
`check fast` and `check full`; it never overrides deterministic evidence and uses no cloud reviewer.
Single-profile results skip synthesis; deterministic answers skip inference entirely.
Routine tips/habits for field-note recording use Cursiv's native recording guidance with no private
notebook retrieval. Simple numeric reports are also code-only; explicit interpretation/discussion
can use a model. Personal composition instructions and explicitly creative requests retain that path.
Reused aggregate scopes are calculated once inside the run, with no cross-run cache. The application
adds excerpt/document coverage to generated answers, independent of the model's wording.

Attempted generation requests, including failures/retries/fallbacks, share limits: individual fast2,
group fast5, individual full4, group full7. Input is conservatively bounded by UTF-8 bytes plus output
reservation against the installed context. Normal/full runs have 240/360-second limits. Exhaustion
returns incomplete work and requires a deliberate retry. No incidental model downloads occur.
Cancellation or person/workspace/conversation changes reject stale answers and stop later stages.
The desktop checks ownership when queued text/history is accepted on the GUI thread. Opening a new
conversation cancels the old worker; delayed replies cannot become the new conversation's history.
Personal profile usage metadata stays bound to the captured person and preserves concurrent teaching.

`queue add <task>` records a deferred prompt; `queue list` shows stable IDs and actual states.
`queue flush` deliberately executes at most five tasks through local read-only profiles, never native
commands, tool loops or cloud fallbacks. A model requesting flush cannot authorize it. The owner and
workspace must still match; dependencies may leave the task blocked. Outcomes are pending, running,
succeeded, failed, blocked or cancelled. Empty/error/placeholder text cannot establish success.

Use `queue cancel <ID>` or `queue retry <ID>`. Expired running claims (eight-minute lease), interrupted
or legacy fired outcomes require reconciliation; after checking any previous effects, use
`queue retry <ID> --reconciled`. Legacy queued/error tasks also need explicit review/retry. No automatic
replay on restart occurs. JSON damage fails closed, atomic writes preserve recoverable claims, and
concurrent flushes cannot claim the same running task. Completed history remains available in storage;
the compatibility history-clear action hides successful tasks rather than deleting failure records.

Hermes and the external Codex bridge are optional integrations requiring their own dependencies;
research profiles work without them. The coding review pair is separate from research coordination.
Fleet Dashboard is a device view, not a distributed research-worker service.
