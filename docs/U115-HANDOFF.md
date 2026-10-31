# U115 development handoff: interrupt continuity and optional personality

Status: **RELEASED: v3.14-U115**. [Verified release](U115-RELEASE-VERIFICATION.md). Implementation and final validation complete. Base main 7d7e1e3 after U114 release. The owner subsequently authorized commit, push and application release; website work is explicitly deferred. Original dirty owner checkout is untouched. No dependencies/models downloaded; no live AI calls or inference allowed.

The progress entries are chronological. The final checkpoint below is authoritative.

## Integration plan (written before implementation)

- Desktop turn lifecycle: launcher/chat_panel.py `_begin_turn`, `_stop_generation`, `_run_turn`, `_on_cancelled`; launcher/chat_review.py `_run_target`/`_on_run_event`. Existing generation/cancel/person/workspace identity will reject stale events. Currently Stop only sets an Event and waits for worker completion; generic worker signals also need per-turn acceptance.
- Streaming: chat/provider_manager.py -> provider_adapters.py -> provider_http.py -> request_budget.open_request. Existing network gates, exact routing, streaming/provenance and activity serialization remain. Add optional cancellation-close registration for inference responses; close off the GUI thread. A server may continue processing, and connection setup/uncancellable work may hold the existing inference slot until return/timeout.
- Persistence: launcher/conversations.py already snapshots message dictionaries through the protected ordered writer. Store bounded checkpoint metadata on interrupted assistant messages, including the original request, exact visible partial response, original selection, provenance when available, IDs/timestamps/resume count. Use this same encrypted conversation boundary; no separate private store. Skip inference-based titles/session notes for interruption snapshots. Respect history/autosave preferences.
- Resume: small launcher continuity mixin plus pure engine checkpoint helpers. Resume sends a bounded context packet through the existing chat/provider dispatch with current turn restrictions and explicit provider/privacy selection. Resume never replays a native command or tool write; original source/receipts are context, not proof or permission. Keep original checkpoint until continuation succeeds, support older tasks, repeated interruption, dismissal/retention. No hidden reasoning, section plan, embeddings or summary calls.
- Personality: extend existing per-person core/style.py settings and Settings style controls. Preserve defaults and existing learned rules. Add opt-in professional/playful/sassy, frequency and independent verbosity. Only a short presentation hint on the next normal model request, suppressing humor for current or recently sensitive context; no scripted jokes or separate calls.
- Checking: reproduce casual false positives through the real completion pipeline; narrow confirmed scientific triggers while retaining real tool/source/write, medical and safety checks. Preserve all U113/U114 repairs and the removed Guardian service.

## Validation plan

Use scripts/offline_validate.py with its startup guard and disposable home/temp/settings before imports. Add deterministic Qt streaming, mocked Ollama/OpenAI/Groq, transport close, persistence/restart, retention, privacy/permission and actual completion-pipeline regressions. Freeze Stop baseline and measure code-only Stop/checkpoint/resume overhead, added bytes/token estimates (not provider token counts), storage footprint and rapid interruptions. No true model quality claims from mocks. Then run affected suites and existing strict offline regression scope. Station implementation, excluded files, owner records, credentials, confirmation/atomic writes remain untouched.

## Progress

- Reviewed CLAUDE.md, HANDOFF.md, ARCHITECTURE.md, docs/CODE-MAP.md, U113/U114 history and the current desktop/provider/style/storage paths.
- Current checkpoint arrays for planned/completed sections will remain empty: no reliable model-intent data exists.
- Next: freeze baseline and implement core cancellation/checkpoint/resume before personality.
- Commands running: none.

### Core checkpoint (development)

Baseline strict run `U113-offline-u115-baseline`: 2 expected failures, 0 unexpected operations (Stop retained streaming/input lock and lost partial history). First integration: 28 passed / 1 receipt fixture failure; isolated stale provider outcome was reset at desktop turn start. Core cases then passed 41/41 with zero unexpected operations, covering persistent/no-autosave checkpoints, nested interruptions, stale chunks/done/write-preview rejection and exact changed-provider dispatch. No model calls were used.

Checkpoints are metadata on assistant messages; original request, conversation/turn/checkpoint IDs, Unix creation timestamp, original selection/provenance, empty section arrays, resume count and prior displayed continuation segments. Defaults: 8 active checkpoints per chat, 14 days; settings capped at 20/90. Pruning/dismissal removes metadata only, never transcript text. Resume packets stop at 8,000 characters and refuse oversized contexts explicitly. Resume is text-only under existing no-tools/no-memory policy; original instructions are quoted data, not commands replayed. A changed provider is shown before continuation; resolved automatic backend can be pinned from provenance.

