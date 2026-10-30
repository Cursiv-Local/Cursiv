# U111 reliability — validation

Unreleased working branch `codex/u111-reliability`, based on U110 main
`ee9b1cf0b99e723d5eb21c8ab257cbc70de497a2`. No commit, push, tag, installer,
website publication or release is part of this worksheet. Continue from
[U111-HANDOFF.md](U111-HANDOFF.md).

## Evidence scope

The owner confirmed the original full transcripts and exact roast prompts are
unavailable. [The frozen corpus](../bench/u111-reliability.json) reconstructs the
reported situations and labels that origin. It is a regression corpus, not a new
blind model benchmark. Tests use synthetic stores; real-Qwen receipts observe
actual Ollama requests separately. No paid/cloud generation was run.

Baseline: [18 contracts](../bench/results/U111-regression-before-expanded.xml),
15 failed/3 passed in23.10s. These are contract failures, not15 independent bugs.
The earlier smaller set accidentally treated a short notebook error as a length
success; the expanded baseline uses an unrelated robot post to isolate length.
All raw failed/intermediate receipts remain in bench/results/U111-*.

## Status by worksheet priority

| Priority | Status and measured boundary |
|---|---|
| 1 Notebook routing | Fixed for reconstructed prompts and tested variants. Both roasts and promotional text reach chat. Quoted/hypothetical examples are inert. A separate explicit operation retains its confirmation, including quoted notes. |
| 2 Warning domains | Fixed tested lab-advice false positives on planted Mars/radiation verdicts. The actual Qwen baseline did not emit that lab warning, so there is no live false-positive improvement claim for it. Drinking-water caution remains tested. |
| 3 Number provenance | Fixed blanket labeling of supplied scenario values. New numerical values remain unverified assumptions/model-derived quantities unless an actual calculator supplied them; fictional experimental result tables remain labeled. |
| 4 Mission constraints | Bounded explicit connectivity constraints, conditional first-month timing and post-draft checks implemented. Final exact-selection smoke appends the missing conditional timing. General natural-language temporal reasoning remains partial; original transcripts cannot be replayed. |
| 5 Grounding | Added code checks for unsupported mining-source confirmation, authority thresholds and unjustified preference for a conflicting table. Model scientific explanations remain partial, not independently verified. |
| 6 Self-review | Relevant prior excerpt retained through compact prompts; invented direct quotations checked against earlier answers. Live baseline already quoted its prior answer correctly. Paraphrase/semantic history accuracy remains partial. |
| 7 Short writing | Three real final posts are275/171/277 characters with no evidence footer. Under280 enforced; one revision maximum, then only a complete supported prefix or explicit failure. No arbitrary mid-word truncation. |
| 8 Provider/model | Desktop Automatic/exact Ollama/cloud choices plus `model <provider> <ID> :: <question>`. Cloud IDs are user-supplied and validated on send. Explicit selection refuses unavailable/offline combinations; no provider fallback/download. Cloud wire tests are synthetic. |
| 9 4B research | Existing native notebook, calculation, retrieval, memory, workspace, permission/encryption boundaries retained. No new agent, mandatory cloud, paid dependency or model-size requirement. |
| 10 Benchmark | Reproducible local harness records provider/model/digest/available quantization/settings/history/raw generations/usage/time/tool invocations/offline state. Automated structure checks and unfilled human-review fields are separate. |

The live baseline did not reproduce every reported symptom. In particular, its
radiation/Mars answers did not get lab advice, its water answer did not literally
confirm acid mine drainage, and its self-review quoted the available answer. Planted
end-to-end drafts establish the missing checks for those failures; live outcomes
are not relabeled as reproduced original incidents. One initial observation-card
contract could use the old local intent interpreter; the final contract explicitly
forbids inference and proves native confirmation instead.

## Real local model runs

All live runs use installed qwen3:4b-instruct, temperature0, seed42, context8192,
offline mode, optional model review off (deterministic checks remain). Installed
metadata, actual responding IDs and request token usage are in the receipts.
Model availability was checked; no download or alternative model was permitted.
Installed digest `0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0`,
4.0B parameters, Q4_K_M. The model's advertised maximum context is not the benchmark
context: the actual transport used8192. Other models and live cloud IDs are untested.

- [U110 baseline](../bench/results/U111-live-before.json): all12 completed. The two
  roasts and promotional description were intercepted before inference. Cross-topic
  post367 characters including status footers; Mars supplied values labeled invented.
- [First after run](../bench/results/U111-live-after.json): all12 completed; roasts
  reached Qwen, but one length revision still failed. Its failure message is **not**
  a successful creative artifact even though structural length/absence-of-footer
  checks pass. Mars/count reasoning remained partial.
- [Second full run](../bench/results/U111-live-final.json): all12 completed, no execution
  errors. Three posts275/171/277 characters, each one request. Native record preview
  and recall use zero requests. Observation save/query/chain is separately covered
  through the actual desktop Save card and public command route.
- [Final pinning smoke](../bench/results/U111-live-pinning-complete.json): exact
  Ollama selection, roast246 characters/two requests (one rewrite), Mars one request
  with conditional timing and explicit new-number provenance. Record preview and
  traced public notebook retrieval use zero requests. Subsequent small native UI/note
  guards have regression coverage; they do not alter this generation path.

