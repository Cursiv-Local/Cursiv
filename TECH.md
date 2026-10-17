# Cursiv — how it's built

Cursiv is a Windows desktop app written in Python (PyQt6). It talks to a local
AI engine (Ollama) first and to online providers only when the person has
added a key. This page explains the code layout, how a message is answered,
where data lives, and how to run, build and release it.

---

## Repository layout

| Folder | What's in it |
|---|---|
| `launcher/` | The desktop app: main window, chat panel, tray menu, dialogs (Setup, Settings, Training Data, USB maker…), login, updater. `main.py` is the entry point. |
| `cursiv_v215/` | The engine the app runs on (the folder name is historical). |
| `installer/` | Inno Setup script (`cursiv_setup.iss`) that wraps the build into `Cursiv-Setup-<version>.exe`. |
| `scripts/` | `build.bat` (PyInstaller), `package.bat` (installer), `verify_build.bat`, `seal_family_letters.py`. |
| `website/` | The public website and phone web app (cursiv.winklers-llc.com). |
| `cloudflare/` | The Cloudflare Worker behind the website and phone app, plus `publish.mjs` to deploy it. |

### Inside `cursiv_v215/`

| Package | Job |
|---|---|
| `ui/chat_app.py` | **The chat engine.** Builds the system prompt, runs the 8 phases, routes to a model (the local Ollama model first; keys you added and Cursiv Cloud are fallbacks), runs the answer check. No user interface of its own. |
| `chat/` | Parts of the chat engine: saved keys (`keys.py`), web search (`web_search.py`), the AI's file tools (`file_tools.py`), paid providers (`paid.py`). `chat_app.py` re-exports them. |
| `core/` | Phases (`phases.py`), speed tuning for small GPUs and free keys (`speed.py`), self-knowledge (`selfknow.py`), read-only computer tools (`tools.py`), plugins / Cursiv Forge (`plugins.py`), talking style (`style.py`), strand memory archive (`strand_store.py`), constitution. |
| `memory/` | Semantic memory (find by meaning with `nomic-embed-text`, keyword fallback), project memory, session logs. |
| `council/` | The advising council behind `council <question>`: seats answer in parallel, synthesizers combine them. |
| `agents/` | Custom agents (`agent new …`), Babel translation, coding agent, offline queue, reference brain, voice. |
| `coding/` | The coding brain: playbooks, worked examples, error diagnosis, run-and-fix sandbox, `evolve` plugin writer. |
| `guardian/` | Login (bcrypt), security questions, owner mode, the files the AI's write tool may never touch, and the identity line for helper prompts. The login fails closed (Cursiv exits if it can't load), new logins need an existing login, and it is a front-door lock only — memories on disk aren't encrypted; saved keys are (DPAPI, `core/keystore.py`). |
| `training/` | LoRA training (`lora_trainer.py`) and merging the adapter into Ollama (`ollama_merge.py`). |
| `family/`, `postal/` | Sealed letters: per-person letters that open with a name and birth date, and signed letters between people. |
| `council/cursiv_facts.md`, `codex/system_prompt.md` | What Cursiv knows about itself and its persona. Keep the fact sheet accurate when features change. |

---

## How a message is answered

1. **`launcher/chat_panel.py`** takes the text from the chat box.
2. **`launcher/chat_commands.py`** checks for commands first (`remember …`, `council …`, `image …`, `evolve …`, key commands, …). Commands return their answer directly.
3. Anything else goes to **`chat_app.chat()`**, which:
   - runs the **8 phases** (`core/phases.py`): notices stress or a crisis (shows help lines first), recalls memories, picks a route and answer shape, checks connectivity;
   - builds the prompt from the persona, the fact sheet, the person's memories and project notes;
   - streams the answer from the first available model via **`cascade_stream()`**.
4. After the reply, memory may learn a new fact about the person.

**Model order:** the local Ollama model first whenever it has one → paid keys the person added (xAI, OpenAI, Claude) → Groq → Gemini → Cursiv Cloud (off unless turned on, and only when no local model is ready). Pasted images skip the local chat model (it can't see them); with file access on and a paid key, the tool-using paid provider goes first because only it can write files. Every reply ends with "Answered by …", added by the code. Local-only use always works; keys are fallbacks, never requirements.

**Images:** reading uses Claude/GPT-4o keys, then a free Gemini key, then a local Ollama vision model (`gemma3:4b`). Making images uses a paid OpenAI key or a free Cloudflare Workers AI account (FLUX.1-schnell).

---

## Where data lives

| What | Where |
|---|---|
| Keys, settings, memories, training data | `.cursiv\` next to the program (`<install>\_internal\.cursiv\`) |
| Conversations, agents, plugins, projects, login | `%USERPROFILE%\.cursiv\` |
| AI models | Ollama's folder (`%USERPROFILE%\.ollama\models`) |

Nothing in these folders is part of the repository or the installer. On a **Cursiv USB** (`launcher/usb_maker.py`), `launcher/portable.py` points the home folder, the models and Ollama at the drive at startup, so everything stays on the drive.

---

## Run from source

Python 3.11+ on Windows.

```bash
pip install -r requirements.txt
python launcher/main.py
```

Install [Ollama](https://ollama.com) and pull a model (`ollama pull qwen3:4b-instruct`), or use the Setup window, or add a free Gemini/Groq key.

---

## Build the installer

You need PyInstaller (in `requirements.txt`) and [Inno Setup 6](https://jrsoftware.org/isdl.php).

1. Bump the version in three places: `launcher/cursiv_launcher.py` (`_CURRENT_VERSION`), `installer/cursiv_setup.iss` (`AppVer`, `OutputBaseFilename`) and `cursiv_v215/core/selfknow.py` (`VERSION`). Versions keep the major number and add an update suffix: `3.14-U55`.
2. Build the app: `scripts\build.bat` (runs `python -m PyInstaller launcher/build.spec`). The Python you build with is the Python bundled into the app.
3. Build the installer: `scripts\package.bat` → `installer\Output\Cursiv-Setup-<version>.exe`.

## Release an update

The in-app updater reads `https://api.github.com/repos/winklersllc2026-bit/Cursiv/releases/latest` and downloads the attached installer. **A git push alone doesn't update anyone** — publish a GitHub release:

```bash
gh release create v3.14-U55 installer/Output/Cursiv-Setup-3.14-U55.exe Cursiv-Setup-latest.exe --title "Cursiv v3.14-U55" --notes-file notes.md --latest
```

Upload the same installer twice: once with its version name and once as `Cursiv-Setup-latest.exe`. The README's download button and the website link to `releases/latest/download/Cursiv-Setup-latest.exe`; asset links are filename-exact, so without the stable name every download button breaks on the next release.

## Publish the website

```bash
node cloudflare/publish.mjs
```

It copies the allow-listed pages from `website/` into `cloudflare/dist/` and runs `wrangler deploy`. Use `--build-only` to build without deploying.

---

## Optional extras

- **LoRA training** needs `torch transformers peft accelerate datasets` in a normal (non-bundled) Python. The Training Data window checks for them and installs them in a visible terminal. CPU training works but is slow (roughly 6 minutes per example per epoch on a typical CPU).
- **Voice** uses `faster-whisper` and `sounddevice` when installed.
