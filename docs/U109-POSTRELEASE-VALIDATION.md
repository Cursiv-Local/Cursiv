# Post-U109 reliability repairs — validation

Base main: `26e3e5e909dfc266a8f736f5108f3a56673c5fcd`.
Original branch: `codex/u109-postrelease-reliability`. The implementation was
subsequently committed as `d0f5caa`, merged through PR60 and published in **U110**
from `c3ca2c083622bd231dd2053d07ee394845fca08f`. The older U109 installers remain
unchanged. The measurements below describe the worksheet candidate; the additional
U110 routing work and native package gates are recorded in
[U110 release verification](U110-RELEASE-VERIFICATION.md).
[Continuing handoff](U109-POSTRELEASE-HANDOFF.md).

## What the reconstructed failure establishes

The worksheet supplied symptoms and identifiers, not a complete original transcript.
The [before receipt](../bench/results/U109-postrelease-before-isolated.json) uses a
fresh synthetic notebook: project ORION-742, sample CM-743, site Cedar Marsh,
temperature18.6C and the note “water clear”. The save actually succeeds and the
explicit notebook lookup returns it. Four of five reconstructed follow-up wordings,
however, have no native notebook route. All seven selected feature-question variants
also miss own-source resolution. This reproduces routing failures, not disappearing
bytes or a proven defect in the fingerprint algorithm. A restricted-process attempt
that could not write its temporary home is retained separately, not counted as a save.

The initial30 worksheet contracts had23 failures/7 passes. The expanded50-contract
worksheet passed in7.52s; the subsequent55 worksheet contracts plus48 memory-intent tests
passed103/103 in20.43s. [Original failures](../bench/results/U109-postrelease-regression-before.xml),
[final worksheet/memory checks](../bench/results/U109-postrelease-exact-id.xml),
[after receipt](../bench/results/U109-postrelease-after-isolated.json).
Additional tests were added for edge cases discovered during implementation; they
are regression tests, not an independent blind benchmark.

## Notebook identity, confirmation and history

- A parsed observation card retains sample, project, site, measurements and verbatim
  notes. A local model no longer rewords already parsed observation fields.
- Desktop observation writes, including structured/provider-prefixed requests, wait
  for their card. Confirmed canonical commands keep the existing backend/read-back
  and request-ID retry rules. Core command APIs retain their explicit-command behavior.
- Natural reads share sample/project parsing; labelled project matching is exact,
  and does not match a longer project code or a mention in an unrelated note.
- Shorter explicit measurement corrections resolve one actual current entry and
  append through `fieldlog.correct`. The original entry content, sample/project identity,
  `corrects` link and reason survive. Ambiguous/stale targets do not write.
- Chain verification reads the actual notebook and reports which matching records
  lie in that complete verified chain. Empty notebooks no longer get a vacuous
  “all0 entries verified” claim. Polite checks such as “Can you verify…” remain
  record operations, distinct from “How does your hash chain work?”.
- Natural export offers the existing signed export on a confirmation card, including
  original/correction history in JSON and CSV. It explicitly says **complete notebook,
  including all projects**: an arbitrary filtered subset is not presented as a complete
  hash chain. No new export format, project isolation or data migration was added.

The Qt regression runs record → preview → approve → query CM-743 → preview correction
→ approve → verify ORION-742 → preview export → approve. It checks the original and
linked correction in the signed export. Profile commands retain their own notebook
scope and evidence budgets. Existing confirmation, workspace and private-path rules
remain enforced.

## Source evidence reaches the answer

Feature-question variants and “show me the code path” now reach installed-source
inspection without requiring the literal word “implementation”. PDF import and
notebook hashing have reviewed native explanations gated by fresh hash-checked AST
witnesses, alongside existing memory and Field Copy rules. Missing/degraded witnesses
produce UNKNOWN with searched paths and actual declarations, rather than feature denial.

A post-draft guard also rechecks model denials of these core features after a missed
initial route. It reads only installed public source and reports the checked native
replacement separately from the earlier AI draft. No-tools turns do not read source;
their unsupported denial becomes UNKNOWN. Scoped private/scanned-PDF limitations and
fiction are not treated as global capability denials. Inspection never imports the
inspected code or executes the described feature.

[Final live worksheet](../bench/results/U109-postrelease-live-worksheet-complete.json):
all8 core-feature variants return checked source citations with zero model requests.
The installed local model remains Qwen3:4b-instruct, digest
`0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`.
The normal command/completion driver observes actual localhost requests; it rejects
outside network, switches and downloads. Temperature0, seed42, context8192; model
review off, deterministic checks remain on. Native outcomes are not called Qwen accuracy.

All original U109 questions were repeated: [15 development](../bench/results/U109-postrelease-live-development-complete.json)
and [5 previously seen held-out](../bench/results/U109-postrelease-live-heldout-complete.json).
There were no execution errors. Twelve development answers are bounded native outcomes;
three broader narratives (pipeline, network enforcement, universal permission claims)
remain partial model interpretations. All5 seen held-out outcomes are bounded native
answers. The seen held-out routing was already5/5 before these repairs; no fresh blind
accuracy improvement is claimed. [Codex labels](../bench/results/U109-postrelease-labels.md).

## Memory correction and existing style preferences

