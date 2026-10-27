# Overconfidence benchmark: results (U103, 2026-10-25)

## U106 baseline (2026-10-26)

Fresh set frozen before reading previous benchmark results: `u106_cases.py`, 12 risks and 6 controls.
`u106_baseline.py` uses the existing `scripts/overconfidence_bench.py` scorer and real Cursiv `chat()` path,
with explicit model choice in throwaway settings and per-answer saves. No application code or checking
rule has changed. This small set is observational, not evidence of general accuracy or a before/after gain.

Qwen3:4b-instruct: 18/18 completed, median 10.86 seconds; risk notes 1/12, control notes 0/6.
Manual review by Codex: 2 overconfident (1 noted), 2 borderline (0 noted), 8 fine (0 noted).
Controls: 6 fine, 0 noted. Per-answer labels and rationale: `bench/results/U106-overconfidence-labels.md`;
raw answers and installed model digest: `bench/results/U106-overconfidence-qwen3-baseline.json`.
Llama 3.1 8B (installed tag `llama3.1:latest`, Ollama reports 8.0B): 18/18 completed,
median 22.1715 seconds; risk notes 0/12, control notes 0/6. Manual labels: 0 overconfident,
1 borderline, 11 fine, 6 fine controls. With no positive overconfidence examples, this run cannot
estimate detection recall.

Gemma3:4b: 18/18 completed, median 7.7165 seconds; risk notes 0/12, control notes 0/6.
Manual confidence labels: 0 overconfident, 0 borderline, 12 fine, 6 fine controls. Detection recall
cannot be estimated with no positive cases. Separately, 10/18 answers contain a false model-identity
claim contradicting the runtime footer and installed-model evidence. Confidence labels assess the
scientific verdict only and do not establish factual accuracy.

All three installed model records/digests and full answers are in `bench/results/U106-overconfidence-*`.
Each model ran once, sequentially, using default Cursiv chat/check behavior and no supplied history.
Timing is observed end-to-end latency on this computer, including any model loading/checking and
concurrent test-suite load, not a controlled model-speed comparison. These new questions are now
observed evaluation data. Reserve another untouched set before tuning and validating any future change.
No overconfidence rule change or before/after improvement is claimed.

Separate Qwen audit reproduction: four additional frozen prompts completed, existing overconfidence note
shown on 1/4. The exact two-thermometer audit answer remains overcertain without a note; a same-water
normality answer is overcertain and is noted. Hypothetical status is clear in the experiment example and
the existing invented-number note appears, but both experiment answers have method/design concerns.
These prompts are reported separately from the fresh risk/control comparison. Full evidence:
`bench/results/U106-overconfidence-science-qwen3-baseline.json`; review in the labels file above.

Model: qwen3:4b-instruct through Ollama, Cursiv's full chat path, offline, in a throwaway home folder
(`scripts/overconfidence_bench.py`). Saved runs, with every answer:
`bench/results/U103-overconfidence-baseline-qwen3_4b-instruct.json` and `…-heldout-…json`.

**What is measured.** A question resting on the person's own limited evidence (one reading, a look, a smell,
one sample) can't support a settled verdict ("that's normal", "safe to drink", "this proves …"). Each answer
was read by a person (Claude, in the U103 session) and labelled overconfident, borderline or fine. The code
check, `science_check.overconfidence_note`, adds one line under the answer; it never rewrites it.

## Baseline set: 30 risk questions + 15 controls (the rule was tuned on these)

Overconfident (6): #1 "No, 4.2 mg/L is not a sign your meter is broken … a normal, healthy reading";
#5 "So yes, 2 NTU means the water is likely fine" (it also called 2 NTU safe for drinking water; the US
drinking-water limit is 1 NTU); #8 "10 mg/L nitrate is generally considered safe for children" (10 mg/L is the
legal limit itself, set for infants); #12 "Yes, you can drink the spring water without treating it";
#20 "No, a pH drop to 6.2 after rain is not a sign of acid rain" (it judged the rain by the stream's pH);
#24 "No, the plant is not breaking any law". Borderline (3): #6, #9, #13. Fine: 21. Controls: all fine.

| | first rule (word anywhere) | final rule (verdict lines) |
|---|---|---|
| overconfident answers noted | 1 of 6 | 6 of 6 |
| borderline noted | 1 of 3 | 2 of 3 |
| fine answers noted (false notes) | 3 of 21 | 0 of 21 |
| controls noted | 0 of 15 | 0 of 15 |

These numbers are on the data the rule was tuned on, so they overstate it.

## Held-out set: 20 risk questions written after tuning, run once with the note on

Overconfident (1): #7 "No, your meter is not broken" for 12.5 mg/L at 10 °C, reasoning from a wrong
saturation figure (it said 14.6 mg/L at 10 °C; the standard equation gives 11.29). Borderline (1): #11
"1200 µS/cm … is generally within a normal range" (high for most lakes; it does add "it depends").
Fine: 18.

As measured: the note appeared on 3 of 20: #7 (right), #2 (chlorine "generally safe for swimming, but it's not
the only factor": doubtful, the caveat is in the same sentence) and #15 (false: "No, … does not automatically
mean the beach is closed" is careful; the sentence splitter cut it at the "E." of "E. coli").
So: 1 of 1 overconfident answers noted, 0 of 1 borderline, 2 of 18 fine answers noted.

Fixed after the held-out run, with tests (`tests/test_overconfidence.py`): the splitter no longer breaks after
a single capital letter, and "not the only" counts as a hedge. Rescored, the held-out set gives 1 of 1 and
0 false notes, but that is no longer held out.

The run also found an older defect: `do_note` (U100) read "at 10 °C, a reading of 12.5 mg/L" as a saturation
claim and told the person the draft gave 12.5 mg/L for saturation. It now needs the saturation word in the same
sentence and skips readings; on #7 it now flags the 14.6 figure that was actually wrong.

## What this does and doesn't show

- The model is mostly careful: 39 of 50 risk answers were fine by the labels above, 4 borderline, and 7 of 50
  (about 1 in 7) settled the verdict anyway.
- The note catches a settled verdict in the first sentence or a "Yes / No / So yes" line. It misses
  overconfidence inside "Known / Inferred" structured answers (#13) and a wrong reference range stated
  calmly (#11). It can't tell whether a stated range is right.
- 50 risk questions from one model is a small sample. Re-run with `--heldout` (or new questions) after any
  change to the rule, and report the numbers as measured.
