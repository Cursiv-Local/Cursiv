# U109 installed-source inspection validation

Unreleased working candidate on main `efc2f961049b767f0fe49e38304e9e70f25a6955`.
The application version remains U108 during comparison. Receipts identify the
candidate using working source hashes and a source inventory snapshot, not a
U109 release tag. No commit, push, signing, release or website deployment occurred.

## Reproduction and evidence

The corpus `bench/u109-self-inspection.json` was frozen before runtime repairs:
15 development questions and five held-out questions. Baseline5 selects startup,
PDF, persistent memory, portability and regex. The small synthetic corpus and
Codex source review are not an independent human evaluation or a general accuracy
estimate. The held-out prompts were authored before implementation, not supplied
by an independent evaluator.

Use the existing locked Python environment; redirect HOME, USERPROFILE,
CURSIV_REAL_HOME, CURSIV_APP_DATA, APPDATA and LOCALAPPDATA to a disposable local
Windows temporary directory before imports. Qt runs offscreen with engine startup
disabled. Pytest uses a unique temporary base outside OneDrive. No real user store
or excluded owner file is opened. Do not install packages into that environment.

`scripts/u109_bench.py --mode profile --output <new-receipt.json>` measures five
preparations per development question and 1,000 ordinary greetings. `--mode live`
uses normal desktop command dispatch and the chat facade; `--set heldout` selects
the frozen held-out questions. Output paths must be new; previous evidence is
retained. Real requests use installed `qwen3:4b-instruct`, temperature0, seed42,
context8192 and localhost Ollama only. Model switches, downloads and external
requests are rejected. Review is off while deterministic answer checks remain.
Later receipts retain raw model text and the evidence supplied to it, separately
from the final answer after source checks. Zero-call native answers are identified
as app-owned, rather than reported as successful Qwen generations.

## Before repairs

`U109-baseline.xml`:20 failed/7 passed in2.01 seconds on unchanged U108.
One missing-feature test also required nonempty excerpts; that contradictory
expectation was corrected afterward. The original receipt is preserved, so this
failure count is not a like-for-like final accuracy score.

`U109-live-before.json` contains actual installed-model output:

| Probe | U108 observed result |
| --- | --- |
| Startup | Unrelated feature/self-modification guidance; zero model requests |
| PDF | False claim that the installed application has no PDF importer |
| Persistent memory | Saved-fact lookup instead of implementation inspection |
| Field Copy | False absence/incomplete-copy explanation from sparse snippets |
| Regex `[a-z_]{3,}` / `page` | Correct True, but claimed source verification without a source read |

The reported incorrect regex diagnosis was **not reproduced** by this live
baseline. Its mathematical correctness is protected by deterministic regression
tests, not claimed as a measured before/after mathematical improvement.

## Development findings

`U109-live-development.json` located PDF and memory code, but still contained
unsupported architecture/encryption/timeout conclusions and withheld feature
answers. `U109-live-context.json` improved code discovery and retained actual raw
generations: the model still denied a feature named Field Copy while identifying
the actual USB copy functions. The denial was withheld, not counted as success.
Primary functions now reuse ordered branch-preserving source slices, while the
Field Copy rules, timeout handling and audit hypothesis use checked app code.

Targeted intermediate receipts preserve their real failures. None is a substitute
for the final checks. Current final development, held-out, broad-suite, USB,
workspace and performance measurements are recorded below when completed.

## Final candidate evidence

Source snapshot `43d70247e6c7693b308c9654ffc0d99153b3918acd4ce0f822d48bba69eccceb`:
`U109-semantic-targeted.xml` has **128 passed in29.21 seconds**. This set includes
actual AST role/relationship witnesses, changed-source and altered-rule rejection,
invented references, permissions, no-tools, read-only/network restrictions, existing
source contracts and synthetic packaged roots for all ten feature areas.

`U109-live-semantic-development.json`:15 completed development cases, no harness
errors, **five actual Qwen requests**. Ten responses are native/scoped outcomes,
not Qwen generations. `U109-source-review.json` records Codex grading: **11 meet
their bounded goal, four partial** (architecture, offline, hash-chain detail and
permissions prose). No general model-semantic accuracy claim follows from this
small test. Source discovery/read coverage for all ten feature areas succeeds;
that is separate from the completeness of model descriptions.

The comparable original four failed implementation questions (startup, PDF,
memory and portability) now reach actual installed-source evidence, replacing
unrelated guidance, saved-fact lookup and false feature denials. Regex remains
mathematically True for `page`, now with an actual deterministic check instead of
an unsupported source-verification claim.

