# U106 work handoff

Updated 2026-10-26. Owner: Joshua Winkler. Owner explicitly authorized **commit, push, release and publish** after approving the preview. Earlier no-commit/review notes below are historical.

## U106 release in progress

- Release scope is the reviewed researcher-experience increment, its tests/benchmarks and measured baseline documentation. Remaining plan items stay documented as unfinished.
- Branch: codex/u106-researcher-experience, from main 79a1636. GitHub main still matches that baseline; latest published release is U105.
- Versions now 3.14-U106 in selfknow, launcher and installer. docs/RELEASE-U106.md and CHANGELOG added. Version/release-doc checks: 6 passed.
- Functional source suite already passed 2253/15; rerunning USB gate after version bump before commit. CI must pass on PR and exact main before tag/build. Owner signing runs in place and key material never enters checkout.
- Stage only named U106 source/test/doc/evidence files; excluded legal handoff, field-notes.txt and test_internals/ remain untouched. Build assets stay in ignored release-u106/ and installer/Output/.
- Release USB gate completed: **45 passed, 2223 deselected in 87.71 seconds**, bench/results/U106-release-usb-tests.xml. Source release commit next; no publication performed yet at this checkpoint.

## Current implementation preview (owner authorized local edits, review before committing)

The owner has now asked to begin the researcher-experience plan and see the result before any commit. The baseline-only stopping point below is historical. No commit/push/merge/release is authorized.

- Phase 1 audit: docs/U106-EXPERIENCE-AUDIT.md records workflow friction, reuse and explicit scope gaps. Imported documents/notebook project labels/memory summaries are not isolated project boundaries; the preview must not claim they are.
- First Phase 2 increment ready for review: ordinary measurement statements offer a deterministic confirmation preview; unknown temperature scales remain unknown; reported times stay notes rather than invented observation timestamps. Edit returns original plain wording. Explicit desktop memory saves wait for confirmation. A contextual correction targets actual backend receipts and current records, retains the old record, and asks when ambiguous. Pending cards are cleared on conversation changes. Unsupported time qualifiers block saving rather than silently changing a place name.
- Frozen deterministic action benchmark: before 10/18, after 18/18; zero observations saved during either probe. Artifacts: bench/researcher/action_cases.py, scripts/researcher_action_bench.py and bench/results/U106-researcher-actions-{before,after}.json. Local-model interpretation is explicitly disabled; these are routing metrics, not live model or human usability scores.
- Initial action regressions: 56 passed in 2.76 seconds (new action tests + existing intent/notebook/confirmation tests). Added conversation-switch checks afterward; final suite pending.
- Recall is implemented and validated: exact positive record selection 3/12 → 12/12, negatives 8/8 both, identical frozen question hash; bounded verified reads, date/site/measurement filter propagation and filtered sample mentions. Existing aggregate-statistics date handling remains deferred.
- UI is implemented: four persistent entry points, embedded actual notebook and imported-file library, draft-preserving navigation and skippable inline guidance. Normal/minimum-size screenshots were inspected; small windows collapse guidance. UI regression group 140 passed, final responsive UI probes 9 passed. Evidence under bench/results/U106-ui-* and U106-research-ui-*.xml.
- Boundary review found two issues, now fixed: model-assisted/numbered memory saves now use preview_saves through the existing native memory resolver; stated today/yesterday stays a note rather than part of a site name. Contextual corrections require real receipts and current records. Pending cards clear on new/open conversation. Targeted final boundary/UI-label regression group: 132 passed in 13.67 seconds.
- Additional 12 fresh source-route probes: first measurement 11/12, with the dated generic 'Find records at ... from ...' request unhandled. Saved that original result; subsequently added a bounded dated-record route and regression. Do not present the original holdout as 12/12 or as untouched after this fix. These probes are synthetic and explicitly model-unavailable.
- No version bump, Gemma changes, station edits, user-data access or commits. Larger project isolation, general report comparisons, broad natural exports and human usability tests remain outside this first preview.
- **Final full regression: 2253 passed, 15 skipped in 501.01 seconds**, zero failures/errors. JUnit: bench/results/U106-researcher-validated-full-tests.xml. Skips: Mac Keychain 1, supplied Vosk zip 1, opt-in live self-knowledge 13. Final USB gate separately passed 45/45. Owner-facing review: docs/U106-PREVIEW.md and actual Qt images under bench/results/U106-ui-after-*.png. Main preview image was queued in the Codex file panel. All changes remain uncommitted and unstaged; HEAD remains 79a1636.

### Commands currently running

None. Session 61542 finished successfully. All UI/routing subtasks and test processes have finished.

