# Cursiv U106: Researcher Experience & First-Time Usability

> Owner-supplied plan, originally titled U107. Numbered U106 after verifying that the latest GitHub release is v3.14-U105 and no remote U106 tag exists. Existing U106 work consists of baseline tests and documentation; see U106-BASELINE.md and U106-HANDOFF.md. This copy changes the version label only.

## Mission

Make Cursiv intuitive for a first-time researcher who has no prior knowledge of the application.

Right now, Cursiv feels easy to its creator because he understands the underlying systems, the correct commands, the expected response structures, the file organization, and how to phrase requests to get the desired results.

**That is not an acceptable dependency for a research product.**

A new researcher should be able to install Cursiv, open it, and immediately understand how to record observations, retrieve information, work with documents, and preserve their research without reading technical documentation or learning special prompt formats.

The goal is not to make Cursiv less capable. The goal is to make its capabilities accessible without requiring users to understand how they were implemented.

## Initial Instructions for Codex

Repository: `Cursiv-Local/Cursiv`

1. Read `CLAUDE.md`, `HANDOFF.md`, and `docs/CODE-MAP.md`.
2. Review the current UI architecture and existing user workflows.
3. Review the latest U106 changes before making modifications.
4. Identify existing components that can be reused.
5. Create `docs/U106-HANDOFF.md` and maintain progress notes throughout development.
6. Preserve the existing desktop application's functionality and security boundaries.
7. Do not modify the experimental Raspberry Pi Field Station or unrelated product editions.
8. Do not perform a wholesale UI rewrite unless the existing architecture makes targeted improvements impractical.

## 1. Identify the Expert-User Dependency

Conduct an audit of how users currently interact with Cursiv.

Identify every situation where successful use depends on knowing:

- Specific command syntax.
- The correct way to phrase a question.
- Which feature or tool to invoke.
- Internal file or folder locations.
- The difference between memory, notebook entries, and working files.
- How to request retrieval from previously saved information.
- How to format observations for reliable recording.
- When explicit confirmation is required.
- How to export, transfer, or verify information.
- How to interpret system responses and technical status messages.

Document each friction point with the current behavior, expected beginner behavior, and proposed solution.

**Core principle: The user should not need to learn how Cursiv thinks in order to use Cursiv effectively.**

## 2. Natural Language Should Be the Primary Interface

A researcher should be able to communicate with Cursiv naturally.

These examples should work without special command structures:

**Recording observations**

"Water temperature was 21.4 degrees at Willow Basin around 2:15."

Cursiv should recognize that this may be a field observation, extract the available information, and offer to save it.

It should not invent missing metadata.

**Retrieving information**

"What was the water temperature at Willow Basin yesterday?"

Cursiv should search the appropriate authorized research records, identify matching observations, and return the answer with a source reference.

If multiple records match, it should distinguish them.

**Working with documents**

"Compare the measurements in these two reports."

Cursiv should identify the referenced documents from the active project or request clarification when necessary.

**Correcting information**

"I recorded the wrong temperature earlier. It should have been 20.4."

Cursiv should identify the likely record, display the proposed correction, and require confirmation before creating a linked correction entry.

The original record must remain intact.

**Remembering research context**

"Remember that we're studying seasonal changes in this lake."

Cursiv should recognize the memory intent, show what will be stored, and follow the existing memory confirmation process.

Do not silently store arbitrary conversational information as permanent memory.

## 3. Improve Intent Recognition

Audit and improve how Cursiv distinguishes between:

- General questions.
- Research document retrieval.
- Field notebook recording.
- Notebook retrieval.
- Record corrections.
- Memory creation and retrieval.
- File operations.
- Calculations.
- Research comparisons.
- Export requests.

The system should not require the user to specify the underlying subsystem.

For example, "What did I record last Tuesday?" should trigger an appropriate search of authorized records rather than a generic language-model response.

Use deterministic routing where practical, with model-assisted interpretation where necessary.

Do not let the language model fabricate successful operations.

If an action fails, report the failure clearly.

## 4. Simplify the Main Interface

First inspect the current interface and identify opportunities for targeted improvement.

Do not replace the entire interface by default.

A first-time researcher should immediately recognize four main capabilities:

1. Record Observation
2. Ask Cursiv
3. Research Files
4. Field Notebook

These should be discoverable without navigating technical settings.

Keep the conversational interface central.

Add contextual shortcuts where useful, but avoid turning Cursiv into a rigid form-based application.

Advanced tools, model configuration, diagnostic controls, and internal settings should remain accessible without dominating the everyday experience.

## 5. Introduce Research Project Context

Evaluate the existing workspace architecture before introducing new storage structures.

Ideally, a researcher can select or create a project and work within its context.

Example:

**Project: Willow Basin Water Study**

- Field observations
- Research documents
- Project-specific retrieval
- Relevant memory
- Exports
- Verification history

Project boundaries must be explicit.

Do not allow retrieval from unrelated projects without authorization.

Preserve compatibility with existing workspaces and portable USB storage.

Avoid unnecessary migrations.

## 6. Make Responses Easier to Understand

Currently, response quality depends partly on the user knowing how to request structured output.

That should change.

Cursiv should automatically choose an appropriate presentation based on the task.

Examples:

**Simple factual question:** Provide a concise answer and source.

**Document comparison:** Show the main differences, supporting evidence, and uncertainties.

**Field observation:** Show a clean preview of extracted measurements before committing.

**Calculation:** Show the verified result, units, and relevant calculation details.

**Record retrieval:** Show the matching record, timestamp, and provenance.

**Failed operation:** Explain what failed and what the user can do next.

Avoid unnecessary headings, repeated disclaimers, excessive self-analysis, and long technical explanations.

