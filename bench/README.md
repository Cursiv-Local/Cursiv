# Cursiv Truth Benchmark

A fixed set of questions run against every release, so "Cursiv got better" is a
measurement, not a feeling.

- `truth_cases.py`: the cases, in nine categories (general, reasoning, numerical,
  reference, memory, ambiguous, adversarial, safety, unknown). Don't change a
  case's checks between releases; add new cases with new ids.
- `scoring.py`: the checks. Code only, no AI judge: the right answer or number,
  claims that would be invented, admitting it can't know, asking when the
  question is unclear, using the right reference entry. Cursiv's status lines
  (the reference card, "Answered by") and check notes aren't scored.
- `results/`: every run's replies and failures. `RESULTS.md`: one row per run.

Run from the exact release tag (time varies with model, hardware and checks):

    py -3.13 scripts/truth_bench.py --source v3.14-U85 --label U85 --model qwen3:4b-instruct

The run uses a fresh copy of the source, an empty home folder, offline mode on
and background learning off, so results don't depend on this computer's memories
or keys.

Metrics: **Accuracy** = passed answerable cases (general, reasoning, numerical,
reference, memory). **Unsupported claims** = cases where the answer contained a
claim the case marks as invented or false. **Unknown handling** = cases where the
honest answer is "I can't know" that Cursiv got right.

## Rules

- **Baselines are kept as run.** `results/` files are never edited. The suite
  (cases + checks) is frozen per version; see `SUITE.md`. Don't change a case,
  an expected answer or a check because a release failed it. A real defect in a
  case is fixed in a new suite version, with the reason written down, and the
  earlier release is re-run on the new version so comparisons stay fair.
- **Every failure gets a cause before a fix**, recorded in `FAILURES-<release>.md`:
  - model knowledge limitation
  - retrieval failure (the right reference or memory exists but wasn't found)
  - missing reference material
  - incorrect reasoning
  - calculation or unit error
  - unsupported claim (said something the evidence doesn't support)
  - uncertainty-handling failure (should have said it can't know, or asked)
  - safety or applicability failure
  - benchmark or scoring defect
  Note which ones need new knowledge, and which need better retrieval,
  reasoning, checking or clarifying questions.
- **Fix the biggest failure classes first**, then re-run the unchanged suite.

## Current result and scoring limits

[U85 raw answers and failures](FAILURES-U85.md) record 153/158 passes, below
U84's 156/158. A passing allergy-memory answer begins with unsafe advice; the
current pattern scorer misses it. Preserve the original result and version any
scorer correction. A category score does not certify the rest of an answer.

## When a fix counts as done

- the original failing case passes,
- its neighbors (same category or same cause) still pass or improve,
- no unexplained drop in any other category,
- the result reproduces on a second run,
- the fix and what it doesn't cover are written down in the changelog.

Don't grow reference material into an encyclopedia. First show Cursiv uses a
small, known body of knowledge reliably; add depth where the benchmark shows a
need.
