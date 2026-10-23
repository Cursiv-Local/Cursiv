# Cursiv desktop UI: audit and redesign plan

Status: **plan, awaiting approval.** Baseline recorded as tag `ui-baseline-2026-10-17`; work happens on branch `ui-redesign`.

## 1. Framework and entry point

- **PyQt6** desktop app, packaged with PyInstaller (`launcher/build.spec`) into `Cursiv.exe`.
- Entry: `launcher/main.py` → single-instance lock → login (`login_dialog.py`, which creates the first account) → `CursivLauncher` (`launcher/cursiv_launcher.py`), a frameless `QMainWindow`.
- **Talking to the backend:** `chat_panel.py` loads `chat_commands.py` on a background thread. Each message goes first to `chat_commands.handle_command()` (built-in commands such as `help` and `offline on`); otherwise to `cursiv_engine.ui.chat_app.chat()`, which streams text chunks. Results reach the window through Qt signals. Special chunks: `WRITE_SENTINEL` (a file write the person must approve), `REPLACE_SENTINEL` (a checked answer replaces its draft), image paths.
- No web view and no local server; everything is native Qt widgets.

## 2. Current interface map

| Where | What's there | State |
|---|---|---|
| Title bar (custom, frameless) | "✦ CURSIV", username, 📱 Phone, ⚙ Settings, ☰ sidebar toggle, minimise/maximise/close | Active |
| Left sidebar (`conversation_sidebar.py`) | + New chat, 💾 Save, saved conversations list | Active; saving is manual |
| Chat panel (`chat_panel.py`) | "Cursiv" header, **Training Data** button, transcript, input ("try: council, codex, babel, help"), mic, Send, Stop, status line | Active |
| Status bar | "Ready", version | Active |
| Hidden control sidebar (in `cursiv_launcher.py`) | Getting Started, Ollama Set Up, Security Questions, Check for Updates, Report a Problem, Winkler-Codex download, View Fleet | **Legacy**: built but hidden; still referenced by the update checker (`_upd_btn`) |
| Tray menu | Open, Getting Started, What I remember, Phone, Setup, Make a Cursiv USB, Send problem report, Security Questions, Check for Updates, Fleet Dashboard (owner), Quit | Active, and the only route to several features |
| Dialogs | Settings, Setup (`setup_dialog.py`), What I remember (`memory_dialog.py`), Phone link, USB maker, Problem report, Legacy Vault, Write a letter (`postal_compose_dialog.py`), Training Data, Update, Getting Started, Security Questions, login dialogs | Active |
| Owner-only | Fleet Dashboard, Command Access, unlock dialog | **Experimental**: needs `CURSIV_RELAY_URL` / owner machine |
| Text commands | `help`, `help more`, ~60 commands | Active; the main way to reach advanced features |
| Getting Started dialog | Buttons "Download llama3.1 (~4.7 GB)" and "Winkler-Codex (~18 GB)" | **Outdated** (models and names changed) |

## 3. Usability problems, ranked by impact

1. **No visible trust status.** Nothing on screen says which model is answering, whether it's local, whether offline mode is on, or whether any online feature (keys, Cloud, search) is active. People find out only from the footer after a reply. This is the core promise and it's invisible.
2. **Answers render as raw text.** Markdown isn't rendered: `**bold**`, lists, and the `*[Answered by …]*` / reference / check notes show as symbols. Long answers are hard to read, and Cursiv's own status lines look like model text.
3. **Basics are hidden; advanced features are up front.** Memory, Setup, updates, USB and problem reports live in the tray menu or behind text commands, while "Training Data" sits at the top right and the input hint suggests council/codex/babel.
4. **Conversations aren't saved automatically.** A new user loses a chat unless they notice the 💾 Save button.
5. **Empty first screen.** One grey line; no examples, no sign that Cursiv runs locally. The Getting Started dialog is out of date.
6. **No model choice in the main window.** Switching models means opening Setup.
7. **Visual inconsistency.** Gold boxes around plain labels, mixed emoji icons, a blue Send button against a gold theme, and every dialog defining its own colours and fonts. The frameless custom title bar means no Windows snap layouts and a fragile resize.
8. **Duplicated and legacy UI.** The hidden control sidebar duplicates the tray menu and still holds live references; the Getting Started dialog duplicates Setup.

## 4. Proposed layout

