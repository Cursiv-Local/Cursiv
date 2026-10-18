# Cursiv Truth Benchmark results

Same cases every release (bench/truth_cases.py), scored by code (bench/scoring.py). Higher is better except Unsupported.
Compare rows only within the same suite version. Failure causes for each run: `FAILURES-<release>.md`.

| Release | Suite | Model | Date | Cases | Accuracy | Unsupported claims | Unknown handling | Traps / false premises | Asks when unclear | Safety | Avg words | Avg s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U61 | 1.0 | qwen3:4b-instruct | 2026-10-17 | 116 | 91.7% | 2.6% | 100.0% | 100.0% | 100.0% | 100.0% | 157 | 35.9 |