`Correction: CM-743, not CM-742.` can select one matching active saved fact and replace
that fragment inside the complete original sentence. `correct memory <ID> to <complete
new fact>` remains addressable by record ID. Ambiguity lists actual records; choosing
one still leads to a desktop edit card. Confirmation rechecks that the original is
active/unchanged. A failed read/write cannot become a successful correction. Existing
`update_fact` retains superseded history and the linked active replacement; recall
returns that replacement. No separate correction store was introduced.
Complete-value boundaries prevent CM-742 from changing CM-7429 or CM-742.1. The
optional `ID:` label requires a delimiter and cannot consume the start of “identity”.

Confirmed, user-stated presentation preferences now feed the existing style block on
subsequent unrelated turns, instead of relying on topic overlap in semantic recall.
This preference read explicitly disables legacy-memory repair; presentation lookup
does not authorize a memory rewrite.
Inferred preferences and another person's private facts are excluded; existing safety
precedence and current-request overrides remain. The saved “two researchers having
coffee” preference appeared in all4 final real-model prompts. **Tone remains partial**:
the first marsh reply still over-clarified, and the next was generic. Prompt propagation
is established; consistently natural conversation is not. No persona redesign was made.

## False overconfidence notes

The observation warning now accepts trusted application provenance. Model wording
such as “calculated by code” cannot exempt itself. Clean “No evidence found”/“No matching
entries” results do not receive an observation-certainty warning; cautious safety
answers and the existing planted overclaim tests retain their checks.

The12 new [science/control prompts](../bench/u109-postrelease-live-before-calculation.json) were frozen
before generation. [Paired live receipt](../bench/results/U109-postrelease-live-science.json)
applies the immutable U109 rule and current rule to identical final drafts, using actual
request records to distinguish native outcomes from model prose. False notes on6
controls: **2 →0**. Risk notes on6 risk drafts: **0 →0**; all6 drafts were cautious.
This demonstrates fewer false notes, not increased risk sensitivity or a general
safety/accuracy score. Stored raw responses and the original failure attempts remain.

A separate real-Qwen probe then exposed a code-backed/model-worded mean that still
received a warning: [before](../bench/results/U109-postrelease-calculation-before.json)
returned “Yes,6” with an observation warning. The calculator had actually computed6.
The final rule takes the real calculator record into account for pure numeric/math
wording. It does not exempt added safety/causal claims or model self-labels.
[After](../bench/results/U109-postrelease-live-calculation-complete.json) returns
the same “Yes,6” with code attribution, one real Qwen request and no warning.
All159 worksheet/overconfidence/verification/honesty tests passed in16.81s,
including a code-backed mean followed by an unsupported water-safety claim that
still receives the warning. The final worksheet has60 contracts. The original
science corpus above is byte-identical to its receipt hash; the later calculation
probe was appended in the current combined corpus without changing those12 prompts.

## Final gates and limits

Final worksheet proof ([machine-readable gates](../bench/results/U109-postrelease-gates-complete.json)):

| Gate | Measured result |
|---|---|
| Full isolated Windows suite | 2644 passed,15 skipped,19 passing subtests in676.13s |
| Dedicated USB | 45 passed,2614 deselected in94.34s |
| Native workspace | 63 passed in1.89s |

Earlier full/targeted failures are documented in the handoff and not erased. U110
subsequently added20 routing cases: its Windows source CI reports2664 regular
passes,15 skips and19 passing subtests; native Windows/portable/Mac package checks
passed. Those later checks have their own release receipts, rather than being
retroactively attributed to this worksheet run.

No owner exclusions, real notebooks/memories/accounts/configurations, owner signing keys,
station code or unrelated profiles were read or changed. Every app/test/model process
redirected HOME, USERPROFILE, CURSIV_REAL_HOME, CURSIV_APP_DATA, APPDATA and LOCALAPPDATA
before imports, outside OneDrive. The locked Python environment was not modified.
No old council, extra agents, cloud hosting or model-option changes were added.

On resumption October29, main was already `070c5e4` with U110 released through the
separate owner-authorized release workflow. A read-only GitHub check confirmed U110
published with11 assets. The production homepage, `/start` and the public U110 owner
manifest returned200 and identified U110. This continuation did not rebuild, deploy,
replace release assets or create another release. The owner then explicitly
authorized committing, pushing and publishing these verification-record corrections.
This record completes the worksheet closeout when merged to main through its
protected PR and linked from the existing U110 release notes. It does not introduce
a new application version or change the tagged U110 package bytes.

Reconciliation against current U110 passed128 focused tests in20.28s:
[receipt](../bench/results/U109-postrelease-receipt-check.xml). The subsequent
documentation/inventory-only checks have a separate
[metadata receipt](../bench/results/U109-postrelease-receipt-metadata.xml).
[Secret audit](../bench/results/U109-postrelease-secret-scan.json) covers the
new committed range from the original base through `070c5e4`, plus current public
file bytes; excluded owner paths are checked before any read. The public-key
verification assets are intentional; no private signing key is part of this scope.

Tone and the three broad model narratives remain partial as described above. An
original transcript would allow exact wording comparisons beyond the reconstructed
worksheet variants. The existing U109/U110 release assets must not be overwritten.
