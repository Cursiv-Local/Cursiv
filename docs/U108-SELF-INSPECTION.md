# U108 automatic own-source inspection

U108 implementation, based on U107/main `2f1118b`; immutable source is
`a63a4cfb16dbd47c5baae5bbddf6aa08909d537b`. [Release verification](U108-RELEASE-VERIFICATION.md)
records source and frozen package completion. This report distinguishes source access from
model understanding; earlier iterations below remain historical evidence.

## Behavior

Latest refinement: critical confirmation, correction-history and provider-fallback explanations
are native, conditional on inspected source witnesses in `self_contracts.py`. The model does
not decide these rules. Changed or missing witnesses stop the explanation. These maintained
contracts are not a general Python theorem prover or a runtime trace. Other implementation
questions use the local model with bounded, ordered AST sections and explicit omissions.
Source fingerprints normalize Git's LF/CRLF translation; other byte changes remain detectable.

People can ask implementation questions naturally, such as “How do you process
my messages?” and “And where does the model actually get called?” Cursiv selects
public application source automatically and asks the installed local model to
explain the checked excerpts. Current-chat user messages can resolve follow-ups;
another chat, assistant assertions and saved memories cannot supply source authority.
This is retrieval when answering, not permanent training or loading the entire
repository into a small model's context.

`core/self_index.py` builds a versioned Git inventory of public source and docs,
Python declarations, import bindings and possible static call targets. The current
development inventory has 375 files and 2,508 declarations. It excludes untracked
owner documents, private stores, station code, tests and protected paths. Only
three explicitly named new public runtime modules are added before commitment.
The index contains metadata rather than whole source files. Selected source bytes
are reread and hash-checked; a version mismatch, modified file, unsupported path
or linked file fails closed. No inspected code is imported or executed.

`core/self_inspection.py` supplies bounded excerpts and normalized Python syntax
observations. Those observations identify source structure; they are not verbatim
quotes or observed runtime traces. App-owned labels identify the installed version,
source snapshot and actual declarations. Source-reference checks can withdraw an
explanation with an invented path, line, implementation module or code quotation.
Passing these checks does not prove all semantic claims in an answer.

Workspace access can remain off. `No tools` still disables own-source inspection.
Explicit questions about another repository retain workspace authorization.
Own-source explanations bypass document retrieval, saved personal context,
plugins, workspace actions and extra planner calls. They use the installed local
model and never automatically download a model or fall back to an online provider.
Optional answer review for this path is also local. Additional agents were not
necessary; the existing Qwen adapter and shared answer checks are reused.

Automatic approval review rejected a proposed automatic online fallback because
it could send repository excerpts to external providers without authorization for
that payload and destination. The proposal was not applied. The local-only
alternative leaves no outstanding approval request.

## Evidence and honest limits

