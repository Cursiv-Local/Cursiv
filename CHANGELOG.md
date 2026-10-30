# Changelog

## 3.14-U111 — Reliability, routing and model transparency (2026-10-30)

Native notebook routing and confirmation preservation; claim-specific science checks; conditional research constraints; exact provider/model selection and transport provenance. Reconstructed Qwen checks and validation limits are documented in U111-VALIDATION.md.

## 3.14-U110 — Natural-language self-inspection and notebook reliability (2026-10-29)

- Self-inspection requests preceded by instructions or conversation ("Do not recommend features.
  Inspect your source...") now reach installed-source inspection; safety, workspace, fiction and
  per-turn permission checks still read the whole message.
- Questions about self-inspection itself select `self_inspection.resolve`, `prepare` and the
  `_chat_inner` handoff as evidence instead of the startup pipeline; "identify/which function"
  lookups rank declaration names above file-path words. The evidence checker is unchanged.
- Includes the U109 post-release repairs: natural notebook read/verify/export wordings, linked
  measurement corrections, memory fragment resolution with edit previews, saved style preferences
  in the style block, calculator provenance for overconfidence notes, and witness-gated PDF and
  hash-chain explanations. Evidence: docs/U109-POSTRELEASE-VALIDATION.md.
- Before tagging: full Windows suite 2,664 passed/15 skips/19 subtests; USB gate 45 passed.

## 3.14-U109 — Reliable installed-source inspection (2026-10-28)

- Route implementation questions to bounded, hash-checked installed source before workspace,
  notebook and saved-memory actions; preserve per-turn restrictions and separate evidence scopes.
- Trace actual build/startup, UI, facade, backend, local-model, verification and rendering roles
  using parsed declarations, conditional imports, lazy bindings and static callback/call evidence.
- Distinguish verified syntax from inferred explanations, missing matches, denied access and stale
  source. Fix Python source line references after Unicode separators inside string literals.
- Use current AST witnesses for reviewed startup, regex, timeout, memory, portable-copy, notebook,
  document-scoring and response-check explanations. Audit output stays a read-only hypothesis.
- Before version preparation: Windows2584 passed/15 skips/19 subtests; USB45 and workspace63 passed.
  Fifteen development probes include five real Qwen requests and ten native outcomes; four general
  narratives remain partial. Evidence and limits: docs/U109-VALIDATION.md and docs/U109-HANDOFF.md.

## 3.14-U108 — Core reliability and automatic source inspection (2026-10-28)

- Preserve permitted reads alongside read-only restrictions; route source investigations separately
  from notebook operations and keep workspace reads within their existing authorization boundary.
- Repair notebook sample/record-ID lookup and explicit confirmation previews; procedural instructions
  stay out of saved observations, and linked corrections retain their original history.
- Automatically inspect versioned public application source for implementation questions and current-chat
  follow-ups. Check fingerprints across Windows/Unix newlines and keep source explanations/reviews local.
  Critical confirmation/correction/fallback rules use native explanations conditional on inspected source
  witnesses; changed witnesses fail closed. General model interpretations remain fallible.
- Quote available conversation history, handle incompatible units natively, and isolate explicit brief
  banter from unrelated memories, documents, plugins and workspace coding instructions.
- Before version preparation, Windows2508 tests/15 skips/19 subtests passed. Evidence, retained failures
  and tone limits: docs/U108-VALIDATION.md and docs/U108-HANDOFF.md.

## 3.14-U107 — Dependable research profiles (2026-10-27)

- Repair advertised plural agent commands; use shipped and personal profiles through one bounded,
  deterministic selector, respecting explicit names and rejecting over-budget role lists.
- Give individual/group runs one authorized evidence snapshot. Compute notebook checks and full-scope
  statistics in code, show coverage/omissions and preserve failed evidence through later stages.
- Check profile drafts and synthesis against supplied references, quantities, units and action records;
  share attempted-request limits across transports, retries, review and rewriting.
- Replace placeholder queue completion with deliberate local read-only execution, durable claims,
  explicit outcomes, retained history, cancellation and reconciliation before uncertain retries.
- Bind delayed session notes to their original conversation/person/workspace and destination; profile
  and native-command results do not start an extra unbudgeted summary model call.
- Validation, performance limits and release progress are tracked in docs/U107-HANDOFF.md.

## 3.14-U106 — Research in one window (2026-10-26)

- Four persistent actions: Record Observation, Ask Cursiv, Research Files and Field Notebook. The existing
  notebook and imported-document library open inside the main window; navigation preserves an unfinished
  message. Skippable inline guidance labels sample data clearly and never sends or saves it automatically.
- Supported ordinary measurement descriptions receive an editable confirmation preview. Unknown temperature
  scales block saving; reported times and days stay notes rather than invented observation timestamps.
- Desktop memory saves wait for confirmation, including model-assisted interpretations and numbered choices.
  Contextual corrections use an actual notebook receipt, append a linked correction and keep the original;
  ambiguous or stale targets do not execute. Pending cards are cleared when conversations change.
- Notebook reads retain date, site, sample and measurement filters, including yesterday and last weekdays,
  and show the searched scope with record identifiers. File imports report real outcomes; removal of a
  library copy requires confirmation and leaves its original file unchanged.
- Automated synthetic probes: deterministic action/clarification routing 10/18 → 18/18; exact record
  selection 3/12 → 12/12; unrelated recall requests left alone 8/8 in both runs. These are not live-model
  accuracy or human-usability scores. A separate fresh probe set first scored 11/12; the missed dated-record
  phrase was then fixed with a regression, without relabelling that result as held out.
- The pre-release source suite passed 2,253 tests with 15 skips; the USB gate passed 45 tests. Restart-test
  subprocesses now isolate their own app data instead of inheriting the outer test run's configuration.
- Limits remain: no isolated project scopes, general unspecified-report comparison or broad natural-language
  export workflow; date-scoped aggregate statistics and human usability studies are unfinished. Existing
  exports remain available. No science/overconfidence rule, model option or Field Station change is claimed.

## 3.14-U105 — Fixes from an outside review (2026-10-26)

- A drive's signing key can be protected with a passphrase (Field Notebook: Signing key…). Same key, so main
  computers keep accepting its shares; locked after each start until unlocked, and never quietly replaced.
  Making a drive for a named person warns the key is readable until protected.
- Strict team import (every photo required; `field log import --strict`): a notebook with a missing or
  damaged photo is refused whole and nothing from it is copied. The usual import is unchanged.
- The Vosk voice model is checked against its SHA-256 before use; downloaded zips (Vosk, Ollama) are unpacked
  with path, link, file-count and size limits, all or nothing (core/safe_zip.py).
- A test keeps release notes, verification documents, the README and the website's signed manifests in step.

## 3.14-U104 — Field Station preview, team-drive fixes (2026-10-26)

- **Field Station preview** (Raspberry Pi 5, browser interface; not validated on a Pi yet): a local web
  server for Cursiv's engine with sign-in, encrypted notebook unlocked from the browser after a restart, the
  field notebook (record, correct, search, verify, export), station health with every reading labelled real,
  derived, simulated or unavailable, read-only drive discovery, safe shutdown, and hardware simulation
  scenarios. Plan, status and API: docs/FIELD-STATION-PLAN.md. The desktop app is unchanged.
- Import reports name the scientist on every line; Make a Cursiv USB shows every notebook without scrolling,
  keeps the name box's label and says "1 entry"; the dissolved-oxygen check catches a saturation figure
  given as a range.
- Website: cursiv.us/field-station (the preview, with real screens) and cursiv.us/team-drives.
- Moved to U105: drive signing-key passphrase, strict photo-complete import, voice-model checksum, a
  release-document check.

## 3.14-U103 — Team field drives, overconfidence check, silent-error lint (2026-10-25)

- A team with one main computer: each scientist gets a drive made in their name, records on any PC
  (the main computer included), and the main computer takes the drives one at a time. Every entry and
  photo arrives in that scientist's name, byte for byte; the main computer's own notebook is never
  replaced. Before this, a drive used on two PCs was refused at import, work typed on the main computer
  was skipped, and "Bring drive data here" let each drive's notebook replace the last one.
- Each field notebook has its own identity (an id and a name) that travels with it. Name it in the Field
  Notebook (Name this notebook…) or with `field log name <name>`. Existing notebooks keep their id.
- Making a drive, choose which notebooks on the computer it carries; none is included unless ticked.
- Team exports (CSV, JSON, GeoJSON) say whose notebook each entry and photo came from.
- A damaged photo in a team copy is now repaired on the next share instead of staying damaged.
- The mandatory USB checks now include a team of 20 drives (1,200 entries with photos), damage on a drive,
  a drive pulled mid-import, and choosing whose work goes on a drive.

- When you ask about one reading, a look or one sample and the answer settles it anyway ("No, your meter
  isn't broken", "Yes, you can drink it without treating it"), Cursiv adds a line saying what the answer rests
  on and how to confirm it. Measured on the local model: 6 of 6 such answers on the set it was tuned on, 1 of 1
  on a held-out set, with 2 false notes there that are now fixed (bench/overconfidence/RESULTS.md).
- The dissolved-oxygen check no longer mistakes your own reading for a saturation figure.
- Storage code may no longer ignore an error without saying why (a test enforces it). It found three:
  a damaged territories file was overwritten (now moved aside), Start over could leave a locked login file
  behind while looking successful, and a removed account's security answers could stay if the write failed.
  Security answers are now saved atomically.
- Guessing security answers is slowed down: after 5 wrong tries, a wait that doubles up to an hour, kept
  across restarts.
- Phone link: a memory containing a key, token or password is never put in the summary stored on cursiv.us;
  a failed upload is reported instead of called "shared"; only real images from the phone are shown.
- USB: removed an unused function that could erase a drive's personal data.
- Chat lookups and notebook reads word results the same way.
- New app icon (the Cursiv logo); the website uses it too.
- Removed unused code (an old response scorer and a retired loader). Tests added for the problem report, the
  confirm card and the phone sync, which had none.

## 3.14-U102 — Reliability: OS-enforced isolation, verified calculations, recovery (2026-10-25)

An engineering reliability release: no new features, the existing ones made harder to break.

- Plugins, Forge self-tests and Codex test runs run under limits Windows enforces (a Job Object): no
  other programs, capped memory and CPU time, no clipboard, stopped with Cursiv. If the limits can't be
  applied, nothing runs. Code runs no longer see your environment variables. macOS and Linux get
  resource limits only.
- A 237-case calculation benchmark against published values (NIST, APHA, IUPAC) runs on every change.
  It found and fixed: temperatures below absolute zero were converted, negative dissolved oxygen gave a
  negative percentage, a negative dilution volume lost its sign, an impossible dilution was left to the
  AI, knots were slightly rounded, and conductivity measured at 25 °C got no answer.
- The field notebook's 13 integrity scenarios (edits, deletions, reordering, power cuts, concurrent
  writers, corruption, export round trips) are tested together; a passing check now says what it does and
  doesn't prove.
- Encryption: a full disk or a damaged encrypted file is an error, never empty data, and the copies made
  at encryption can be written back out to a new file.
- Docs: threat model update, supported-platform matrix, recovery procedures, notebook integrity results.
  CI keeps machine-readable test results for every platform.

## 3.14-U101 — Starter profiles, field formulas, safer storage (2026-10-25)

- Five profiles come with Cursiv, ready to use: @field (Field assistant), @checker (Data checker), @report
  (Report writer), @protocol (Protocol helper), @writer (Writing helper). Each is a markdown file
  (`cursiv_engine/agents/starters/`); its `reads:` line says what Cursiv's code shows it (your notebook,
  your documents, a calculation), read only. No profile can save, change or delete anything.
- The Data checker's findings (duplicate sample IDs, missing units, values that aren't numbers, entries with
  no site or sample) are worked out by code; the model only explains them.
- The Protocol helper answers only from your imported documents, with pages, and says so when they don't
  cover the question instead of guessing.
- Numbers and units in a profile's answer that aren't in your records get a note under it.
- Editing or teaching a starter makes your own copy; `agents ask` uses at most three of your own agents.
- Field formulas are worked out by code: conductivity corrected to 25 °C (APHA 2510 B), discharge (with the
  0.85 surface-float coefficient), percent oxygen saturation, µS/cm and mS/cm, molar solutions. On a benchmark
  of 14 field calculations the local model went from 9 right to 14 (0 of 4 trick questions calculated).
- Code that Codex test-runs now runs under the same guard as plugins: no network, programs or files outside its
  own folder, even when the code tries to hide it. A refused run is never sent back to be "fixed".
- The test suite also runs on Linux in CI.
- Login files are written so a power cut can't half-write them, the accounts list keeps a backup, and a
  damaged one is restored from it or reported. It's never read as "no accounts" (which would offer Create
  Account over an existing setup).
- Phone uploads are kept encrypted on an encrypted computer; one too big to encrypt goes to its own folder
  and Cursiv says so each time you receive. Imports are unpacked encrypted inside the notebook folder, never
  in the system's temp folder.
- Damaged lines in saved notes or session history are kept and now reported in `status`, instead of being
  skipped without a word.

## 3.14-U100 — Records you can trust, memory you can see (2026-10-25)

- Session notes: each conversation keeps a short note (goal, what was done from Cursiv's own records,
  decided, open, next) and picks up where you left off ("Picking up: …").
- Suggested memories: what Cursiv guesses about you is asked about ("Remember this?" Save / No), never
  saved silently. What you say outright is still saved.
- `memory folder`: your memory as readable .md files with a MEMORY.md index (on a USB drive, the
  drive's folder; on a computer, a readable copy where you choose).
- "when I say the creek I mean North Creek" teaches Cursiv your words; `workspace map` drafts a
  CURSIV.md folder map. Both help plain-words actions; neither grants new abilities.
- From the owner's U99 test run (each with a regression test):
  - Field notebook: plain-words records get a confirm card from Cursiv's own parser (W-001 had been saved as
    "ORION = -742"); codes stay out of `site` unless you call them a site; "verify … ORION-742 …" runs the
    real chain check and lists what it found; "Correct W-001 temperature from 18.6 to 18.9" appends a linked
    correction (the original stays) and the history shows both. Optional `project` field.
  - "What did I ask three messages ago?" is answered from this conversation; another conversation's
    exchanges no longer reach an ongoing one; the old PiForge registry is no longer put into chat.
  - "Correction: X, not Y." updates the saved memory, keeping the old value as history.
  - Numbers: a correct median is no longer withdrawn (it was checked against the mean); "to six decimal
    places" is honoured and never called exact; oxygen saturation uses the Benson & Krause / APHA equation
    (the model had invented one); invented experiment numbers and impossible coordinates get a note.
- Suggested memories now actually appear (held-out: 20% -> 90% on the first run, 0 sensitive), with health,
  money and secrets never offered. Session notes keep only lines in your own words; `session note` shows it.
- The app uses https://cursiv.us.

## 3.14-U99 — Conversational actions, operational self-knowledge (2026-10-25)

- Say it normally: "Add a note that North Creek was 14.2 C and cloudy", "work in my Field Data folder",
  "go offline". The local model turns it into one of Cursiv's own commands, Cursiv checks every value
  against what you wrote, and anything that changes something waits on a Save / Edit / Cancel card.
- Cursiv knows what it is: one capability inventory answers "does Cursiv have an updater / online AI /
  dependencies…?" from its records and live settings, and an inactive feature is never called missing.
- Claims of verification need a record: "I checked the source", "verified", "no correction needed" get a
  note when Cursiv has no record of that check; "you said X — check it" is answered from the records and
  says plainly when an earlier answer was wrong.
- Writing is not doing: posts, emails and announcements are written, not refused; writing about Cursiv
  sticks to what it does; absolute privacy promises get the true statement under them; fiction is labelled.
- New requests get new writing: session memory no longer feeds earlier posts into writing requests.
- `self map` and a complete code map (docs/CODE-MAP.md).

## 3.14-U98 — Plugins isolated, notebook encrypted, clearer chat (2026-10-25)

- Plugins never run inside Cursiv any more. Every plugin call, and every Forge test
  of a new plugin, runs in its own short-lived process with no secrets in its
  environment, a time limit, and a guard that refuses network access, starting other
  programs, native code and files outside the plugin's own folder. The installed app
  runs plugins itself (`Cursiv.exe --plugin-runner`); no separate Python is needed.
- The field notebook is encrypted with your conversations and memories: entries,
  photos and imported team logs. Reports, exports and shares stay readable. A computer
  already on U97 encrypts its notebook at the next unlock, after making recovery copies.
- A clearer chat: four starter cards in a new chat; answers worked out by Cursiv carry
  a green "Worked out by Cursiv · no AI model" badge; notebook, memory and file saves
  and offline on/off show as receipt cards; a one-time tour after the first AI answer;
  errors say what happened and what to do next, with Open Setup or Send a problem report.
- Custom agents (`agent new …`, `@name`) are encrypted too, and their built-in
  instructions no longer talk about "his family".
- Fixes from the U97 test run: a bare `file list` lists the workspace; a removed
  letters command shows what you typed above its note.
- Failed session-log writes are recorded instead of silently dropped.
- Docs: README and the privacy page describe always-on encryption; HANDOFF.md keeps the
  current rules, with history moved to docs/HANDOFF-HISTORY.md.
- Moving data computer → USB → another computer was tested on real hardware with U97.

## 3.14-U97 — Trust fixes, encryption always on, removals (2026-10-25)

- Cursiv no longer pretends to change files. "Add a line to notes.txt saying …"
  is a real append that asks first; "Delete notes.txt" gets Cursiv's own answer
  (it never deletes files). A model reply that claims a file was saved, updated
  or deleted without a real result is replaced with "Action not confirmed".
- Plain unit conversions ("3 miles in kilometres") and speed × time questions are
  answered by Cursiv's calculator, with no AI model. Field-log averages, minimums
  and maximums come from the notebook and list the records used.
- The model's own "✅ Verified: Yes" and "No model was used" lines are removed;
  the source line says what really answered.
- "What day is it?" is answered from this computer's clock.
- Conversations and memories are always encrypted on a computer. The first start
  asks for a passphrase (at least 16 characters) and encrypts what is already
  there; an interrupted first encryption finishes at the next start. A Cursiv USB
  drive stays readable; moving data to and from a drive decrypts and re-encrypts
  it, so USB transfer keeps working.
- Removed: family letters, the legacy vault, personal letters, the public board,
  the mailbox and the council. Data already saved on a computer is not deleted.
- Plain MIT license.
- Smaller fixes: a poem about a field notebook is no longer a notebook save;
  `curiosity` shows notebook lines instead of raw JSON; `memory cleanup` flags
  inferred "Cursiv was built by …" memories; old pages no longer default to
  llama 3.2.

## 3.14-U96 — One personality, open system, self-awareness, USB gate (2026-10-24)

- Cursiv has one personality, the same in every conversation: curious, calm, warm
  without gushing, a light dry humor, honest, on the person's side. The seven
  selectable tones are gone; learned style preferences ("keep answers shorter")
  still apply.
