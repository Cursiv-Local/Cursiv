# What Cursiv can do today, and where each thing should live

Extracted from the source (`launcher/chat_commands.py`, `chat_panel.py`,
`memory/semantic.py`, `ui/chat_app.py`, `settings_dialog.py`, `setup_dialog.py`,
the tray menu) on 2026-10-17. Every command keeps working as typed; this is about
adding a visible control where one is missing. Goal: dead simple, and every
control explains itself in one plain sentence.

Where: **S** = Settings · **M** = main window (chat, sidebar, header) · **T** = Tools ·
**K** = Memory & Knowledge · **Y** = System (inside Settings) · **H** = Help only ·
**R** = review (legacy or redundant).

## Preferences (become Settings controls)

| Today | Where | Notes |
|---|---|---|
| `offline on/off` | S · Privacy | Also shown by the status pill (done) |
| `websearch on/off` | S · Privacy | Already a checkbox in Settings |
| `autoupdate on/off` | S · Updates | Already a checkbox |
| `cloud on/off/status` | S · Privacy | Already a checkbox |
| Keys: `gemini`, `groq`, `key`, `openai`, `anthropic`, `free keys` | S · Online AI (optional) | Already in Settings; collapse under "Optional online AI" |
| Model choice (Setup window) | M (header picker, done) + S · Models | Downloads stay in Setup, reached from S · Models |
| `memory learn on/off` | K · Memory | No control today |
| `tone <…>`, `style` | S · How Cursiv answers | No control today |
| `files on/off`, `workspace`, `mode` | T · Coding (advanced) | Only relevant with paid keys |
| `tier 1` | R | Alias of offline mode; keep typed only |

## Actions (main window or Tools)

| Today | Where | Notes |
|---|---|---|
| Chat, `search: …` | M | Search explained in the input's help |
| `save this`, `notes`, note export/import | K · Notes | |
| `remember …`, `what do you remember`, `forget …` | K · Memory | "What I remember" window exists (tray only today) |
| `translate … into …` | T · Translate | Simple form: text box + language list |
| `write to`, `letters`, `open letter`, `legacy` | T · Family letters | Dialogs exist |
| `voice`, `listen`, `paste` | M | Voice button; paste an image into the input |
| `council`, `/full`, `agents`, `@name`, `agent council` | T · Advanced | Explain in one line each |
| `codex`, `ref` | T · Coding / K · Reference | `ref` becomes browsing the reference |
| `evolve`, `plugins`, `projects` | T · Advanced | Owner-oriented |
| `image <description>` | T | Needs a key; say so on the button |
| `pull <url>` | T · Advanced | Online; disabled in offline mode |
| `grok`, `claude`, `chatgpt` (retry with a provider) | R | Keep typed only |
| Make a Cursiv USB (tray) | T | |
| Phone link (title bar, tray) | T and title bar | |
| Training data (header "⋯") | T · Advanced | |

## System (Settings · System)

| Today | Where |
|---|---|
| `status` | Y · About this computer (model, Ollama, offline, keys, version) |
| Setup window (tray) | Y · Models and engine |
| Check for Updates (tray, hidden button) | Y · Updates |
| Send problem report (tray) | Y · Help and diagnostics |
| Security Questions (tray) | Y · Account |
| Data folder (Settings) | Y · Your data (open, back up) |
| `phases` / "why that answer" | H, plus a "Why this answer?" link on each reply later |

## Help only

`help`, `help more`, `help <topic>`, explanations of council, agents, memory,
the offline reference, keyboard shortcuts, troubleshooting.

## Review (legacy, redundant or owner-only)

| Item | Why |
|---|---|
| Hidden control sidebar in `cursiv_launcher.py` | Duplicates the tray; remove after its update-button logic moves |
| Getting Started dialog | Out of date (llama3.1 / "Winkler-Codex" downloads); replace with the first-run screen |
| Fleet Dashboard, Command Access | Owner-only, needs env vars; keep behind owner mode |
| `hermes`, `queue`, `obsidian …`, `postal …` key commands | Niche; keep typed and list in Help → More |
| `tier 1`, provider-retry commands | Aliases; keep typed only |

## Gaps: important things with no visible control today

1. What Cursiv remembers: only from the tray or by typing. Needs a sidebar entry.
2. Memory learning on/off: typed only.
3. How Cursiv answers (tone): typed only.
4. Updates, problem report, security questions: tray only.
5. Notes and the offline reference: typed only.
