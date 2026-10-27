# U106 researcher experience — reviewed preview

This records the source preview the owner reviewed and approved. The owner has now authorized committing,
pushing, releasing and publishing this increment as U106. Release progress is recorded in U106-HANDOFF.md;
publication is confirmed only in the eventual U106-RELEASE-VERIFICATION.md. Existing baseline evidence is retained.

## What you can review

- Four persistent actions: **Record Observation**, **Ask Cursiv**, **Research Files**, **Field Notebook**.
- Research Files and the actual existing Field Notebook open inside the main window, with a return to chat.
  Moving between views keeps an unfinished message and conversation history.
- Inline, skippable getting-started guidance explains observations, documents and memory. Its example is
  labelled **Example only — not saved** and never sends or writes sample data. Small windows collapse the guide.
- Supported ordinary measurement sentences become a confirmation preview without a model call. For example,
  “Water temperature was 21.4 degrees Celsius at Willow Basin around 2:15.” A missing scale stays unknown
  and blocks saving. Stated clock times/days stay reported notes; the application does not invent AM/PM,
  observation timestamps, coordinates or sample identifiers. Edit restores ordinary wording.
- Desktop memory saves wait for confirmation, including model-assisted interpretations and numbered choices.
  Confirmation runs the existing checked native writer once. Cancellation and conversation switching preserve
  the boundary; inferred memories still use the existing suggestion flow.
- Supported historical questions search validated records by place, measurement and date, including yesterday
  and last weekday. Native notebook reads retain those filters and show the searched scope, IDs and local timestamps.
- A correction phrased as “I recorded the wrong temperature earlier. It should have been 20.4.” can use a real
  notebook receipt from this conversation to identify one current reading. It shows the existing linked-correction
  preview. Missing, ambiguous, forged-prose or stale targets do not execute. The original entry stays intact.
- Research-file import reports actual outcomes; removal of an imported copy requires explicit confirmation.
  The original source file stays unchanged.

## Before and after evidence

These are automated native-routing probes over synthetic data, not model-accuracy or human-usability scores.

| Probe | Before | After |
|---|---|---|
| Correct deterministic action/clarification result | 10/18 | 18/18 |
| Correct exact notebook record selection | 3/12 | 12/12 |
| Unrelated recall requests left alone | 8/8 | 8/8 |

The action probe explicitly disables local-model interpretation; neither run saves observations. The recall
probe seeds actual synthetic records, verifies their chain, compares exact record IDs and checks unchanged
notebook bytes. It uses the same frozen question hash before/after. Latency is recorded in raw artifacts;
the baseline includes unhandled fast paths, so no response-speed improvement is claimed.

Fresh source-route probes initially scored 11/12. The missed “Find records at [place] from [date] to [date]”
phrase was retained as measured, then fixed with a focused regression. That set is now observed and must not
be described as untouched or as an original 12/12 result. Review also found and fixed a classifier-confirmation
bypass and a trailing-day/site-name error before the final suite.

Evidence: `bench/results/U106-researcher-actions-{before,after}.json`,
`U106-researcher-recall-before.json`, `U106-researcher-recall-after-final.json`,
`U106-researcher-heldout.json`; cases/runners are indexed in CODE-MAP.md.

Targeted final boundary/label regressions: **132 passed in 13.67 seconds**.
UI/notebook group: **140 passed in 15.59 seconds**; final responsive UI probes: **9 passed in 2.01 seconds**.
The isolated full run exposed an existing persistence-test helper inheriting the outer app-data override.
Its subprocess environments now point to their copied app. Data guards were kept intact, and the affected
persistence, verification and final action tests passed **95/95 in 15.80 seconds** after that fixture fix.
Only synthetic temporary files were involved. The earlier failed full-run evidence is retained.
Final USB gate: **45 passed, 2,219 deselected in 84.07 seconds**. This is automated coverage, not physical filesystem or drive-removal testing.
Final full suite: **2,253 passed, 15 skipped in 501.01 seconds (8m 21s)**, with zero failures or errors.
JUnit: `bench/results/U106-researcher-validated-full-tests.xml`. Skips are Mac Keychain (1), supplied Vosk
zip verification (1), and opt-in live self-knowledge tests (13). This suite also includes the USB-marked tests.
No commands remain running.

## Actual Qt previews

The images use real application widgets and separate synthetic data. AI startup, updater, tray and phone
background work are disabled during capture. They show interface behavior, not live-model evaluation.

- [Main view](../bench/results/U106-ui-after-normal.png)
- [Small window](../bench/results/U106-ui-after-minimum.png)
- [Research files](../bench/results/U106-ui-after-files.png)
- [Embedded notebook](../bench/results/U106-ui-after-notebook.png)
- [Embedded notebook, small window](../bench/results/U106-ui-after-notebook-minimum.png)
- [Original main view](../bench/results/U106-ui-before-normal.png)

## Limits and next work

This is the first increment of the supplied plan, ready for visual review after regression validation.
It does not complete every requested phase.

- True isolated research projects are not implemented. Workspace grants remain enforced filesystem boundaries;
  the imported library is available across workspaces, and notebook project labels do not restrict retrieval.
  The interface says so explicitly. No storage migration or path change was introduced.
- General comparisons of unspecified documents, broad conversational export requests, comprehensive date-scoped
  statistics and all possible natural-language phrasing remain further work. Existing import/export/correction
  controls continue to work.
- Date filters use saved local recording timestamps. Reported observation times remain notes and are not treated
  as precise event timestamps.
- No unfamiliar human users have been recruited or timed. Physical filesystem/drive-pull testing and an installed
  application walkthrough are still outstanding. No improved human task completion is claimed.
- Earlier answer-quality findings and remaining original U106 core work remain documented in U106-BASELINE.md.
  This preview does not change science/overconfidence rules, safety text, station code or Gemma options.

The owner approved this preview and subsequently authorized commit, push, release and publish.