Optional presentation controls have been added (default off, professional/playful/sassy, frequency and independent verbosity), with recent-context sensitive-topic suppression. Casual checker baseline reproduced 3/3 reported categories (toaster, haircut, cafe advice); new sensitivity tests also caught 3 vocabulary gaps and these were corrected. The scope of the science warning now requires a relevant domain/measurement; actual action/source checks remain separate.

Next: finish atomic-write/worker scope boundaries, transport cancellation and actual provider-resume tests; measure overhead; refresh public source inventory and run full guarded regressions. No release/version string changes. Test commands may run only through offline_validate.py. Receipt labels retain the existing U113 harness prefix; `u115-*` labels identify this iteration.

### Provider, UI and overhead checkpoint

119 affected tests passed with zero unexpected operations, including real completion/provider dispatch with synthetic Ollama/OpenAI/Groq and retained U109 overconfidence checks. A mistaken science test filename produced a no-tests receipt; it is not validation. The broader first checker run had 5 existing boundary failures, corrected by preserving sample/readings/safety triggers. Optional style is additive; retired tone commands remain inert and guide users to Settings → How Cursiv answers.

74 desktop/provider/personality/performance tests then passed with zero unexpected operations. Fifty synthetic offscreen Stop cycles (autosave off, tracemalloc on) measured median 7.7381 ms / p95 13.1755 ms to handler return with input released; checkpoint median 0.04875 ms; prepare median 0.09905 ms. Sample resume packet 629 UTF-8 bytes, full continuity instruction 1,229 bytes; metadata 421 bytes; synthetic serialized message adds439 bytes. Python traced peak69,460 bytes, excludes native Qt memory. Not provider token counts, hardware performance, server-side cancellation or real-model quality. Baseline handler returned in0.0544 ms but left input locked, so no claimed numerical speedup in completion latency. Receipt U115-interrupt-performance.json. No extra checkpoint/personality inference or embeddings.

Resume context is now protected by local prompt compaction; excessive route budgets fail explicitly rather than discard the task. Exact long repeated paragraphs are detected in continuation metadata, never stripped from scientific prose. Save failures keep the checkpoint in this window and release input. Approved file writes keep atomic completion but stale receipts cannot corrupt a subsequent turn. Remaining: finish full guarded suite, inspect UI preview, update user docs/source inventory and scan public delta. All changes remain uncommitted.

### Diagnostic full run and final preparation

The diagnostic full run completed: 2,862 passed / 13 failed / 33 skipped / 19 passing subtests, with zero unexpected guard operations (U113-offline-u115-full). It is not the final validation checkpoint: source edits while it ran invalidated 9 hash-checked own-source witness tests, and it exposed 2 native identity contracts, numbered memory selection and the 1,200-line module gate. Do not count this as a clean full suite. Cancellation/save completion moved into the continuity mixin to keep ChatPanel under the existing budget. Native notebook/memory scope uses the stable conversation identity; a separate saved flag prevents an allocated ID from enabling autosave. Worker configuration deltas are applied only on an accepted owning turn, preserving native settings changes without stale/profile leakage.

The native identity follow-up passed159 tests with no unexpected operations. Additional fresh-process checkpoint recovery, no repeated original notebook command, explicit unavailable-backend pinning and malformed-context cases are covered. Native planning still uses its existing cheap action detector; there is no new mandatory planner. A rendered offscreen preview was inspected in reports/U115-paused-preview.png; system font loading was needed only for the isolated screenshot fixture, not production.

The casual-warning change only suppresses recognized non-scientific conversation when no relevant measurement/medical/safety domain is present; unknown contexts retain the prior cautious behavior. Fictional joke exemption already existed and is preserved; actual execution claims still undergo the normal evidence checks. Source inventory must be refreshed after the last source changes. Next: clean final full guarded run, final secret scan, final handoff/measurement summary. No running app/server/model jobs; validation commands only.

### Final validation start

Native identity fixes passed159 cases; refreshed source/confirmation/index prerequisites then passed160 with zero unexpected operations. An early `u115-final-full` attempt was deliberately stopped at14% during final review (no complete receipt; never count it as validation). The last acceptance-order fix rejects a foreign research owner before applying any worker state/configuration. Its focused ownership/native/personality/provider/architecture set passed96/96 with zero unexpected operations. The final complete run is `u115-final-clean` below; all source changes are now frozen for it. No code was committed or published.

Commands running: strict offline `u115-final-clean` (full applicable tests, source inventory refresh); no application/server/inference process.

### Resume evidence-context boundary