First held-out `U109-live-heldout.json`:4/5 inspection routes, with a mathematically
correct but model-only regex answer. After the routing repair, the five **seen**
regressions in `U109-live-semantic-seen-heldout.json` all initiate the expected
inspection/check route; only the PDF explanation calls Qwen. This is a seen retest,
not a fresh held-out score. No external reviewer supplied or graded these cases.

Later development review also caught real notebook-verification confusion,
misleading memory-backup prose, imprecise document scoring and overstatement of
response-check certainty. Those failed receipts are retained. Reviewed native
rules check their current AST witnesses and fail to UNKNOWN when witnesses change.
They reuse the U108 critical-rule approach; they are maintained rules rather than
general proof of arbitrary implementation changes.

## Performance

`U109-profile-before.json` and `U109-profile-after-semantic.json` use the same
machine, five preparation repetitions/case and1,000 greetings. Greeting median
was **0.0195ms before /0.0046ms after**, with **zero source-index loads** in both
ordinary-chat loops. This measures that greeting/intent path, not every ordinary
conversation or model latency.

| Source request | Before median ms | After median ms | Actual files read after |
| --- | ---: | ---: | ---: |
| Document search | 38.30 | 19.64 | 1 |
| Field Copy | 48.61 | 78.93 | 10 |
| Offline enforcement | 32.85 | 11.52 | 1 |
| Notebook lifecycle | 17.93 | 67.56 | 9 |
| Ollama timeout | 58.68 | 47.47 | 9 |
| File restrictions | 22.12 | 35.11 | 4 |
| Startup | Unhandled | 891.41 | 24 |
| Message pipeline | Unhandled | 864.83 | 24 |
| PDF | Unhandled | 19.04 | 4 |
| Memory | Unhandled | 62.00 | 4 |
| Hash chain | Unhandled | 45.98 | 5 |
| Response checks | Unhandled | 62.71 | 6 |
| Audit | Unhandled | 643.39 | 24 |
| Regex | Unhandled | 111.86 | 5 |

Earlier handled routes could select unrelated modules; these timing comparisons
do not imply equal evidence quality. More extensive inspection costs more on
several routes. Previously unhandled requests have no useful successful latency
baseline. Prepared prompts remain below4,900 UTF-8 bytes (maximum4,899 measured).
Native replies do not send those prompts to a model. Local generation timings and
tokens are in the live receipts; cold loads and changed native/model paths prevent
claiming a general model-speed improvement.

## Security and broad gates

Gitleaks8.30.1 found **zero findings in45 changed public files** at the first final
scan (`U109-public-secret-scan.json`); excluded owner files were filtered before
reads. The earlier U108 audit separately covered available Git history. This
candidate has no new commits. No private signing keys, API credentials or user-store data
is included in these test receipts.
The final changed-file scan and exact public-file hashes are in
`U109-public-secret-scan-final.json`; excluded owner files are omitted before
reading. Its scope is changed public files, rather than a new all-history audit.

The first full run was stopped before further source repairs after manual review
found semantic errors; its partial ignored log is not a successful test receipt.
Final Windows suite: **2,584 passed, 15 skipped, 19 subtests passed in448.75 seconds**
(`U109-full-final.xml`). Runtime and source inventory were frozen throughout.
Dedicated USB: **45 passed, 2,554 deselected in76.91 seconds** (`U109-usb-final.xml`).
Native workspace gate: **63 passed in1.99 seconds**, with exit0 recorded in
`U109-final-gates.json`. Each gate used a separate disposable local home.
No native U109 binary has been built.

All local source gates pass; no source-test blocker remains. Remaining work before
distribution is owner review/authorization, versioned release preparation, hosted
platform CI and tagged native Windows/Mac package/signature checks. General model
prose remains partial as recorded above. Do not claim every U109 acceptance
criterion or complete runtime/codebase understanding has been independently proven.

## Scope and limitations

VERIFIED means hash-checked source/AST or a bounded deterministic expression
test, not runtime behavior. Model interpretation is INFERRED. UNKNOWN,
NOT FOUND IN SEARCHED SCOPE, ACCESS DENIED and CONTRADICTED are separate states.
Coverage distinguishes full symbol-metadata lookup from selected source-body
reads, reports unavailable files and bounds, and names uninspected scopes.

Inspection reads at most24 source files/1.2 million characters by default, with
48 relationships and depth3; no request launches arbitrary inspected code.
The AST cache holds16 parsed files and is consulted only after fresh hash checks.
Dynamic dispatch, unselected branches and dependency behavior remain unknown.
Regex execution is restricted to a bounded single character class and quantifier;
general expressions and arbitrary mathematical programs are not executed.

Synthetic PyInstaller-root tests cover source availability and changed-file
rejection. They do not establish a new native Windows or Mac binary build.
No source self-audit is claimed to reproduce a defect, prove a vulnerability,
verify a private notebook or perform a transfer to a real drive.
