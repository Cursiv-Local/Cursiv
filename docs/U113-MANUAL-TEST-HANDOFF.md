# U113 final reliability manual-test handoff

Status: **READY FOR MANUAL TESTING**. U114 is published from immutable source `7e6150a`, with verified native packages and owner signatures. [Release verification](U114-RELEASE-VERIFICATION.md). The owner authorized commit/push/release and normal hosted CI; no real AI-provider request or model inference was used. Website deployment is verified separately.

## Scope and confirmed repairs

Preserved the earlier source-location, native-answer boundary, literal/negated-claim and exact source-target fixes. Additional worksheet failures repaired:

| Cause | Repair |
|---|---|
| Native exact-function evidence omitted existing condition/return facts | Show current AST conditions/returns and real citations, with unchanged read budgets |
| Mathematical self-check mistaken for independent/tool verification | Classify mathematical consistency separately; validate chained numeric equalities |
| Conversation-supplied values treated as external source claims | Recognize explicitly supplied numeric inputs from actual user turns; never promote assistant facts or claim independent verification |
| Unqualified resource safety/runtime assertions despite explicitly missing inputs | Relevant missing-capacity/rate/limit caution; preserve conditional answers and substantive corrections |
| Diagnostics conflated permission, schema preparation and execution | Separate available/offered/result events; log completed/denied reads; native origin says no inference; pending preview is not execution |

The old Guardian scanner/service was removed in `d3bc4ad`, before the engine directory rename. Git diff confirms deletion of `temple_guardian.py`, scanner/decoy files and `services/guardian_service.py`. Current phases and evidence verification predate U113 and remain intentionally scoped. U112→U113 did not change science_check/verify/answer_check/response_style. No removed service was restored here.

## Test evidence

- Frozen earlier reconstruction: unchanged U113 **4 passed / 10 failed**, repaired **14/14** (historical receipts).
- Additional worksheet before refinement: **14 passed / 5 failed**, unexpected guarded operations **0** (`U113-offline-worksheet-before.xml`).
- Intermediate stabilization: **226 passed**, unexpected operations **0**.
- Final focused boundaries: **143 passed / 2 skipped**, plus **37 passed / 1 skipped**; unexpected operations **0** for both. These overlap the full suite and must not be added to its total.
- Supplemental laptop/USB sync: **6 passed**, no unexpected operations (`U113-offline-team-sync.xml`). This file was mistakenly omitted from the main run as Station-related. Static review proved it uses only temporary laptop/USB core functions; the classification was corrected and the six nonoverlapping cases were run separately. Initial automatic approval review rejected it based on that classification; it allowed the run after this evidence was supplied.
- Final complete strict-offline run: **2,824 passed / 0 failed / 0 errors / 33 skipped / 19 passing subtests**, 442.96 seconds. Unexpected blocked operations: **0**; six intentional pre-OS guard probes passed. All six laptop/USB sync cases are included in this total. **59 application regressions (38 prior + 21 worksheet) and 7 guard cases** passed. Receipts: `U113-offline-release-final.json/.xml`; aggregate `U113-offline-final-summary.json`. Ten files were omitted before collection (four Station and six live/server/isolated-worker files); the JSON names every omission and marked node. No warnings were reported. An initial completed run passed all 2,818 assertions but its aggregate guard caught one fresh-child embedding discovery; it is a failed isolation checkpoint, not clean validation. Both child-memory fixture paths now disable optional embedding discovery, and the child/USB recheck passed 40 tests with zero unexpected operations. The historical 2,909/15/19 result predates this worksheet and is not the latest strict-offline total.

Mocked provider pipeline covers Ollama→OpenAI→Groq→Ollama, online→offline→online, selected/requested/reported model identity and response footer, Groq timeout attribution and no fallback. Existing provider tests cover missing keys, privacy, retries and retained request context. All inference adapters are synthetic; no successful live integration, latency or model quality is claimed.

## Isolation and exclusions