Validation history: restart-test subprocess environments now explicitly use their copied app data; affected persistence + verification + final action probes passed 95/95 in 15.80 seconds. Earlier full run 76907 reported 2247 passed, 15 skipped, 2 failures and 3 teardown errors because the old persistence-test helper inherited the outer synthetic CURSIV_APP_DATA; it altered only that temporary config/settings and polluted the later free-key/offline test. Data guards remained intact; no owner data involved. Fixed the test helper and reran the entire suite successfully (2253/15). Final USB gate: 45 passed, 2219 deselected in 84.07 seconds. Earlier run 5278 was interrupted after the now-updated starter-label expectation.

### Next action

Wait for owner visual review of this first uncommitted preview. Do not commit, push, merge, tag, package or release without explicit owner instruction. Read docs/U106-PREVIEW.md for remaining scope. Continue the supplied researcher plan incrementally after review; do not describe the entire U106 plan as complete or claim human-usability gains from synthetic probes.

## Researcher-experience plan and release numbering

Owner supplied a researcher-experience and first-time-usability plan originally labelled U107, asking whether it should be U106. Verified GitHub releases and remote tags on 2026-10-26: latest published release is `v3.14-U105`; no remote `v3.14-U106*` tag exists. The local application version is still 3.14-U105. U106 has only the unreleased baseline test/documentation work recorded below.

Saved the supplied plan as **docs/U106-RESEARCHER-PLAN.md**, changing the U107 label to U106 and adding a provenance note. Use this existing handoff for its progress notes; do not create a competing U107 handoff. The plan starts with a workflow/friction audit and a beginner-language benchmark before behavior changes. Preserve the completed baseline evidence and the owner's Qwen priority. No application implementation was performed during this numbering check.

## Baseline and constraints

- Checkout HEAD is the requested `79a1636` (U105 evidence merge).
- Read CLAUDE.md, HANDOFF.md, docs/CODE-MAP.md and docs/U105-HANDOFF.md; retrieved the complete U106 request from the referenced chat.
- Only pre-existing untracked items are the three excluded paths. Do not open, modify or stage them.
- Leave station/, user data, secrets, external profiles and existing safety text untouched.
- Work order: answer quality, memory, notebook/data, usability, code health. Core regrouping comes last.
- Release/version changes are deferred until release authorization, as specified in the release runbook.
- Locked Python exists at C:/Users/joshu/AppData/Local/Temp/cursiv-u88-build-39c0ad1699b74be8bab5385ce1b281d8/Scripts/python.exe. Never install into it.
- Ollama responds outside the restricted execution environment. Installed: qwen3:4b-instruct, gemma3:4b, llama3.1:latest (confirmed 8.0B by Ollama), and nomic-embed-text:latest.

## Progress

Owner steering: run a series of baseline tests before making application changes. No application fixes authorized by assumption that there is a defect; report measured findings first. Application code remains unchanged.

Latest owner steering: disregard Gemma answer issues for follow-up fixes; the owner plans to remove Gemma as an option and use `qwen3:4b-instruct` as the main model. Preserve the measured evidence, but do not spend work fixing Gemma-specific behavior. Source inspection confirms Qwen is already `chat_app.OLLAMA_MODEL` and first in `speed.chat_model_prefs()`. No model options or user settings changed in response to this preference update.

Frozen `bench/overconfidence/u106_cases.py`: 12 new risk questions and 6 controls, before reading results. Added a baseline-only real-chat harness using the existing scorer, explicit model selection in throwaway settings, installed model identity, question hash, and per-question checkpoints. No mocked model answers or production patches.

1. Inspected benchmark and science checks without opening previous result files. Existing benchmark supports old HELDOUT only and has no explicit model selection or incremental save. Added a separate baseline-only harness; the existing script and application are unchanged.
2. Baseline test series is complete. Read **docs/U106-BASELINE.md** for the consolidated findings and limitations. All 54 fresh-set answers and 4 science-reproduction answers were read; labels are saved beside the raw JSON evidence.

## Next

- Owner's latest direction is testing before changes. Present the completed baseline findings before making application edits.
- If implementation resumes, preserve the original order: thermometer/experiment checks and verification callers, paraphrase conflicts/retrieval, memory, notebook/data, usability, code health last.
- Do not tune overconfidence on this now-observed set and call it held out. Reserve another untouched set for any change's validation; require measured before/after improvement.
- A real long multi-conversation Ollama memory run remains outstanding; the new 144-switch probe uses deterministic summaries.
- Remaining implementation sections 3–5 have not started. No version/release work performed.

## Running commands

None. Full suite (2570), Qwen (23388), Llama/Gemma (64699), USB (58008) and science reproduction (65015) all finished.

## Results and blockers

All completed test/model results are below and in docs/U106-BASELINE.md. No unresolved execution blockers. Restricted execution cannot connect to Ollama; approved elevated execution can. No product changes or improvements are claimed.

