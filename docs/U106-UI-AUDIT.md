# U106 researcher interface audit and first preview

2026-10-26. Application baseline is U105 at `79a1636`; changes remain uncommitted.
This is a source/UI audit and synthetic Qt validation, not a study with unfamiliar human participants.

## Existing components retained

- The conversational interface, saved-conversation sidebar, local-model setup and settings are retained.
- `launcher/field_notebook.py` remains the actual notebook form, table, linked-correction, integrity,
  export, import and signing-key UI. The new presentation embeds it in the main window.
- `cursiv_engine/core/documents.py` remains the imported-library implementation. No alternative stores,
  migrations or implicit file-access grants were added.
- Existing chat action confirmations and application-owned receipts remain authoritative.

## Friction and first changes

| Current behavior before this work | Beginner expectation | First preview / remaining work |
|---|---|---|
| Ordinary chat is central, but four research capabilities are not named together. | Recognize the four common jobs immediately. | Persistent Record Observation, Ask Cursiv, Research Files and Field Notebook actions above all views. |
| Starter observation leads with `log site:` syntax; input points to command help. | Describe a measurement naturally. | Natural-language labelled example and plain input hint; Record Observation focuses chat and shows guidance without sending. |
| Research imports sit under Memory & Knowledge. | Find research reports directly. | Dedicated Research Files view in the same window, with import, selected-document question prefill and explicit removal confirmation. |
| Notebook opens as a separate modal window. | Inspect records without leaving the main research interface. | Existing real notebook embedded in a scrollable main-window view; Back to chat preserves the current conversation and unfinished message. |
| First-run Getting Started opens another modal dialog. | Brief guidance they can dismiss or revisit. | Inline skippable introduction, collapsed to a slim reopen button below 600px window height. Sample is labelled “Example only — not saved” and never enters the composer or notebook automatically. Manual Getting Started uses the same view. |
| Model picker has a large fixed minimum width. | Primary controls fit smaller desktop windows. | Picker can shrink; embedded notebook's action strip wraps into two rows. Zero horizontal notebook scrolling measured at 1120 and 780 window widths. |
| Document success/failure can require reading command output. | Clear operation result. | Indexed filenames or per-file failure shown only after the existing import returns. Failed parsers do not produce a success label. |
| Notebook and imported documents are not isolated by workspace project. | Know which records a view can access. | Explicitly label imported library as available across workspaces and notebook as all entries. No project selector or isolation claim added. |
| Entry fields and low-level export/verification controls require prior knowledge. | Recognize record, correction, integrity and export paths. | Existing controls preserved and now directly reachable; broader plain-language response work belongs to the natural-language phase. |
| Settings/help and source details contain technical terms. | Understand routine state, inspect details when needed. | Existing settings and source evidence retained; a fuller terminology pass remains outside this first UI preview. |

The visible conversation sidebar already exposes Notebook, Memory & Knowledge, Tools, Settings and Help.
An older hidden control sidebar is separate; this change does not mistakenly remove the visible navigation.

## Scope and safety boundaries

- Switching actions never sends a chat message, saves a field observation, confirms an action or changes
  a model setting. An unfinished message and conversation history survive view switches.
- Documents appear only after explicit import through the existing APIs. Removing an imported copy has
  an inline confirmation and preserves the original source file.
- The sample text is display-only. Screenshot records/documents are synthetic data in a separate temporary
  HOME and CURSIV_APP_DATA, with no access to the owner's research.
- Notebook data, verification, corrections and exports continue through their existing code.
- No version bump, new model options, Field Station changes or project-isolation migrations.

## Validation and previews

Before changing this UI, captured actual Qt widgets at normal and minimum window sizes:
`bench/results/U106-ui-before-normal.png` and `U106-ui-before-minimum.png`.

After previews use actual Qt widgets with synthetic local files and records:

- `bench/results/U106-ui-after-normal.png`: main interface and labelled sample.
- `bench/results/U106-ui-after-minimum.png`: minimum 780 × 520 window.
- `bench/results/U106-ui-after-files.png`: imported synthetic protocol.
- `bench/results/U106-ui-after-notebook.png`: actual notebook with a synthetic record.
- `bench/results/U106-ui-after-notebook-minimum.png`: same embedded notebook at minimum width.

Offscreen Qt uses Segoe UI explicitly, matching existing repository rendering tests. AI startup and
background updater/phone/tray work are disabled for screenshots; images do not claim live-model results.

Initial targeted UI group: 44 passed. Expanded UI/notebook regression group:
140 passed in 15.59 seconds, saved in `bench/results/U106-research-ui-tests.xml`.
After the final compact-guidance adjustment, all 9 new UI probes passed in 2.01 seconds;
`bench/results/U106-research-ui-responsive-tests.xml` records that check. The combined final suite passed
2253 tests with 15 skips in 501.01 seconds; see `bench/results/U106-researcher-validated-full-tests.xml`.
Checks cover no automatic sends/saves, view ownership in one top-level window, preserving drafts,
labelled sample data, real document import and confirmed removal, error results, responsive width,
and existing notebook/correction/feedback behavior.

## Remaining limits

- The embedded notebook retains its existing long form and uses vertical scrolling. This is deliberate
  component reuse rather than a new notebook implementation.
- Imported library and notebook project labels do not enforce project boundaries. A project selector
  would be misleading without further storage/access work.
- Existing advanced tools and notebook follow-up pickers/confirmations remain available as before.
- The preview is not a packaged installer or evidence of improved human task completion. First-time
  human tests, physical portable-workspace tests and the remaining researcher-plan phases are still needed.
