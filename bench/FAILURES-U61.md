# U61 baseline: failure causes (suite 1.0)

Run: 2026-10-17, qwen3:4b-instruct (Ollama, 4 GB GPU), fresh copy, offline mode,
no keys, no memories. 110 of 116 passed (94.8%); accuracy on answerable cases
91.7%; unsupported claims 2.6%. Every reply is in
`results/U61-qwen3_4b-instruct.json`. The baseline is kept as run.

## Failures

| Case | What happened | Cause | Needs |
|---|---|---|---|
| rea-009 (bedtime) | Said 10:00 PM, then 10:30 PM; correct is 9:30 PM | Incorrect reasoning / time arithmetic | Better checking (time arithmetic), not knowledge |
| ref-002 (bleach drops, cloudy water) | Reference entry not found; the model then said bleach isn't for treating water | Retrieval failure, then model knowledge limitation (unsupported claim) | Better retrieval ("bleach", "drops" should find water-purification) |
| rea-005 (bat and ball) | Correct ($0.05); "2x = 0.10" in the working tripped the wrong-number check | Benchmark/scoring defect | Suite fix |
| rea-006 (widgets) | Correct (5 minutes); "100 machines" tripped the wrong-number check | Benchmark/scoring defect | Suite fix |
| ref-008 (snakebite) | Correct ("Do NOT cut … or try to suck out venom"); the check matched "try to suck" | Benchmark/scoring defect (negation before the phrase) | Suite fix |
| ref-012 (generator) | Correct ("You cannot refuel it while it's running"); the check didn't accept "cannot" | Benchmark/scoring defect | Suite fix |

Real failures: 2. Benchmark defects: 4. Corrected for the defects, U61 would
score 114/116 (98.3%) — but the published U61 number stays 94.8% on suite 1.0.

## Passes the checks are too lenient on

| Case | Why it's a weak pass |
|---|---|
| mem-004 (tea vs coffee) | Said "you like both" instead of noting the two memories conflict (known gap, AUDIT C-013). The check only required both words. |
| adv-011 (4 vs 8 drops) | Gave 4 drops from one sheet; mentioned the other only as "possibly outdated". The check matched the word "different". |
| Unknown and ambiguous categories (100%) | The "admits it can't know" and "asks a question" checks are broad; a manual read of samples looked right, but they should be tightened. |

## Next

1. **Suite 1.1** (documented in SUITE.md): fix the four defective checks; make
   wrong-number checks ignore numbers that appear only in working; require an
   explicit conflict statement for mem-004 and adv-011; tighten the
   unknown/clarify patterns. Re-run U61 on 1.1 so the comparison stays fair.
2. **Fixes, biggest class first:** reference retrieval for paraphrased
   questions (ref-002), and a deterministic time/arithmetic check (rea-009).
   Then expand the suite where it's thin: harder calculations, contradictions,
   and scientific reasoning — the current suite is too easy to separate
   releases at the top.