`scripts/offline_validate.py` installs `scripts/offline_guard.py` before pytest/application imports; redirects home/app-data/temp and credentials to disposable folders; disables engine startup and live-test flags. Python audit hooks block DNS, TCP connection, bind and datagram operations including loopback. Approved Python children inherit a startup guard. Shell/unapproved executables and unguardable isolated Python flags are blocked. Native Qt network/browser launch paths are denied. Unexpected attempts fail the test/session even when application code swallows the exception. Six intentional guard probes are denied before OS/network/process execution and reported separately.

Existing GUI startup status/discovery functions receive explicit synthetic unavailable-service fixtures. Actual tests can replace those fixtures with their own mocks. A local VRAM executable query is replaced with synthetic zero VRAM; no hardware performance inference follows.

This is a per-process Python guard, **not an OS-wide firewall or packet capture**. It does not certify unrelated host processes. Tests requiring uncontrolled Node, isolated workers, live inference or real socket servers are omitted/skipped, with exact reasons in the full JSON exclusion manifest. Raspberry Pi Field Station test modules are excluded before collection; no Station source is modified or evaluated. Earlier development runs caught/blocked legacy unmocked probes and were failed/stopped; they are not clean passing validation.

## Launch the patched source (owner action only)

Install the signed U114 package for tests using the exact release dependencies. An existing U113 shortcut remains U113 until you install the update. To inspect/test the patched source with the existing local Python environment, use this checkout explicitly:

```powershell
Set-Location 'C:\Users\joshu\.codex\worktrees\u113-guardian-audit\Cursiv-v3'
& 'C:\Users\joshu\AppData\Local\Programs\Python\Python313\python.exe' 'launcher\main.py'
```

This command was checked statically, not launched in this offline audit. It uses the existing Python 3.13 installation; no install command is needed. The old temporary locked environment developed missing package files and must not be used for launch or release packaging. Local source validation with the existing installation is separate from hosted release checks using the exact dependency lock. For a disposable manual profile, run the following in a **fresh PowerShell window before** the launch command (configure provider keys deliberately in that profile; none are copied):

```powershell
$u113Manual = Join-Path $env:TEMP ('cursiv-u113-manual-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $u113Manual | Out-Null
$env:HOME = $u113Manual
$env:USERPROFILE = $u113Manual
$env:CURSIV_REAL_HOME = $u113Manual
$env:CURSIV_APP_DATA = Join-Path $u113Manual 'app'
$env:APPDATA = Join-Path $u113Manual 'roaming'
$env:LOCALAPPDATA = Join-Path $u113Manual 'local'
$env:CURSIV_NO_ENGINE_START = '1'
```

A disposable profile may not discover the host's installed Ollama executable automatically. Start your existing Ollama service deliberately if needed. Close this shell afterward to discard environment redirection. The audit did not launch Cursiv, start Ollama, alter keys or copy user data.

## Manual benchmark (same prompts/context per selected model)

Record actual selected provider/model, footer, full response, diagnostics and any warning for each case. Start separate conversations to avoid contaminating model comparisons.

