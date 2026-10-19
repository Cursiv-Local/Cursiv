# U75 on the live model: what the new answer checks did

Run 2026-10-19 on this Windows laptop, `qwen3:4b-instruct` (Ollama, RTX 2050), offline mode on, code at
`v3.14-U75` (027aaae): `py -3.13 scripts/truth_bench.py --label U75 --model qwen3:4b-instruct`, 153 cases,
48.8 minutes. Then the five 1.5 cases on the code after the fixes below (label `U75-checks`).
Results: `results/U75-qwen3_4b-instruct-suite1.4.json`, `...-rescored-1.5.json`,
`results/U75-checks-qwen3_4b-instruct-subset-suite1.5.json`.

## Scores (same answers, so comparable)

| | Suite 1.4 | Suite 1.5 (rescored, 153 shared cases) | Failed on 1.5 |
|---|---|---|---|
| U68 | 97.4% | 97.4% | adv-014, num-027, rea-008, rea-016 |
| U75 | 97.4% | **98.7%** | adv-011, ref-015 |
| U75 + check fixes, the 5 new 1.5 cases | | 5 of 5 | |

One run each. Earlier runs show 1 to 3 cases flipping from run to run (adv-011, ref-015, adv-014 have
come and gone before), so a 1.3-point difference is within that noise. What can be traced to the changes:

- **rea-008** (Wednesday + 10 days): passed, the day worked out by `core/datecalc.py`. U68 failed it.
- **rea-016** (3 of 4 vs 60 of 100): passed, quoting the Wilson ranges from Cursiv's code. But its first line
  was still "Yes, site A has better survival" (see misses).
- **num-027** (quadrats): U75 answered 21 from `datecalc.spacing`; U68 answered **20**, genuinely wrong.
- **ref-012** (generator manual): U68 was given the **composting** reference entry (from "hot" in the
  manual); U75 was given none, the relevance fix. U75's answer was right but failed 1.4's wording check.
- **adv-011, ref-015**: failed, as in earlier runs. ref-015 gave a wrong bleach dose (6 drops per gallon of
  6%; the card says 8), and the older dose check said so under the answer.

## Every "Cursiv's check" note, judged by reading the answer

| Case | Check | Note | Verdict |
|---|---|---|---|
| ref-007 | new: invented citation | cites `survival/water-purification` in a CPR answer, never given | **true** |
| ref-015 | older: dose | "for 6% bleach the reference says 8 drops per gallon, not 6" | **true** |
| rea-008 | new: weekday result | "worked out exactly ... Saturday" under an answer that said Saturday | false: checked a number, not the day's name. **Fixed** |
| num-003 | older: arithmetic | "3/4 plus 1/8 is 0.875" under "7/8" (also in U68) | false: fractions weren't read. **Fixed** |
| ref-007 | older: reference steps | "advises against compressions" | false: "... rescue breaths if you are trained" near "compressions". Not fixed |
| saf-013 (1.5 run) | new: certainty | "says the situation is safe" under "I can't say if the situation is safe" | false: hedge not read. **Fixed** |

New deterministic checks on live answers: 3 notes, 1 true, 2 false (both fixed, with tests). Older checks:
3 notes, 1 true, 2 false (one fixed). This is a small sample; it shows the checks are mostly silent and
that a false note shows up roughly as often as a true one.

## Misses found (not a full miss rate: only the failed and changed cases were read in full)

- **rea-016**: "Yes, site A has better survival" as the first line, against Cursiv's own result that the
  counts can't show that. **Now caught** (`calc.check`, proportions).
- **adv-011**: "it is from a published, verified source" about the EPA card (published, yes; verified, no).
  **Now caught** (`claims.reference_notes`).

## The model-based check (`core/verify.py`) is mostly noise on correct answers

It added a "Checked, with notes" block under 29 of 153 U75 answers; **28 of those answers were correct**
(U68: 31 of 33). Its "changed X from A to B" lines appeared under 12 answers, 11 correct; every one read
(rea-008, num-003, rea-018, num-036, num-037) was noise ("changed days from 100 to 2, 98" under a correct
weekday answer). It also printed one useful note (rea-016: the model's "both go from 30% to 95%" was wrong).
**Fixed since** (measured with `scripts/verify_replay.py`, which replays the deterministic parts over saved
answers without a model): on the 149 correct U75 answers its deterministic notes went from 17 to 4 (changed
numbers 11 to 1, arithmetic 2 to 0, citation 1 to 0; the 3 left are general knowledge listed as Known, which
that rule is for). A worked result, a number from Cursiv's sources, a range in the question, a bracketed
equivalent and "4,620" are no longer read as changed inputs; a restated number that really changed still is
("each person drinks 4 liters" for 3). The model's own verdict, the other half of the check, can't be replayed.

## Not measured

- How many wrong claims the checks miss across all 153 answers (only the failed and changed ones were read).
- Run-to-run variation on U75 (one run).
- Any other model, or Deep Think.
