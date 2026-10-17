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

Run (takes about 30 s per case on a 4 GB graphics card):

    py -3.13 scripts/truth_bench.py --label U62

The run uses a fresh copy of the source, an empty home folder, offline mode on
and background learning off, so results don't depend on this computer's memories
or keys.

Metrics: **Accuracy** = passed answerable cases (general, reasoning, numerical,
reference, memory). **Unsupported claims** = cases where the answer contained a
claim the case marks as invented or false. **Unknown handling** = cases where the
honest answer is "I can't know" that Cursiv got right.
