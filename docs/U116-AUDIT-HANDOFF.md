# Audit handoff: Codex U115 review, UI cleanup, health check (Claude, 2026-10-31)

Status: **the owner authorized commit, push, release and website publication (October 31, 2026).**
Released as [v3.14-U116](U116-RELEASE-VERIFICATION.md); §9 records how. No real AI-provider calls, no model inference, no
model or large dependency downloads. Station code untouched.

Base: `main` at `d16368a` (U115 released from `523f017`, release proof PR76). Working tree
was clean before this work; no other developer's uncommitted changes existed.

## 1. Repository state found

- No open PRs or issues. Last CI on `main` green, but that run was the reduced docs-only scope.
- Everything from Codex for U115 (`e371946`, `e150aec`, PR75; proof PR76) is committed and released.
- Full local suite on the untouched `d16368a` (strict offline harness, Linux container):
  2,865 passed / 3 failed / 1 error / 49 skipped / 19 subtests.
  - 2 real failures in `tests/test_release_docs.py`: PR76 added
    `docs/U115-RELEASE-VERIFICATION.md`, which makes U115 "verified", but `docs/README.md`
    had no U115 row and `website/assets/cursiv-owner-release-U115.json` does not exist.
    CI missed this because PR76 only ran the docs-only scope.
  - 1 failure + 1 error in `tests/test_problem_report.py`: environment only. In this
    container `platform.platform()` spawns `uname`, which the offline guard blocks. Passed in
    U115 hosted CI on all three OSes.

## 2. Defects found and fixed (each has a regression test that fails on the old code)

| # | Defect | Root cause | Fix | Test |
|---|---|---|---|---|
| 1 | Permanent **"AI Providers…"** button under the chat box (owner photo) | U112 (`7f41d19`) added it as a failure-recovery companion to "Retry preserved request", but only the retry button was created hidden. Nothing ever hid "AI Providers…". | Created hidden; one helper `ProviderControls._show_provider_recovery` shows both buttons beside a provider failure and hides them at the next turn / clean completion. Settings → AI Providers stays the everyday route. | `tests/test_provider_recovery_ui.py` (3 cases; 3/3 fail before) |
| 2 | Casual chat still got the science warning ("repeat the measurement, check the instrument's calibration") for a toaster, a dog's name, a landlord, a car noise | U115 only *skipped* the warning for a fixed list of casual words (cafe, haircut, joke…). Any topic not on that list still warned. U115's own toaster test only passed because it also said "playful line". | The warning now *requires* a measurement or a science/health/safety/field domain (`science_check.scientific_context`). Added missing field words (creek, marsh, algae, weather, insects…), so a "weird glow on the creek" still warns. | `tests/test_casual_science_warning.py` (12 cases); all 233 existing checker tests still pass |
| 3 | **"forget it" silently deleted a saved memory.** After chatting about the dog, "forget it" removed "my dog is called Biscuit" with no confirmation. | "forget it" was parsed as *forget the thing I just said*, resolved against the previous user message, and the matching memory was deleted. | Idiomatic dismissals ("forget it", "forget about it", "never mind, forget it", "oh, forget it") are no longer memory commands (`memory/intents._DISMISSAL`). | `tests/test_memory_intents.py::test_forget_it_dismisses_the_topic_and_never_deletes_a_memory` (5 cases) |
| 4 | "forget that my dog is called Biscuit" said "I couldn't find a memory matching that" | The leading "that" stayed in the search query. Predates U115. | A leading "that"/"about" before a multi-word memory is dropped; bare "forget that" is still a reference. | `test_an_explicit_forget_still_removes_the_memory` |
| 5 | `docs/README.md` had no U115 row and still said U115 "development, not released"; `ARCHITECTURE.md` called the U112 provider manager "unreleased" | Stale docs | Updated | `tests/test_release_docs.py` (docs-index case) |

## 3. Codex U115 audit

Reviewed the U115 diff (`7d7e1e3..523f017`, 18 production files, +813/−157) and probed behaviour directly.

Verified correct (by reading the code and running tests):
- Stop/interrupt continuity (`chat/continuity.py`, `launcher/chat_continuity.py`): cancellation
  closes transports on daemon threads and never blocks the GUI. Checkpoints are bounded metadata on
  assistant messages, in the existing encrypted conversation store. Resume is text-only with no tool
  or command replay, and stale or foreign worker events are rejected by turn identity. 22 tests.
- Provider pipeline: a provider error during a cancelled request is reported as cancelled, not as a
  malformed reply. `reset_response()` stops an old failure leaking into a new turn. The resume
  context is protected from prompt compaction and fails explicitly when over budget (`cloud_providers._slim`).
