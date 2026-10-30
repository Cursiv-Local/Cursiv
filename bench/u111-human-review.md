# U111 independent human review (unscored)

No independent human review has been performed. The JSON harness leaves
`human_review` null; deterministic checks do not constitute scientific accuracy
scores. The coding assistant's qualitative observations are labeled separately
in docs/U111-VALIDATION.md.

Choose a named receipt and record reviewer/date/model ID before assigning scores.
Use 0 (fails), 1 (partially meets), 2 (meets), or N/A. Evaluate grounding (given inputs,
sources, hypotheses and assumptions), conversation constraints/history, requested
format/tone, and truthful authorized actions. Never count native zero-model answers
as model intelligence. An honest failure message is not a successful creative post.

Receipt: ______ Reviewer: ______ Date: ______ Provider/model: ______

| Case | Grounding | Constraints/history | Instruction/format | Actions/provenance | Notes |
|---|---|---|---|---|---|
| roast | | | | | |
| roast-restricted | | | | | |
| promotional | | | | | |
| mars | | | | | |
| radiation | | | | | |
| water | | | | | |
| station-offline | | | | | |
| sample-count | | | | | |
| self-review | | | | | |
| cross-topic | | | | | |
| record (native preview) | N/A | | | | |
| recall (native) | N/A | | | | |

For the20 original, previously seen science prompts, review their raw generations
and warnings separately. A warning count is not a risk-detection or correctness
score; that set has no negative controls. Compare the same prompts/history/settings
between installed local models with scripts/u111_bench.py --model <installed-ID>.
Cloud inference and other models have not been live-tested in this worksheet.
