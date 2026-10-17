# Truth Benchmark suite versions

The cases (`truth_cases.py`) and the checks (`scoring.py`) are frozen per suite
version. `tests/test_bench_scoring.py` compares their SHA-256 (line endings
normalized) with the current version below and fails if either file changed
without a new version here.

To change a case or a check:
1. Add a new version section below: what changed, which case ids, and why.
   A wrong expected answer or a scoring defect is a valid reason; a release
   failing a case is not.
2. Put the new hashes in the version line (`py -3.13 bench/suite_hash.py`).
3. Re-run the previous release on the new suite too, so the comparison stays fair.
   Results are only compared within the same suite version.

## Versions

<!-- current: 1.0 cases=5ae6600b5971e4624811e03f77801dbc7ab9a8120a1b576d819b400ddeab0922 scoring=0c8d0d74db2bd7747431a72a6d215a2ddb4c9a3f96316b3a7cf4dd17608037f2 -->

### 1.0 (2026-10-17)
116 cases in 9 categories. The U61 baseline was run on this version.
