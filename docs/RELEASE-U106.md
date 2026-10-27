# Cursiv v3.14-U106 — research in one window

The reviewed first increment of the researcher-experience plan makes existing desktop capabilities easier
to find and use. [Implementation evidence and limits](U106-PREVIEW.md).
[Release verification](U106-RELEASE-VERIFICATION.md) records the tagged builds and published assets once checked.

**Four everyday actions, one main window**
- Record Observation, Ask Cursiv, Research Files and Field Notebook stay visible. The existing notebook
  and imported-document library open inside the main window, with a return to chat that preserves a draft.
- Skippable inline guidance explains where observations, documents and memories belong. Its labelled sample
  is never sent or saved automatically. Smaller windows collapse the guide to keep room for chat.

**Describe a reading, then check its preview**
- Supported ordinary measurement sentences become editable confirmation cards without a model call.
  Missing temperature scales block saving. Reported clock times and days remain notes; Cursiv does not
  invent an observation timestamp, AM/PM, coordinates or sample identifier.
- Explicit desktop memory saves wait for confirmation, including model-assisted interpretations and numbered
  choices. Changing conversations clears pending cards.
- A conversational correction can identify one current reading from an actual notebook receipt in that
  conversation. It previews a linked correction and preserves the original record. Ambiguous, stale or
  assistant-prose-only targets do not execute.

**Find the records you meant**
- Supported historical notebook questions preserve dates, sites, samples and measurement filters through
  the native read path, including yesterday and last weekdays. Results show the searched scope, identifiers
  and saved local timestamps.
- Research-file imports report the actual outcome. Removing an imported copy requires confirmation; the
  original source file stays unchanged.

**Measured source checks**
- Frozen synthetic probes: deterministic action/clarification routing **10/18 → 18/18**, exact notebook
  record selection **3/12 → 12/12**, and unrelated recall requests left alone **8/8** in both runs.
- A separate fresh set first scored **11/12**. The missed dated-record phrase was retained as measured,
  then fixed with a regression; that set is no longer untouched. These are native-routing checks, not
  live-model accuracy or evidence of improved human task completion.
- Before the version bump, the combined source suite passed **2,253 tests with 15 skips** and the separate
  USB gate passed **45 tests**. A persistence-test helper was corrected to isolate subprocess app data;
  the data-protection guard remained intact. Tagged build, CI and installer results belong in the release
  verification report and are not assumed here.

**Known limits.** This release does not complete the entire researcher-experience plan. The imported library
is available across workspaces, and notebook project labels are not isolated project boundaries. General
comparison of unspecified reports, broad conversational exports, comprehensive date-scoped aggregate
statistics, physical filesystem/drive-removal tests and first-time human usability studies remain unfinished.
Existing export controls continue to work. Date filtering uses saved local recording timestamps; reported
observation times remain notes. No science/overconfidence rule improvement or model-option change is claimed.
The experimental Field Station is unchanged.

The installers have no Windows Authenticode signature or Apple notarization. Mac packages are built and
self-tested in CI, not validated on a physical Mac. Nothing has been independently reviewed. The existing
owner identity authenticates final package bytes separately from operating-system code signing.