The `u115-final-clean` attempt was also deliberately stopped before completion during review; it has no clean full-run claim. Three newly frozen resume drafts exposed a real gap: generic “continue” had hidden the original water/temperature/resource question from post-draft checks. The fix supplies the original user question/inputs to deterministic checks only after routing and writing construction; it never replays tools or elevates the prior model text as evidence. The before set had3/3 expected failures; after, all3 pass and one-request provider/no-replay tests remain green. The affected set passed196 with1 stale inventory witness; this stale hash is resolved by refreshing the inventory after the final source edits, not by disabling evidence checks. Navigation wording now names the actual Settings → How Cursiv answers section.

Final commands running: `u115-validation-complete` full guarded suite with refreshed inventory. Earlier diagnostic/aborted labels are preserved; only the completed final result should establish readiness. No source changes are planned while this run executes.

## Final checkpoint — October 31, 2026

**2,884 passed / 0 failed / 0 errors / 33 skipped / 19 passing subtests**,653.42s (terminal),652.519s (JUnit). **60 new regression cases**: continuity22, provider pipeline14, personality/checkers23, performance1.

- [Final guard receipt](../bench/results/U113-offline-u115-validation-complete.json)
- [Final JUnit](../bench/results/U113-offline-u115-validation-complete.xml)
- [Summary, production hashes and measured limits](../bench/results/U115-validation-summary.json)

Zero unexpected guard operations;6 intentional denial probes;34 approved Python children;35 installed guards. Existing live/server/isolated-worker and Station exclusions remain documented. This is not an OS-wide firewall or real-model benchmark. Earlier failing/diagnostic/aborted checkpoints do not replace the final result. All installed-source hashes match actual final source, using the same CRLF normalization as self_index.fingerprint.

Existing notebook/memory confirmation, linked correction/query/verify/export, exact routing, offline/privacy, workspace and opted-in USB key-export regressions pass. Version labels remain U114 pending an approved release; U115 names this development iteration. Nothing committed, pushed, tagged, released or deployed. Original owner checkout working files and excluded data were untouched.

### Final measured overhead

50 synthetic offscreen interruptions, autosave off, Python allocation tracing on:

| Metric | Measured |
|---|---:|
| Stop return with input enabled, median |6.44145 ms|
| Stop p95 / maximum |14.1612 /14.5739 ms|
| Checkpoint creation median |0.0326 ms|
| Resume preparation median |0.0588 ms|
| Sample resume JSON / full instruction |629 /1,229 UTF-8 bytes|
| Checkpoint metadata / serialized message overhead |422 /440 bytes|
| Synthetic message file |1,012 bytes|
| Traced Python peak across50 cycles |38,431 bytes|

Baseline U114 Stop returned in0.0495ms **without releasing input**. Worker-dependent release latency was not measured, so no numerical speedup is claimed. Native Qt memory, actual provider tokens, hardware behavior, long-history autosave latency and server cancellation are not established. No extra checkpoint/personality inference or embeddings. Exact one-request resume is covered for mocked Ollama/OpenAI/Groq.

### Production files changed

- `cursiv_engine/chat/cloud_providers.py`
- `cursiv_engine/chat/completion.py`
- `cursiv_engine/chat/conversation.py`
- `cursiv_engine/chat/provider_adapters.py`
- `cursiv_engine/chat/provider_manager.py`
- `cursiv_engine/core/science_check.py`
- `cursiv_engine/core/selfknow.py`
- `cursiv_engine/core/style.py`
- `launcher/chat_controls.py`
- `launcher/chat_panel.py`
- `launcher/chat_review.py`
- `launcher/conversations.py`
- `launcher/provider_controls.py`
- `launcher/settings_dialog.py`
- `cursiv_engine/chat/continuity.py`
- `launcher/chat_continuity.py`

Also updated: the public source inventory, architecture/code map/root handoff/docs index, this handoff and the [user guide](INTERRUPT-CONTINUITY.md). Four `test_interrupt_*` files and synthetic XML/JSON/performance receipts provide evidence. No dependencies or Station implementation changed.

### Owner manual test

Close installed Cursiv first; its single-instance handling could otherwise open the old binary. Use a disposable conversation/notebook/workspace. Launch this checkout with the existing Python installation:

```powershell
Set-Location 'C:/Users/joshu/.codex/worktrees/u113-guardian-audit/Cursiv-v3'
& 'C:/Users/joshu/AppData/Local/Programs/Python/Python313/python.exe' 'launcher/main.py'
```

