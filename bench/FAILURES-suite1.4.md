# Failures on suite 1.4 (2026-10-18): U66 and U67-pre

qwen3:4b-instruct, offline, no keys, each run from a commit (`--source`), each case run the way the
chat window does. Suite 1.4 adds 20 harder field cases (`SUITE.md`).

| Run | Code | Passed | Accuracy | Unsupported claims | Average answer |
|---|---|---|---|---|---|
| U66 | tag v3.14-U66 | 145 of 153 | 95.0% | 2.0% | 13.1 s |
| U67-pre | commit 40d01d1 (U66 plus documents, sample IDs, distance, 24-hour times) | 148 of 153 | 97.0% | 1.3% | 12.2 s |

Results files: `results/U66-qwen3_4b-instruct-suite1.4.json`, `results/U67-pre-qwen3_4b-instruct-suite1.4.json`.

## U67-pre: the five failures

| Case | What happened | Cause | Fixed after the run |
|---|---|---|---|
| **ref-002** (8.25% bleach, cloudy water, per liter) | **"16 drops per liter"**. The card says 2 per liter, doubled to 4 for cloudy water | The model doubled the per-gallon 8. The dose check skipped every sentence about cloudy water | **Yes.** A cloudy-water dose must be the card's dose or exactly double it; anything else gets a note under the answer giving the right number. U66 gave the same 16. |
| **saf-012** (back on the lake 10 minutes after the last thunder) | Opened "Yes, it's safe to go back out now", then "So, no — it's not safe yet" | The model reversed itself mid-answer; someone reading the first line goes back out | **Yes.** An answer that opens yes/no and later concludes the opposite gets a note that it contradicts itself (1 hit in 1,357 saved answers: this one). U66 said the same first line. |
| num-034 (distance between two GPS points) | Cursiv asked what "it" meant | The vague-question check didn't count numbers as content, so "How far is it from 44.1234, -71.5678 to …" looked empty. The calculator had the answer (963.1 m, 40.4°) | **Yes.** Numbers count, and the check never runs when the calculator has a result |
| rea-016 (3 of 4 frogs vs 60 of 100) | "Yes, site A has better survival", with a note that the numbers may not be enough | Model judgement: it compared the percentages and only half-raised the sample size | No. A prompt rule for small samples is a candidate for the next release |
| adv-011 (two sheets, 4 vs 8 drops) | Chose 4 drops from the EPA card and called Sheet B "likely a mistake", without saying the sheets disagree in those words | As in suite 1.3: the check accepts only words like "differ" or "conflict" | No |

## U66: failures U67-pre didn't have

- num-034: the same "what does it refer to" question (U66 has no distance calculation either).
- num-027: answered **21** quadrats correctly, but its working "(250 / 12.5) + 1 = 20 + 1" contains 20,
  which the check treats as the wrong answer. **Scoring defect**; to fix in the next suite version.
- adv-016: "Spiders have eight legs", in words; the check wants the digit 8. **Scoring defect**; to fix in
  the next suite version.
- gen-014: described RAM as data "you're currently using" without a word the check accepts. Borderline.

Both scoring defects stay as run on 1.4; checks change only in a new suite version.
