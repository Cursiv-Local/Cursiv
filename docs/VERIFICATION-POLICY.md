# Answer verification policy

## Evidence and result

Deterministic checks operate on the answer and the evidence actually supplied
this turn: calculations, reference titles, document pages and execution records.
The same assessment callback checks a proposed replacement. A directory listing
is not source evidence, and a model's save claim is not an execution receipt.

`core/problems.py` defines immutable `Problem(code, severity, message, source)`
records with a serializable `record()` method. `verify.PassResult` provides
`issues` (remaining findings), `resolved` (findings addressed by an accepted
revision), legacy display messages, `status`, `clear` and learning eligibility.
Callers can assert on codes without parsing generated prose.

| Status | Meaning |
|---|---|
| `skipped` | Optional model review was unnecessary. `clear=False`; no verified origin. |
| `checked` | Bounded deterministic checks found no problem and a nonempty checker said clear. |
| `revised` | One replacement passed the same evidence checks, new-number checks and a second nonempty clear verdict. |
| `problems` | Retain the original draft and notes. No verified origin or assistant-derived retention. |
| `unavailable` | Requested checker returned no result. Retain the draft as unverified. |

“Verified” is an internal provenance label for this bounded review. It does not
prove every statement, establish clinical safety, or authenticate model prose.
Pure-code coverage is deliberately finite.

## Rewrite rules

1. Deterministic checks run before a model verdict. A `CLEAR` response cannot
   erase their findings.
2. Error-severity findings get notes only: contradictory conclusions, conflicts
   with a supplied reference/dose/calculation, invalid document citations,
   unsupported source/action claims, unsupported n=0/1 inference or failed checks.
   These do not invite the model to overrule execution or safety evidence.
3. In opt-in full mode, noncritical constraint/ledger/assumption findings and concrete model-review
   findings may permit **one** rewrite. Its instruction limits changes to the
   listed problems and forbids new factual claims.
4. Recheck a changed replacement with the original evidence. An unchanged
   rewrite makes no second model call. Reject new numbers,
   remaining or newly detected problems, failed checks, empty output or an empty
   second verdict. The user sees the original draft and notes, not rejected text.
   Machine-readable findings retain why the replacement was rejected.
5. Casual turns skip optional review when no deterministic problem is found.
   Emergencies, application-owned receipts and battery-saving flows retain their
   existing model-review exclusions. Deterministic warnings still apply; a
   failed deterministic check is surfaced as unavailable.
6. Existing exact unit-conversion correction uses a calculated result directly.
   It is distinct from an LLM rewrite. Tool execution receipts are never revised.
7. Detected dose/reference contradictions withdraw the model instructions and
   display the actual supplied reference with its provenance/review status. This
   application-owned replacement uses no model rewrite and learns nothing from
   the withdrawn draft. Callers without replacement support get an explicit
   retraction/correction after the streamed draft; the Qt caller replaces it.

## Desktop review timing and modes

`check fast` is the default: deterministic findings receive immediate notes and
an otherwise eligible high-risk/explicit-check turn permits one 180-token local
verdict. `check off` keeps pure-code checks while disabling model review.
`check full` allows a bounded verdict/rewrite/recheck (300-token rewrite), with
no extra ledger-only model call. Years, dates, generic recommendations, memory
update wording and a prior failed turn no longer trigger a model pass alone.

The desktop finalizes the draft/enables input before starting model review.
Results are labeled follow-ups; accepted full-mode replacements are suggested
revisions. Jobs copy the original supplied context/evidence and cannot mutate
session ledgers or learn pending assistant claims. No additional memory lookup
occurs to assemble reviewer context. Qt slots reject stale/cancelled results.
The background reviewer uses an installed standard local model, never starting
one or falling back to an external service. Programmatic callers without the
desktop callback retain a bounded synchronous path. See
[implementation, controlled timings and limitations](ASYNC-ANSWER-REVIEW.md).

## Stable code families

The later [trust-boundary follow-up](TRUST-BOUNDARY-FOLLOWUP.md) makes source
formatting independent of model-answer words. Final prompt assembly records
supplied memory separately from recalled/withheld facts; evidence and optional
review use that same scoped record. A supplied-memory label does not establish
use or correctness. Case-varied model source footers cannot become the app's
status label. Explicit external Cross-check now has a 400-token cap on all
supported providers; automatic model review retains its 180/300-token limits.

`CONSTRAINT_MISMATCH`, `ASSUMPTION_AS_FACT`, `UNGROUNDED_KNOWN`,
`UNSUPPORTED_CITATION`, `MISSING_LEDGER`, `CONTRADICTORY_CONCLUSION`,
`REFERENCE_CONTRADICTION`, `DOSE_MISMATCH`, `SMALL_SAMPLE_INFERENCE`,
`UNEXECUTED_LOOKUP`, `EXECUTION_*`, `CALCULATION_MISMATCH`,
`DOCUMENT_CITATION`, `UNCONFIRMED_STATE_CHANGE`, `CHECK_UNAVAILABLE`,
`CHECKER_UNAVAILABLE`, `MODEL_FINDING`, `REWRITE_NEW_NUMBER`,
`CHECK_INPUT_LIMIT`, `REVIEW_GROUNDING`.

Quoted examples, code/blockquote examples and conditional lookup descriptions
are excluded from the narrow web-lookup assertion check. Actual first-person
lookup claims remain checked, including those containing a quoted search query.
This is a bounded language heuristic, not a general claim parser.
Optional checker context may use already supplied conversation turns, but cannot
recall saved memory when the active turn forbids inspection.

## Measurements

The standalone 16-case deterministic replay is separate from the frozen Truth
Benchmark. Its JSON fixtures, runner, raw results and comparison are linked in
[the maintenance report](MAINTENANCE-HARDENING.md). The live six-case subset uses
the unchanged Truth Benchmark 1.5 questions and scorer. Neither subset is a
general accuracy estimate or a production-readiness certification.