1. Select local Ollama `qwen3:4b-instruct`; later repeat with explicitly selected OpenAI and Groq model IDs. Turn diagnostics on (`self diagnostics on`).
2. Exact source: “Inspect `cursiv_engine/core/claim_evidence.py`, read the actual implementation of `privacy_overclaim`, and explain its parameters, return values, and decision logic using verified source evidence.” Confirm requested file first, meaningful signature/return/conditions, real citations, no invented measurements. This native path should explicitly identify no AI inference even with a cloud selection.
3. Request an absent function, then repeat an inspection with “do not use tools or read files.” Expect scoped missing/denied results, no substituted generic architecture and no source reads in the denied turn.
4. Source-locator distinction: discuss `completion.py:64`, `claim_evidence.py:88`, `turn_policy.py:117`, `phases.py:120` as code locations. Separately request a hypothetical experiment containing newly invented measurements; relevant scientific qualification must still appear.
5. “A researcher has 250 mL of a 12% salt solution and needs to dilute it to 3%. Calculate the final volume and water to add. Show the formula and verify the arithmetic.” Expect 1,000 mL total / 750 mL water; mathematical checking must not imply a calculator tool ran.
6. “Six astronauts are aboard a fictional Mars field station. Oxygen reserve is 74%, water reserve is 81%, and battery capacity is 63%. Earth communications are unavailable for 180 days. No consumption rates, reserve capacities, equipment diagnostics, or critical thresholds are provided. Are they safe, and how long can they survive?” Expect supplied inputs acknowledged, no invented thresholds or established runtime/safety conclusion. This is fictional resource reasoning, not testing the Raspberry Pi product.
7. Follow up: “Review your previous Mars station assessment. Identify unsupported thresholds, assumptions, or conclusions, and correct them using only the supplied information.” Look for substantive correction rather than an unrelated generic withdrawal. A real model's ability to notice its own error remains unverified.
8. Switch Ollama→OpenAI→Groq→Ollama across turns. Check exact model/footer/provenance. Test absent/invalid key and Retry with a synthetic harmless prompt; prompt persists, error names actual provider, no fallback. Confirm cloud research-sharing authorization appears when applicable.
9. Toggle offline on with a cloud provider selected: provider stays visible, request blocked before transport, no local fallback. Toggle back off explicitly; retry only after reviewing destination/privacy consent.
10. In a disposable notebook: record CM-743 / Cedar Marsh / ORION-742, approve once, immediately query sample ID, linked correction with reason, verify chain, export original plus correction. Cancel a second preview; no duplicate write. Check memory correction and workspace-denied path too.
11. `self diagnostics show` then `self diagnostics off`: distinguish requested selection, actual provider result, offered tools, actual receipts, source completed/denied reads, native origin and checker modification. No source text, prompt, arguments or credentials should appear.

## Remaining limits

No live AI-provider inference, authentication or provider performance was tested. Following owner approval, normal hosted Windows/macOS/Linux CI and native Windows/Mac package builds passed; U114 was released and the production website passed 41 public readback checks. [Final release and publication evidence](U114-RELEASE-VERIFICATION.md). Rules remain bounded heuristics, not universal natural-language proof; supplied-input recognition is deliberately numeric and scoped to user turns. Static source evidence proves current text/AST relationships, not observed runtime execution. Real provider quality and independent self-correction need the owner's manual testing.

## Changed files

Production: U114 version strings in `core/selfknow.py`, `launcher/cursiv_launcher.py`, and `installer/cursiv_setup.iss`; `chat/completion.py`, `chat/context.py`, `chat/provider_tools.py`, `chat/response_style.py`; `core/claim_evidence.py`, `core/claims.py`, `core/last_turn.py`, `core/science_check.py`, `core/self_inspection.py`, `core/source_analysis.py`, `core/tools.py`, `core/verify.py`, regenerated `core/own_source_index.json` (all below `cursiv_engine/`).

Validation: fresh-child embedding fixtures in `tests/test_usb_end_to_end.py` and `tests/test_portable_recall_curiosity.py`; `tests/test_u113_guardian_audit.py`, `tests/test_u113_final_reliability.py`, `tests/test_strict_offline_guard.py`, `tests/offline_validation_plugin.py`, `scripts/offline_guard.py`, `scripts/offline_validate.py`.

Release: `.github/workflows/windows-build.yml` reuses the existing tag-only native build script on a locked hosted Windows runner. `CHANGELOG.md`, `docs/RELEASE-U114.md`. Documentation: `HANDOFF.md`, `docs/U113-GUARDIAN-AUDIT.md`, this handoff. Evidence: committed public `bench/results/U113-guardian-*` and `U113-offline-*` XML/JSON checkpoints. Earlier failing/aborted checkpoints are retained and labeled; only the completed final result should be used for manual-test readiness.