Keep responses readable without requiring the user to say "format this properly."

Do not add an expensive second language-model pass merely to beautify every response. Prefer lightweight formatting and structured tool results.

## 7. Make System Status Human-Readable

Translate technical states into understandable language.

Examples:

- "Saved locally"
- "Record verified"
- "No matching observation found"
- "Waiting for confirmation"
- "Document indexed"
- "Working offline"
- "Export complete"

Allow researchers to inspect detailed technical information when needed.

Verification must be based on actual verification results, not assumptions or language-model statements.

Never display a successful save, verification, or export status unless the underlying operation succeeded.

## 8. Improve First-Run Onboarding

A new user should understand Cursiv's purpose within the first minute.

Evaluate adding a short introductory experience explaining:

- What Cursiv does.
- How to start a research project.
- How to record an observation.
- How to import research documents.
- How to retrieve previous information.
- How offline operation works.
- Where research data is stored.

Provide a guided first observation using clearly labeled sample data.

Do not mix demonstration records with real research records.

Allow experienced users to skip onboarding.

Preserve existing Ollama and local-model setup workflows.

## 9. Improve Error Recovery

A beginner should not be left wondering what went wrong.

If a request is ambiguous, ask a short clarification question.

If a document cannot be found, explain which authorized scope was searched.

If an observation is incomplete, identify only the missing information needed for the operation.

If the AI cannot reliably interpret a request, provide a safe alternative.

If the user asks for something unsupported, explain the limitation without implying that the entire task is impossible.

Do not silently invent data, sources, file paths, or successful actions.

## 10. Preserve Research Integrity

Usability improvements must never weaken Cursiv's core protections.

Preserve:

- Append-only field notebook behavior.
- SHA-256 chain verification.
- Linked corrections rather than destructive edits.
- Explicit confirmation before consequential writes.
- Authorized file access boundaries.
- Offline network restrictions.
- Source attribution and provenance.
- Separation of model-generated content from verified records.
- Portable workspace integrity.
- Existing security controls and regression tests.

Convenience must not come at the expense of research integrity.

## 11. Test With Beginner Language

Create a new usability benchmark using prompts that do not contain Cursiv-specific terminology.

Examples:

"Save this water reading."

"What did I write down yesterday?"

"Find that report about soil contamination."

"Did the temperature go up between these samples?"

"I made a mistake in my last entry."

"Can you put all my observations into a spreadsheet?"

"Where did my notes go?"

"Does this work without Wi-Fi?"

"Show me where that number came from."

"Bring up everything from the lake project."

For each test, evaluate:

- Whether Cursiv understood the intent.
- Whether it selected the correct operation.
- Whether it found the correct information.
- Whether the response was understandable.
- Whether it preserved security boundaries.
- Whether it asked for clarification appropriately.
- Whether the user needed special syntax.
- Whether it falsely claimed an action succeeded.

Include negative and ambiguous cases.

Do not optimize exclusively for these exact prompts. Test paraphrases and previously unseen requests.

## 12. Measure Improvements

Establish a baseline before changing behavior.

Track:

| Metric | Objective |
|---|---|
| First-try task completion | Increase |
| Correct intent routing | Increase |
| Unnecessary clarification questions | Decrease |
| Special commands required | Reduce toward zero for common tasks |
| Successful natural-language retrieval | Increase |
| Incorrect record selection | Decrease |
| Unsupported success claims | Zero |
| Average response latency | No material regression |
| Existing regression tests | Remain passing |

Separate automated benchmark results from actual human usability testing.

Do not claim improved human usability based solely on synthetic prompts.

For human testing, recruit unfamiliar users and measure task completion, time, errors, and requests for assistance.

## 13. Development Strategy

Implement improvements incrementally.

Recommended order:

**Phase 1: Audit**

Identify usability friction and document current behavior.

**Phase 2: Natural-language interaction**

Improve intent recognition, retrieval routing, and clarification behavior.

**Phase 3: Response clarity**

Simplify response presentation and technical status messages.

**Phase 4: Interface improvements**

Add or refine discoverable actions using existing UI components.

**Phase 5: Onboarding**

Introduce a beginner-friendly first-run experience.

**Phase 6: Validation**

Run regression tests, natural-language benchmarks, offline tests, portable-workspace tests, and first-time user tests.

After each phase, update `docs/U106-HANDOFF.md` with completed work, test results, remaining issues, and the next action.

Do not sacrifice reliability to finish more features.

## 14. Definition of Done

U106 is successful when a researcher unfamiliar with Cursiv can:

1. Open the application and understand its primary purpose.
2. Create or select a research project.
3. Record a field observation using ordinary language.
4. Retrieve that observation without knowing its filename.
5. Import a research document and ask questions about it.
6. Identify where an answer came from.
7. Correct a previous observation without destroying its history.
8. Export research records without navigating internal directories.
9. Understand whether an action succeeded or failed.
10. Complete common workflows without learning Cursiv-specific prompt syntax.

Any incomplete capability must be documented rather than represented as finished.

## Final Direction

Cursiv should feel like a research companion, not a technical system that requires the researcher to learn its internal architecture.

The creator already knows how to use Cursiv because he built it. That knowledge must not be a prerequisite for everyone else.

**The researcher should understand their research. Cursiv should handle the complexity of the software.**

Prioritize intuitive workflows, reliable natural-language interaction, trustworthy records, and clear feedback.

Do not rebuild what already works.

Do not add features simply because they are impressive.

Make the existing capabilities easier to discover, easier to use, and harder to misuse.

**The ultimate test: Hand Cursiv to someone who has never heard of it. Can they conduct useful research without being coached?**

That is what U106 needs to prove.