The natural-question corpus was frozen in `bench/u108-self-inspection.json` before
implementation: six development questions and four held-out questions. Real runs
use installed `qwen3:4b-instruct`, digest
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`, temperature 0,
seed 42, context 8192. The harness rejects requests outside local Ollama and uses
disposable application stores. Optional model review is off; deterministic checks
remain on. Counts and claims come from saved receipts rather than expected values.

The frozen automatic-entry baseline failed all six source-context cases; both
unrelated/new-chat controls passed (`U108-self-before.xml`). Six baseline live
questions used four model calls and two generic native help answers. The baseline
invented notebook storage/confirmation behavior and lacked implementation evidence.

Development runs are retained rather than overwritten. One intermediate structured
run exposed an index variable-shadowing defect, which was repaired and covered by
comparing every installed declaration's name and line against the actual Python AST.
The last pre-holdout development run made six local requests: an incorrect module
reference was withheld, while fallback prose still simplified conditions. Source
selection success must not be reported as six semantically correct answers.

The first held-out run (`U108-self-live-heldout.json`) made four successful local
generation requests. Manual Codex review found two material semantic failures:
the correction answer said the original was replaced despite retained history,
and the retrieval answer made an unsupported exclusivity claim. The Send answer
identified real components but compressed intermediate dispatch; the path-boundary
answer described the inspected containment check. This is a small sample and is
not independent human grading. Later reuse of these questions is a regression
retest, not another unseen evaluation.

The focused privacy/source/review gate passed 155 tests (`U108-self-focused-final.xml`).
A synthetic packaging probe (`U108-self-package.json`) exercised the actual build
spec's data plan: five public files plus a generated manifest, untracked private
fixture excluded, and a successful hash-checked read from a simulated frozen bundle.
It did not build, install or launch a packaged app. Full Windows and USB follow-up
results are recorded in `U108-HANDOFF.md` and `U108-VALIDATION.md`.

The broad run caught 25 routing regressions: feature overviews, known workflows,
current-state queries and real saved-memory recall were being mistaken for code
questions. The classifier now requires implementation mechanics; those native
routes remain authoritative. The affected source/native/privacy/science set passed
359 tests after repair. The selector also now reserves space for matching code
operations before surrounding context, includes the actual notebook append path,
and retains enclosing branch conditions in syntax observations. Nested definitions
are excluded from parent execution facts. The final affected set passed 393 tests.

Final live receipts are `U108-self-live-scoped-development.json` and
`U108-self-live-scoped-regression.json`. All ten questions received source context
and completed one local generation request each. The six development questions
used 6,800 input/630 output tokens, versus 7,889/1,345 over four model requests and
two native help replies at baseline. These changed routes and small samples do
not justify a general efficiency claim. `U108-self-comparison.json` records the
counts and manual case labels; all 31 emitted file/line references matched actual
locations in hash-matching indexed source bytes. This is citation accuracy only.

The final local-invocation, sample-matching and containment answers were supported.
Message-flow answers still overgeneralized the proposal shortcut, confirmation
explanations omitted the decisive preview/approval boundary, and local-fallback
ordering was wrong. The seen correction retest described append and preserved
history but retained ambiguous opening replacement wording. Retrieval improved
without the previous exclusivity claim. These remaining semantic failures are
not converted into a passing quality score because the citations are real.

After the final source-scope repair, the complete Windows suite passed **2,484 tests,
15 skips and 19 subtests in 410.93 seconds** (`U108-self-full-validated.xml`). Code
and index remained unchanged during that run. The earlier 25-failure run and the
interrupted follow-up remain visible in the handoff. Automated regression success
is separate from the unresolved model interpretation results.

The final dedicated USB gate passed **45 tests in 74.48 seconds**
(`U108-self-usb.xml`), using synthetic folders. No physical-drive or installed-app
claim follows from that result.

Known limits include dynamic dispatch, sparse excerpts, implicit questions outside
the recognized topics, and small-model interpretation errors. The index is a
maintained source lookup, not universal working understanding. Initial casual
banter from the original U108 brief also remains only partly resolved. Native
Mac/Linux testing was outstanding at that checkpoint. Completed native source and package
checks are recorded in the release verification; physical USB and independent human review
remain outstanding.

## Reproduction and maintenance

Establish disposable `HOME`, `USERPROFILE` and `CURSIV_APP_DATA` before imports.
Windows broad checks also redirect `APPDATA`, `LOCALAPPDATA` and `CURSIV_REAL_HOME`.
Use a unique local temporary pytest base outside OneDrive and the existing locked
Python interpreter; do not install dependencies into it.

```text
python scripts/build_self_index.py
python -m pytest tests/test_self_index.py tests/test_automatic_self_inspection.py -q
python scripts/u108_self_live.py --set development --output <new-result.json>
python scripts/u108_self_live.py --set heldout --output <new-result.json>
python scripts/u108_package_probe.py --output <new-result.json>
```

Regenerate the development index after indexed source changes. The packaging spec
builds a fresh inventory from the source being packaged. Release/version edits also
require regeneration. Never broaden the inventory to owner documents to resolve
a failed lookup, and never equate metadata generation with installed-app validation.