[Paired rules](../bench/results/U111-paired-checks.json) apply U110 and current rules
to identical drafts. On2 planted non-water safety verdicts, lab advice2→0 while
relevant generic uncertainty remains2→2; drinking-water caution remains1→1. The
supplied-input table's blanket warning1→0; invented experimental result table1→1.
These are deterministic checker measurements, not model scientific-accuracy scores.

The original, previously seen20-question `--heldout` science set was rerun twice:
[first](../bench/results/U111-overconfidence-heldout.json),
[final](../bench/results/U111-overconfidence-heldout-final.json), with
[final raw transport/settings/usage](../bench/results/U111-overconfidence-heldout-final-telemetry.json).
Each made20 actual Qwen requests. Notes6/20→5/20; applying both rules to the *same*
first-run drafts also gives6→5, eliminating the cautious “No one can say for sure”
false note. Five remaining noted verdicts settle safety/instrument/closure judgments
from limited inputs. This is the coding assistant's inspection of the raw wording,
not independent human scoring or proof that the five judgments are scientifically
wrong. No controls were included (`0/0`), so a false-positive rate/sensitivity cannot
be inferred. Median total turn times15.7s/12.5s are run observations, not a speed
improvement claim. Final provider/native edge changes do not alter the scored
overconfidence rule; paired scoring uses its final bytes.

Raw Mars reasoning still invents deadlines and sometimes unsound oxygen figures;
new numeric claims are not application calculations. Temporal advice needs the
application's conditional constraint note. None of these receipts establishes
human-level research reasoning or independently confirmed scientific accuracy.
Native zero-model outcomes are not counted as Qwen accuracy.

The baseline's `answered_by` field can retain a previous label on zero-call native
rows; actual HTTP calls and native response text establish those rows' origin. The
current harness records null on such rows. Earlier receipts are not overwritten.

## Tests, safety boundaries and remaining validation

Final isolated Windows source: **2736 passed,15 skipped,19 passing subtests in686.72s**.
Dedicated automated USB: **45 passed,2706 deselected in87.44s**.
[Machine-readable gates](../bench/results/U111-gates.json),
[source JUnit](../bench/results/U111-full-final.xml), [USB JUnit](../bench/results/U111-usb.xml).
The XML total2770 includes the19 additional subtests; it is not2770 regular passes.
All18 original contracts now pass (before15 failures/3 passes); the final suite has
72 new U111 contracts. The earlier source run was intentionally stopped around41%
before the last provider boundary changes and is not a passing receipt.
Final focused provider/worksheet checks128 passed in4.79s; picker/native checks29
passed in1.69s. Earlier affected/focused receipts are retained, not retroactively
attributed to the final source. No further runtime edits followed the final source gate.

Exact selection also disables alternate-model review: code checks remain, and a
writing revision uses the same responding provider/model. Failed selected requests
withdraw partial text and stop review/learning. An empty cloud-model field cannot
disable native notebook previews. Refresh cannot replace an explicit local model;
Advanced exact-model choices pin the backend too. The capability inventory now
calls Cursiv Cloud an AI fallback, explicitly distinct from notebook/file backup.
The scoped Gitleaks8.30.1 audit scanned69 public changed/new files with **zero
raw findings and zero credential findings**. Owner exclusions and station paths
were filtered before reads. [Initial audit](../bench/results/U111-secret-scan.json);
[final file-hash receipt](../bench/results/U111-secret-scan-final.json) includes
the final documentation and initial audit. No private key or real user store is
part of this scan. No file content is staged and HEAD remains the starting U110 main.

Every app/test/model process redirects home, real-home, app-data, roaming and local
data before imports to fresh temporary locations outside OneDrive. The existing
locked Python environment is unchanged. Owner exclusions, secrets, real notebooks,
memories/accounts/configuration, station code and unrelated profiles are untouched.
Intent-to-add registers the two new public modules for development source indexing;
no content is staged and no commit exists.

Exact cloud selection currently supports text answers; image input is explicitly
unsupported, and automatic mode retains the existing provider/tool cascade. Native
operations remain available before inference. Source explanations retain their
local-only boundary and explicitly refuse an exact cloud-model explanation request.
Automatic Cursiv Cloud can report an unknown underlying model rather than invent an
ID. A full cloud model catalogue, live cloud combinations and independent human
review are deferred. Conditional constraint recognition and scientific checks are
lexical, bounded safeguards, not proofs that every unsupported claim will be found.
New Mac/Linux CI, frozen installers, deployment and publication were not run; those
remain release work after owner approval. The manual human-review worksheet is
[unscored](../bench/u111-human-review.md).

## Reproducing the probes

With the repository's existing dependencies and local Ollama running, use a fresh
output filename each time. These scripts redirect all app stores before imports,
block outside network and downloads, and preserve raw receipts:

```text
python scripts/u111_bench.py --output NEW.json
python scripts/u111_bench.py --exact --model qwen3:4b-instruct --output NEW-exact.json
python scripts/u111_heldout_bench.py --out NEW-heldout.json --telemetry NEW-telemetry.json
python scripts/u111_paired_checks.py --live NEW.json --heldout NEW-heldout.json --output NEW-paired.json
```

Only installed local models are permitted by this harness. App cloud selection is
covered by synthetic transport/error/pinning contracts; supplying a cloud ID does
not claim that it exists or is available to a particular account.