Initial restricted pytest attempt failed in fixture setup because pytest could not create its numbered temporary directory; interrupted it and confirmed the cause with `tests/test_verify.py -x` (1 setup error). This is an execution-environment issue, not evidence of a product defect. Full rerun uses normal temporary-folder access.

- Qwen real Ollama baseline complete: 18 cases, existing scorer notes 1/12 risks and 0/6 controls, median 10.86 seconds. These are note-trigger counts, NOT model accuracy. Manual labels now in bench/results/U106-overconfidence-labels.md: 2 overconfident (1 noted), 2 borderline (0 noted), 8 fine (0 noted); 6 fine controls (0 noted). Appended these measured counts to bench/overconfidence/RESULTS.md. No tuning or improvement claimed.
- New baseline probes: 2 passed in 7.58 seconds with explicit isolated HOME/USERPROFILE/CURSIV_APP_DATA and pytest directory. 24 conversations revisited 6 times (144 switches), notes separated, exact facts/suggestions deduplicated, duplicate origin never upgraded, markdown exports stable in file count, confirmed suggestion saved once. Real Qt dialog constructed, rendered, searched and duplicate-add checked. This is offscreen Qt, not an installed interactive desktop session.
- Initial Qt image had missing glyphs in offscreen Qt. Existing test_saved_notes_viewer.py explicitly loads Segoe UI for the same reason; adopted that test setup and re-rendered successfully. No product rendering defect established.
- Automatic approval review rejected the first custom-probe launch over potential persistent storage writes. Explicit process-wide temporary home/data paths resolved that concern; safe rerun approved. Restricted file replacement then gave WinError 5; elevated isolated rerun passed. No user-data access was needed.
- Existing direct tests found: tests/test_problem_report.py and tests/test_confirm_cards.py. No direct login-recovery dialog tests were found in the later search.
- Full unchanged existing suite finished: **2200 passed, 15 skipped in 369.74 seconds**. Skips: 1 Mac Keychain, 1 real Vosk zip pin, 13 opt-in live-model cases. Evidence: bench/results/U106-baseline-tests.xml. New U106 probes were collected separately after that suite started.
- Font-loaded Qt rerun: **2 passed in 8.15 seconds**. Inspected bench/results/U106-memory-dialog.png: readable labels, origin/date/family rows, search and add controls. No rendering fix needed in application code based on this probe.
- Froze a separate four-question science audit reproduction set, including the exact thermometer and hypothetical-experiment wording in existing U100 tests, before running it. All four completed on real Qwen; overconfidence note 1/4. Exact thermometer answer remains overcertain and unnoted; same-water normality answer is overcertain and noted. Hypothetical status/invented-number label works in the example, but both experiment answers contain method/design concerns. No fix or before/after gain claimed.
- Mandatory USB gate finished: **45 passed, 2172 deselected in 79.55 seconds**. Evidence: bench/results/U106-baseline-usb.xml. This is existing automated coverage, not a claim of physical exFAT/NTFS/FAT32 or drive-pull testing.
- Removed only this run's synthetic isolated-test-home directory from bench/results after validating its exact absolute path; retained JUnit and screenshot evidence. No user data removed.
- Deterministic paraphrase diagnostics in bench/results/U106-paraphrase-baseline.json: reference retrieval 4/4 title-word questions vs 0/4 semantic paraphrases; conflict check 1/1 direct numeric conflict, 0/3 paraphrased conflicts, 1/1 compatible preference correctly unflagged. Small synthetic diagnostic set, no general accuracy claim. No model calls or app changes.
- Read all of launcher/login_recovery.py and searched tests: no direct recovery-dialog class/module tests found. Existing account-file/security behavior coverage is separate. Not changed.
- Llama baseline: 18 completed; median 22.1715 seconds; notes 0/12 risks, 0/6 controls. Manual confidence labels 0 overconfident, 1 borderline, 11 fine. Installed tag llama3.1:latest is 8.0B; digest retained.
- Gemma baseline: 18 completed; median 7.7165 seconds; notes 0/12 risks, 0/6 controls. Manual scientific-verdict confidence labels 0 overconfident, 0 borderline, 12 fine. Separate substantial defect: 10/18 answers falsely identify the runtime model. Full per-answer labels in bench/results/U106-overconfidence-labels.md. Narrow confidence labels are not overall accuracy scores.
- Final targeted checks after adding benchmark paths to docs/CODE-MAP.md: **5 passed in 7.79 seconds** (code map plus new memory probes). JUnit: bench/results/U106-final-baseline-probes.xml.
- Final artifacts: docs/U106-BASELINE.md; this handoff; benchmark harness/frozen sets; raw JSON/model records; per-answer labels; JUnit reports; memory-dialog screenshot. Only test/evidence/documentation changes; no application edits.
- Application, launcher, installer, site and original handoff diffs remain clean. docs/CODE-MAP.md only gains the required baseline-harness index entry. No excluded-path contents were read or modified.