- Post-draft checks on a resumed turn use the original question, so evidence checks still apply
  (`completion.py`). The prior model text is not promoted to evidence.
- Optional presentation style (`core/style.py`): default off, a pure-regex hint, no extra model
  call, suppressed in sensitive contexts.

Needed correction:
- The casual-warning fix (defect 2 above). The U115 handoff says this was fixed, but it only
  worked for the topics on its list.
- The release docs left `main` failing 2 tests (defect 5; the website half is still open, see §6).

Not verified (needs the owner, real models or real hardware):
- Real-model resume quality, real provider token use, server-side cancellation.
- Windows/Mac look and feel. Screenshots here are Linux offscreen with fallback fonts.

## 4. UI review (offscreen render, Linux, 1100×760)

- Bottom of the chat panel after fix 1: attach, input, Voice, Send, Stop, Cross-check. No persistent prompt.
- The "Describe a task or ask a question / Cursiv-v3 / Worktree" bar in the owner's photo
  is the **Codex desktop app's** own composer behind the Cursiv window, not part of Cursiv.
- Observed, not changed (cosmetic): the model menu truncates its label
  ("qwen3:4b-instruct · availabilit…"), and the model-refresh button is wide for a single ↻ icon.

## 5. Test results

Commands (all through the strict offline harness; local receipts deleted afterwards so they are not committed):

```
python3 scripts/offline_validate.py <label> [pytest args]            # targeted
python3 scripts/offline_validate.py <label> --refresh-index tests -q  # full suite + source index
```

- Baseline untouched `d16368a`: 2,865 passed / 3 failed / 1 error / 49 skipped / 19 subtests.
- After fixes (full suite): see §7. The source inventory (`core/own_source_index.json`) was rebuilt,
  as required after editing indexed source.

## 6. Remaining issues (by severity)

1. **Medium: `main` is red on `test_every_verified_release_has_its_signed_manifest_on_the_website`**
   until `website/assets/cursiv-owner-release-U115.json` exists. This is deferred website work and needs
   an owner signature, so it was not done here.
2. Medium: memory saves on loose "remember to …" phrasing. "remember to drink water is good advice"
   saved a memory. It is visible (with a receipt) and removable, so it was left unchanged pending an owner decision.
3. Low: an explicit reference "forget that" still deletes the memory matching the previous message
   without a confirmation card. This is intended behaviour, but a confirmation would be safer.
4. Low: `test_problem_report` cannot run under the offline guard on Linux hosts where `platform`
   spawns `uname` (environment only).
5. Low/cosmetic: model menu truncation; wide refresh button.
6. The `docs-only` CI scope can hide failures in `test_release_docs.py`. Consider including that
   file in the docs-only scope.

## 7. Final checkpoint

Full suite after all fixes, with the source index rebuilt
(`offline_validate.py health-audit-full --refresh-index tests -q`, Linux container, 181 s):
**2,887 passed / 2 failed / 1 error / 49 skipped / 19 subtests.**

- Baseline → after: +22 passing (new regression cases plus the docs-index test now passing).
- Remaining failures: the website-manifest test (deferred website work, §6.1) and the
  `test_problem_report` environment failure and error (`uname`). The guard's single blocked operation
  is that same `uname` call, the same as in the baseline run.
- Production files changed: `launcher/chat_controls.py`, `launcher/chat_panel.py` (net −0 lines, 1,198/1,200),
  `launcher/chat_review.py`, `launcher/provider_controls.py`, `cursiv_engine/core/science_check.py`,
  `cursiv_engine/memory/intents.py`, plus the regenerated `cursiv_engine/core/own_source_index.json`.
- Performance: the changes are regex checks and widget visibility only. They add no model calls,
  embeddings, threads or disk writes. No timing was measured for them.

## 7b. Second round: the remaining small fixes (owner request)