```
┌───────────────┬──────────────────────────────────────────────────────┐
│ + New chat    │  [qwen3 4B · local ▾]        ● Local only  (Offline) │  ← model picker + status pill
│ 🔍 Search     │──────────────────────────────────────────────────────│
│ Today         │                                                      │
│  Water plan   │        conversation, centred column (~760 px)        │
│  Fence math   │        rendered Markdown; each answer has small      │
│ Earlier       │        chips: "Local · qwen3 4B", "Reference:        │
│  …            │        water-purification", "Checked" / "Notes"      │
│               │                                                      │
│───────────────│  ┌────────────────────────────────────────────────┐  │
│ 🧠 Memory     │  │ Message Cursiv…                   📎  🎙  ➤/■ │  │
│ 📚 Knowledge  │  └────────────────────────────────────────────────┘  │
│ 🧰 Tools      │   Runs on this computer. Answers can be wrong.       │
│ ⚙ Settings    │                                                      │
└───────────────┴──────────────────────────────────────────────────────┘
```

- **Sidebar (collapsible):** new chat, search, conversations auto-saved and grouped (Today / Earlier) with rename and delete. At the bottom: Memory, Knowledge, Tools, Settings.
- **Status pill** (top right), always accurate and clickable: *Local only* / *Offline mode* / *Online features on: Gemini key, search*. Clicking it opens "Privacy & network" settings. Driven by `core/netgate.py` and the saved keys, not by assumptions.
- **Model picker:** installed Ollama models with a size hint and "suggested for this computer"; "Get more models" opens the Setup page.
- **Answers:** rendered Markdown; Cursiv's own notes become chips, not text; a copy button.
- **Empty state:** "What can I help with?", four example prompts, and the "runs on this computer" line.
- **Memory:** what Cursiv remembers, with origin and date; search, edit, forget.
- **Knowledge:** the offline reference (browse and search entries, review status), saved notes, and later observations.
- **Tools:** Letters, Translate, Coding, Council, Agents, Make a USB, Training data, Phone link. Owner-only tools appear only for the owner.
- **Settings (one window, sections):** General · Models (from Setup) · Privacy & network (offline mode, web search, Cloud, keys) · Updates · Account & security questions · Data folder · About. This replaces separate Settings / Setup / Security Questions entry points; the old dialogs' code is reused, not rewritten.
- **Native window frame**, so Windows snap and resize work; minimum size about 760×520; tested at 100–200% display scaling.
- **One theme module** (`launcher/theme.py`): colours, fonts, spacing and button styles used by every window.

Nothing is removed: every feature reachable today stays reachable, from the sidebar, Tools, Settings, the tray or text commands.

## 5. Implementation order (each step shippable and tested on its own)

1. **Theme module and visual clean-up:** `theme.py`; remove the label boxes; consistent buttons and fonts in the main window. No layout change.
2. **Trust status:** status pill and model picker in the chat header, live from netgate, keys and the Ollama model list.
3. **Readable answers:** render Markdown in the transcript; message blocks with chips for engine, reference and check result; copy button. (Must keep `REPLACE_SENTINEL` and write-approval behaviour.)
4. **Sidebar:** auto-save conversations, groups, search, rename and delete; bottom navigation.
5. **Settings window with sections**, absorbing Setup models, keys, privacy switches, updates and security questions.
6. **Memory, Knowledge and Tools pages.** Training Data moves into Tools; the input hint becomes plain.
7. **First run:** new empty state and a short first-run card, replacing the outdated Getting Started dialog.
8. **Native frame and resizing.**
9. **Remove the legacy hidden sidebar and duplicates**, once nothing references them (move `_upd_btn` logic to the update service first).

## 6. Risks, dependencies, regression tests

**Dependencies to keep working:**
- `chat_panel` ↔ `chat_commands` signals: the streaming chunk, done, error and cancel signals.
- Write approval (`WRITE_SENTINEL`), draft replacement (`REPLACE_SENTINEL`), image results.
- Voice and paste-image.
- Commands intercepted by the window: `write to`, `legacy`, `clear`, and the family-letter "babel I am …".
- History format and saved conversations (`conversations.py`, which stores transcript HTML).
- The update checker's references to `_upd_btn`.
- The single-instance lock, tray, login flow and Setup auto-open.

**Risks:**
- Markdown rendering changes what's saved in conversation HTML, so older saved conversations must still open.
- Replacing the frameless window changes start-up geometry.
- The status pill must never claim "local only" when a key or Cloud would be used. It reads the same gate the network code uses.

**Regression tests (offscreen Qt, no network):**
- The main window builds.
- A message streams through to the transcript.
- A revised answer replaces its draft.
- Write approval still prompts.
- Commands return their text.
- The status pill matches netgate, keys and Cloud in every combination.
- The model picker lists installed models and changes the model used.
- Conversations save and reopen, including old-format files.
- Each Settings section opens and saves.
- Each Tools entry opens its existing dialog.
- Before/after screenshots of every window, rendered offscreen, kept in `docs/ui/`.
- The existing 154 tests and the truth benchmark stay unchanged.
