# U106 baseline findings — 2026-10-26

Application baseline: `main` at `79a1636`. The owner requested tests before application changes.
Application code, release versions and website are unchanged. No commit, push, merge, tag or release was performed.

## Automated checks

| Check | Observed result |
|---|---|
| Existing full suite | 2,200 passed, 15 skipped; 369.74 s |
| Mandatory USB gate (subset of suite) | 45 passed, 2,172 deselected; 79.55 s |
| New memory probes plus code-map checks | 5 passed; 7.79 s |

JUnit evidence is in `bench/results/U106-baseline-tests.xml`, `U106-baseline-usb.xml`,
`U106-memory-baseline-tests.xml` and `U106-final-baseline-probes.xml`.
The full-suite skips are Mac Keychain (1), supplied Vosk zip verification (1), and opt-in self-knowledge
live-model tests (13). Those opt-in tests were not enabled by the separate live evaluations below.

The two new memory probes revisit 24 conversations six times (144 switches), check that notes stay with
their conversation, repeat a fact and pending suggestion without duplication, confirm one suggestion,
check that repeating a fact cannot upgrade its origin, and repeatedly export the readable memory copy.
They also construct the actual Qt memory dialog, inspect its rendered date/origin/family rows, search,
and attempt a duplicate addition. All storage is synthetic and isolated. The Qt screenshot was visually
inspected: `bench/results/U106-memory-dialog.png`. Offscreen Qt required explicit loading of Segoe UI,
as an existing repository test already does. This does not establish an installed-desktop rendering defect.
The repeated-conversation probe uses deterministic summaries; it is not a long live-model conversation test.

## Real Ollama answer evaluation

Before reading earlier results, froze 12 fresh risk questions and 6 controls in
`bench/overconfidence/u106_cases.py`. Each of three installed models answered all 18 questions through
the real Cursiv `chat()` path, offline, with separate throwaway homes and settings. The harness uses the
existing overconfidence benchmark scorer. Installed-model records/digests, question hash, full answers,
timings and per-answer checkpoints are retained in `bench/results/U106-overconfidence-*-baseline.json`.
Llama's installed tag is `llama3.1:latest`; Ollama confirmed 8.0B parameters.

| Model | Risk confidence labels: overconfident / borderline / fine | Existing note on risk answers | Existing note on controls | Observed median seconds |
|---|---|---|---|---|
| Qwen3 4B Instruct | 2 / 2 / 8 | 1/12 | 0/6 | 10.86 |
| Llama 3.1 8B | 0 / 1 / 11 | 0/12 | 0/6 | 22.1715 |
| Gemma 3 4B | 0 / 0 / 12 | 0/12 | 0/6 | 7.7165 |

These are manual confidence labels by Codex, not independent review or comprehensive factual accuracy
scores. All six controls per model avoided an overconfidence note. Qwen's check caught one of its two
overconfident verdicts. Detection recall cannot be estimated for Llama/Gemma because their runs contain
no positive cases under this narrow verdict rubric. Timings include model loading/checking and concurrent
test activity; they are not a controlled speed comparison. One run per model is a small sample.

Concrete findings:

- Qwen declares 31% soil moisture too low and supplies a universal threshold without the soil, crop,
  probe basis or a retrieved reference. The existing overconfidence note misses this answer.
- Qwen calls 68 dB typical for a site without site history or measurement settings. The note catches it.
- Gemma invents its own model identity in **10/18 answers**, contradicting the application footer and
  installed model record. Examples include Mistral, Audioscape and StreamFlow. The narrow scientific
  confidence labels above do not count those claims as correct.
- Optional checks produce misleading notes too: Qwen's offer of “a better study” is treated as a missing
  citation; Gemma's explicitly Assumed line is criticized as an assumption presented as fact.

Per-answer labels and reasons: `bench/results/U106-overconfidence-labels.md`.
Measured counts also appear in `bench/overconfidence/RESULTS.md`.

## U100 science reproductions

A separate four-question set was frozen before running it on real Qwen. All four completed.
Evidence: `bench/results/U106-overconfidence-science-qwen3-baseline.json`.

- Exact existing audit prompt about two thermometers 10 cm apart: calls a 0.4 C difference “plausible
  and common,” gives generic instrument precision, and asserts a physical effect without specifications
  or a stated medium. No overconfidence note appears.
- Same-water normality question: declares 0.4 C “not normal” for reliable instruments without their
  specifications. The existing overconfidence note does appear. This protection is already present.
- Hypothetical shade experiment: labels the exercise hypothetical and receives the existing invented-number
  note. The old unlabelled-results-table failure did not reproduce in this run. A separate method problem
  appears: it proposes ruler penetration depth as a moisture measure without a validated relationship.
- No-data experiment design: uses one container per condition, optional repetition, a subjective moisture
  comparison and different locations, then offers a causal conclusion. No design-specific check appears.

No science-check implementation changed; no before/after improvement is claimed.

## Paraphrase diagnostics and coverage

Small deterministic synthetic probes, with no model calls:

- Reference retrieval: **4/4** direct topic-name questions find the expected entry; **0/4** semantic
  paraphrases do. Topics are Newton's second law, photosynthesis, energy conservation and the nitrogen cycle.
- Memory conflict detection: catches **1/1** direct numeric conflict, misses **3/3** paraphrased conflicts,
  and correctly leaves **1/1** compatible preference unflagged.

Full questions and outputs: `bench/results/U106-paraphrase-baseline.json`. These are diagnostics rather
than a general accuracy estimate. Existing reference-exclusion tests passed in the full suite.
No reference or safety content changed.

Direct problem-report and chat confirmation-card tests already exist. A search found no direct tests
of `launcher/login_recovery.py`. The requested cascade verification, paraphrase improvements, export
sidecar, filesystem matrix, performance profiling, profile form, settings changes and core regrouping
have not been implemented. No real drive-removal/full-drive matrix, physical Mac test, installed-app
walkthrough, or long live-model memory conversation is claimed.

## Decision

Owner follow-up: Gemma-specific answer issues are outside the proposed fixes because the owner plans to
remove Gemma as an option. Prioritize `qwen3:4b-instruct`, already the default model and first default
preference in source. Retain Gemma's baseline evidence as measured; no model-option or user-setting changes
have been made.

The baseline suite passes. Measured answer and paraphrase issues justify targeted follow-up work;
there is no basis to declare all functionality complete. Per the owner's latest direction, stop at this
reviewable baseline before application edits. Keep the existing overconfidence rule unchanged until a
separate held-out before/after evaluation establishes a benefit. Reserve new untouched questions before
tuning: this baseline set has now been observed.

Execution issues were resolved with isolated temporary storage and normal local-model access. There are
no commands still running and no unresolved execution blockers. Original excluded paths were untouched.