| # | Fix | Test |
|---|---|---|
| 6 | "forget that", when resolved from the conversation, now shows the exact saved memory and deletes it only after "1"/"yes" ("no"/"cancel"/"keep it" keeps it) | `test_forget_that_resolved_from_the_conversation_asks_before_deleting` |
| 7 | Talking about a saying ("remember to drink water is good advice") is not saved | `test_talking_about_a_saying_is_not_a_memory_save` |
| 8 | The model menu fits its full label; the refresh button is a compact icon | offscreen render |
| 9 | Docs-only CI changes now run `tests/test_release_docs.py` (`.github/workflows/tests.yml`, Linux job) | CI |
| 10 | `website/assets/cursiv-owner-release-U115.json` copied from the public U115 release. Its SHA-256 `881b73fd…ea` equals the recorded download, all 8 assets verify against the pinned owner key, and a tampered copy is rejected (`InvalidSignature`). | `test_every_verified_release_has_its_signed_manifest_on_the_website` |
| 11 | Website and release docs moved U114 → U115 with `scripts/website_release.py` (download links, hash, signed manifest, counts, test-page section). `node cloudflare/publish.mjs --build-only` built 23 pages; 31/31 website tests and the discovery measurement passed. | cloudflare tests |
| 12 | Version 3.14-U116 in `selfknow.py`, `cursiv_launcher.py` and `cursiv_setup.iss`; CHANGELOG; `docs/RELEASE-U116.md` | `test_versions.py`, `test_release_docs.py` |

## 8. Owner manual tests

1. Start Cursiv. Below the chat box there must be no "AI Providers…" button.
2. Select OpenAI or Groq with no key and send a message. "AI Providers…" (and "Retry preserved request"
   if the request was kept) appears beside the failure. Send a normal local message and both disappear.
3. Ask "my toaster makes a weird noise, is that normal?" No calibration or lab warning should follow the answer.
   Ask "I measured the creek pH at 9.4 once, is the water safe?" The warning must still appear.
4. Say "remember that my dog is called Biscuit", chat about the dog, then say "forget it". Check the
   Memory window: the fact must still be there. Then "forget that my dog is called Biscuit" must remove it.
5. Continue the U115 manual sequence in `docs/U115-HANDOFF.md` (Stop/Resume with real models).

## 8b. Owner prompt run (November 1, 2026)

The owner ran the test prompts on installed U116 and found failures the mocked tests missed. All are covered by
`tests/test_owner_prompt_run.py`:

- "forget it" still reached the confirm card through `core/intent.py`, and after Yes the model claimed a removal
  that did not happen. Model prose can no longer claim a memory change (`memory/intents.unverified_claim`).
- "search my notebook for Site A" searched for the request's own words.
- "remember to drink water is good advice" fell through to the old `remember` search and listed stored notes.
- A question about readings ("What's the difference?") became a notebook save instead of an answer.
- "how do you decide whether to route a question to the notebook?" got the canned decline; it now reads the source.

## 9. Release and website

**Done (October 31, 2026), from the owner's Windows PC:** tagged, built, signed, published and the website
updated. See [the verification record](U116-RELEASE-VERIFICATION.md). The steps below are kept as the record of the plan.

Done from the cloud session, following the runbook order:
- **PR #78** (website and docs only, merged as `e7ac5a0`): the site moved to U115 with its verified signed manifest.
  The website tests read the app version, so a U116 site must wait for the U116 signature.
- **PR #77** (app fixes and version 3.14-U116, merged as `9e5b672`). Exact-main CI
  [41223923153](https://github.com/Cursiv-Local/Cursiv/actions/runs/41223923153) passed on Windows, Mac and Linux.

Blocked in the cloud container: the git proxy accepts branch pushes but refuses tag pushes, so
`v3.14-U116` is **not tagged yet**. `windows-build.yml` builds only from an immutable tag.

Owner steps on the Windows PC, in Git Bash from an up-to-date checkout (`docs/RELEASE-RUNBOOK.md`):

```bash
git fetch origin && git tag -a v3.14-U116 9e5b672045446ce7c4a147071e3368751f009445 \
  -m "Cursiv v3.14-U116 — Audit fixes: cleaner chat bar, safer memory, fewer false warnings; exact-main CI 41223923153 passed"
git push origin v3.14-U116
gh workflow run windows-build.yml --repo Cursiv-Local/Cursiv -f ref=v3.14-U116
gh workflow run mac-build.yml --repo Cursiv-Local/Cursiv -f ref=v3.14-U116 -f upload=false
```

Then runbook §5 (collect and check the 8 assets), §6 (sign with the owner key; never copy it), §7
(`gh release create v3.14-U116 … --notes-file docs/RELEASE-U116.md`, then cancel the release-triggered
Mac run). §8 covers the website: `scripts/website_release.py --old U115 --new U116 …`, copy
`owner-release.json` to `website/assets/cursiv-owner-release-U116.json`, add
`docs/U116-RELEASE-VERIFICATION.md`, open the PR, merge, then `node cloudflare/publish.mjs`
(needs the Cloudflare login) and check it live.

The site in `main` already points at **U115** (PR #78) but is **not deployed yet**. Running
`node cloudflare/publish.mjs` now publishes the U115 pages, if you want them live before U116.