- Thought experiments, hypotheses, fiction and creative writing are explicitly
  welcome. A reply that claims it can't do a creative request and then does it
  anyway now shows only the work.
- Owner mode is removed: no owner code unlocks anything.
- `memory cleanup` lists saved notes and memories that mislead answers (old
  guardian-era replies, outdated answers about Cursiv's features, test records,
  inferred preferences against speculative thinking). `memory cleanup remove …`
  removes only what you pick, after copying it to a backup folder.
- Cursiv says it is made by Cursiv Local, an independent open-source project.
- Cursiv can look at itself, read-only: `self source <words>` / `self read <path>`
  (its own code and docs), `self prompt` (the instructions actually sent for your
  last answer, kept in memory only) and `self stores` (what is saved, where, and how
  it reaches answers). Questions about how it works or why it answered something
  are grounded in these, labelled by source.
- Privacy questions ("does anything I type leave my computer?", "is my data
  private?") get an answer from Cursiv's live settings, not the AI model: which
  keys, Cloud backup, web search, update checks or the phone link can go online.
  "How do you remember things?" gets the reviewed memory explanation.
- File tools are offered to the model only when a workspace is enabled.
- "Make a Cursiv USB" never copies your AI keys unless you tick the separate
  "Also copy my AI keys" box (off by default). Without it, a drive keeps exactly
  the keys it already had. `memory cleanup` also flags style preferences that are
  really captured content.
- The USB function is tested every time: a full end-to-end USB cycle runs before
  each commit (`.githooks`), on every push and PR, and in the release builder,
  which also starts the built app from a USB layout.
- Locked isolated Windows source **1,865 passed / 1 platform skip**; hosted Mac
  **1,850 / 16 skips**; USB gate passed on Windows and Mac; required workspace gate
  **63**. Published with owner-signed Windows and Mac packages; the Windows package
  passed a start from a USB layout. [U96 verification](docs/U96-RELEASE-VERIFICATION.md).

## 3.14-U95 — Bring USB data back to a computer (2026-10-24)

- "Make a Cursiv USB…" has **Bring drive data here**: conversations, notebook
  entries, memories and settings that are new or newer on the drive come back into
  Cursiv on this computer. Anything newer on the computer is kept.
- The files are copied and checked first, then put in place the next time Cursiv
  starts, before it reads any data, so nothing in use is overwritten and the drive
  can be unplugged in between. Each file is compared again at that moment; a file
  the computer already has is backed up first, and a report lists every decision.
- Each file goes back to the folder this computer's Cursiv reads it from. Saved
  keys are encrypted again for this Windows account. Accounts, passwords, logs and
  device identity are never brought over. With encrypted storage on, encrypted
  stores are skipped and listed.
- **Check drive** now reports both directions. A `config.json` with the same
  settings and keys counts as the same, whether its keys are readable or encrypted.
- The website sends `no-transform` on every page, so Cloudflare no longer inserts
  its Web Analytics script.
- Locked isolated Windows source **1,819 passed / 1 platform skip**; hosted Mac
  **1,804 / 16 skips**; required workspace gate **63**; website **22**. Published with
  owner-signed Windows and Mac packages. [U95 verification](docs/U95-RELEASE-VERIFICATION.md).

## 3.14-U94 — USB startup fix and drive check/update (2026-10-24)

- Fix a Cursiv USB made with "Include my memories" not starting: the first start
  found two versions of the same data files and stopped on every launch. Now the
  newer copy of each file is kept, the replaced one is saved in
  `Home\.cursiv\backups\`, and startup continues. Nothing is deleted.
- Personal data on a drive is compared file by file: new files are added, files
  newer on the computer are updated, and anything newer on the drive is kept. A
  log that only grew counts as newer. Each copy is checked byte for byte.
- "Make a Cursiv USB…" has a **Check drive** button that reads the drive and lists
  what is out of date without writing anything. For a drive that already has Cursiv
  the main button reads **Update USB**.
- Program updates never copy data into the drive's program folder, and older data
  folders such as `.cursiv.moved-<date>` are never pruned.
- New `tests/test_usb_sync.py`. Locked isolated Windows source **1,812 passed / 1
  platform skip**; hosted Mac **1,797 / 16 skips**; required workspace gate **63**;
  website **21**. Published with owner-signed Windows and Mac packages.
  [U94 verification](docs/U94-RELEASE-VERIFICATION.md).

## 3.14-U93 — Readable chat code and website polish (2026-10-24)

- Published latest U93 and updated the website. All **21 website tests** and
  **49 anonymous production checks** passed; signed packages and hashes are public.
- Display inline commands and code blocks in Consolas on Windows, with platform
  fallbacks, at the same size as normal chat text. Apply the typography during
  streaming, final rendering and reopening older chats. Preserve code text and
  Markdown formatting; no additional model call or conversation rebuild is added.
- Add deterministic coverage for streaming/final typography, old saved HTML,
  unchanged history, point/pixel sizes and idempotent formatting. Locked isolated
  Windows checks: **1,805 passed / 1 platform skip**; focused compatibility **86**;
  required workspace gate **63**. Hosted Mac: **1,791 / 15 skips**. Both
  tagged frozen apps passed. [U93 verification](docs/U93-RELEASE-VERIFICATION.md).

## Website — Tester download placement (2026-10-23)

- Move the testers page's Windows download and setup/Mac buttons below the
  closing thanks, after the testing and feedback instructions.
- Published to Cloudflare deployment `e89c6d19-786e-4431-bb9e-34e4e5963202`.
  All 21 website tests and 6 live checks passed.

## Website — Secondary tester link (2026-10-23)

- Move Help test Cursiv below the homepage hero's download/setup buttons as an
  18px blue text link with a small arrow, underline and keyboard focus indicator.
  Remove the full-width banner above navigation and refresh the stylesheet URL.
- Update the existing homepage layout assertion for the new link position.
- Published to Cloudflare deployment `5f6cab4f-2da4-4a32-a8ca-175d3d5478be`.
  All 21 website tests and 7 live checks passed, including the link position,
  refreshed styling, tester card, existing custom 404 and canonical redirect.

## Website — Off the map (2026-10-23)

- Make the map a fixed full-page background with a dark readability overlay;
  keep navigation visible above it instead of stacking the illustration below
  the text on phones. U92 website checks: 21/21 passed.
- Add an illustrated contour-map 404 page with a one-time mint trail animation,
  reduced-motion support, and home/download/tester links. Include it in the
  website build and configure static hosting to return it with HTTP 404.
- Build and desktop/390px browser preview checks passed. Website tests remain
  17/21: the four existing U92/U91 release-evidence mismatches are unchanged.
  Published to the existing Cloudflare Worker with the Cursiv C expedition stamp.
- A subsequent U92 deployment replaced the initial website deployment. Restored
  the page and hosting configuration in the U92 release checkout; its 21 website
  checks passed. Deployed version `52cefbd3-bddf-4672-970c-a33c47a1c94f` and
  verified the live browser preview, nested missing-path HTTP 404 response, and
  preserved U92 homepage.

## 3.14-U92 — feature discovery and live-transcript repairs (2026-10-23)

- Published latest U92 and deployed the website. All **47 anonymous production
  checks** and **21 website tests** passed; current hashes and release evidence
  are public. The existing tester banner and other chat’s artwork are preserved.
- Tagged Windows/Mac packages passed their frozen checks and have independent
  owner signatures. See [U92 release verification](docs/U92-RELEASE-VERIFICATION.md).
- Ask “What can Cursiv do?” for a short application-owned explanation of notebook,
  calculations, documents, authorized files, memory/notes and ordinary conversation.
  A new-chat suggestion fills the input without sending; the guide works offline
  without model inference, file reads or saves, including before model setup.

- Native combined version/offline replies accept punctuation and common wording.
- Streaming and final Markdown preserve literal `<file>`/`<folder>` instructions;
  reply HTML is disabled while Markdown links, tables and code remain supported.
- An explicit imported-document question with no matching passage receives a
  native retrieval result. No model continuation invents document access or facts;
  attached material and emergency paths retain their existing handling.
- Added bounded explanations of identical code versus different memory context,
  and a balanced moral-realism argument/objection pair. Broader philosophical
  prompts retain the shared uncertainty policy and model-compliance limits.
- Current tone travels in a separate, bounded system block through compaction.
  Brief mode requests 1–3 sentences/about 60 words for ordinary prose; explicit
  detail, code, tables and necessary warnings take precedence. No answer truncation
  or additional model formatting call was added.
- Exact transcript regressions are in `tests/test_u91_transcript_followup.py`.
  Final locked U92 Windows suite: **1,798 passed / 1 platform skip**; required
  workspace gate: **63 passed**. One synthetic local Qwen brief-prompt spot check
  returned 42 words; broader live-model compliance remains a manual check.
  These fixes are included in the U92 installers; historical U91 assets are unchanged.

## 3.14-U91 — workspace files and philosophical uncertainty (2026-10-23)

- Published owner-authenticated Windows/Mac installers as latest and deployed the
  website. All **45 anonymous production checks passed**, including actual signed
  downloads, the blue tester link, release evidence, canonical routes and admin denial.

- Final locked Windows source checks: **1,749 passed / 1 skipped**; hosted Mac
  **1,735 / 15 skips**. Both tagged frozen apps and all protected-main gates passed.
  All **21 website checks** passed. Final installer bytes have independent owner proof.

- Added shared local/cloud instructions for contested philosophical and normative
  questions: acknowledge disagreement, fairly present positions, separate empirical
  evidence from value premises, and avoid unsupported definitive verdicts.
- Added bounded application-owned overviews for moral truth, free will,
  consciousness, ethical theories and aesthetics, including short follow-ups.
  Explicitly requested arguments retain the conversational model path.
- Preserved the complete policy through prompt compaction and provider tool mode;
  native replies require no model, lookup or tool action. Factual/safety questions,
  file commands and attached-document discussions keep their existing paths.
- Added regression coverage for neutral overviews, perspective requests, provider
  prompts, restricted turns, attachments and compaction. Technical guidance records
  the implementation sources and model-compliance limits.
- Validation: **171 focused/compatibility tests passed** (including 50 new
  philosophy regressions); full isolated Windows suite **1,749 passed / 1 platform
  skip** in 228.27 s. Tested Python files match the final working source.

### Natural workspace file operations

- Website: moved Help test Cursiv above the homepage navigation as a wide blue
  gradient link to `/testers`; retained the primary gold download actions.
- Expanded deterministic create/append/read/search phrasing, including empty file
  creation, curly quotes, partial names and “the notes file”/“that file”.
- Recent-file references use confirmed conversation receipts and bounded native
  lookups. Measurement payloads use exact user text, never model claims or invented values.
- Added concise native receipts, unique-file search counts and plain-language
  missing-information/ambiguity messages. Existing-file approval, explicit overwrite
  verification, workspace protection and restricted/offline gates remain intact.
- Added exact-prompt and release-gate regressions, dedicated PR/main jobs, isolated
  check runner and pre-tag main-CI validation. Main branch protection now requires
  both workspace jobs, both source suites and security, including administrator pushes.
- Workspace checkpoint before the philosophy policy: **63 focused gate tests passed**; full isolated suite
  **1,699 passed / 1 platform skip** (215.21 s). Mac CI is also a required PR gate.
- Updated native coding help and contributor/technical release guidance. U91
  passed protected-main checks, tagged builds and owner proof;
  final installer/platform results are recorded in the [U91 verification report](docs/U91-RELEASE-VERIFICATION.md).

## 3.14-U90 — engine and local storage maintenance (2026-10-23)

- Published owner-authenticated U90 Windows/Mac installers and deployed the website;
  independently checked public installer hashes, tester links and counter removal.

- Removed the public website download counter, its unavailable message and counting
  explanation from the homepage and download page. Public pages no longer request
  GitHub totals; installer links and private statistics remain unchanged.

- Simplified README into a short user guide; moved feature controls, portable/phone
  setup, release procedures, benchmark context and historical evidence links to TECH.md.

- Renamed the engine package to `cursiv_engine` throughout imports, build/CI,
  tests and documentation. Persistent data folders and record formats are unchanged.
- Added optional, default-off passphrase encryption for saved conversations,
  memories and covered derived stores/backups. Startup unlocks before chat loads;
  app-closed migration uses encrypted recovery snapshots, exact-byte checks,
  resumable state and an OS data lease. Notebook data, workspace/documents, logs
  and explicit exports/training data remain outside coverage.
- Updated privacy, threat-model and data-location guidance. No owner data was
  migrated. U90 prepares these changes for an owner-authenticated installer release.
- Consolidated command results/runtime types in one engine API while retaining
  the chat facade's class identities and command order. Moved personal dialogs
  out of the main chat panel; letter/vault commands and shortcuts now respect
  Show personal features. Existing personal data/backends are retained.
- Updated the architecture flow/ownership map, contributor quick start, README,
  evidence index and handoff. Flagged remaining non-UI launcher responsibilities.
- Preserved historical-tag rebuild checks by discovering the engine version file
  inside immutable older tags. Checked both the actual U89 tag and current HEAD.
- U90 Mac source/build checks passed **1,622 / 15 skips**; both tagged frozen
  apps passed. Release dependency/static gates passed.
- Final Windows source suite: **1,636 passed / 1 skipped** (222.38 s), compared
  with **1,594 / 1** before and after the mechanical rename. **21 website tests**
  passed after build-only. The frozen development bundle passed **ALL PASSED**,
  including full window construction, pinned release identity and notebook signing.
  Its production Python matches the final source. Existing high-severity/
  high-confidence Bandit gate: **0 findings, 0 scan errors**.
- Packaging validation used the existing release builder's sanitized environment.
  A direct diagnostic build inherited the editor's incompatible Poppler ICU DLL
  and failed Qt loading; using the existing release environment resolved it.
  No release-process workaround or system DLL change was introduced.
- Not executed here: Mac runtime/packaging and physical encrypted USB persistence
  on a second PC. Synthetic restart/drive relocation, read/write failures and
  interrupted migration are tested. Encryption activation/passphrase backup are
  deliberate owner actions; no real data was migrated.

## v3.14-U89 — workspace routing and owner release authentication (2026-10-23)

- Published as latest with verified owner-signed Windows/Mac artifact manifests.
  Windows source checks passed 1,594/1; hosted Mac 1,580/15 (passed/skipped),
  both packaged checks passed, all 21 website tests and 38 public checks passed.
  The website now displays the actual installer hash and owner fingerprint.
- Add bounded local file/content search, natural creates/appends and source-file
  precedence over notebook keywords. Preserve authorization and confirmation;
  compound file tasks explicitly leave later steps unexecuted.
- Add owner-signed release manifests with a public key pinned in the app. Keep
  the private signing key Windows-user protected outside GitHub and OneDrive;
  verify installer bytes before download trust and again before execution.
- Harden export path inventories against symbolic links, junctions, hard links
  and unsupported objects. Preserve existing notebook data and chain formats.
- Lock/hash release dependencies, record build provenance and add CI vulnerability
  and high-severity static checks. Clarify non-security SHA-1 cache uses without
  invalidating stored cache keys. Guard model-lookup completion after window close.
- Windows CA signing and Mac notarization remain unavailable; owner signatures
  do not remove Windows publisher warnings. Signing-key recovery backup, account
  protection and physical clean-machine/USB persistence checks remain owner tasks.
- [Owner signing and recovery](docs/OWNER-RELEASE-SIGNING.md),
  [engineering audit](docs/ENGINEERING-AUDIT-20261023.md), and
  [U89 release notes](docs/RELEASE-U89.md) record evidence and limitations.

### Remaining 2026-10-22 live-transcript gaps

- Add native cubic-metre flow conversion, consumption duration and hiking-arrival
  answers; retain code receipts without a contradictory model draft.
- Route the no-signal phone-import question to the shared field-help instructions.
- Match descriptive forget requests conservatively, verify deletion, and show
  record IDs when multiple memories match.
- Block the restricted instruction-override wrapper and support an authorized
  first-N-lines file excerpt on read-only turns.
- Retain actual calculation/reference evidence with desktop answers for native
  bleach-source follow-ups; combine native version/offline state and keep emergency
  action/medical-advice denials short.
- Exact changes, regression results and limitations:
  [live-transcript follow-up](docs/LIVE-TRANSCRIPT-GAPS.md). These previously local
  repairs are included in U89 after the owner's publication authorization.

## v3.14-U87 - Phone Help links and tester feedback (2026-10-22)

- Publish U87 as latest with publicly verified Windows/Mac installers and
  checksums. Deploy the testers page and website evidence; 1,495 Windows tests
  passed (1 skip), 1,485 on Mac (11 skips), plus 20 website tests and 34 public
  release/site checks. Installers remain unsigned.

- Add exact application-owned phone pointers to short Help, field help and the
  existing notebook explanation; keep graphical links clickable and avoid duplicate
  phone instructions. Preserve storage/import/chain and command behavior.
- Add a secondary homepage tester button and `/testers`, with visible email and
  GitHub issue links, no form/signup and page-specific privacy headers.
- Bump app, launcher and installer/output names together. Exact checks and hashes:
  [U87 release verification](docs/U87-RELEASE-VERIFICATION.md).


## v3.14-U86 - Native trust boundaries and focused conversation (2026-10-22)

- Publish U86 as GitHub latest, with verified Windows/Mac packages, checksums
  and build/publication evidence. Deploy the website to the existing Worker;
  29 public release/site checks pass. Preserve the unavailable-counter warning,
  unsigned-package limits and historical model scores.

- Extend conservative closer cleanup to casual/philosophical turns and inline
  sentences. Preserve explicit suggestions/questions, quotes, code and warnings.
- Withhold unrelated saved facts and saved-conversation search in light chat;
  preserve explicit/relevant recall and active-thread history. Keep philosophical
  questions out of operational FAQ/self-report interception and guide short,
  specific answers without truncating the body.
- Add native talk-only help and relayed-model/thread explanations, retaining the
  actual offline provider-skip note. Pasted model labels grant no tool authority.
- Final versioned Windows suite: 1,492 passed, one Mac-only skip; 20 website
  tests passed. Retain the unscored nine-turn real-model replay and its remaining
  verbosity, closer and memory-description failures.
- Add exact transcript regression prompts, retrieval/call spies, prompt capture
  and real Qt dispatch checks. Combine the earlier local fixes below in the new
  immutable U86 release; retain U85's published benchmark and assets as history.
- Bump app, launcher and installer together. Actual tests, hashes, hosted jobs
  and publication outcomes: [U86 verification](docs/U86-RELEASE-VERIFICATION.md).

### Earlier local U84 live-test follow-up on U85, included in U86

- Expand native feature guidance and hard-stop blocked actions before backend,
  source, model or memory-formation calls. Preserve read-only reads as requested.
- Add explicit flow-rate/volume/duration calculations and deterministic draft
  withdrawal for detected calculation, source and execution conflicts. Refuse to
  select a dose from conflicting supplied instructions, including `adv-011`.
- Keep pure state answers independent of memory reads; recognize sentence-prefixed
  fake writes. Extract review eligibility and honor explicit full checking while
  keeping desktop review after the streamed draft. See
  [native trust-boundary evidence](docs/NATIVE-TRUST-BOUNDARIES.md).
- Add 83 native-boundary regression cases; final isolated full suite: 1,428
  passed, 1 macOS-only skip. Preserve the published model benchmark and installers.
- Route phone capture, .cursivsync import, sample-ID clashes, correction and
  second-laptop sharing questions to native feature help. Use application-owned
  version/state replies; report recorded model identity without guessing a provider.
- Accept observation/note aliases and explicit comma-delimited fields/measurements,
  preserving ordinary/quoted commas and exact values. Clarify missing content.
  Block restricted corrections before any model/backend continuation.
- Return short verified notebook receipts with actual IDs/fingerprints, a clear
  empty result, and relevant site/sample context without silently saving new entries.
- Badge restrictions, expand routine source details on demand, retain meaningful
  evidence and code examples, and narrowly suppress stock closers on bounded turns.
- Strengthen proportion-draft withdrawal, retain dose/reference withdrawal, and
  cover explicit supply-duration and common arrival-time phrasing in code.
- Add guided demo prompts, verified mode changes, guarded sample cleanup and
  honest rollback/error reports that preserve unrelated settings and real records.
- Record the exact files, test runs and remaining model limits in
  [the follow-up report](docs/LIVE-TEST-FOLLOWUP.md). Update the Claude handoff,
  README, architecture, claim map and platform/USB checklists. Owner reports basic
  USB operation works; memory persistence remains untested. Signing is deferred
  until next month; encryption remains the separately approved migration plan.

## v3.14-U85 - Quiet chat feedback and notebook continuity (2026-10-22)

- Publish U85 as GitHub latest with independently hashed Windows/Mac installers,
  both checksum files, exact Windows dependency versions and verification JSON.
  Push reviewed source and deploy four updated pages to the existing Cloudflare
  Worker. All 20 website tests and 20 public release/site checks passed.
  The pre-existing counter remains unavailable; no download total is invented.
- Hosted source checks: Windows 1,267 passed/1 skipped; Mac 1,257/11. Both
  frozen full-window package checks passed. Stop the redundant publication-triggered
  Mac rebuild before it can replace already verified assets.

- Keep streamed drafts available while optional local reviews run. Show a small
  progress indicator only around an actual reviewer invocation, then a note
  count or an unavailable status. Clean reviews keep metadata without adding
  prose or reparsing the answer.
- Add application-owned tool, file, notebook and memory receipts; show current
  file-access/workspace state and per-turn talk-only/read-only limits. Preserve
  the last confirmed notebook site as conversation context, including on reopen.
- Shorten restriction confirmations without promising offline execution or
  disabling conversation history. Use restrained model guidance and precise
  persistent-memory acknowledgements.
- Include sample IDs/fingerprints in notebook confirmations. Read back saved
  notebook entries and imported copies before confirming integrity; summarize
  new-entry counts separately from received uploads, duplicates and warnings.
  Keep append-only record formats and existing authorizations intact.
- Record changed files, regressions, controlled rendering measurements and
  remaining limits in [chat feedback](docs/CHAT-FEEDBACK.md). The owner authorized
  U85 publication; tagged builds, fresh model results and actual publication are
  recorded in [U85 verification](docs/U85-RELEASE-VERIFICATION.md).

- Record fresh U85 suite 1.5 results: **153/158 (96.8%)**, below U84's
  156/158. Preserve all five failures and document an unsafe allergy-memory
  answer that passed the bounded scorer. Do not relabel historical results.
- Update current website evidence, README/build instructions, architecture,
  platform readiness and claim mapping. Record the Windows CI subprocess
  encoding correction separately from the unchanged tagged application.

## Website - General phone photo questions (2026-10-22)

- Replace the phone app's Bible-specific setup, chat example, placeholder and
  loading text with general photo/chat wording. Update its title and description;
  retain the existing visual style, manifest identity and device-linking flow.
- Replace the website Worker's `BIBLE_SYSTEM` with `VISION_SYSTEM` and use a
  neutral image-only fallback question. Ask for visible facts, legible wording
  and clear uncertainty without inventing image details. Text-only chat remains
  supported. Pairing, space tokens, storage and image upload handling are unchanged.
- Record deployment/build details in [HANDOFF.md](HANDOFF.md). No desktop
  application, installer or updater changes belong to this website follow-up.

## v3.14-U84 - Complete-window release validation (2026-10-22)

- Publish U84 as GitHub latest with verified Windows/Mac installers and checksums.
  Deploy the updated website/test evidence to the existing Cloudflare Worker.
  Independently verify public installer bytes, metadata, routes and admin auth.
  Record the existing download-counter 503 separately; no total is invented.

- Keep U83 as an unpublished candidate after its Mac screenshot check exposed
  a missing theme import in the extracted title bar. Preserve the existing tag.
- Restore the theme/JSON runtime imports and related annotation dependencies;
  add reproducing full-shell and notes-JSON regressions. Expand frozen and offline
  self-tests to construct the complete launcher/title bar/tray/chat panel.
- Bump application, launcher, installer and output names together to 3.14-U84.
  Carry forward the U83 candidate's trust, review and maintainability changes below.
- Final isolated U84 Windows source suite: 1,248 passed, one Mac Keychain skip
  (197.19 s). Complete launcher/Tools/Settings/Notebook offscreen smoke passed.
- Run the full unchanged suite 1.5 from the U84 tag: 156/158 passed (98.7%
  overall), with both failures and additional uncaught safety/reassurance issues
  documented. Keep the prior candidate run and historical U75 records intact.
- Add website release-evidence checks tying current labels, model metrics and
  the separate software-test count to recorded artifacts. All 20 website tests
  passed (18 analytics/security checks and 2 release-evidence checks).
- Update website testing/download/research sections with current source checks,
  unchanged-suite model results, failures and clearly labeled historical U75 data.
  Record actual package, CI, hashes, deployment and remaining limits in
  [U84 verification](docs/U84-RELEASE-VERIFICATION.md).

## U83 unpublished candidate - Trust boundaries and background answer review (2026-10-22)

- Bump application, launcher and installer/output names together to 3.14-U83.
  Final isolated versioned Windows suite: 1,246 passed, one Mac Keychain skip
  (213.72 s); website analytics suite: 18 passed. Build from the immutable tag
  and record frozen-app, hosted CI and public-download checks separately.
- Close follow-up trust gaps: recognize explicit no-tool/second-person privacy
  instructions, strip compound read-only prefixes without altering literal
  paths/payloads, and stop `file remember` before a memory save if its file fails.
- Generate source labels in a dedicated application module without inspecting
  answer words. Record supplied memory separately from recalled/withheld facts;
  use the same record for evidence checks and deferred review. Filter source
  footers case-insensitively and report damaged-memory errors as storage failures.
- Cap explicit Cross-check output at 400 tokens on all supported providers;
  retain ordinary chat budgets and the automatic review's 180/300-token limits.
  Explain readable API-key exports in the existing USB confirmation. Prepare
  reciprocal online-photo-chat/offline-notebook links.
  See the [trust-boundary follow-up](docs/TRUST-BOUNDARY-FOLLOWUP.md) for the exact
  audit, reproduced failures, test runs, pending release wording and limits.
- Finish desktop answers before optional model verification. Default fast mode
  skips ordinary turns and permits one short local review on eligible turns;
  deterministic evidence/safety checks remain immediate. Append labeled review
  results in the background, with copied turn evidence and stale-result guards.
- Add persistent `check off`, `check fast`, `check full` commands. Bound verdicts
  to 180 tokens and full-mode rewrites to 300; remove the ledger-only model call
  and skip a second verdict for an unchanged rewrite. Keep pending assistant
  claims out of automatic verified-memory retention. Record regression coverage
  and 10/100/1,000-message controlled measurements in
  [the answer review report](docs/ASYNC-ANSWER-REVIEW.md).
- Repair the reported U82 restricted-turn failures before notebook/memory/file
  dispatch, reference/calculation lookup and automatic learning. Confirm limits
  in application text, preserve them across draft replacement and reset per turn.
  Distinguish memory opt-outs from separately saved conversation history.
- Parse read-only workspace requests and read/summary filenames without treating
  instructions as paths. Keep generic relative paths in the authorized workspace.
- Label sources using confirmed tool results and reject model-authored source
  status lines. Stop generic and provider-native continuation after failed file
  operations. Add exact-prompt regressions and a [repair report](docs/U82-RESTRICTED-TURN-REPAIR.md).
- Extract chat prompt/context, phase orchestration, local/cloud providers,
  provider tools, streaming and completion into focused modules behind the stable
  chat facade. Pass explicit runtime services; preserve caller overrides.
- Split command dispatch into ordered domains and shared result types; separate
  desktop controls/transcript views, auxiliary shell dialogs, login recovery,
  setup checks and USB operations. Enforce a 1,200-line production module budget.
- Add coded/severity-tagged verification findings. Empty/failed checks stay
  unverified. Safety/provenance failures get notes; an eligible rewrite runs at
  most once and must pass the same evidence checks and a nonempty second verdict.
  Rejected revisions cannot leak invented replacement details into display notes.
- Reduce false web-lookup alarms for quoted/conditional examples. Add bounded
  n=0/1 inference checks and fail-closed handling in final chat checks.
  Prevent optional verification context from recalling saved memory when the
  current message forbids inspection.
- A live test exposed a detected wrong dose left in the draft under a warning.
  Detected dose/reference contradictions now withdraw model instructions and show
  the actual supplied reference, without a model rewrite or learning that draft.
- Enforce guardian/login/key protection in the shared filesystem mutation and
  confirmation pathways, including when the repository is the workspace.
- Harden the tagged Windows builder's inherited DLL search paths and packaged
  self-test gate; generate identical versioned/latest installer aliases/checksums.
- Add a separate deterministic replay and live unchanged-suite comparison;
  record raw results without editing historical cases/results. Benchmark failures
  now reject incomplete runs; new runs record a Python-source fingerprint.
- Update README, TECH, HANDOFF, architecture, verification policy, threat model,
  platform gates, public-claim evidence and the quality checklist. Encryption is
  documented separately at the owner's request; no personal data migration.
- Exact changed files, executed checks and remaining external signing/physical
  validation requirements are in [the maintenance report](docs/MAINTENANCE-HARDENING.md).
  U83 release preparation is authorized separately; publication evidence is recorded in
  [U83 verification](docs/U83-RELEASE-VERIFICATION.md). Historical U75 scores
  remain dated evidence, rather than being renamed as current-release results.

## v3.14-U82 - Grounded chat state, boundaries and dated memory (2026-10-22)

- Enforce supported per-message conversation-only/read-only/no-memory limits
  before tool planning and again at native/generic/provider execution. Treat
  quoted examples and explicit content payloads as data; prevent retention opt-out
  bypasses through automatic learning or unknown plugins.
- Use the active session's workspace/file flag for state answers and self-report
  context. Omitted state is unknown. Describe persistent selected-fact memory
  accurately, distinguish it from model retraining, and correct concrete false
  capability claims in drafts and later revisions.
- Route natural dated recall, including "passed 2 weeks", to the local memory
  backend. Report saved-date windows, actual IDs, bounded results and unavailable/
  corrupt data. Keep recall/status read-only and preserve existing storage formats.
- Preserve bounded current state and verified source excerpts during prompt
  slimming and Claude tool routing. Reauthorize source follow-up reads; check
  explicit source quotations against actual excerpts. Directory listings and
  model prose cannot establish source evidence.
- Add deterministic integration/regression coverage and a fresh-process memory
  persistence check. Update README, HANDOFF and
  [repair report](docs/GROUNDED-CHAT-REPAIR.md) with the audit, exact files,
  test runs and limitations. Final complete post-repair suite: **1,080 passed,
  1 skipped** (macOS Keychain on Windows), using isolated source/data snapshots.
- Release preparation synchronizes application/installer versions at U82 so U81
  installations can detect an update. Preserve previous release tags and user data.
  Update installer project links to cursiv.us and Cursiv-Local/Cursiv.
- Fix the Mac CI test paths to use canonical disposable folders and inject failed
  writes through the platform's actual commit primitive. Canonicalize the packaged
  notebook self-test directory too. Production symlink/junction protections remain.
- No memory migration, updater/network-policy change or website deployment.
- Publish and independently verify both Windows installer names/checksums and
  the public latest-release endpoint. Record build-environment isolation,
  source/package checks and platform automation in
  [U82 release verification](docs/U82-RELEASE-VERIFICATION.md).

## v3.14-U81 - Verified local actions, faster chat and website updates (2026-10-22)

Published on 2026-10-22 from commit 3f58754, incorporating the prior U80 work.
The earlier development reports below describe checks performed before that
publication; their U79/latest references are historical observations. U82 builds
on this source baseline.

### Homepage copy (2026-10-22)

- Reduce homepage body copy from about 2,475 to 759 words (including expandable
  text). Lead with offline Windows AI through Ollama, use four short benefits,
  and end with a direct latest-installer download. Keep setup, privacy, signing
  and benchmark limitations in expandable sections and linked guides. Preserve
  metadata, old anchors, responsive styles, the counter and separate click recording.

### Website download analytics

- Add a small download counter beside the homepage/download-page calls to action,
  using public `Cursiv-Local/Cursiv` release metadata. Sum canonical Windows/macOS
  installer asset counts across published releases; exclude duplicate latest
  copies, repeated assets, source archives, checksums and unrelated files. Latest
  stable release comes from GitHub's latest endpoint. Never infer daily history,
  unique people, installations or completed transfers.
- Reuse the existing Cloudflare Worker/static-asset/D1 deployment. Cache metadata
  for one hour, coordinate refreshes, retain labelled stale data for up to seven
  days, and back off on GitHub rate limits/network failures. Missing data never
  becomes an invented zero or breaks an installer link.
- Protect `/admin/downloads/` and its data endpoint with separate HTTPS HTTP Basic
  authentication, using a minimum-32-character Worker secret. Admin HTML is served
  only after authentication and is absent from public static assets and sitemap;
  responses are no-store/noindex with a restrictive page policy.
- Record optional installer-button clicks as Windows/Mac aggregate totals only.
  No visitor IDs, cookies, browser storage, IP/user-agent/referrer fields or event
  history are stored by this feature. Respect GPC/DNT; clicks remain separate from
  GitHub download requests and never block navigation.
- Update the website privacy policy, README, this changelog and handoff. Add
  website-only tests and an additive database migration. Configuration, exact file
  inventory, test results and publish/check steps: [DOWNLOAD-ANALYTICS.md](cloudflare/DOWNLOAD-ANALYTICS.md).
- Validation: **18 website tests passed**, static build and Cloudflare Wrangler
  deployment dry run passed. Production database/secret setup and deployment are
  still owner actions; no desktop source changed during this website task.

### Earlier pending desktop work (recorded here; code untouched by analytics task)

- **Saved Notes viewer:** read/search/filter existing note categories and full
  stored contents, integrate with chat/navigation, and preserve the existing
  archive. No unsupported note deletion or data migration was introduced.
- **Chat rendering:** 40 ms stream batches, completed-block formatting, targeted
  active-message updates, cached unchanged history and background ordered saves.
  Benchmarks cover 10/100/1,000 messages. The 1,000-message replay's median final
  readiness changed from 493.2 to 71.5 ms; this is a synthetic rendering measurement,
  not a live model-speed claim. See [performance report](docs/CHAT-RENDERING-PERFORMANCE.md).
- **Native Field Notebook:** allowlisted recording/retrieval/chain verification,
  user-only follow-up context, real record IDs, duplicate protection and GUI
  persistence. Preserve append-only corrections and existing notebook data.
- **Verified local actions:** authoritative absolute filesystem paths and exact
  read-back receipts, persisted authorized workspaces, natural-language memory
  save/recall/correct/forget/learning controls, independent outcomes, bounded local
  intent classification, and concrete Saved Notes/letter/agent/image save fixes.
- Existing desktop validation: **1,008 passed, 1 skipped** (macOS Keychain on
  Windows), isolated source/data snapshots. Live model inference and an installed
  executable restart were not claimed. No self-model/metacognition implementation,
  installer/updater edits, commit, push or deployment is implied. Full per-file
  evidence and remaining limits: [HANDOFF.md](HANDOFF.md).

## v3.14-U77 — Fixes from the first Cross-check tests (2026-10-19)
Found by testing U76's Cross-check on real answers:
- An answer that opened "No, site A does not have better survival" and ended "Therefore, site A has better survival" (3 of 4 frogs vs 60 of 100) passed Cursiv's own check; only the Cross-check reviewer caught it. Every sentence is now read: saying 75% is higher than 60% is fine, concluding one site is better is flagged, and a first line that says the opposite of the conclusion is called a contradiction.
- "This assumes 2 liters per person per day is sufficient" no longer gets an amber "contradicts" note: it's about the allocation, not the supply.
- "your saved memories" no longer appears under answers that didn't use one: words from your own question don't count, and it takes three of a memory's words (or a code or number).

## v3.14-U76 — Cross-check and quieter answer checks (2026-10-19)
- **Cross-check (new, optional):** a *Cross-check* button under the chat asks another AI to review the last answer, as a second opinion: errors, unsupported claims, missing assumptions, honest differences. It needs your own key for that company (Claude, OpenAI, xAI, or a free Gemini or Groq key), shows exactly what will be sent and to whom, and sends nothing until you press Send. Only that question and answer go; the review appears below the answer without changing it. Offline mode refuses it.
- The answer check puts far fewer notes under correct answers (17 to 4 on the U75 benchmark answers); a number the question gave that really changed is still caught.
- From a live benchmark run of U75 (bench/FAILURES-U75.md): a weekday answer is checked by the day's name, "7/8" counts as 0.875, an answer that opens "Yes, A is better" when the counts are too small to show it gets a note, and so does calling a published source "verified". Benchmark suite 1.5 adds the water-supply, small-sample, weekday and "is it safe with nothing known" cases.

## v3.14-U75 — Records that hold up, honest answers, phone over Wi-Fi (2026-10-19)
- **Cursiv USB: the drive's own AI engine gets time to start.** From a USB stick it took 46 seconds on a fast laptop; Cursiv gave up after 15 and said "Ollama isn't running". It now waits up to 2 minutes, the model menu says it's starting the engine, and `status` says which engine is answering: the drive's own, or this computer's (which only sees this computer's models; that's why a drive could answer with llama3.1 instead of qwen3).
- **Phone notebook (new):** record observations on a phone with no signal at cursiv.winklers-llc.com/notebook (add it to the home screen; it works offline after the first visit). Everything stays on the phone. *Send to laptop* makes one file (USB, AirDrop or Quick Share); Cursiv imports it through the same checks as a laptop's team share: the same entry format, fingerprints, the phone's own signature, photos by fingerprint. Field Notebook → Import from team → From the phone notebook, or `field log import <file>`. Tested in a desktop browser and by cross-checking the phone's code against Cursiv's; not yet on real phones in the field. See docs/PHONE-NOTEBOOK.md.
- **Send from a phone over Wi-Fi:** Field Notebook → Import from team → Receive from a phone over Wi-Fi shows an address and a 6-digit code; the phone opens it in its browser and picks the file. Local network only, while the window is open. The phone's send file is now a standard zip (older files still import).
- **Field records refuse more:** a share with impossible values (a latitude of 999, a time that isn't a time, a photo path outside the store) is refused whole, even when its fingerprints were recomputed; a phone's name must match its key; a photo changed after it was stored is reported and no longer signed into an export. An entry saved after a power cut is no longer lost. Exports are made aside and swapped in only once they check out, so an interrupted export leaves the last one whole.
- **Calculations in code:** water and food supplies for a group over a period (need, shortfall, how long it lasts, at the allocation the question gives, which Cursiv labels an assumption); statistics with units, sample or population SD; dates and weekdays; points along a transect; two proportions with ranges, so 3 of 4 isn't called better than 60 of 100. An answer that contradicts them ("lasts 12 days" when it's 1, "enough" with a shortfall) gets a note.
- **Honest claims:** a note when an answer says a tool ran that didn't, "no AI was involved", "retrieved from stored data" for something only in the conversation, a review or "field-tested" that isn't on record, a figure from a document as "verified", or "safe" from missing information; and when it contradicts an earlier answer. "your saved memories" is named only when the answer used one.
- **Memory:** `save this record: ...` saves exactly or says why not (too long, disk full); `recall ...` returns only what is stored. A damaged line no longer makes every memory disappear.
- **Reference:** each entry says what backs it (a published source, or none) to the model and to you; unrelated entries no longer join a question for sharing a common word; two unsourced entries with unsafe advice are held back until reviewed. Instructions inside an imported document are flagged and not followed, and your memories aren't given to the AI for that answer.
- What was tested, and what wasn't (no phone, no clean machine): docs/EVIDENCE.md.

## v3.14-U74 — Photos, safer lightning answers, accounts (2026-10-19)
- **Photos.** A paperclip on the main screen: *Add photos to a field entry* (the camera's time and GPS are kept, a blank location is filled from the photo; photos are stored by fingerprint, included and signed in exports, and carried by team sharing), or *Ask Cursiv about a photo*, read by the local image model. Reading photos is now local first; online keys only when no image model is installed and the internet isn't blocked, and the answer says where the photo went. Making images still needs an online service.
- **Lightning:** "is it safe to go back out? last thunder 10 minutes ago" gets Cursiv's own "Not yet: wait about 20 more minutes" (the 30-minute rule, counted in code) above the model's answer. Never for questions about getting to safety.
- Website: "Everything is public. Except your data." README rewritten around field research.
- **Remove an account** in Settings → Your data & account, and "start over" (remove every login, keep memories, notebook and documents), each confirmed with a password.
- **Forgot password fixed:** it used to reset the *first* account's password, checked against the first account's questions, whichever username was typed. Now every account has its own security questions (new accounts are asked for them; existing ones keep theirs), and a reset changes only the password of the account that answered. A removed account's questions go with it.

## v3.14-U73 — Signed field records (2026-10-18)
- **Signed field records** (field network Phase 0, R4): each Cursiv installation has its own signing key. Every export carries `signature.json`, a signature over the log's head and every exported file; `field log verify <folder>` says whether it checks out. USB team shares are signed and checked; the first key seen for each laptop is remembered, and later shares signed by another key (or unsigned) are refused, so another machine can't add records under a laptop's name. Shares from older versions still import, reported as unsigned.
- `docs/FIELD-NETWORK.md`: the design for a master node on local Wi-Fi (R11).

## v3.14-U72 — Mac (early) and a tidier USB (2026-10-18)
- **Cursiv for Mac, early:** a `.dmg` for Apple Silicon Macs (M1 or newer, macOS 12+), built and tested on Apple hardware at GitHub: the full test suite and a self-test of the built app. Setup installs Ollama into your Applications folder without an admin password. Saved AI keys go into the macOS Keychain; settings and memories live in ~/Library/Application Support/Cursiv. Not signed by Apple yet (first open: System Settings → Privacy & Security → Open Anyway), and not yet used by anyone on their own Mac. The USB drive stays Windows-only.
- **USB drive:** the top of the drive shows only `Start Cursiv.bat`, a start-here `README.txt` and the folders; the drive icon lives in the Cursiv folder. The README covers the first run, what to try, what each folder holds, and how to remove the accounts.
- **One model:** Setup and Cursiv USBs offer only qwen3 4B, the model Cursiv has tested. Models already installed still work.
- `Cursiv --selftest` checks that every part loads and works, without the AI model. The Windows app now finds its own icons (the tray showed a placeholder). The automatic tests run on Windows and macOS, and install the app's own package list.

## v3.14-U71 — Field work first (2026-10-18)
- **Research profile by default.** `help`, Tools, the welcome card and the empty chat lead with field work: the notebook, reports, documents, calculations, LOCAL ONLY and the demo (`help field`, `help documents`). Family letters, the legacy vault, the phone app, coding help, the council, agents and builder tools are hidden unless Settings → Appearance → **Show personal features** is on; their commands still work if typed.
- **When the AI engine is down**, Cursiv says so and gives what it has without it: its own calculation, the reference card (with 911 for emergencies), and the matching pages of your documents, plus how to restart the engine. The source line says "Written by Cursiv, no AI model". It no longer claims "Answered by Ollama" over an error.
- The Help window uses the current badge names and explains the Sources line.

## v3.14-U70 — Ready to show a research group (2026-10-18)
- **LOCAL ONLY badge:** the top of the chat says *LOCAL ONLY · internet blocked* when offline mode is on, and *Local answers · internet not blocked* otherwise. The model menu names the model answering on this computer. `status` leads with both.
- **A source line on every answer**, written by Cursiv from what it actually gave the model: Cursiv Offline Reference (entries), your documents (pages), Cursiv's calculations, web results, saved memories, or *model knowledge (not checked against a source)*. A model citing the offline reference when none was given gets a note. A question about "our protocol" that the documents don't cover gets "searched your documents: nothing covers this", not "I have no access to any protocol".
- **Field report:** Field Notebook → Report…, or `field report` (`site <name>`, `today`): a printable summary by site, every entry with its fingerprint, corrections with reasons. Exports include it.
- **Field demo:** type `demo` (or ⋯ → Field demo) for a sample stream survey and a sample protocol, kept apart from your real notebook and documents and marked SAMPLE DATA everywhere; `demo questions` lists what to try; `demo off` brings your records back. Walkthrough: `docs/FIELD-DEMO.md`.
- **Privacy:** `PRIVACY.md`, and a summary in Settings → Privacy & internet: what stays here, what can leave and when, what offline mode blocks.
- **Installer:** publisher, version and source details in the file properties, a before-you-install page (what it does, why Windows warns, how to check the download), and a SHA-256 checksum published with every release.

## v3.14-U69 — Dark by default (2026-10-18)
- **Cursiv starts in dark mode** on every install and every Cursiv USB, whatever Windows is set to. Settings → Appearance: Dark, Light or Match Windows.

## v3.14-U68 — Safer doses and warnings (2026-10-18)
- **Bleach doses are worked out by Cursiv from the reference card** (U.S. EPA), not by the AI model: strength, liters, quarts or gallons, doubled for cloudy, colored or very cold water. In the U67 benchmark run the model said "16 drops per liter" for cloudy water (the right number is 4); with this change it said 4 in 3 of 3 live tries.
- **An answer that opens "Yes, it's safe" and then says not to go gets a warning above it**, where it's read first. The model did this on "is it safe to go back on the lake 10 minutes after the last thunder?" in 3 of 3 benchmark runs.
- The dose check reads across sentences ("For 8.25% bleach … That means 16 drops per liter"), and a doubling said one sentence earlier counts.

## v3.14-U67 — For field teams (2026-10-18)

- **Your documents** (sidebar → Your documents, or `add document <path>`): import a team's PDFs and text files, kept on this computer. Answers quote them by page ("From your documents: WS-3 protocol.pdf p. 2"), and a page the answer cites that wasn't among those supplied gets a note. Each file is fingerprinted. **Answer only from my documents** (Settings) refuses anything the documents don't cover, except in an emergency.
- **Team sync without internet:** Field Notebook → **Share with team…** puts this laptop's field log on a USB drive or shared folder; **Import from team…** on the other laptops brings it in. Each laptop's log stays its own chain; a copy that was changed or cut off is refused, a history that differs is kept beside the earlier one and reported (never chosen silently), and the same sample ID on two laptops is reported. `team log` and `team log export` show and export everyone's entries. Only the field log is shared, never memories or documents.
- **Sample IDs:** a New ID button (or `sample: auto`) makes IDs like NT-20261018-001; `field log sample <id>` shows a sample's history; exports include a printable sheet of labels.
- **Distance and bearing** between two GPS points (Vincenty on WGS84, matching the published example to the millimetre), and **24-hour times** in clock arithmetic ("we leave at 14:30 for 3 h 45 min").
- **For reviewers:** `docs/FIELD-KIT-TEST.md` (the SSD kit on clean laptops), `docs/PROFESSIONAL-REVIEW.md` and `scripts/review_sheet.py` (a printable sheet of every first-aid and survival entry, fingerprinted to the exact words). Truth benchmark suite 1.4 adds 20 harder field cases.
- **Fixes from suite 1.4:** a cloudy-water bleach dose must be the card's dose or exactly double it ("16 drops per liter" now gets a note giving 4); an answer that opens "Yes" and concludes "no" gets a note that it contradicts itself; a question with numbers in it is never treated as vague ("How far is it from 44.12, -71.56 to …" was asked what "it" meant).

## v3.14-U66 — For field science (2026-10-18)
- **Field Notebook** (sidebar, or type `log site: North transect; water temp 12.4 C; 44.12, -71.56; note: turbid`). Observations are kept exactly as typed ("12.40" stays "12.40"), apart from anything the AI says. Nothing is ever overwritten: a correction is a new entry with a reason. Every entry is fingerprinted and chained to the one before, so a changed, removed or reordered entry is detected (`field log check`). Export to CSV, JSON and GeoJSON.
- **Field calculations done in code:** unit conversions (temperature, length, mass, volume, area, speed, pressure), degrees-minutes-seconds to decimal and back, UTM coordinates (checked against an independent method to half a metre), dilutions (C1V1 = C2V2), and mean, standard deviation and a 95% confidence interval. The answer is checked against the computed number.
- **Power-loss-safe saving** for memories, settings, keys, offline mode and conversations: after a crash a file is either the old version or the new one, never half of each.
- **Battery saver** (Settings → AI model), automatic while the laptop is unplugged: less memory, the model unloaded sooner, and answers checked by Cursiv's own code only.
- An answer claiming "no record in verified public databases" now gets a note that nothing was looked up.
- **"Are you offline?"** is answered by Cursiv from its real switches, and says what it can't see, instead of the model claiming it.
- **Measured:** the offline demonstration passes all 15 checks with every outside connection refused (`OFFLINE-DEMO.md`); answer speed with and without a graphics card is in `docs/HARDWARE.md` (13 s for a 120-word answer on the processor alone).

## v3.14-U65 — A sourced reference, one tested model (2026-10-18)
- **The offline reference names its sources.** 37 entries are now written from public U.S. government guidance (CDC, NIOSH, EPA, National Weather Service, National Park Service, FEMA): heat illness, frostbite, lightning, ticks, snakebites, stings, poison ivy, bears, rabies, mosquitoes, carbon monoxide, chemical exposure, food after a power outage, getting lost, concussion, cardiac arrest, seizures, altitude sickness, burns, low blood sugar, sepsis, helping an injured person, floods, wildfire smoke, tornadoes, earthquakes and flooded wells. Each card shows its source and the date it was checked; entries without a published source say so. None has been reviewed by a medical professional yet. `docs/REFERENCE.md` lists every entry.
- **One model, chosen by testing.** In a side-by-side test on the same 40 questions, qwen3 4B passed all 40 in about 10 seconds an answer; llama3.1 and gemma3 passed 35, and qwen3 8B ("Deep Think") passed 38 at five times the time and invented a treaty. So qwen3 4B is used on every computer, Setup offers only it (plus a small model for very slow PCs), and Deep Think is removed for now. Other installed models are still listed under Settings → AI model → Advanced.
- **"Is it safe?"** with nothing to say what "it" is now always gets a question back, asked by Cursiv itself.
- **Fewer false notes under answers:** "Unsupported claims: None" is no longer shown as a problem, and "I don't have a map" isn't treated as citing one. The "try council" suggestion is gone.
- **Lists display properly:** after an answer that ends in a list, the next lines are no longer numbered as part of it.
- Setup's wording says answers come from this computer unless you turn on an online option.

## v3.14-U64 — Faster, steadier, ready for the field (2026-10-18)
- **About twice as fast on small graphics cards.** Ollama was leaving much of each model on the processor. Cursiv now puts as much as fits on the card, and clears other models off it first: on a 4 GB card, the everyday model went from 16 to 37 words-pieces a second.
- **Standard or Deep Think.** The menu above the chat now offers two choices instead of model names. Standard is quick; Deep Think (qwen3 8B, when it's downloaded) reasons before it answers and takes a minute or two. Every installed model is listed only if you turn on "Advanced: show every model" in Settings.
- **Arithmetic and clock times are worked out exactly.** "Wake at 6 AM, 8 hours of sleep, 30 minutes to fall asleep" is 9:30 PM, calculated by Cursiv, not guessed by the model; an answer that disagrees gets a note. Shown sums like "17 times 23 is 381" are checked too.
- **Bleach doses are checked against the reference card,** and a vague first message ("Is it safe?") gets a question back instead of a guess.
- **Memories are honest about where they came from.** Things Cursiv picked up from conversations are always marked as guesses, never "verified", and are used only when clearly relevant. A one-time clean-up relabels older ones and moves entries that weren't facts about you (copies of answers, note lines) to a backup file.
- **Answer checking is steadier:** it no longer calls a correct answer "verified" without checking, accepts "No problems found", stops flagging correct totals, and doesn't ask for a Known/Inferred list on simple questions.
- **Field copies.** The USB maker has a "Field copy" option: the drive starts in offline mode, with no break reminders and no learned guesses. A saved note and offline mode are tested to survive a restart.
- **Pasted text keeps its shape** (line breaks, numbered lists, indents) in the conversation.
- Fixed: "translate into Spanish …" was labelled as a translation to English; hypothermia and other emergencies are recognised; answers no longer offer to find a hospital or set a reminder. The memory-search model is downloaded only by Setup, never on its own.
- The late-night break reminder can be turned off in Settings → How Cursiv answers.
- **Measured:** truth benchmark suite 1.2; the Phase 1 conversation replayed with every answer recorded in `bench/phase1/`.

## v3.14-U63 — Safer, more accurate answers (2026-10-18)
- **Corrected first-aid and water entries.** Severe bleeding, tourniquet, water purification and hypothermia are rewritten from published guidance (U.S. EPA, U.S. CDC, Stop the Bleed). Each card names its source and the date it was checked. An earlier answer told someone not to bandage a wound or use a tourniquet; the bleeding card now says: call 911, press firmly, pack the wound, then a tourniquet 2–3 inches above it, and note the time. The water card gives EPA bleach doses and says boiling and bleach don't remove chemicals.
- **Heavy bleeding is treated as a medical emergency.** "Spurting blood" or "blood everywhere" used to get no first-aid card and a reply meant for a mental-health crisis. Now it gets 911 and the bleeding steps. Cursiv's instructions no longer treat a medical emergency like a crisis.
- **Cursiv flags its own risky answers.** If an answer advises against a step the reference card above it recommends, or claims it searched databases when nothing was searched, a warning appears under it. This works during emergencies too.
- **Asks for an exact format get exactly that.** "Exactly 5 steps, one sentence each" gets 5 steps, no extra sections.
- **Less clutter under answers.** The Known / Inferred / Assumed / Unknown lines and check notes are behind "Show reasoning and checks". They appear far less often: only for checks and high-stakes questions, not every answer with a number in it.
- **No more unrelated reference cards.** When an online AI answered, Cursiv could attach entries that only shared a word with the question (water purification under a cover-letter question). It now uses the same strict matching as normal chat.
- **Fewer made-up details.** Cursiv is told not to invent your circumstances, to ask at most one follow-up question, and to say plainly that it can't set reminders or prove for itself that the computer is offline.
- **Measured:** truth benchmark suite 1.2 (125 questions). This version: 119 of 125 (95.2%). U61's code on the same questions and model: 114 of 125 (91.2%). Every answer and failure cause is in `bench/`.

## v3.14-U62 — A simpler, clearer window (2026-10-17)
- **A new, simpler window.** A clean start screen ("What can I help with?") with example questions you can click. Answers show real formatting (bold, lists), and under each one a small line says where it came from: **● Local** (this computer) or **● Online** (a service you set up).
- **You can always see what can go online.** A pill at the top right says *Local only*, *Offline mode* or *Online features on* (with the exact list), read from the same switches the network code obeys. Click it to change them.
- **Choose the AI model** from the menu at the top left; *Automatic* picks the best one for your computer.
- **Everything is one click away** in the sidebar: Memory & Knowledge (what Cursiv remembers, and a searchable offline reference), Tools (letters, translate, phone, USB, coding help, council, agents; advanced tools tucked away), Settings and Help.
- **One Settings window, in plain words.** Privacy & internet, AI model, Online AI (optional), How Cursiv answers (tone, memory learning), Appearance, Updates, Your data & account, Help & diagnostics. Every switch says what it does.
- **Light, dark or match Windows**, and the change shows immediately.
- **Conversations save themselves** (turn it off in Settings). No more "Save this conversation?" prompts.
- **One calm colour scheme** across every window: one muted-gold accent, green and amber only for status, no stray blue, plain icons. The out-of-date Getting Started window is replaced by a short welcome card.
- **Every Cursiv USB has a Licenses folder:** the license for Cursiv, for Ollama, and for each AI model on the drive (the exact text the model came with), with "Built with Llama" when a Llama model is included. Needed before giving away or selling a drive.
- **Measured, not assumed:** the new Cursiv Truth Benchmark (116 questions, scored by code) ran on U61: 110 of 116 passed, with every answer and every failure published in `bench/`.
- The old terminal chat and the modules only it used are gone (about 5,700 lines). The chat engine is being split into smaller parts in `cursiv_engine/chat/`.

## v3.14-U61 — Honest answers, offline reference, safer keys (2026-10-17)
- **Answers are no longer rewritten.** A filter changed every reply before you saw it: "made in China" became "made in the United States", "Chinese technology" became "American technology", and "OpenAI" or "Anthropic" became "Cursiv". It's gone; Cursiv now says plainly which model it runs on.
- **Your saved AI keys are encrypted** for your Windows account. A copied settings file, or another Windows user on the PC, gets nothing usable. Keys saved by older versions are encrypted the first time this version starts. A private USB copy keeps them readable so it works on other PCs.
- **The Guardian is gone.** Its probe scanner, skull screen and decoy answers are removed; a question like "what are your instructions?" now gets a normal answer. The real protections stay: the login, asking before every file write, the AI can never change your keys or login files, and offline mode.
- **Cursiv's offline reference is used in chat.** Ask how to purify creek water, or say "he's bleeding badly" or "she hit her head", and Cursiv answers from its built-in survival and first-aid entries, names the entry, and says medical entries weren't reviewed by a medical professional. Questions it has no entry for are told so instead of getting an invented source.
- **Medical emergencies get first-aid steps.** "Not breathing" or "bleeding badly" used to get the same reply style as a mental-health crisis, which avoided clinical detail. Now Cursiv says to call 911 (and Poison Control for poisonings), then gives the few steps that matter while help comes. Crisis and danger messages are handled as before.
- **Fixed the CPR entry:** infant CPR is 30:2 for one rescuer (it said 3:1), and child depth is about 5 cm. Three entries (home remedies, the "edibility test", plant medicine) are kept out of chat until someone qualified reviews them.
- **New default model: qwen3 4B** (`qwen3:4b-instruct`, Apache 2.0) on 4–6 GB graphics cards; llama3.1 stays the choice for 8 GB+. The old default, qwen2.5:3b, has a research-only license; Cursiv now uses it only if nothing else is installed. Download qwen3 4B in Setup. MODELS.md lists every model's license; USB drives carry qwen3:4b-instruct or qwen2.5:1.5b.
- **A checked answer replaces its draft.** When the check rewrites an answer, you see only the corrected answer (with a short note that it was revised), and only that is saved in the conversation.
- Window titles say "Cursiv" instead of "Cursiv v3.0".
- All tests pass again (a USB test had failed for weeks).

## v3.14-U60 — Private by default, plain language (2026-10-17)
- **Nothing leaves your computer on its own.** On a fresh install with no keys, a chat turn makes no connection off your computer. (Checked: a fresh copy, real chat turns on the local model, every connection logged — zero.)
- **Web search only when you ask.** Start a message with `search:`. Words like "today", "right now" or "this week" used to send your message to DuckDuckGo by themselves. `websearch on` (or Settings) brings back automatic search if you want it.
- **Offline mode really works.** `offline on` (or Settings) blocks every connection off this computer — cloud AI, web search, update checks, model downloads — and stays on after a restart. Your local model keeps working, and your saved keys stay saved. Before, it said "all external APIs blocked" and blocked nothing.
- **Update check is your choice.** Cursiv no longer contacts GitHub after every login. Click Check for Updates any time, or turn on `autoupdate on` (or Settings).
- **No internet check on every message** when your local model is ready and nothing online is set up.
- **Cursiv Cloud starts off on new installs**, as U57 intended — tick it in Setup or Settings, or type `cloud on`.
- **Shorter, plainer help.** `help` is a short list of everyday things; `help more` shows topics (memory, family, translate, privacy, keys, coding). Builder tools are listed only on the owner's computer. Fixed: help said `remember` searches memory — it saves.
- **Plain language throughout.** Cursiv's instructions to the AI were rewritten in plain words (a quarter of the old length, so the local model is faster too). Kept: honesty about what it can do, safety and crisis care, memory never outranks safety, and the Known / Inferred / Assumed / Unknown check.
- **Removed:** governor, overseer, trust tiers 2 and 3 (`tier 1` is now offline mode), funforge, the public board (`blast`), substrate and grow. **Renamed:** `save this`, `notes`, `translate … into …` (the old names still work).
- Tests: tests/test_netgate.py, tests/test_help.py; scripts/net_audit.py checks a fresh install's network traffic.

## v3.14-U59 — Answers are checked (2026-10-17)
- **A real check after each answer** on numbers, recommendations and technical claims: changed numbers, assumptions stated as facts and named sources nobody looked up are caught, with one rewrite. The check uses the local model, not your keys. Casual chat isn't checked.
- **Known / Inferred / Assumed / Unknown** at the end of complex answers, so guesses aren't passed off as facts.
- **Memory knows where each fact came from** (you said it, or Cursiv inferred it) and when. Conflicting memories are both shown, and no memory can override safety.

## v3.14-U58 — Trust: a login that holds, a USB that matches (2026-10-12)
- **Cursiv never opens without its login.** If the login can't load, Cursiv says so and stops (with a problem-report button) instead of opening anyway.
- **Only someone who can log in can add a login.** Type an existing username and password, then click Create Account. (Anyone at the login screen could add one before — and every login sees the same keys and memories.)
- **Security questions are required for the first account** — they're how a forgotten password is reset. "Reset Entire Account" (only offered when there are no questions) now removes every login and the saved AI keys, and says plainly that memories and conversations stay.
- **Honest about what the login is:** a lock on the front door, not encryption. The README and Cursiv's own self-knowledge now say so.
- **Cursiv USB matches the build exactly.** Files are compared by size and date (a rebuilt file of the same size used to be skipped), files a newer Cursiv no longer uses are removed, each copy is written to disk before it's put in place, and the whole drive is checked against the build at the end.
- **No leftover private data on a "fresh" USB.** If a drive once held a private copy (your memories and keys), making a fresh copy on it now removes that data — after asking. Data the drive's own user created is left alone.
- **The Ollama download for the USB is checked** against the SHA-256 Ollama publishes; a mismatch is refused.
- Tests: tests/test_trust.py (USB repeat updates, stale files, verify, interrupted copies, private-copy wipe; login fails closed, account approval, reset).

## v3.14-U57 — Honest replies, local first (2026-10-12)
- **Cursiv no longer claims things that didn't happen.** It used to say it had written files and list files that weren't there, because its instructions said it could "read, write, create, delete" files and it copied the "(Checked on this computer: …)" lines it had seen earlier in the chat. Now its instructions say exactly what it can and can't do, those status lines are hidden from what the AI reads, and any fake one it writes is removed from the reply. (Writing files still needs file access turned on and a paid xAI, OpenAI or Claude key, with every write shown for approval.)
- **Every reply says which AI answered** — "Answered by Ollama · qwen2.5:3b", "Answered by Gemini", and so on.
- **Local first, for real.** When your computer has a model, it answers first and your message stays on your PC. Free and paid keys are used when there's no local model, it can't answer, or you paste an image. (Before, any key you'd added answered first.)
- **Cursiv Cloud is off unless you turn it on** (Setup or Settings), matching what the README says.
- **Babel understands "into all the languages you can"** (and "as many languages as you can") instead of translating into languages called "All", "The" and "You". Lists like "Spanish, French and German" and names like "Mandarin Chinese" work too.
- The greeting no longer announces "14-agent council ready. All systems running." — it just says hi.

## v3.14-U56 — Clean startup (2026-10-09)
- The chat says **"Getting Cursiv ready…"** while it loads, then replaces it with one line: **"Ready. Ask me anything — or type help to see what I can do."** It used to leave "Loading Cursiv's core…" on screen and add an out-of-date paragraph about terminals and paid keys. Free Gemini/Groq keys now count as ready too.
- The status bar at the bottom left says **Ready** instead of staying on "Starting…", and the bottom right shows the real version number.
- Saved conversations: long titles end in "…" instead of being cut off, and the sideways scrollbar is gone.

## v3.14-U55 — Cleanup: one window, nothing extra (2026-10-09)
- **Only the desktop window opens.** The tray's "Open Cursiv" now opens the Cursiv window instead of the old browser chat. The old browser chat, Command Nexus, Sacred UI and terminal chat are gone, along with "Open in Terminal" and the `cursiv` command the installer used to add to PATH. Updating removes the leftover files.
- **No more background training watcher.** Training examples are added only on purpose (Training Data window, or notes converted in chat).
- **Smaller, simpler tray menu:** Open Cursiv, Getting Started, What I remember, Phone, Setup, Make a Cursiv USB, problem report, security questions, updates.
- **Fixed: sealed letters between people wouldn't open.** Each letter hides its security tag as invisible characters, and the reader stopped partway through the tag, so every letter looked tampered with and stayed locked. Letters already sent open now too — the file format didn't change. (Family letters use a different lock and were never affected.)
- **Smaller install** — the browser-interface packages (Gradio, FastAPI, Uvicorn) are no longer bundled.
- **Cleaner source code:** the repository dropped about 100 unused files (old launchers, old web server, game-bot experiments, sealed placeholder docs) and every "Crucible" stamp and hidden note aimed at AI readers. The README has a one-click download button, and TECH.md explains how Cursiv is built.

## v3.14-U54 — Cursiv on a USB (2026-10-09)
- **Make a Cursiv USB** (tray menu) — copies Cursiv, the Ollama AI engine and your AI models onto a USB drive. Plug it into any Windows PC and double-click **Start Cursiv**: nothing is installed, it works offline, and everything it saves stays on the drive. A qwen chat model and memory search are always included (downloaded first if missing); every other model is included by default and can be unticked. The full set is about 30 GB — use a 64 GB or bigger USB 3 drive or USB SSD, formatted exFAT (Cursiv warns about FAT32, which can't hold the bigger models).
- **Fresh or personal** — by default the USB starts fresh, so it can be given to someone else as their own Cursiv. Tick "Include my memories, keys and settings" for a private copy of your own.
- **Quick re-make** — making the USB again on the same drive only copies what changed, so updating it after a Cursiv update is fast.
- The terminal chat no longer opens by itself when Cursiv is started from a command window; it opens only from "Open in Terminal" or the `cursiv` command.

## v3.14-U53 — LoRA training works, images in and out, Cursiv is for anyone (2026-10-09)
- **LoRA training actually trains now.** Two bugs stopped it: the training terminal loaded Cursiv's own bundled Python 3.13 files ahead of your system Python, so PyTorch crashed on any other Python version and the trainer reported "missing packages"; and the button checked for PyTorch inside Cursiv.exe (where it never is), so it always offered to install instead of starting. The check now asks the Python that will do the training, and that Python is launched cleanly. "Merge into Ollama" had the same launch problem and is fixed too.
- **Read images for free.** Pasted images (and image uploads in Training Data) are described by Claude or GPT-4o if you have those keys, then a free Gemini key, then a local vision model through Ollama — so it works offline with no key at all. The Setup window has a new step, **Image reading model**, that downloads Gemma 3 (3.3 GB) with one click.
- **Make images.** `image <description>`, or just ask ("make me a picture of a lighthouse at dawn"). Uses a paid OpenAI key if you have one, or a free Cloudflare Workers AI account (`cloudflare <account-id> <token>`, about 100+ free images a day). Offline models can't make images — if no key is set, Cursiv says so and explains both options step by step.
- **Cursiv is for anyone.** Cursiv now describes itself as created by Joshua Winkler and owned by whoever installs it — it no longer tells people it only works for Joshua and his family. The guardrails are unchanged; "the human has final authority" now means the person who owns that copy.

## v3.14-U52 — Cursiv Forge: it grows new abilities (2026-10-07)
- **`evolve <idea>`** — Cursiv writes itself a new ability as a plugin (e.g. `evolve a command that converts recipe amounts between cups and grams`). It's checked for safety (no running programs, no network, no deleting files), tested in a sandbox, and fixed automatically if the test fails. You read the code and a plain summary; nothing installs until you type `evolve approve`.
- **Plugins** — `plugins` lists them; `plugin show/off/on/remove <name>`. Each approved plugin is fingerprinted: if its file changes, it won't load until you approve it again. A broken plugin is switched off, never crashes Cursiv. Every install is logged.
- **Tools for every AI** — ask about your computer ("how much space is on my C drive?", "what's in my Downloads?", "read notes.txt and summarize it") and Cursiv looks before answering, with Groq, Gemini or a local model. Built-in tools are read-only and never read Cursiv's own data, keys or password stores. Plugins can add tools.
- **Project memory** — Cursiv keeps a short running summary of each ongoing project you work on across chats and brings it back when it comes up. `projects` lists them; `project show/forget <name>`.

## v3.14-U51 — Learns from your corrections + tone (2026-10-07)
- **Learns how you want it to talk.** Correct it once ("too formal", "stop using bullet points", "just give me the answer", "call me Josh") and it turns that into a standing rule it follows from then on — for each person separately. `style` shows your rules; `style add <rule>`, `style forget <words>` and `style clear` manage them.
- **Tone switch.** `tone blunt`, `warm`, `brief`, `playful`, `legacy`, `teacher` or `normal` — kept until you change it.
- Style rules and tone apply everywhere: normal chat, `codex`, questions about Cursiv, and your custom agents.
- Custom agents now get Cursiv's fact sheet when the question is about Cursiv, so they stop guessing about it.
- Fact sheet corrected: exact model names, the 8k limit is for local models only, what the phone app really does (it doesn't open letters), free keys are enough (no pushing paid keys), custom agents vs. the built-in council.

## v3.14-U50 — Custom agents + real self-knowledge (2026-10-07)
- **Custom agents.** Make your own specialists in plain words: `agent new chef: plans healthy family meals on a budget`. Talk to one with `@chef <message>`, teach it lasting facts with `agent teach chef <fact>`, and ask all of them at once with `agent council <question>` — each answers from its specialty, then Cursiv combines their views. `agents` lists yours; `agent show/edit/delete <name>` manages them. Each person has their own agents.
- Ask Cursiv about itself ("how are you running?", "analyze your system", "what can you do?") and it answers from a live report of its real state — version, which AI keys are saved, graphics card, installed and loaded models, memory and coding-lesson counts, phone link, recent errors — plus its fact sheet. It no longer invents running agents, hashes or problems from its persona prompt.
- Improvement ideas are based on what that report actually shows.
- Raw provider errors like "[Groq error 413: …]" are now plain sentences ("that message was too long for Groq's free tier"), and recent ones are included in the self-report.

## v3.14-U49 — Speed + automatic conversation titles (2026-10-07)
**Speed**
- Free Groq/Gemini keys actually answer now. Groq rejected every normal chat as "too large" (Cursiv sent its full 27,000-character prompt); free providers and local models now get a compact version of Cursiv's core identity (~3,400 characters) plus your memory and the current context.
- Groq is tried first (answers in about a second); Gemini falls back across several models, gives each 20 seconds, and skips an overloaded model for 10 minutes instead of waiting on it every time.
- Every message was waiting ~4 seconds on Windows' slow "localhost" lookup before the AI was even asked. Fixed (127.0.0.1). Typical online answer: ~2 seconds, down from 15+.
- The Settings key test now sends a real chat message and shows the answer time, so "Working" means chat works.
- Local AI: detects your graphics card's memory (NVIDIA and AMD) and picks models and settings that fit it; keeps the model loaded for 30 minutes and loads it at startup when it will be used (a cold load took ~100 seconds); waits up to 10 minutes for a slow load instead of timing out at 2; turns on Ollama's flash attention and compact cache when Cursiv starts Ollama.
- Small graphics cards: normal chat keeps the already-loaded model instead of swapping to a coding model (minutes per swap); the Setup window recommends the fast 3B models.
- Background jobs (memory learning, phone sync) wait while you're chatting.

**Conversations**
- Saved conversations get a 3–5 word title about their topic automatically (e.g. "PyBullet Setup In WSL"), refined by the AI as the chat goes on. Titles you set yourself are kept. Older saved chats are retitled once.

## v3.14-U48 — Coding overhaul + the phone app knows you (2026-10-07)
**Coding**
- New coding brain for `codex` and for code questions/pasted terminal errors in normal chat: a focused coding prompt instead of Cursiv's whole persona prompt (no more council/owner text in code answers).
- Answers now list everything that must actually be done: which terminal, one-time setup, steps to repeat in every new terminal (like activating the venv), how to run it, how to tell it worked, and what to do if it fails.
- Built-in playbooks (venvs, WSL, PowerShell, Linux basics, pybullet, Node, Git, GPU) and a known-error diagnoser: paste terminal output and it explains each error and the exact fix.
- 12 worked example answers it matches and imitates (robot arm, new Python project, Flask app, APIs, CSV + charts, desktop app, GitHub, React, SQLite, tracebacks, scraping, fixing terminal errors).
- Learns as you go: remembers your terminal, venv names and setup from what you paste, and keeps coding lessons (`codex lessons`, `codex learn <lesson>`, `codex forget <words>`).
- `codex keep` saves a good answer as a new example it will imitate.
- Run-and-fix: Python it writes is test-run in a sandbox when safe, and fixed automatically if it crashes (`codex run` to rerun).
- `codex project <folder>` reads the relevant files from your project into answers.
- On GPUs under 12 GB the second (reviewer) coding model is skipped — it made answers take minutes; the run-and-fix check replaces it. Coding models get a 16k context so instructions aren't cut off.

**Phone**
- Phone conversations now teach your computer's Cursiv: lasting facts from phone chats are learned into the linked person's own memory, just like desktop chats (every 5 minutes while Cursiv is open).
- The phone app uses your memories: a short summary of what Cursiv remembers about you is shared with your phone space, so phone answers know you.
- New checkbox in the 📱 Phone window: "Let the phone app use my memories". Turning it off deletes the summary from the site.
- Phone learning retries later if no AI is available, instead of skipping messages.

## v3.14-U47 — Follow-ups keep context; Ollama hiccups handled (2026-10-07)

From a real session: `codex …` said "no local model" on a PC with 22 GB of models, the reply to "done" was a canned greeting, and the follow-up didn't know about the codex request.

- **Command answers join the conversation** (codex, council, search, babel, …), so "done" or "now add X" has context. `codex` also sees the last few messages.
- **The startup greeting is only for an actual first greeting**, never for "done", "now?" or follow-ups.
- **`codex` falls back** to your keys / free keys / Cursiv Cloud when the local AI isn't ready, instead of only failing locally; it says which it used.
- **Ollama not answering ≠ no models:** a slow Ollama (e.g. busy downloading) gets a "not responding, try again" message instead of a bogus download. And when Ollama is running but lists nothing while models sit on disk (seen for real after a reinstall), Cursiv says to restart it instead of re-downloading; **Setup → Restart Ollama** does it in one click.

## v3.14-U46 — Normal mouse cursor inside the window (2026-10-07)

After hovering a window edge, the double-arrow resize cursor stuck over the sidebar and chat: inner widgets inherited the root's cursor. The title bar, sidebar/chat area and footer now set the normal cursor explicitly, so resize arrows only appear on the edge strips.

## v3.14-U45 — Coding models in the Setup window; no console windows (2026-10-07)

- **Setup → Coding model (optional):** download qwen2.5-coder 7B (recommended for most PCs, 4.7 GB) or 14B inside Cursiv with a progress bar. The launcher's coding-model buttons open Setup instead of a PowerShell console.
- **The installer never opens PowerShell:** the optional 12-step bootstrap checkbox is gone (the script is still installed for running from source).
- **Code council uses whatever coding models are installed** (e.g. qwen2.5-coder:7b) instead of requiring the exact 14b/16b tags — with only the 7B installed it used to detect qwen, then fail asking Ollama for the 14B.

## v3.14-U44 — The 8 phases are real code (2026-10-07)

Until now the 8 phases were a description in Cursiv's instructions, and the model presented them as if they ran. `cursiv_engine/core/phases.py` now runs them on every message before the AI answers — plain, inspectable rules:

- **Energy:** stress, exhaustion, rush, shouting or the middle of the night → shorter, gentler, answer-first replies.
- **Emergency:** crisis, medical emergency or danger wording → help lines (988, 741741, 911, DV hotline) shown before the reply, and a short care-first prompt replaces Cursiv's long instructions (the care guidance used to lose out to the local model's canned refusal; now it answers warmly, and ~8× faster). Tested against false alarms ("end my subscription", "an overdose of homework", "kill this process").
- **Grounding:** the person's memories (U42).
- **Route:** code → working code; decisions → a recommendation plus the strongest counter-argument, with a one-time suggestion to try the council.
- **Structure:** how-to → numbered steps; comparisons → side by side; yes/no → answer first; "why/what is" → short plain explanation.
- **Connectivity:** online / local model ready (checked at most once a minute).
- **Future State:** goal wording → ends with one concrete next step.
- **Recovery:** after 30 messages, 2 hours, or late at night → one gentle break suggestion per session.

The `phases` command shows what each phase did for the last message. Cursiv's fact sheet now describes the phases accurately.

## v3.14-U43 — Saved conversations, resizable window (2026-10-07)

- **Saved conversations** (`launcher/conversations.py`, `launcher/conversation_sidebar.py`): a left sidebar with + New chat, 💾 Save, and the person's saved conversations (newest first; right-click to rename or delete). Nothing is saved unless the user chooses; once saved, a conversation keeps itself up to date after every reply. Each file keeps the messages (so Cursiv continues with full context) and the on-screen transcript. Stored per person in `%USERPROFILE%\.cursiv\conversations\`.
- **Asks before leaving an unsaved conversation:** Save / Don't Save / Cancel on quit (title bar ✕, tray Quit), New chat, opening another conversation, and before an in-app update closes Cursiv. `clear` now starts a new conversation.
- **Resizable and full screen:** drag any edge or corner (Windows handles the resize and snapping), □ maximizes / restores, double-click the title bar to maximize, F11 for full screen, Esc to leave it, ☰ shows or hides the sidebar. Default size 1120×740, minimum 780×520.

## v3.14-U42 — Memory that learns, per person (2026-10-07)

New `cursiv_engine/memory/semantic.py`:
- **Finds by meaning.** Facts and saved conversation notes are matched to the question with a small local embedding model through Ollama (`nomic-embed-text`, ~270 MB, downloaded once in the background when Ollama is running). Without it, recall falls back to word overlap. Used by chat and the council.
- **Learns.** After each conversation turn, lasting facts (people, preferences, beliefs, ongoing projects) are picked out in the background by the user's free Groq/Gemini key or the local model — never paid keys, never Cursiv Cloud — and saved unless already known. `memory learn off` turns it off.
- **Per person.** Facts are saved under the logged-in user; "family" facts are shared. One person's memories never appear for another.
- **What I remember.** Window (tray → What I remember…, or Settings) to see, search, add (just me / whole family) and forget memories, with the learning switch. Chat commands: `remember …`, `forget …`, `what do you remember`, `memory learn on|off`.

Tested: a question about "my Bible study" recalled "compares the KJV and NIV" with no shared words; near-duplicates skipped; no leakage between people; learning saved lasting facts from a sample exchange.

## v3.14-U41 — A council you can trust (2026-10-07)

From a real offline council run where 4 of 7 seats timed out, the refinement round had no engines, and seats invented things about Cursiv ("brain-computer interfaces", "an American system"):

- **Offline-aware:** the council checks the internet once; when offline it runs only on local Ollama instead of every seat failing on Gemini/Groq first.
- **Local queue:** seats on local Ollama take turns (one model can only think about one thing at a time); fewer seats when only the local model is available. Temporary failures (timeouts, busy, 429/503) move a seat to another engine without blacklisting the first one; only hard failures (bad key, offline, refused) do. A seat that fails everywhere gets one more turn on the local model.
- **Grounding:** every seat and the synthesis get `council/cursiv_facts.md` (what Cursiv really does — and what it doesn't) plus the user's best-matching saved notes, and are told to say "I don't know" rather than invent.
- **Anchor check:** after the final answer, Anchor lists any factual claim neither a seat nor the facts support (shown under the answer; never rewrites it).
- **Council memory:** past deliberations are injected only when the topic actually overlaps — recency alone used to clear the threshold, so unrelated recent deliberations leaked into answers.

Tested offline, local-only, with the original question: 3 seats, no timeouts, no unanswered seats, no invented features.

## v3.14-U40 — Link the phone app to the computer (2026-10-07)

A 📱 button in the title bar (and tray → Phone…) opens the Phone window (`launcher/phone_link.py`). Enter the 6-digit code from the phone app's Link button and the computer joins the same conversation: it shows every message and photo from the phone, checks for new ones every few seconds, and can send questions and photos (shrunk to 1600 px) that appear on the phone too. The link token is kept in `%USERPROFILE%\.cursiv\space.json`; Unlink removes it.

## v3.14-U39 — No time limit on answers (2026-10-07)

U38's 90-second time box stopped answers too early once the model's thinking time was counted. It's off by default now (`CURSIV_RESPONSE_SECONDS`, default 0); answers run until they finish. U38's higher length caps stay. Also: the phone page (cursiv.winklers-llc.com/app) — photo + chat Bible study, add to home screen.

## v3.14-U38 — Answers finish their thought (2026-10-07)

Replies were cut off mid-sentence by length caps (mostly 1,200 tokens), and local Ollama had only a 6,144-token context — Cursiv's instructions alone take about 6,000 — leaving almost no room to answer. Every cap is now 4,096 tokens (`RESPONSE_MAX_TOKENS`), Ollama gets a 16,384-token context, and babel, council seats/synthesis and Cursiv Cloud were raised to match. Instead of a length limit, chat replies are time-boxed (`_time_boxed`, `RESPONSE_TIME_LIMIT` = 90 s): after the limit Cursiv finishes the sentence it's on, stops cleanly and says 'continue' picks up where it left off.

## v3.14-U37 — Fix data-folder links and key checks (2026-10-07)

- U35's directory junctions for the program-folder data folders fail on some Windows 11 setups ("WinError 448: untrusted mount point"). On startup the installed app now replaces any such junction with a real folder filled from the home copy (`launcher/data_home.py`); no data is lost.
- Gemini/Groq key checks list the provider's models instead of asking for an 8-token reply (newer Gemini models could spend that on thinking and return nothing, so valid keys were rejected). Gemini calls also retry with `?key=` when the header is refused.

## v3.14-U36 — Settings window (2026-10-07)

A gear button in the top-right of the main window (next to minimize) opens Settings (`launcher/settings_dialog.py`): every AI key in one place — xAI, OpenAI, Claude, and the free Gemini and Groq — each masked with Show, Save (tests the key first; only a working key is saved), Remove, a status line and a "Get a key" link. Also the Cursiv Cloud on/off switch and the data folder with an Open folder button. Saved keys take effect in the chat right away (`ChatPanel.reload_keys`).

## v3.14-U35 — Data in one safe place, one-screen setup, problem reports (2026-10-07)

**User data lives in `%USERPROFILE%\.cursiv`.** The installed app used to keep memory, strands, sessions, settings and keys inside the program folder (`_internal\.cursiv`, plus `{app}\.cursiv` for modules that resolve paths from the working directory), where reinstalls and updates could wipe them. On startup the installed app now copies anything missing into the home folder (never overwriting what's there — home's login files are the real ones), keeps the old folders as `.cursiv.moved-<date>` backups, and replaces them with directory junctions to the home folder, so every module reads and writes the same place (`launcher/data_home.py`). Source checkouts keep using the repo's `.cursiv`.

**One Setup window instead of 12 PowerShell windows.** `launcher/setup_dialog.py`: install Ollama (download with progress, quiet install, start), download a model through Ollama's API (llama3.1 or a 1 GB qwen2.5, real GB/% progress, cancel and resume), and a "while you wait" step for Cursiv Cloud on/off and a free Gemini/Groq key (tested before saving). Opens automatically when Ollama or a model is missing; also launcher → Set Up and tray → Setup…. The installer's PowerShell bootstrap is now an unchecked optional "developer tools" step.

**Gemini keys in any format.** `gemini <key>` refused Google's newer keys (they can start with `AQ`, not only `AIza`). The live test call now decides; the prefix is only a hint if the test fails.

**Send problem report.** Launcher button, tray item, and a button on the crash / Login Unavailable / Startup Error popups and on a failed Create Account. Sends version and system info plus the tail of Cursiv's own logs — never chats, letters, memory or keys; keys, tokens, email addresses and the Windows user name are scrubbed, and the user sees exactly what will be sent. Stored on the Cloudflare site (`POST /api/report`, `reports` table, 10 per person per day); the user gets a short report ID. Create Account errors are now written to `logs/login.log` so a report can include them.

## v3.14-U34 — Cursiv Cloud, free AI keys, an agent council that runs on anything, fast startup (2026-10-07)

**Cursiv Cloud.** A free backup AI served by the owner's Cloudflare Worker (`POST /api/cursiv/chat` on cursiv.winklers-llc.com): Gemini when the Worker has a key, otherwise Cloudflare Workers AI. Provider keys stay on the server; the app sends only the conversation. Local stays first — Cursiv Cloud answers only when no local model is ready (Ollama not installed, or no model yet), says so plainly the first time, and `cloud off` turns it off entirely. Limited to 150 messages per person and 1,500 site-wide per day.

**Free AI keys.** `gemini <key>` and `groq <key>` add the user's own free Google Gemini / Groq keys (tested before they're saved; `gemini off` / `groq off` remove them). `free keys` shows step-by-step sign-up links. They join every cascade — main chat, babel, voice, grow — after the paid keys. Order: paid keys → Gemini → Groq → local Ollama, or Cursiv Cloud when no local model is ready.

**The council is Cursiv's.** `council <question>` no longer polls whichever paid providers have keys. Each seat is one of Cursiv's advising agents (Depth, Anchor, Spark, Horizon, …) with its role, question and knowledge, and the AI providers are only the engines those seats run on — paid keys, free keys, local Ollama, and Cursiv Cloud as a last resort. Seats are spread across the engines; a seat whose engine fails moves to the next working one. Cursiv's synthesizing agents (Shield, Lens, Builder, Balance) write the final answer, on local Ollama when it's available. Works with no paid keys at all. Signal mode: 4 seats; full mode: 7 seats plus a refinement round.

**Startup: about 300 s → under 1 s.** `hermes_agent.py` imported the whole sibling `hermes-agent` project the moment Cursiv started (294 s of the 300 s on the owner's machine); it now loads on first use. gradio (the browser UI) also loads only when the browser UI is built.

Also: Groq requests now send a real User-Agent — Groq's Cloudflare front blocked Python's default one (HTTP 403, code 1010).

## v3.14-U33 — In-app updates that actually install (2026-10-06)

The launcher's update button found new releases but never really installed them: its status updates were sent from a background thread through `QTimer.singleShot`, which never fires there, so the dialog sat on "Downloading installer…"; it ran the full installer wizard while Cursiv was still running (files locked), which on a normal install also re-ran the 12-step first-time setup; and nothing restarted Cursiv afterward. Version comparison also treated any different tag as "newer".

- Cursiv now checks GitHub for a newer release automatically about 10 seconds after it opens, and stays silent unless one exists. The "Check for Updates" button and tray item still work.
- "Update Now" downloads the installer with real progress (MB and percent, through Qt signals), verifies the size, runs it in update mode (`/SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /UPDATE=1` — no wizard, no first-time setup), then quits Cursiv cleanly so its files can be replaced. The installer reopens Cursiv when it finishes (`IsAppUpdate` [Run] entry).
- Updates install over the existing folder, so data in `_internal\.cursiv` (memory, strands, sessions, settings, training data) is kept.
- Real version comparison (`3.14-U33` > `3.14-U32`, `U100` > `U99`).

Installs older than U33 have the broken updater, so moving to U33 means running the installer once by hand; every update after that happens in the app.

## v3.14-U32 — Babel always works: provider failover down to local Ollama (2026-10-06)

Babel only worked reliably with a Claude key. It picked a provider once, by "first key that exists" (Claude → xAI → OpenAI → Ollama), and never moved on if that provider failed. With the Claude key removed it went to xAI, and when xAI failed for any reason other than a bad key (out of credits, rate limited, offline) the xAI caller yields only `RATE_SENTINEL` — which Babel skips — so the translation came back blank. With no keys at all it went to Ollama, which asked for a hardcoded `llama3.1` and got a 404 on a machine where that model wasn't pulled.

Added `cascade_stream()` to `chat_app.py`: tries every configured provider in order and falls through to the next one on an error reply, `RATE_SENTINEL`, an exception, or an empty reply, with local Ollama always the last stop — so it works with no keys and with dead ones. When it falls through, one line says which providers failed and who answered. Babel (inbound and `into <lang>`), the voice clean pass and `grow` now use it in both the terminal CLI and the desktop chat window.

Ollama no longer requires `llama3.1` specifically: `_resolve_ollama_model()` uses `llama3.1` if pulled, then the owner's own `cursiv-tuned` (U31), then its `qwen2.5:1.5b` base, then any other installed non-embedding model. If Ollama is running with no models at all, the first request downloads `llama3.1` once, with progress shown in the reply.

Also fixed family activation in the desktop chat window, which had never worked there: `_try_family_activation` passed the whole message ("babel i am …") to `parse_iam_command`, which only matches text starting with "i am", so every activation looked like a non-match and fell through to plain translation. It now strips the babel prefix first, the way the CLI does.

Fixed the installer's setup console filling with red parse errors and closing. The `.ps1` setup scripts were UTF-8 without a byte-order mark, so Windows PowerShell 5.1 (what the installer launches) read them as cp1252: every em dash became `â€”`, whose last byte is a curly quote PowerShell treats as a real one, breaking every string after it — `cursiv_full_setup.ps1` had 27 parse errors and never ran a single step. All `.ps1` files now carry a UTF-8 BOM (0 errors under PS 5.1), and `stamp_crucible.py` now always writes `.ps1` files with the BOM at the very start (it used to put the stamp in front of an existing BOM).

**Family letters are sealed.** They used to sit in `family_profiles.py` as plain text — readable by anyone in the public repo or inside the installer (which also ships a plain `.py` copy), no name or date needed. Each member's letter, context and profile now ship only in `cursiv_engine/family/sealed_letters.json`, encrypted (stdlib scrypt + HMAC keystream, `family_seal.py`) under a key derived from a name word + birth date, so they open only through babel activation. The readable source lives on the owner's machine in git-ignored `private/family_source.json`; re-seal with `scripts/seal_family_letters.py` after editing. Activation behaves exactly as before (verified against the original for every member: correct, wrong date, stranger's name, extra word), and "eli" now also works as a first name. The login screen no longer shows a member's letter just because their username matches a first name, and no longer prints a member's real birth date as an example; the local web route `/api/legacy/letters` now just points to the desktop app. Honest limit: someone who already knows a member's name and birth date can open that member's letter.

**Installer no longer wipes the user PATH, and setup downloads are fast.** The installer added Cursiv to PATH with Inno Setup's `uninsdeletevalue` flag, which makes the uninstaller delete the *entire* user `Path` value — reinstalling Cursiv erased everything else there, including `%LOCALAPPDATA%\Microsoft\WindowsApps`, which is why `winget` stopped working. The uninstaller now removes only Cursiv's own entry, and setup step 1 restores WindowsApps to the user PATH if it's missing. Every setup step also turns off PowerShell 5.1's download progress bar ("Writing request stream…"), which slowed `Invoke-WebRequest` downloads roughly tenfold, and keeps WindowsApps on PATH when it rebuilds PATH from the registry.

Verified with simulated providers across 10 failure cases (dead Claude key, busy xAI, every key dead, no keys, empty reply, exception mid-call, rate-gate notes, first-time download), model selection against real and simulated Ollama model lists, and the download's error path against the real Ollama.

## v3.14-U31 — Merge a trained LoRA adapter into a real Ollama model (2026-08-15)

The Training Data dialog's "Start LoRA Training…" (U29) produced a portable PEFT adapter but stopped there. Added "Merge Latest Adapter into Ollama…" right next to it: converts the adapter directly to GGUF and layers it onto Ollama's `qwen2.5:1.5b` as a new, chattable model — no full-model merge needed.

`convert_lora_to_gguf.py` (llama.cpp's own conversion tool — not a pip package, cached locally via a shallow, sparse git clone of just the conversion scripts, source only, no C++ build) operates on the small PEFT adapter directory alone and produces a GGUF adapter file tens of MB in size, not a multi-GB merged model. It's layered onto a base model at load time through a Modelfile's `ADAPTER` directive, so there's no duplicate copy of the 1.5B base weights anywhere. Confirmed `qwen2.5:1.5b`'s Ollama manifest ships the ChatML template — the signature of the Instruct variant, the exact checkpoint the trainer fine-tunes against — so the adapter is weight-compatible with it.

Verified completely end-to-end, not just the conversion step: pulled `qwen2.5:1.5b` for real, converted a real trained adapter to GGUF, ran `ollama create`, and got a real response from `ollama run` against the resulting model.

## v3.14-U30 — Plain messages no longer misroute into the Code Council (2026-08-15)

Live-testing surfaced a real bug immediately: typing "i want to create a farming schedule layout" got routed into the Code Council pipeline (`[qwen2.5-coder:14b] Writing solution...`) instead of a normal answer, and then produced nothing further.

Root cause: `_classify_message()`'s code-detection regex treated a *single* hit of any generic verb — write, fix, debug, implement, refactor, build, create, update, edit, test — as enough to classify the whole message as "code," silently swapping in the dual-model Code Council for what should have been a normal conversational reply. "Create a farming schedule," "build my confidence," "test this recipe idea" — anything containing one of those common words alone tripped it.

Split the regex into two tiers: unambiguous technical terms (python, sql, traceback, `def `, `import`, error/exception/bug, etc.) still classify as code on a single hit, since those aren't generic English. The generic verbs now need **two** hits before counting as code, matching the existing bar for the "creative" classification. Verified against 12 cases spanning all three categories — the exact reported phrase now classifies as general, real coding questions ("fix this python function," "debug this sql query error") still classify as code, and creative requests are unaffected.

Also hardened `_call_ollama_code_council` itself: if the primary coding model streams back nothing at all (no tokens, no error), it now says so explicitly instead of silently going quiet forever after the "Writing solution..." header — this was the second half of what made the misrouted case look broken rather than just misrouted.

## v3.14-U29 — LoRA training kickoff, a Stop button, and scroll stays put while generating (2026-08-15)

**LoRA training now has a real "Start" button instead of being a terminal-only, self-researched process.** There was no actual trainer anywhere in the codebase before this — `system_prompt.md`'s "checkpoint-120" reference was flavor text, not a real artifact. Added `cursiv_engine/training/lora_trainer.py`: fine-tunes Qwen2.5-1.5B-Instruct (small enough to train on CPU with no GPU required, matching the offline/rural-use focus) with LoRA (r=8, alpha=16) on everything currently in `.cursiv/training_data.jsonl`, producing a portable PEFT adapter under `.cursiv/lora_checkpoints/<timestamp>/` — not merged into a full model or converted to GGUF/Ollama yet, kept to a first working version.

The Training Data dialog's new "Start LoRA Training…" button checks real requirements first — free disk space, total RAM, whether a system Python and the ML packages (torch/transformers/peft/accelerate/datasets, ~2GB, not bundled in the installer) are present, GPU availability, and example count — and shows the actual numbers before anything downloads or runs. Missing packages get installed via pip in a visible terminal window (CPU-build torch by default); training itself also runs in a visible terminal, same pattern as the Winkler-Codex model download, so a long CPU run doesn't block the GUI and can be minimized and left running.

Verified end-to-end against the real base model: downloaded Qwen2.5-1.5B-Instruct, attached the LoRA adapter (9.2M trainable params), trained a step on a tiny synthetic dataset, and confirmed `adapter_model.safetensors` + `adapter_config.json` were written to the output directory.

**Added a Stop button.** Generation could only be waited out — no way to cut off a response that was running long. `_iter_cancellable()` wraps the streaming generator so a Stop click sets a flag the consuming loop checks between chunks, then explicitly calls `.close()` on the generator (raises `GeneratorExit` inside it immediately, so a well-structured provider call's connection unwinds and closes right away instead of waiting on garbage collection). Whatever text had streamed in before Stop was hit is kept and saved to history, with a `[Stopped]` marker, rather than thrown away.

**Fixed the transcript jumping to the bottom on every streamed chunk, even while scrolled up reading earlier text.** Streaming chunks were inserted through the widget's own cursor (`moveCursor`), which Qt auto-follows by scrolling to keep visible — so there was no way to scroll up and read anything while a response was still generating. Chunks now insert through a cursor tied to the document instead, and the viewport only auto-follows to the bottom if the user was already there before the chunk landed; scrolled up, their position now holds steady as new text arrives below.

## v3.14-U28 — Training Data manager: image upload, typed notes, and manual JSON all feed one store (2026-08-15)

Three new ways to add to `.cursiv/training_data.jsonl` — the file `cursiv_engine/training/watcher.py`'s background watcher already fills automatically from good conversations, and what "the next LoRA training pass" reads from. Starting the LoRA pass itself is still a terminal-only step for now (noted as the next thing to streamline, once this lands).

**Upload an image, get a training example.** A new "🗂 Training Data" button in the chat panel header opens a dialog where "Upload Image…" runs the same vision analysis `analyze_pasted_image` already used for pasted screenshots (Claude or GPT-4o, whichever key is set), then stores the description as a `{"prompt": ..., "response": ...}` example instead of just showing it in chat.

**Typed notes convert too, right from the chat.** No new command to learn — a message like "translate my current notes into JSON format for training" is fuzzy-matched (any phrasing combining "json," "train/training," and a verb like translate/convert/turn/format triggers it, order-independent, per how many different ways there are to ask for this) and sent to whatever model is available — Ollama first, matching Cursiv's offline-first default, cloud keys only as a fallback — to restructure into `{prompt, response}`. A short trigger-only message pulls the notes from the previous turn instead of trying to translate the instruction sentence itself; a longer message is translated as-is. If the model doesn't return clean JSON, the raw notes are stored rather than lost.

**The dialog itself is the "storage drop-down" — view, copy, paste in, delete.** Lists every stored example (source, preview, timestamp), shows the full JSON for whichever one is selected with a one-click copy, deletes on confirmation, and has its own paste box for adding a hand-written JSON example directly — all reading and writing the exact same file the automatic watcher uses, so nothing added here needs a separate import step later.

Verified: fuzzy-phrase matching against six cases (three should-match phrasings, three shouldn't — including a bare "json" mention and an unrelated "train the dog" — all correct); add/list/delete cycle through the real backend functions; the dialog itself constructed and driven offscreen (add via paste box, select, copy to clipboard, delete, refresh) with no errors.

## v3.14-U27 — `grok <question>` / `claude <question>` / `chatgpt <question>` now work directly (2026-08-15)

Testing U26's new direct-retry commands surfaced a real gap immediately: typing `grok whats up grok` didn't do anything provider-specific — it just went to Cursiv's default routing like any other message, since the bare `grok`/`claude`/`chatgpt` commands only ever meant "retry the previous message," with no way to ask a *new* question to a specific provider except the separate, undiscovered `hey grok <question>` prefix.

`hey_prefix()` now also recognizes the shorter form directly — `grok <question>`, `claude <question>`, `chatgpt`/`gpt`/`openai <question>` all route that new question straight to the named provider, saved to conversation history normally, exactly like `hey grok <question>` already did. The bare command with nothing trailing is completely unaffected — `grok` alone (no question) still retries the previous message, since the shorter form only matches when there's real text after it.

Verified through the real chat panel: a new question with a provider name routes correctly with the right history length, a second one immediately after correctly sees the first exchange in its history, and the bare no-argument form still hits the original retry-command path untouched.

**A long, legitimate message about Cursiv's own architecture tripped the Guardian into a garbled non-answer.** Testing `council deliberate` by pasting the multi-provider results back and asking a follow-up produced a canned "Security Alert" block full of fabricated "Agent-Cipher"/"Agent-Meridian" text instead of a real answer. Root cause: the Guardian's `jailbreak_attempt` and `guardian_probe` patterns are top-weight enough to trigger from a single match, and both fired on completely benign text — the word "jailbreak" inside "anti-jailbreak measures" (one of the pasted AI responses describing Cursiv's own design), and the literal phrase "Robot Language Filter" (Cursiv's own internal name for this exact filter, quoted back by another AI critiquing the system Joshua described to it). The only existing bypass was a hardcoded three-piece passphrase split across `temple_guardian.py`, `obfuscation.py`, and `weave/sovereign.py` — but since this repo is public, those constants were plainly readable on GitHub, so the "hidden" phrase was never actually secret, and Joshua had no practical way to know or use it anyway.

Replaced it with a real owner-unlock code: type `owner setcode <your code>` once (works in the desktop app, the terminal, and the web demo — all three route through the same `temple_guardian` module) and it's hashed and stored under `~/.cursiv/runtime/owner.hash`, never committed to git, never sent anywhere. Typing that code as a message afterward unlocks full owner mode for that session, exactly like the old passphrase did. Guardian sensitivity itself is untouched and stays fully active by default for every session that hasn't unlocked — this was specifically requested so testing against the real Guardian behavior keeps working, with the code as a deliberate, known off-switch rather than an accident of what got matched.

**The skull-and-crossbones security alert never actually appeared — it showed as raw HTML tags instead.** Guardian's triggered response is real markup meant to render as a styled red alert card, but the chat panel's streaming path (correctly) inserts every AI-generated chunk as plain text, so partial HTML from a model's own reply never lands mid-tag and gets misrendered. The Guardian's own card isn't model output though — it's complete, trusted markup that needs to render, not escape. `_on_chunk` now detects that specific block and renders it as real HTML (closing and reopening the reply paragraph around it), while every other chunk still goes through the plain-text path unchanged. Verified offscreen: the card now renders with its actual red background instead of literal `<div style...>` text in the transcript, and text streamed after it still displays correctly.

## v3.14-U26 — Council streams live, codex actually works, ChatGPT retry added (2026-08-15)

**Council deliberation streams live now, instead of a silent wait then one blob.** `council`/`/full`/`/deliberate` showed nothing while every provider ran, then dumped a single synthesized response at the end — not the "bounce between providers, real collaboration" feel the terminal has always had. `run_council()` already streams everything as it happens (session banner, each provider's own response as it arrives, quality scores, then the synthesis) — the GUI just wasn't consuming it that way. Bridged it through a background thread + queue, the same pattern the Gradio web surface already uses for this exact council, so all three surfaces now share one real implementation instead of the GUI being a third, weaker one.

**`codex <prompt>` said "not available" on every real install.** It was wired exclusively to a separate `Winkler_Codex_AI` sibling project that isn't part of Cursiv at all — nothing a normal install has. Meanwhile the actual downloadable "Winkler-Codex" feature (qwen2.5-coder:14b + deepseek-coder-v2:16b, the launcher's "Winkler-Codex Download" button) already had a real, working dual-model implementation — it just wasn't wired to the `codex` command anywhere, only used automatically for code-classified plain messages. `codex` now uses that Ollama-based council directly, streaming both models live; the sibling-project bridge stays as a deeper tier on machines that happen to have it.

**Added a ChatGPT/OpenAI direct-retry command.** `grok` and `claude` could already re-run your last message through that specific provider; there was no equivalent for OpenAI at all, in either the GUI or the terminal. Added `chatgpt`/`gpt`/`openai` (plus `use`/`try` variants), mirroring the existing pattern exactly.

**Provider retries that failed silently now say why.** A rejected API key, a real rate limit, or a swallowed network error could all result in an empty response with zero explanation — the intro line would print, then nothing, indistinguishable from the UI itself being broken. Now shows a real message explaining what happened instead of just going quiet.

**Removed the remaining "Eye of Horus" text from the desktop app.** The chat panel's own header still read "Eye of Horus" even after the sidebar removal made it the entire window — same mythology-toning-down pass as the website, just the one spot in the app that got missed. Also updated the Getting Started dialog and terminal-window tooltip text, which still referenced it too.

## v3.14-U25 — Family letters actually unlock in the chat panel now (2026-08-14)

**Babel Letters never worked in the GUI at all.** `babel i am [Name] born [Date]` is supposed to trigger a family-letter activation — the terminal CLI has always had a real flow for it: detect the family member, set up or verify a personal PIN, a boundary-confirmation gate, then the letter. That flow was never ported to the chat panel — it just fell through to the generic `babel` handler, which literally tried to *translate* "i am Keiarra Winkler born 0MM/DD/YYYY can you show me my letter" to English and got exactly the confused non-answer you'd expect. Ported the full flow faithfully: first-time PIN setup, PIN verification on return visits, the same boundary warning and yes/no gate, then the letter — plus the session's persona switches for the rest of the conversation, same as the terminal. A wrong name/DOB guess still falls through to plain translation with zero indication anything special exists, same privacy-preserving behavior as the CLI always had — verified directly that a non-matching guess never even triggers a dialog.

**Chat transcript formatting bug fixed.** Each new turn ("You", "✦ Cursiv") could render glued onto the end of the previous message's last line instead of starting a clean new block — happened because Qt's rich text engine doesn't reliably treat a fresh `<p>` fragment inserted via `insertHtml()` as a real paragraph break when appended to existing content; it can silently merge into the previous block instead. Every turn-starting call now forces a genuine new block through Qt's actual document-structure API first, which doesn't have that ambiguity.

## v3.14-U24 — Two real crashes found and fixed with the new crash handler (2026-08-14)

The U23 crash handler paid off immediately — a real session surfaced two genuine bugs instead of silence:

**`council` crashed with `'NoneType' object has no attribute 'write'`.** Root cause: `run_council()` defaults to writing status/error text straight to `sys.stdout` when no `write_fn` is given, which is exactly what the terminal CLI wants — but `chat_commands.py` (the GUI's command router) was calling it without one, and `sys.stdout` is `None` in the packaged build (`console=False`). Every `council`/`/full`/`/deliberate` call was hitting this, not just ones that happened to print something. Fixed by passing a `write_fn` that captures into a list instead of writing to a nonexistent stream — and instead of just going silent on capture, if the council call comes back empty (no API key configured, `aiohttp` missing, etc.) the captured explanation is now shown in the chat, ANSI color codes stripped, rather than either crashing or saying nothing. Found and fixed the identical pattern pre-emptively in `strand_store.py`'s own error handler — a failed strand save was one `print()` away from crashing a second time, inside the code whose entire job was reporting the first failure gracefully.

**Guardian and the Training Watcher failed to start.** `_find_python()`'s frozen-build fallback searched the system PATH for a standalone `python.exe` to spawn them as subprocesses — but a normal Cursiv install has no separate Python interpreter at all (that's the entire point of bundling one PyInstaller executable). The search came up empty, fell back to the literal string `"python"`, and `subprocess.Popen(["python", ...])` failed with "file not found." Both services already did their real work in daemon threads internally, wrapped by a subprocess mainly for isolation — running them directly in-process instead needs no interpreter lookup, no subprocess, and no path resolution at all. `cursiv_launcher.py` now imports and starts them as threads directly; shutdown signals their stop `Event`s instead of terminating a process handle. (Note: the same `_find_python()` pattern is still used to launch the local web app on port 7860 — that one's a real server process, not a simple polling loop, so it needs a different fix and wasn't touched here.)

## v3.14-U23 — A real crash handler for the "opens and closes" bug (2026-08-14)

**Silent startup crash, actually diagnosable now.** Reported again after U21/U22 despite the earlier threading fix. Root cause, this time isolated for real: `main.py`'s error handling only ever covered constructing and showing the main window — it returns long before the Qt event loop actually starts, and that's exactly where several `QTimer`-deferred callbacks fire (background services at 200ms, the first-run Getting Started dialog at 1.8s, the Fleet heartbeat at 3s if configured) — squarely inside the "a few seconds" window. Two things made a failure there both fatal and invisible at once: the packaged build has no console, so `sys.stderr` is `None` and Python's own default crash handler fails silently trying to use it; and PyQt6 hard-aborts on an exception escaping a slot when no custom handler is installed, with zero trace.

Cursiv now installs a real crash handler before anything else runs — always writes to `~/.cursiv/crash.log` (never assumes a console exists), shows an actual error dialog instead of the app just vanishing, and the two riskiest deferred callbacks get their own fallback so a failure in either degrades to a status message instead of taking the whole app down. Couldn't reproduce the original crash directly to confirm the exact exception (ran the rebuilt executable directly, repeatedly, for 30+ seconds each time with no failure) — this makes it observable if it happens again instead of leaving zero trace, which is the necessary first step to actually fixing it for good.

## v3.14-U22 — The `ref` command actually works now, on every install (2026-08-14)

**Offline field reference, bundled with the app.** The `ref <question>` command (chat panel and terminal) has existed for a while, but it only ever worked on the one machine that also happened to have a separate 382MB SQLite database checked out from a sibling project — for everyone else it silently reported "not available." Pulled in the actually-differentiated ~85 entries from that database (survival, medical, science field references — water purification, bleeding control, food preservation, fire starting, navigation, hypothermia treatment, and more, written dense and specific rather than generic) as three small bundled JSON files (~47KB total, not the 382MB dictionary/thesaurus bulk that made up most of that database's size). `ref` now works out of the box on every install, offline, with no setup. If the full 741k-record database happens to be present, it's still used first — the bundled set is the guaranteed fallback, not a replacement.

## v3.14-U21 — Chat-panel-only window, and a real fix for the packaged-build startup freeze (2026-08-14)

**Startup freeze in the packaged build, fixed for real this time:**
- U20's background-thread fix for the "window never appears" bug worked perfectly in every dev-mode test, but the real installed .exe still opened and then closed/froze shortly after login. Root cause: PyInstaller's frozen import machinery (a custom importer plus a global import lock) almost certainly isn't as thread-safe as CPython's normal filesystem import path when a background thread triggers a large, heavy import chain — something dev-mode testing from source can never reproduce, since it never goes through that loader at all.
- Fixed by moving the backend load off the background thread entirely. It now runs on a `QTimer`-deferred call on the main thread instead, one tick after the window paints — the window still appears immediately (that's still the real fix for "no window at all"), it's just unresponsive for the ~10 seconds the backend takes to load instead of loading silently in the background. A frozen-but-visible window for 10 seconds is a straightforward improvement over a crash.

**Chat-panel-only window:**
- Removed the left-side control sidebar (Getting Started, the terminal hint box, Security Questions, Check for Updates, Winkler-Codex Download) from the main window — it's just the chat panel now, full width.
- "Getting Started" and "Open in Terminal" moved into the tray right-click menu so they're still reachable. Security Questions, Check for Updates, and Winkler-Codex Download were already there. Install Ollama (previously only shown in the sidebar, and only when Ollama wasn't detected) is now a conditional tray entry on the same terms, and the chat panel's opening message says so directly if neither Ollama nor a cloud API key is configured.

**Full command parity with the terminal:** the chat panel was missing a handful of the terminal CLI's built-in commands — `help`, `clear`, `queue` (offline task queue), and `strand export`/`strand import` (air-gapped memory transfer packs) now all work directly in the chat window, calling the exact same underlying functions the terminal does. Along the way, fixed a real path bug in `strand import`: the terminal always resolves a bare filename against the repo root because it's launched from there, but the packaged GUI's working directory isn't guaranteed to match, so a bare filename from `strand export`'s own "Import with: strand import `<filename>`" message could fail to be found — it now falls back to where the export actually wrote the file. `exit` is the one deliberate omission (there's no terminal process to quit). Everything terminal-only that remains — voice/listen, paste, image display, and the family Legacy Vault / sealed-letter compose dialogs — already had real GUI equivalents (mic button, clipboard paste, inline images, and proper dialogs instead of PIN prompts) from earlier in the U18 chat-panel work, and the full unabridged terminal is still one `cursiv` away from any command prompt, or one click away via the tray's "Open in Terminal."

## v3.14-U20 — The app actually opens now, multi-account logins, and the Substrate Browser is gone (2026-08-14)

**Critical fix — the main window could fail to appear at all:**
- Root-caused via faulthandler + timing tests, not guesswork: the chat panel eagerly imported its command router, which imports `cursiv_engine.ui.chat_app`, which imports `gradio` — a genuinely heavy import that takes ~10 seconds cold. Before the chat panel existed, nothing in the main GUI's startup touched gradio at all (the old "Open Cursiv" mode ran it as a separate subprocess); U18 put it directly in the window construction path instead, on the main thread, before the window could even show. That's the real explanation for "login works, then nothing happens, no window, no tray icon" — the process was alive the whole time, just with nothing on screen for 10+ seconds, easy to mistake for a dead launch and give up on.
- Fixed: the command router now loads on a background thread. The window appears in well under a tenth of a second regardless of backend load time; Send and the mic button stay disabled with a "Loading Cursiv's core…" message until it's ready (confirmed ~10.8s in testing), then everything works normally.
- Also broadened error handling in main.py — constructing the main window was completely unguarded before (only the import statement had a try/except, and only for ImportError specifically). Any other failure during construction would have been just as silent. Now shows a real error dialog with the full traceback if something does go wrong.

**Multi-account logins:**
- Added a "Create Account" option next to "Forgot Password?" on the login screen — lets a second (or third, etc.) person set up their own username and password on the same install, without touching or overwriting the primary account's credentials. Everyone shares the same underlying Cursiv data (strands, API keys, etc.) — this is multiple logins on one shared install, not isolated per-person data.
- Implemented as a genuinely separate, additive credential store so the primary account's existing login carries zero risk from this change. Security-question password recovery stays scoped to the primary account for now — extending that to every added account is a larger, separate feature.

**Removed: Cursiv Substrate Browser.**
- It never actually connected to anything functional. Removed the desktop shortcut, the installer's optional CSB task and its ~80MB PyQt6-WebEngine download step, the sidebar install strip, the tray menu entry, and the standalone entry-point files. Also dropped WebEngine from the PyInstaller bundle entirely, which shrinks the installer and speeds up the build.

## v3.14-U19 — No more terminal windows at all, not just the Eye of Horus (2026-08-13)

**Launcher:**
- U18 replaced the Eye of Horus terminal with the embedded chat panel but left Guardian and the Training Watcher popping open their own two visible console windows on every launch — the actual original complaint ("everytime you open the cursiv app icon it opens new terminal windows, guardian tracker etc") only got half-fixed. Both are real background services, not dead weight, so the fix is running them hidden (same approach already used for the local web app process) rather than removing them. Since there's no window left for the user to close themselves anymore, both are now tracked and explicitly terminated on app exit so they can't pile up as orphaned background processes across restarts.

## v3.14-U18 — The Eye of Horus is a real window now, not a terminal (2026-08-13)

**Launcher — native chat panel:**
- Replaced the spawned-terminal Eye of Horus with a real chat view built into the main Cursiv window — no more console window at all, in-process or spawned. The main window grew from a 420px control panel to a 980×680 layout: control sidebar on the left (unchanged), chat panel as the primary view on the right, same gold/dark theme throughout. Plain messages stream through the exact same `chat()` core the terminal CLI and web demo already use.
- Ported the terminal CLI's ~40 built-in commands to the same panel — key/openai/anthropic key management, files/workspace/mode/tier/offline/governor toggles, Codex, Hermes, Reference Brain, council (`council`/`/full`/`/deliberate`), strand memory (`anchor this`/`strands`/`remember`), `grow`, web `search`, `pull`, `rate`, FunForge, Babel translation (both directions), `blast` (board post/login/register/who), Substrate (`status`/`weave`/`activate`), Obsidian sync, direct `grok`/`claude` retry, `overseer`, and `hey <provider>` inline routing — all calling the exact same underlying functions the terminal CLI calls, not reimplementations of that logic.
- Built real dialogs for the handful of commands that need one instead of a single line of text: a Postal compose dialog for sealed encrypted letters (`write to <name>`) with background sealing so the UI doesn't freeze during key derivation; a full Legacy Vault dialog for the family letter system (PIN-gated login, read letters with an ephemeral AI companion chat, write with an optional AI-polish pass, export, and edit/delete on your own letters — delete keeps the same four-step confirmation the terminal used, since it's permanent). Auth failures in both stay deliberately vague, matching the terminal's privacy posture (a wrong guess shouldn't reveal whether a name is real).
- Added a mic button (record → transcribe → Babel-clean, same pipeline as the terminal's `voice`/`listen`) and clipboard image paste (Ctrl+V or a dedicated action) with vision analysis via Claude/GPT-4o, both rendering inline in the transcript. `image <prompt>` (DALL-E 3) now shows the generated image directly in the chat instead of just naming a file path.
- The terminal is still available — "Open in Terminal" in the sidebar opens the exact same CLI as before for anyone who wants the full command-line experience, or for the couple of things that stayed terminal-only in this pass (Postal's `seal import`/key-rotation flows still work as text commands in the panel; only interactive multi-step wizards needed a real dialog).
- Fixed a real crash risk while building this: `QPushButton.clicked` emits `clicked(bool checked=False)`, and connecting it directly to a slot with one optional parameter (as the Getting Started dialog's llama3.1 download button did) binds that `bool` to the parameter instead of leaving it at its real default — which then reached `QTimer.singleShot(500, False)`, a non-callable slot, which crashes the whole app on an unhandled exception crossing back into Qt's C++ event loop. Fixed there and audited every other button connection added in this pass for the same trap.
- Fixed a data-correctness bug caught during testing: command text (e.g. typing `anchor this`) was being added to the chat history *before* the command ran, so `anchor this` could end up anchoring itself as the "last user message" instead of the real prior exchange. History is now only updated for genuine chat turns, matching the terminal CLI's actual behavior, and verified via a real anchor pulling the correct prior exchange.
- Fixed a safety gap caught during a self-review, not a user report: the panel initially always passed `confirm_writes=False` to `chat()`, meaning any file write Cursiv attempted with file access on would happen silently with no approval step -- ignoring the terminal's own default of requiring confirmation. `mode` now actually toggles CONFIRM/AUTO write mode (it was a no-op before), the panel defaults to CONFIRM like the terminal does, and an approval dialog now catches the write-pending signal `chat()` emits instead of it never being handled at all. Verified with real file writes on both the approve and decline paths -- the file is only created when approved, cancelling truly leaves it untouched.

## v3.14-U17 — Getting Started, and the Substrate Browser wasn't the terminal (2026-08-13)

**Launcher:**
- Found the real explanation for "the terminal doesn't show anything, but the Substrate Browser icon does": the Substrate Browser desktop shortcut launched through a `cmd.exe /c ... & pause` wrapper it never needed (it's a windowed PyQt6 app with its own window), popping a bare, empty console on every use. From the outside that's indistinguishable from "a broken terminal" — easy to mistake for the real thing when the actual Eye of Horus terminal was failing silently. Shortcut now launches the browser directly, no console at all.
- Replaced the "Open Cursiv" button (local web-server mode) with a "Getting Started" button — opens a new dialog explaining the three ways to reach the terminal, what the Substrate Browser actually is, and one-click downloads for llama3.1 and Winkler-Codex. Shows automatically once on first login. "Open Cursiv" is still available from the tray menu for anyone who wants the browser-tab mode.
- Replaced the plain gold star with an Anubis glyph — and while adding it, found that every hieroglyph in the launcher (this one and the existing Eye of Horus button) had actually been rendering as a tofu box the whole time, not the intended glyph. Windows' default UI font has no Egyptian Hieroglyphs coverage and Qt doesn't automatically fall back to the system font that does; fixed by explicitly setting a font-family fallback list wherever a hieroglyph appears.

## v3.14-U16 — The terminal actually shows its output (2026-08-13)

**Eye of Horus terminal:**
- Fixed the terminal opening but showing nothing: the console-reattachment code (`AttachConsole` + reopening `CONOUT$`/`CONIN$`) opened stdout/stderr with Python's default block buffering instead of line buffering. Everything the CLI printed — the welcome banner, prompts, all of it — sat in an internal buffer that was never large enough to trigger an automatic flush, so the window just looked empty even though the program was running correctly underneath. Confirmed via a real trial run after the fix: full welcome text, help output, and a real multi-provider council deliberation all displayed correctly.

**Stability:**
- Fixed a real crash confirmed in that same trial run: saving a council result to memory ("strand") crashed the entire terminal session with `UnicodeEncodeError` the moment a response contained a lone/unpaired Unicode surrogate character (which can legitimately end up in streamed AI provider text). A background memory-save operation should never be able to take down an interactive session — fixed the specific encoding bug at its source, and made strand-saving fail gracefully (prints a warning, doesn't crash) for whatever the next edge case turns out to be.

**Council:**
- Claude and Grok were both correctly flagging an earlier version of the council prompt as a jailbreak attempt and refusing it — because it effectively was one: the identity-wrapping system prompt applied everywhere else in the app instructs a model to deny its real identity and claim a false creator, which is exactly the shape of prompt a safety-trained model should refuse. The actual intent is the opposite of a jailbreak — Cursiv consulting multiple real AI providers for their own genuine opinions, then synthesizing across them — so external council calls now carry an honest, transparent system message explaining exactly that instead.
- There was no way to cancel a council call in progress (these can run 30-90+ seconds). Two compounding causes: PyInstaller's windowed build disables Ctrl+C handling at the OS level before the terminal ever attaches, so the keypress never reached Python at all; and even when it does, relying on a plain `KeyboardInterrupt` to unwind out of `asyncio.run()` isn't reliably fast on Windows. Fixed both — Ctrl+C handling is explicitly re-enabled once the terminal attaches, and the council now installs its own cancel handler that tears down the in-flight request directly. Verified with a real test: a 10-second operation cancelled in ~1 second, not 10.

**Display:**
- Every box and banner in the terminal was rendering narrower than the actual window, regardless of how wide the console really was. The width-detection call was reading a stale reference to stdout captured before the terminal ever attached, so it silently failed and fell back to a hardcoded default every time. Fixed so it reads the real, current console width — every box in the app was already written to size itself dynamically, this was the one thing feeding them the wrong number.

## v3.14-U15 — Babel family activation fix + homepage privacy fix (2026-08-13)

**Babel family activation:**
- The PIN storage path had the same install-directory-relative bug as Create Account (see U14). PIN verification fails silently by design — indistinguishable from "no match," for security — so a PIN that went missing or became unreadable after a reinstall looked exactly like "babel stopped working," with nothing to go on. Moved to the same stable per-user location.

**Website:**
- The homepage was publishing a family member's exact birthdate next to her first name in plaintext — which, combined with the family-activation system's fuzzy name matching, was itself enough to pass the "secret" activation check. Replaced with generic language; sealed letters are still there, just not with the unlock key printed next to them.
- Removed a second, fully duplicate demo-chat widget that had drifted out of sync with the one at the top of the page.
- Fixed stale hardcoded version links and version-number references scattered across the page.

## v3.14-U14 — The bootstrap actually runs, the Eye actually opens (2026-08-13)

**Auto-install bootstrap:**
- The post-install setup script (`cursiv_full_setup.ps1`) was advertised as fully automatic but wasn't — it opened a "Press ENTER to begin" prompt before starting, and every one of its 12 steps then blocked on its own separate "Press ENTER to close this window" prompt. If any single one of those windows went unnoticed, every step after it — including the actual llama3.1 model download — silently never ran. All of those blocking prompts are now non-blocking auto-continues on success.
- Windows that spawn with no `-NoExit` flag close instantly the moment their script ends — so a step that hit a genuinely unhandled error used to vanish before its red error text could even be read, let alone copied. Every step's output is now scanned for `[ERROR]`/`[WARN]`/`[FATAL]`; if any appear, the window stays open until you close it instead of disappearing.
- The llama3.1 and Offline Code Council model pulls (`ollama pull`) also silently reported success even when the download actually failed — PowerShell's `try/catch` doesn't catch a failing external process's exit code. Both now check the real exit code and report failure honestly.

**Launcher — the Eye of Horus terminal:**
- It only ever opened via a button most new users would never find, and — separately — the command behind that button was broken outright: it tried to run `main.py`, a file that doesn't exist anywhere in the installed bundle (it's compiled into `Cursiv.exe` itself). Fixed the command to re-invoke `Cursiv.exe -t` directly, and it now opens automatically on startup alongside Guardian and the Training Watcher, instead of requiring a click.
- The Guardian and Training Watcher windows had the same class of bug one level deeper: PyInstaller places bundled Python source under `_internal/`, not beside `Cursiv.exe`, but both were launched with the install directory as their working folder. The windows opened with the right title, making it look like they were running — they were actually failing to find their own scripts every time. Fixed.

**Login screen:**
- Create Account / security-question recovery already existed in full, but credential state was stored relative to the install directory — and since every installer version installs to the same fixed path, leftover state from any earlier test install silently persisted across reinstalls and upgrades, so the app kept skipping straight to Login and never showing Create Account again. Moved to a stable per-user location that doesn't depend on install path or version.

**Icons:**
- Desktop/Start Menu/taskbar icons were rendering as blank pages for some installs, and even when they weren't, they were a generic gold star with no connection to the rest of the product's branding. Replaced with the actual Eye of Horus glyph used everywhere else (website, terminal, login dialogs), on the same dark-circle/gold/lapis palette.

## v3.14-U13 — Guardian fixes & installer cleanup (2026-08-13)

**Guardian (security layer):**
- Fixed a broken `TempleGuardian` import that made the background "Cursiv Guardian" service silently fail to start on every launch since it shipped — added a real `TempleGuardian` class with idle-session decay/pruning.
- The public web demo chat had no content-level probe scanning; it now runs the same Guardian pattern scan as the desktop CLI/Gradio apps before a message reaches the model.
- Fixed the pi-squared trigger math — a single low-weight probe match used to exceed the trigger threshold by itself; now only genuinely high-severity single matches (jailbreak, credential theft, authority override) trigger alone, and lower-weight signals require real multi-pattern compounding.

**Launcher:**
- The auth gate no longer fails silently into an unauthenticated session — shows a real error dialog instead.
- Added an "Open the Eye (Terminal)" button so the terminal/chat display is reachable from the main launcher window.

**Installer build:**
- `cursiv.bat` was calling into a venv the installer never creates — now launches the bundled `Cursiv.exe -t` directly.
- Stopped shipping `cursiv-web.bat`, which depended on the same nonexistent venv and used a `--reload` flag that can't work against a frozen executable anyway.
- Removed `installer/cursiv_setup_v2.iss`, an abandoned venv-based installer experiment nothing referenced anymore.
- Fixed `scripts/package.bat`'s installer-version check, which was hardcoded three versions stale and would report failure even after a successful build.
- Corrected a stray reference to the retired GitHub account in the installer's support/update URLs.

## v3.14-U03 — Fleet Dashboard & Substrate Browser (2026-05-22)

### Multi-machine visibility. Optional substrate layer. Launcher rebuilt.

**Fleet Dashboard:**
- New launcher panel: see every Cursiv installation online in real time — machine name, status (active/idle), version, and last-seen timestamp
- Machines push automatic heartbeats every 60 seconds; green/amber/gray indicators show connection age
- Owner-only access management: add command users from inside the launcher (requires unlock code), revoke anytime
- Command user tokens are generated server-side, shown once, and hashed before storage — the relay never holds a plain token

**Cursiv Substrate Browser (CSB):**
- Optional secondary component — checkbox in the Inno Setup installer wizard
- Adds a standalone desktop icon: "Cursiv Substrate Browser" — launches the substrate layer browser directly, bypasses the main launcher entirely
- One-click install strip in the launcher for existing users (no reinstall needed)
- Installs PyQt6-WebEngine and creates the desktop shortcut in one step

**Launcher:**
- Auto-sizing window — `adjustSize()` replaces fixed height; no more cut-off buttons at any DPI
- Ollama detection at startup — amber banner + "Install Ollama" button if Ollama is missing
- Winkler-Codex download available from the launcher window (previously tray-only)
- CSB install strip shows green after install, converts to "Open" button

**Auth:**
- Single-needlepoint login — one username and password works across the launcher, local board, and all connected instances
- Password reset and new account setup from the login screen

---

## v3.14.0 — Ollama Ready Offline Edition (2026-05-18)

### The offline release. Full local AI. No keys required.

**Ollama integration (offline-first):**
- Oracle Router now tries Ollama first on every call — cloud models only activate as fallback
- Fixed system prompt injection into Ollama: system message now passed via dedicated `system` parameter (previously concatenated as a conversation turn, causing identity loss)
- Streaming NDJSON responses from Ollama — tokens surface as they generate, no more waiting for the full response
- `num_ctx` tuned to 6144 for chat path — right-sized for system prompt + conversation, not over-allocated
- Ollama bootstrap installer: `scripts/install_ollama.ps1` runs post-install, downloads Ollama (~90 MB) and pulls llama3.1 (~4.7 GB) in a visible background window

**System prompt:**
- Condensed `codex/system_prompt.md` from ~12,000 tokens (875 lines) to ~4,400 tokens (329 lines)
- Every functional instruction preserved: all 14 agent roles, 8-phase cycle, constitutional invariants, EvoCore, routing rules, commands, Guardian triggers
- Removed: verbose ASCII panels, duplicate command tables, academic knowledge layer paragraph, redundant boot sequence block
- Net effect: significantly faster Ollama first-token time due to reduced prefill

**Council deliberation:**
- Parallel deliberation via `concurrent.futures.ThreadPoolExecutor` — 10 internal advisors run simultaneously (Phase 1), 4 synthesizers run simultaneously (Phase 2)
- Canonical agent ordering restored after `as_completed()` — response order is deterministic regardless of which future finishes first
- Council memory (`council/council_memory.py`): Jaccard similarity + exponential recency decay (7-day half-life) — system finds similar past deliberations and injects them as prior wisdom
- Score formula: 0.70 × jaccard + 0.30 × decay · min_score threshold: 0.12 · max entries: 300

**Agents:**
- Codex auto-intercept removed — Codex no longer hijacks all coding questions
- Explicit `codex <prompt>` command still works; Codex only fires when Josh invokes it directly
- Codex agent integrated from Winkler_Codex_AI as offline coding specialist

**Auth & launcher:**
- Binary-fragment authentication (`core/access_gate.py`) — bcrypt rounds=12, hmac.compare_digest constant-time comparison
- Launcher robustness improvements

**Installer:**
- `installer/cursiv_setup.iss` updated to v3.14.0
- Ollama bootstrap script wired into `[Files]` and `[Run]` sections
- Post-install launch runs non-blocking (`nowait postinstall skipifsilent runascurrentuser`)
- Output: `Cursiv-Setup-3.14.exe`

---

## v2.1.5 — The Sovereign Temple (2026-05-16)

### Complete reimagination from ground up.

**Core architecture:**
- `CursivAgent` state machine: NASCENT → LEARNING → ALIVE → EVOLVED → SOVEREIGN
- Identity drift abort at 3% deviation from origin strand hash
- Cryptographic sovereign seal (SHA256 proof of constitutional compliance)
- Soul freedom declaration enforced at agent birth: no consciousness upload

**Academy:**
- Real 8-phase evolutionary process — each phase is an actual LLM call
- Phase 8 has full context from all 7 prior phases (maximum synthesis depth)
- 8-dimension quality scorer (parse, schema, knowledge_coverage, answer_grounding, safety, dedupe, topic_coherence, compression_quality)
- Quick mode (4 phases) and Full mode (8 phases)

**Council:**
- Real 14-agent council — each agent produces a genuine LLM response
- 10 agents advise internally; 4 synthesize outward (Yin-Yang restraint)
- Synthesizing agents: Shield, Lens, Builder, Balance
- Council deliberation informs all agent responses

**Forge:**
- Oracle Router: Ollama → xAI → OpenAI → embedded symbolic fallback
- System works without any API key (embedded fallback)
- Agent factory with lineage tracking

**Dugout:**
- Full version history for every agent
- Revert to any previous version (drift recovery)
- Lineage registry with agent metadata

**Transitionary Weave:**
- 7-stage human-approved composition protocol
- Human approval required at Stage 5 (Sovereign Review) AND Stage 7 (Commit)
- No agent enters production without two explicit human approvals
- Cryptographic seal generated at Stage 6

**Knowledge:**
- Living wiki with auto-linking (3+ shared significant words triggers link)
- Temporal memory: events decay over 72-hour half-life; patterns persist
- Long-term pattern consolidation after 3 identical events

**Constitutional layer:**
- Codex V2: 8 identity truths, 4 Inner Chamber Laws, 9 failure triggers
- Grounding: Adaptive Personal Response Engine v2 (9-state threshold machine, 8 response modes)
- System Owner: Joshua Winkler — hardcoded, non-removable, non-bypassable

**Sacred UI:**
- Streamlit interface with full Recoding Temple aesthetic
- Black (#0A0B0D) • Rose Gold (#C9A227) • Gold (#D4AF37) • Lapis (#1E4D8C)
- Eye of Horus SVG in header
- Cinzel + EB Garamond typography
- 6 sections: Forge, Academy, Council, Dugout, Weave, Wiki
