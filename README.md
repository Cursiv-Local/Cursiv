# Cursiv — Offline. Yours. Everywhere.

> Not a subscription. Not someone else's server. A private AI companion that lives on your own computer, works without the internet, and belongs to you.

<p align="center">
  <a href="https://github.com/winklersllc2026-bit/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">
    <img src="https://img.shields.io/badge/Download_Cursiv-Windows_10_%2F_11-2255DD?style=for-the-badge&logo=windows&logoColor=white" alt="Download Cursiv for Windows" height="48">
  </a>
</p>

<p align="center">
  <b><a href="https://github.com/winklersllc2026-bit/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">Download Cursiv for Windows</a></b> — one click, about 100 MB ·
  <a href="https://github.com/winklersllc2026-bit/Cursiv/releases/latest">release notes</a> ·
  <a href="CHANGELOG.md">what's new</a>
</p>

**The speed of the answers reflects your hardware. The accuracy of the information must always be verified by you. Cursiv was not designed to replace human judgment — it was designed to support it.**

---

## Install in three steps

1. **Download** the installer with the button above and run it.
   Windows may say *"Windows protected your PC"* because Cursiv isn't from a big company — click **More info → Run anyway**.
2. **Create a username and password.** They're stored only on your computer.
3. **The Setup window** opens and installs Ollama (the free local AI engine) and an AI model, with progress bars. Pick a model, click Download, and start chatting while it finishes.

That's it — one window, nothing else to open. Updates arrive inside the app.

**Needs:** Windows 10 or 11 (64-bit) · 8 GB RAM · about 6 GB free disk for one model (more for extras).
**No download wanted?** Paste a free Gemini or Groq key in Setup and Cursiv answers right away.

---

## What it does

- **Chats offline** through Ollama on your own computer. Cursiv picks the right model for your graphics card.
- **Local first.** When your computer has a model, it answers — your messages stay on your PC. A free [Gemini](https://aistudio.google.com/apikey) or [Groq](https://console.groq.com/keys) key is a backup for when there's no local model or it can't answer, and the way to read images. Paid keys (OpenAI, Anthropic, xAI) are optional, never required. Every reply ends with **"Answered by …"** so you always know which one answered.
- **Remembers you** — lasting facts about each person, learned from conversations or added with *"remember …"*. Everything stays on your computer. *"What I remember"* lets you see, edit and delete it.
- **Reads images** you paste in — offline with the free Gemma 3 model, or with a key.
- **Makes images** with a free Cloudflare account or a paid OpenAI key (type `image a lighthouse at dawn`). Offline models can't make images, and Cursiv tells you how to turn it on.
- **Helps you code** — step-by-step help with local coding models, error diagnosis, and a sandbox that runs and fixes the Python it writes.
- **The council** — ask `council <question>` and Cursiv's advisors each answer from their own angle, then one combined answer comes back.
- **Your own agents** — `agent new <name>: <job>` creates a specialist you talk to with `@name`.
- **Adds new abilities** — `evolve <idea>` writes a plugin, safety-checks it, tests it in a sandbox, and installs it only when you approve.
- **Learns your voice** — save examples in Training Data, then train a small personal model with LoRA and add it to Ollama.
- **Phone app** — link your phone to share one conversation with your computer.
- **Sealed letters** — write letters that only open for the right person.

---

## Cursiv on a USB

Tray menu → **Make a Cursiv USB…** copies Cursiv, its AI engine and your models onto a USB drive. Plug it into any Windows PC and double-click **Start Cursiv** — nothing gets installed, it works offline, and everything it saves stays on the drive.

- Everything together is about **30 GB** — use a **64 GB or bigger** USB 3 drive or USB SSD, formatted **exFAT**.
- By default the USB starts fresh, so you can **give someone their own Cursiv**. Tick *"Include my memories, keys and settings"* to make a private copy of yours.

---

## A note on the guardrails

Cursiv checks messages for jailbreak and probing attempts, has a local-only login, and has an offline mode (`offline on`) that blocks every connection off your computer.

These were not built to restrict you. Every guardrail exists to protect you — to keep your data from leaving without your knowledge, your identity from being impersonated, and your machine from being used against you. If the system feels locked down, that lock faces outward, toward the things that would compromise you. Not inward toward you.

Whoever installs Cursiv owns that copy. You have the final say over it.

**What the login is — and isn't.** It keeps people at your keyboard out of your Cursiv: it never opens without it, and a new login can only be added by someone who can already log in. It is a lock on the front door, not encryption — anyone who can open this computer's files can read Cursiv's memories and conversations, the same as your other documents. Your saved AI keys are the exception: they're encrypted for your Windows account, so a copied file or another Windows user gets nothing usable (a private USB copy holds them readable, so it can run on other PCs — keep that drive safe). Set the security questions when you create your account; they're how you reset a forgotten password.

---

## Why this exists

Every major AI system runs in the cloud — on someone else's terms, on someone else's servers, subject to someone else's decisions about what stays online.

Cursiv was built on a different premise. What happens to all the knowledge we've built when the internet goes down? When a service shuts off? When access is restricted?

**Cursiv is a knowledge seed.** Each install is a piece of AI that lives in a home, a workshop, a school, a studio. It grows with every conversation and can be trained on your own voice.

The goal is simple: **reduce the chance that future generations lose the systems of knowledge we are building for them.**

---

## Honest about what it is

**Speed** — local models run on your CPU and graphics card. A gaming PC is fast; an older laptop is slower. On a computer too slow for local models, skip the model download and use a free key instead.

**Accuracy** — the model does its best, and it will sometimes be wrong, confidently. Treat answers as a starting point. Verify what matters.

**Coding** — built to get you most of the way there and help you understand the rest.

**Privacy** — when the local model answers, nothing you type leaves your computer. A key you added is used only when there's no local model, it can't answer, or you paste an image — and then that message goes to that provider. Cursiv Cloud, a free backup that answers only when no local model is ready, is off unless you turn it on (Setup, Settings or `cloud on`). Web search happens only when you start a message with `search:`. The automatic update check is off unless you turn it on (`autoupdate on`); the Check for Updates button reads GitHub's public release list and sends nothing about you. The phone link and problem reports send only when you set them up or click them. **Offline mode** (`offline on`, or Settings) blocks every connection off your computer and stays on after a restart.

**Ownership** — your data, your models, your copy. Nobody can change it or shut it off remotely.

---

## For developers

**[TECH.md](TECH.md)** explains how Cursiv is built — the desktop app, the chat engine, memory, the council, the Guardian, training, the USB edition — and how to run it from source and build the installer.

---

## About

Cursiv was designed and built by **Joshua Winkler**. It is shared freely: anyone with a computer should be able to have a real AI that runs on their own machine, without subscriptions, without cloud dependency, and without handing their data to anyone.

The world's knowledge should not live in one place. It should be spread across people, machines, homes and schools, so no single failure can take it all down.

Take it. Use it. Build on it. Make it yours.

---

## License

Released under the [MIT License](LICENSE) — you are free to use, modify and share it. Copyright © 2026 Joshua Winkler.
