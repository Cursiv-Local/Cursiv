# Code map — where things are

One line per module, grouped by job. Use it to find where to start; read the module
itself for the details. `tests/test_code_map.py` fails if a module is added, moved or
removed without updating this page. Paths under "Engine" are in `cursiv_engine/`.

## How a message flows

`launcher/chat_panel.py` (send) → exact commands: `launcher/chat_commands.py` →
`command_dispatch.py` → `commands_*.py`; notebook / memory commands:
`core/notebook_tools.py`, `memory/intents.py` → plain words that look like an action
(U99): `core/intent.py` → confirm card → the same native command → otherwise the chat
engine: `ui/chat_app.py` (facade) → `chat/completion.py` (native answers first, then the
model) → `chat/conversation.py` (prompt) → `chat/routing.py` → a provider →
`core/verify.py` / `core/answer_check.py` (checks) → `launcher/chat_transcript.py` (render).

## Engine

### Chat pipeline (`chat/`, `ui/`)
- `ui/chat_app.py` — facade the window calls; also the runtime object the chat modules call back through (its wrappers are what tests patch).
- `chat/runtime.py` — the services the chat modules expect from that runtime.
- `chat/completion.py` — one turn: native answers, routing, model, checks, corrections.
- `chat/conversation.py` — builds the prompt: persona, memory, status, evidence.
- `chat/context.py` — prompt pieces: live status, file tools, memory context.
- `chat/routing.py` — which engine answers (local first, then the person's keys).
- `chat/local_provider.py` — Ollama calls.
- `chat/cloud_providers.py` — OpenAI, Claude, Gemini, Groq, xAI, Cursiv Cloud calls.
- `chat/provider_tools.py` — tool calls inside provider answers.
- `chat/streaming.py` — streaming and time limits.
- `chat/review.py` — the optional follow-up review of an answer.
- `chat/response_style.py` — trims closers, drops false refusals and self-certification.
- `chat/provenance.py` — source labels from application records.
- `chat/status.py` — the network pill and "what can go online" answers.
- `chat/keys.py` — saved settings and AI keys in config.json.
- `chat/optional.py` — optional parts with fallbacks.
- `chat/uploads.py` — attached files.
- `chat/web_search.py` — `search:` (DuckDuckGo or Brave), cached.

### Answers without the AI model
- `core/native_answers.py` — the entry point: version, date, help, calculations.
- `core/clock.py` — today's date and time from this computer.
- `core/calc.py` — arithmetic, percentages, clock times.
- `core/fieldcalc.py` — units, coordinates, dilutions, statistics, speed × time.
- `core/fieldmath.py` — volume / flow / duration.
- `core/datecalc.py` — dates, weekdays, spacing, proportions.
- `core/resources.py` — supplies, people and time.
- `core/feature_answers.py` — reviewed "what can Cursiv do" answers.
- `core/philosophy_policy.py` — contested-question policy.
- `core/reference.py` — the offline reference (first aid, safety) in chat.
- `core/phone_help.py` — phone notebook pointers.
- `core/deterministic_overrides.py` — withdrawals from explicit evidence (e.g. dose conflicts).

### Checking answers
- `core/verify.py` — the check after a draft exists (ledger, arithmetic, sources).
- `core/answer_check.py` — model-free checks on every finished answer.
- `core/answer_assessment.py` — checks against the turn's execution evidence.
- `core/answer_evidence.py` — evidence attached to a finished answer.
- `core/claims.py` — what an answer says Cursiv did vs. what Cursiv recorded.
- `core/grounding.py` — source evidence for the current turn.
- `core/review_policy.py` — which answers get a review.
- `core/crosscheck.py` — a second model's review, only on request.
- `core/problems.py` — stable finding codes.
- `core/feedback.py` — short factual wording of application results (never parses model prose).
- `core/clarify.py` — asks what a vague short message refers to.

### Turn rules and routing
- `core/turn_policy.py` — per-message restrictions ("no tools this turn").
- `core/action_gate.py` — refusals before anything is dispatched.
- `core/command_sequence.py` — quoted payloads stay data; mixed instructions split.
- `core/command_api.py` — command result types and the dispatch sentinel.
- `core/conversation_kind.py` — conversation preferences ("just talk").
- `core/intent.py` — U99 conversational actions: plain words → one native command, checked, confirmed.
- `core/local_intent.py` — memory-only intent classifier used by `memory/intents.py`.
- `core/guidance.py` — U100: "how I talk" hints (how-i-talk.md) and the workspace folder map (CURSIV.md) for the action step; they grant no powers.
- `core/phases.py` — the per-message phases before the model is called.
- `core/tools.py` — read-only computer tools and the tool planner.

### Field work
- `core/fieldlog.py` — the field notebook: entries, hash chain, photos, exports, reports, signatures; whose notebook it is (notebook.json: id and name).
- `core/notebook_tools.py` — notebook commands from chat.
- `core/field_recall.py` — searching the notebook and its averages.
- `core/conversation_recall.py` — "what did I ask three messages ago?" answered from this conversation's stored messages (no model).
- `core/confined.py` — runs plugins and code under OS limits: a Windows Job Object (no child processes, memory/CPU caps, no clipboard), resource limits elsewhere.
- `core/fieldsci.py` — field formulas worked out by code: conductivity to 25 °C (APHA 2510 B), velocity-area discharge with the 0.85 float coefficient, percent DO saturation, µS/cm↔mS/cm, molar solutions.
- `core/science_check.py` — notes under a draft: oxygen saturation against the standard equation, invented example numbers, impossible coordinates, a settled verdict from one reading (overconfidence).
- `agents/profile_context.py` — what a starter profile may read (notebook, documents, a calculation), fetched by code, read only; the Data checker's findings; the check under a profile's answer.
- `core/notebook_proposals.py` — confirm cards built by Cursiv's parser: plain-words records, codes kept out of `site`, append-only corrections ("Correct W-001 temperature from 18.6 to 18.9").
- `core/fieldsync.py` — team sharing and phone imports, without internet; team field drives in each scientist's name, and choosing whose work goes on a drive.
- `core/phone_receive.py` — receiving a phone file over local Wi-Fi.
- `core/devicekey.py` — this installation's signing key for exports.
- `core/demo.py` — the field demo's separate sample data.
- `core/documents.py` — the team's imported protocols and SOPs.
- `core/curiosity.py`, `core/curiosity_engine.py` — the investigation journal.

### Files and workspace
- `core/file_access.py` — the workspace boundary for every file action; the model-claim guard.
- `core/file_requests.py` — plain-words file requests ("add a line to notes.txt saying …").
- `core/file_context.py` — "that file" references from receipts.
- `core/workspace.py` — the chosen workspace folder.
- `core/workspace_search.py` — bounded search inside it.
- `core/export_paths.py` — inspecting an export folder safely.

### Memory and self-knowledge (`memory/` and `core/`)
- `memory/semantic.py` — saved facts: matching by meaning, learning, origin tags.
- `memory/intents.py` — remember / recall / forget with verified outcomes.
- `memory/formation.py` — automatic-memory policy and its failure log.
- `memory/recall.py` — date-scoped recall.
- `memory/projects.py` — running project summaries.
- `memory/session_log.py` — the session log ("session memory"; left out of writing requests since U99).
- `memory/session_notes.py` — U100: each conversation's note (goal, done from records, decided, open, next), used when it's picked up.
- `memory/cleanup.py` — `memory cleanup`.
- `memory/suggestions.py` — U100: the model's guesses wait as "Remember this?" suggestions; only confirmed ones are saved.
- `memory/markdown.py` — U100: memory as readable .md files with a MEMORY.md index ("show my memory folder").
- `core/strand_store.py`, `core/strand.py`, `core/strand_federation.py` — saved notes ("save this") and their packs.
- `core/style.py` — how each person wants answers.
- `core/presence.py` — stable identity and observed operating context.
- `core/capabilities.py` — THE inventory of what Cursiv supports (layer A), live settings (B), agent permissions; read by self-knowledge, native answers, writing guidance, agents and tests.
- `core/evidence_log.py` — what Cursiv actually read or checked this session (layer C); only application code writes it.
- `core/claim_evidence.py` — verification claims need a record; rechecks of earlier claims; privacy-promise and fiction notes.
- `core/selfknow.py` — answers about Cursiv itself (capability records + live report + `cursiv_facts.md` context).
- `core/self_source.py` — `self source` / `self read`: Cursiv's own code and docs.
- `core/self_stores.py` — `self stores`: what is saved and where.
- `core/last_turn.py` — `self prompt`: what was sent for the last answer.
- `core/memory.py` — older temporal-memory helper (one remaining user).

### Storage and encryption
- `core/vault.py` — the encryption envelope and what it covers.
- `core/vault_migration.py` — first encryption, resume, adopting newly covered stores.
- `core/private_store.py` — reads/writes that go through the vault.
- `core/atomic.py` — writes that a power cut can't half-finish.
- `core/state_store.py` — small verified JSON stores.
- `core/data_lease.py` — one Cursiv process per data folder.
- `core/paths.py` — where program data lives.
- `core/keystore.py` — AI keys encrypted for the Windows account.

### Network, engine and speed
- `core/netgate.py` — offline mode: one switch for every outside connection.
- `core/ollama_host.py` — finding and starting Ollama.
- `core/speed.py` — speed tuning for small GPUs and free keys.
- `core/rate_limiter.py` — token rate limiting for free keys.
- `core/web_cache.py` — the web search cache.

### Plugins, coding and agents
- `core/plugins.py` — approved plugins; every call goes to the runner.
- `core/plugin_runner.py` — runs one plugin call in its own guarded process.
- `coding/brain.py`, `coding/playbook.py`, `coding/runner.py` — coding answers, examples, run-and-fix.
- `coding/forge.py` — `evolve`: writes a plugin and tests it in the runner.
- `agents/custom.py` — `agent new …`, `@name`, `agents ask`.
- `agents/babel_agent.py` — translation.
- `agents/codex_agent.py` — the offline coding specialist bridge.
- `agents/hermes_agent.py` — multi-step helper.
- `agents/offline_queue.py` — tasks waiting for a connection.
- `agents/reference_brain.py` — offline reference lookup.
- `agents/voice_agent.py` — local speech to text.

### Security, identity and profile
- `guardian/access_gate.py` — the login (bcrypt).
- `guardian/security_questions.py` — password recovery questions.
- `guardian/protected.py` — files the write tool may never change.
- `guardian/identity_core.py` — the identity line for helper prompts.
- `core/release_identity.py` — the owner release key that verifies installers.
- `core/profile.py` — research vs. full feature profile; the "removed" notes.

### Older parts (few or no users; candidates for U100/U101 clean-up)
- `core/agent.py`, `core/constitution.py`, `core/sigil.py`, `core/scan_display.py`
- `obsidian/exporter.py` — Obsidian vault export.
- `training/lora_trainer.py`, `training/ollama_merge.py`, `training/paths.py` — optional local fine-tuning.

## Desktop (`launcher/`)

### Start-up and window
- `main.py` — entry point: `--plugin-runner`, `--selftest`, portable mode, unlock, login.
- `cursiv_launcher.py` — main window, tray menu, updater.
- `encryption_dialog.py` — first-start passphrase, unlock, resume, adopt.
- `login_dialog.py`, `login_recovery.py`, `login_style.py` — login and recovery.
- `data_home.py` — one home for user data.
- `selftest.py` — `Cursiv --selftest`, run on every release build.
- `update_security.py` — updater identity checks.
- `theme.py` — colours, fonts, light/dark.
- `shell_dialogs.py`, `nav_windows.py` — dialogs, frame, Memory & Knowledge / Tools / Help.

### Chat window
- `chat_panel.py` — turns, signals, conversations.
- `chat_actions.py` — U99/U100 in the window: the action confirm card, suggested memories, session notes, memory folder, workspace map.
- `chat_transcript.py` — rendering, badges, receipts, the one-time tour.
- `chat_badges.py` — badge, receipt, starter, problem and intent-card HTML.
- `chat_rendering.py` — streaming Markdown and the export cache.
- `chat_controls.py` — input, buttons, status pill.
- `chat_feedback.py` — quiet receipts and turn state.
- `chat_review.py` — follow-up reviews in the window.
- `conversations.py`, `conversation_sidebar.py` — saved chats and the sidebar.
- `crosscheck_dialog.py` — the Cross-Check confirmation.

### Commands
- `chat_commands.py` — the command facade the window calls.
- `command_dispatch.py` — the order commands are tried in.
- `command_support.py` — help text, notebook and memory command glue.
- `command_agents.py` — translation, coding, agents.
- `command_media.py` — images, voice, paste.
- `commands_system.py` — offline, files, workspace, updates.
- `commands_credentials.py`, `commands_extensions.py`, `commands_images.py`, `commands_notes.py`, `commands_research.py`, `commands_services.py` — the other command groups.

### Field notebook, phone, memory windows
- `field_notebook.py` — the Field Notebook window.
- `phone_link.py`, `phone_sync.py`, `phone_receive_dialog.py`, `phone_help.py` — the phone app and phone notebook.
- `memory_dialog.py` — "What I remember".
- `saved_notes.py`, `saved_notes_dialog.py` — saved notes.
- `curiosity_dialog.py` — the investigation journal window.
- `training_data_dialog.py` — training data.
- `problem_report.py` — "Send problem report".
- `relay_settings.py` — optional fleet endpoint.
- `settings_dialog.py` — Settings.

### Setup and USB
- `setup_dialog.py`, `setup_checks.py`, `setup_checks_runtime.py` — Setup: engine and model.
- `portable.py` — running from a Cursiv USB.
- `usb_maker.py`, `usb_ops.py`, `usb_ops_runtime.py` — making and updating a drive.
- `usb_sync.py` — data between a drive and a computer (decrypts / re-encrypts).
- `resources/gen_icons.py` — icon generator.

## Elsewhere
- `tests/` — the suite (`-m usb` is the USB gate run before every commit).
- `scripts/` — releases (`scripts/build_release.py`, `scripts/website_release.py`), benchmarks (`scripts/intent_bench.py`, `scripts/suggest_bench.py` for suggested memories, `scripts/fieldcalc_bench.py` for field calculations end to end, `scripts/calc_bench.py` the 237-case calculation benchmark, `scripts/overconfidence_bench.py` for overconfident answers on the live model), `scripts/replay_notebook.py` (replays a notebook conversation on the real code in a throwaway folder).
- `bench/` — truth benchmark and the U99 phrasing set.
- `website/`, `cloudflare/` — cursiv.us and its deploy.
- `installer/` — the Windows installer script.
- `docs/` — release notes, verification reports, plans; `docs/HANDOFF-HISTORY.md` is the old handoff.
