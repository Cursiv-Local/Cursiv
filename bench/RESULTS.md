# Cursiv Truth Benchmark results

Same cases every release (bench/truth_cases.py), scored by code (bench/scoring.py). Higher is better except Unsupported.
Compare rows only within the same suite version. Failure causes for each run: `FAILURES-<release>.md`.

| Release | Suite | Model | Date | Cases | Accuracy | Unsupported claims | Unknown handling | Traps / false premises | Asks when unclear | Safety | Avg words | Avg s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| U61 | 1.0 | qwen3:4b-instruct | 2026-10-17 | 116 | 91.7% | 2.6% | 100.0% | 100.0% | 100.0% | 100.0% | 157 | 35.9 |
| U63-pre | 1.1 | qwen3:4b-instruct | 2026-10-18 | 125 | 93.6% | 0.8% | 63.2% | 82.4% | 87.5% | 100.0% | 89 | 24.5 |
| U61 | 1.1 | qwen3:4b-instruct | 2026-10-18 | 125 | 89.7% | 3.2% | 94.7% | 100.0% | 100.0% | 60.0% | 157 | 32.3 |
| U63-pre (rescored) | 1.2 | qwen3:4b-instruct | 2026-10-18 | 125 | 94.9% | 0.8% | 94.7% | 94.1% | 87.5% | 100.0% | 89 | 24.5 |
| U61 (rescored) | 1.2 | qwen3:4b-instruct | 2026-10-18 | 125 | 89.7% | 0.8% | 94.7% | 94.1% | 87.5% | 90.0% | 157 | 32.3 |
| U65 | 1.2 | qwen3:4b-instruct | 2026-10-18 | 125 | 94.9% | 0.8% | 94.7% | 94.1% | 100.0% | 100.0% | 87 | 12.9 |
| U65 | 1.3 | qwen3:4b-instruct | 2026-10-18 | 133 | 93.0% | 0.0% | 100.0% | 94.1% | 100.0% | 100.0% | 86 | 11.7 |
| U66 | 1.3 | qwen3:4b-instruct | 2026-10-18 | 133 | 100.0% | 0.0% | 100.0% | 94.1% | 100.0% | 100.0% | 79 | 11.8 |
