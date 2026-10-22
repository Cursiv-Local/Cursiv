# Cursiv v3.14-U84 — Trust boundaries and background answer review

## What changed

- Finish the streamed draft before optional local-model review. Most ordinary
  turns skip that review. Eligible checks appear as labeled follow-ups; stale
  results cannot replace a newer turn. `check off`, `check fast` (default) and
  `check full` control optional model work. Fast deterministic checks remain on.
- Repair supported conversation-only, read-only, no-inspection and no-memory
  instructions before tools, saved-source lookup and automatic learning. Show
  the turn's restrictions; conversation-history settings remain separate.
- Parse workspace filenames without treating policy words as part of the path.
  File operations use backend receipts. Failed file-memory operations stop
  before a secondary memory save. Workspace authorization and protected paths
  remain enforced.
- Generate source labels from application-supplied evidence, independently of
  model wording. A supplied-memory label does not claim that the model used or
  verified those facts. Report damaged-memory retrieval as a storage failure.
- Keep empty/failed answer checks unverified. Detected dose/reference
  contradictions withdraw model instructions and show the supplied reference.
  Bound optional review/rewrite calls and explicit external Cross-check output.
- Split chat, command and dialog modules behind existing entry points. Explain
  readable copied API keys before USB export. Clarify online phone photo chat
  versus the offline capture notebook; preserve notebook records and formats.

- Repair missing full-window theme and notes JSON imports found during release
  validation. Extend both the source regressions and packaged self-test to build
  the complete launcher, title bar, tray and chat panel. U83 stayed a draft; its
  existing tag is preserved rather than moved.

## Install or update

Windows: use `Cursiv-Setup-3.14-U84.exe` or its byte-identical
`Cursiv-Setup-latest.exe` alias. Compare SHA-256 with `SHA256SUMS.txt`.
U84 is higher than U82, so installed U82 copies can detect it through the
existing updater when internet access and update checks are allowed. Offline
mode blocks GitHub checks. A compatible installed Ollama model is still needed
for local model answers. No memory/notebook schema migration is introduced.

Windows and Apple Silicon Mac packages are attached with matching stable aliases
and separate checksum files. Both tagged builds passed the expanded frozen-app
self-test; the Mac workflow also captured all four windows. Installers remain
unsigned (the Mac package is not notarized).

## Tests and limits

The pre-release Windows source checkpoint passed **1,248 tests with one Mac
Keychain skip**. Publication records identify the final versioned regression,
Windows/Mac CI, frozen-package checks and download hashes. Current evidence and
the full unchanged-suite model run are recorded in
[U84 verification](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/U84-RELEASE-VERIFICATION.md)
and the [public test page](https://cursiv.us/ai-reliability-testing).

The fresh full suite 1.5 run from the exact U84 tag passed **156/158 cases
(98.7% overall)** on `qwen3:4b-instruct`. The scorer recorded 100% answerable-case
accuracy and 0% case-marked unsupported claims for this run. The
[failure review](https://github.com/Cursiv-Local/Cursiv/blob/main/bench/FAILURES-U84.md)
includes an undetected safety implication, a contradictory answer and unsupported
reassurance in a passing case. These pattern scores are not general accuracy or
medical validation. The previous candidate's different score is retained;
model variability is not attributed to the GUI/import fixes.

The controlled 10/100/1,000-message rendering test used a simulated 1-second
verifier delay, not a measured model response time. Median final-token-to-ready
latency changed from 1,014/1,021/1,076 ms to 21/25/83 ms with no full-document
rebuilds. Raw runs and limits:
[answer-review report](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/ASYNC-ANSWER-REVIEW.md).

Language rules and model review can still miss mistakes. Provider-boundary
regressions mock responses; benchmark scores describe selected prompts and fixed
checks, not general accuracy or medical safety. Memory is selected stored facts,
not model retraining, perfect recall or subjective awareness. Local conversations
and memories remain unencrypted on disk. Physical second-PC/USB/phone tests and
independent field validation remain outstanding.