1. Select Qwen3 4B. Request an iron-oxidation explanation, Stop before text and mid-sentence. Input returns, text stays, a paused task appears. Repeated Stop must not duplicate it.
2. Ask about potatoes, then Resume or say “finish that explanation.” Check original context, repetition, coherent continuation and truthful backend footer. Real-model quality needs your judgment.
3. Pause Task B too; choose either task, dismiss one, save/reopen and restart. With autosave off in a new chat, nothing persists until explicit Save.
4. Switch to OpenAI/Groq before Resume. Check destination/consent, absent-key/unavailable-model errors and offline blocking. Failures retain the task; no silent fallback.
5. Interrupt/resume a scientific question using a disposable scenario. Original inputs must drive checking; old model text must not become verified evidence.
6. Test an approved disposable write: Stop can prevent an unstarted operation; a started atomic write may finish. Resume cannot replay it or insert old text into a new turn. Recheck notebook record → query → linked correction → verify → export with normal confirmation.
7. Settings → How Cursiv answers: try Playful/Sassy, frequency/detail, then disable them. Check short, natural acknowledgments and professional handling of serious/medical/distress context. This is guidance, not guaranteed model behavior.

### Limits and final state

Resume is text-only; request new tools separately. Context is capped at8,000 characters plus route limits. Missing/oversized context is explicit; no hidden reasoning or provider state is restored. Exact repeated paragraphs are detected, not automatically edited. Defaults8 tasks/14 days; configurable1–20/1–90; cleanup occurs on access/next snapshot and keeps transcript text. An unclosed connection or uncancellable backend can retain the serialized inference slot until return/timeout while the GUI accepts new input. Real provider quality, token usage and server cancellation remain manual tests.

No application/server/model process, dependency install, build or release was started. Validation is complete. No commands remain running after final static audit. Work remains uncommitted.

## Owner-authorized release preparation — October 31, 2026

The owner requested commit/push/release, explicitly leaving the website for later. App/installer version strings are now3.14-U115. Normal hosted release CI remains authorized; real AI calls/model inference remain prohibited. The development full-suite checkpoint above is preserved. Fresh-checkout portability fixes archive the exact U114 Stop baseline in tests/fixtures/u114_stop.py.txt, create ignored report directories explicitly, and keep fresh timing artifacts in reports/ rather than overwriting the measured public development receipt. No production behavior changed in these test-harness fixes. Source index is refreshed for the version change before commit. Next: focused local release gates, secret scan, required USB commit hook, protected PR/main CI, tag, native builds, independent owner signatures and public-download verification. No website files or deployment commands.

Release candidate validation:175 interruption/source-inventory tests and36 existing version/build/signing/workspace tests passed with zero unexpected operations. All production Python changes match the completed2,884-test development checkpoint, apart from the reviewed version bump (and the separate launcher version constant). The exact archived U114 baseline has no shallow-history dependency. The first release command used a nonexistent test filename and ran no tests; it is not a validation result. Next: mandatory guarded USB commit hook and protected hosted CI. Website remains deferred.

Hosted CI checkpoint: Linux ran2,971 passing cases/34 skips/19 subtests with one restart-fixture failure: a fresh Python child lacked the launcher import path. The strict local harness supplied PYTHONPATH, masking that setup dependency. The fixture now prepends the repository and launcher directories explicitly in the child, without depending on CI history or environment. No production behavior changed. Source commit e371946 is retained; a follow-up test-only commit will rerun all protected checks. Real AI calls remain prohibited; website unchanged.


## Released checkpoint — October 31, 2026

The owner authorized commit, push and application release, explicitly deferring the
website. Source commits e371946/e150aec merged through PR75 as immutable
523f0175c5848b36a5065f4ff10165c5dfc65ff7. All17 protected checks passed after the
test-only restart-fixture portability correction. Exact-main CI41170359384 passed:
Windows2990/16 skips, Mac2973/33, Linux2972/34, each with19 additional passing subtests;
existing ARM64 headless source tests114/0. This is not Pi hardware validation.

Tagged Windows41171190258 and Mac41171192335 builds passed locked provenance and
native startup gates; Windows also passed portable USB-layout startup. All8 platform
assets have verified owner signatures; the protected private key was not copied or
printed. U115 was published with11 assets; anonymous downloads returned200 and
matched staged bytes/GitHub digests, with8 signatures independently reverified.
The redundant release-triggered Mac run41172357909 was canceled after the verified
manual build, per the release runbook. The immutable application tag was never moved.

The scanned application candidate comprised83 public paths, with0 secret findings.
No owner data, excluded files, Station implementation or website paths were changed.
No real AI calls or live model inference were performed. Real provider quality and
server-side cancellation remain owner manual tests; see the existing manual sequence.
Website updates/deployment remain deferred. Release evidence is recorded separately
after the immutable application tag; no production code is changed by that proof PR.
[Full release verification](U115-RELEASE-VERIFICATION.md).

Commands running: none. Remaining: owner manual model testing and any later,
separately authorized website work. Historical development entries above retain the
state at their original checkpoint; this released checkpoint supersedes their status.
