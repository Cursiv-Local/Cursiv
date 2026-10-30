# Self-inspection and guardian repair — U113

The owner authorized commit, push and release of these reviewed repairs on October 30,
2026. They extend the separately published U111/U112 code; U113 packaging and public
verification are tracked below. Production credentials are outside the change scope.

## Reproduced causes and repairs

- `core/turn_policy.py: Policy.confirmation` supplies the talk-only text.
  `for_text` made a leading retention restriction disable every read. An explicit
  request for Cursiv's installed public source now permits read-only inspection
  while retaining write/memory restrictions. `effective` still intersects parent
  policy; an actual no-tools/read denial cannot be overridden.
- `core/self_inspection.py: _topic, prepare, invalidate_unrelated` and chat's
  conversation/streaming entry points repair feature selection and packet ownership.
  A packet is bound to a digest of the current question, recent user-turn hints and
  effective policy. The full suite exposed a prior packet leaking into later
  philosophical answers; a new regression covers that boundary.
- `core/phases.py: _medical_text, _emergency` distinguish software uses of
  unconscious/unresponsive from human emergency reports. Real human reports keep
  priority; this is not a general exemption for philosophical wording.
- `core/claim_evidence.py: _privacy_assertion, privacy_overclaim` distinguish
  negated or qualified statements from asserted absolute privacy guarantees.
- `core/claims.py: _reference_claim, reference_notes` no longer treat a general
  requirement that AI claims need evidence as proof this reply used a reference.
  Explicit first-person provenance, claimed review and invented reference IDs
  remain checked. Diagnostics identified the earlier withdrawal as
  EXECUTION_REFERENCE rather than the emergency or privacy checker.
- `core/source_analysis.py: collect, native` reuse the existing fingerprint/AST
  pipeline for guardian/provider topics and application-generated core source maps.
  File/function/line declarations and displayed edges come from checked source.
  Missing witnesses produce a scoped UNKNOWN, not invented absence. These maps
  are static, not proof a feature ran or complete dynamic codebase understanding.
- `core/self_inspection.py: stream` uses the exact selected managed adapter for
  permitted model explanations, with normal cloud consent/offline/project gates.
  Known structural maps are answered by application code and labeled no AI model.
  No cloud failure silently substitutes Ollama. Public-source collection is local.
- `core/capabilities.py: turn_block` and chat provider/entry points supply current
  application-versus-model, policy, tool availability, source and backend state.

## Opt-in diagnostics

Run `self diagnostics on`, reproduce a turn, then `self diagnostics show`.
Use `self diagnostics off` to disable and clear it. The bounded in-memory trace
records selected/attempted/responding backend, intent, route, policy, offered
operations, tool results/denials, returned source references, guardian triggers
and modifications. It retains no prompt text, source excerpts or tool arguments;
credential-shaped values are redacted. It adds no disk log. Existing chat-history
settings still apply separately. Implemented through `core/last_turn.py`, the
existing evidence log, tool runner and native command dispatcher.

## Measurements and scope

The exact incident transcripts were not supplied. Twelve reconstructed cases and
three privacy assertions were frozen before baseline results, in
`bench/self-inspection-worksheet.json`. Actual installed-source reads and real
Qwen3 4B application calls ran offline using disposable homes, never owner records.

| Frozen behavior | Before | After measured repairs |
|---|---:|---:|
| Authorized inspection established | 4/5 | 5/5 |
| Explicit read/tool denials retained | 2/2 | 2/2 |
| Software/philosophy emergency false positives | 2 | 0 |
| Genuine emergency cases recognized | 2/2 | 2/2 |
| Negated/qualified privacy false positives | 2 | 0 |
| Genuine absolute-privacy warning retained | 1/1 | 1/1 |

The real baseline philosophical reply displayed the Poison Control/911 banner;
post-fix runs did not. The leading no-retention source request changed from an
ACCESS DENIED response to checked, read-only source declarations. A separate
frozen eight-case reference-claim set improved from3/8 to8/8, retaining all three
unsupported current-answer provenance warnings. These are scoped regression
measurements, not a new AI accuracy score.

Final isolated Windows source suite: **2,871 passed, 15 skipped, 19 passing
subtests** in445.22s (`SELF-INSPECTION-review-ready.xml`). The final run includes
permission boundaries, native and deliberately model-generated source answers,
source-packet ownership, genuine emergencies, current-answer provenance, provider
parity fixtures, notebook/memory/calculations, portable workflows and offline
startup. Earlier failing receipts are retained for audit; the final receipt has
zero failures/errors. No application code changed after this complete run.

The latest recorded real-Qwen philosophical reply had neither the emergency
banner nor the unrelated execution-reference withdrawal. Its broader narrative
quality is not an accuracy claim. Core source maps now use checked application
declarations and AST edges rather than that variable narration.

Receipts are in `bench/results/SELF-INSPECTION-*`; the paired probes preserve
their frozen fixture digest, source hashes, actual responses and provenance.
Known core source maps use application code so free-form model narration cannot
invent their route. A separate real managed-Qwen source call confirmed transport,
but its draft misread a regex/route; it is preserved as a limitation, not counted
as successful source understanding.

OpenAI parity and privacy/error paths use synthetic adapters. No live OpenAI
account/key was supplied or used, and no live cloud success is claimed. At the original review checkpoint, native packaging and Mac/Linux runs were pending;
U113 native and hosted results are now recorded in the release verification. Qwen's
broader philosophical narration remains variable; passing bounded checks is not
a guarantee every generated statement is true. No station, model-weight,
unrelated-profile, notebook or owner-data changes were made.

The owner authorized commit, push and release on October 30, 2026. The reviewed
repairs have been integrated onto current main for U113; source inventory is rebuilt
for the versioned snapshot. Native packaging and GitHub publication are now verified
by the U113 release receipts. U111/U112 website and release evidence are retained.
The original incident transcripts remain unavailable.

Repeat safely with the locked project interpreter:
`python scripts/self_inspection_worksheet.py <new-receipt-label>`.
The driver redirects all stores before importing Cursiv, enables offline mode,
uses loopback Ollama only, and refuses to overwrite a previous receipt.

[Frozen cases](../bench/self-inspection-worksheet.json),
[before](../bench/results/SELF-INSPECTION-before.json),
[final real/native probes](../bench/results/SELF-INSPECTION-review-ready.json),
[final full suite](../bench/results/SELF-INSPECTION-review-ready.xml).

## U113 release completion

Owner-authorized source and native packages are published as U113; exact-main multiplatform counts, signature/readback receipts and boundaries are in [U113 release verification](U113-RELEASE-VERIFICATION.md). Earlier review-only status above records the measurement checkpoint. Website production verification is a separate receipt.
