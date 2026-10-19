# Cursiv: an offline AI assistant for field research

> Runs on your own laptop with the internet blocked if you want. Records field data you can defend,
> works out the numbers in code, answers from your own protocols with page numbers, and says where
> every answer came from.

<p align="center">
  <a href="https://github.com/winklersllc2026-bit/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">
    <img src="https://img.shields.io/badge/Download_Cursiv-Windows_10_%2F_11-2255DD?style=for-the-badge&logo=windows&logoColor=white" alt="Download Cursiv for Windows" height="48">
  </a>
</p>

<p align="center">
  <b><a href="https://github.com/winklersllc2026-bit/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">Download Cursiv for Windows</a></b> (about 80 MB) ·
  <a href="https://github.com/winklersllc2026-bit/Cursiv/releases/latest/download/Cursiv-mac-latest.dmg">Mac, early (Apple Silicon)</a> ·
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

### On a Mac (early)

For Apple Silicon Macs (M1 or newer), macOS 12+. Download `Cursiv-<version>-mac-arm64.dmg` from the
[latest release](https://github.com/winklersllc2026-bit/Cursiv/releases/latest) and drag Cursiv into Applications.
This build isn't signed by Apple yet, so the first time: try to open it, then **System Settings → Privacy & Security →
Open Anyway**. Setup installs Ollama into your Applications folder (no admin password) and downloads the model.

Honest status: the Mac version is built and tested automatically on Apple hardware at GitHub (the full test suite and
a self-test of the built app), but nobody has used it on their own Mac yet. The Cursiv USB drive is Windows-only.
Saved AI keys go into the macOS Keychain.

---

## What it does

- **Local only, and you can see it.** The AI model runs on your computer. Offline mode blocks every
  connection off the computer; the top of the window says *LOCAL ONLY · internet blocked*. See
  [PRIVACY.md](PRIVACY.md) for everything that could ever leave the computer, and when.
- **A field notebook you can defend.** Observations are kept exactly as typed (12.40 stays 12.40), with
  site, coordinates, sample IDs, observer and photos. Nothing is overwritten: a correction is a new entry
  with a reason. Every entry is fingerprinted and chained, and exports are signed by the laptop's own key
  (`field log verify <folder>` checks them). CSV, JSON, GeoJSON and a printable field report.
- **Photos.** The paperclip adds photos to a field entry (the camera's time and GPS are kept) or asks the
  local image model what a photo shows. Making new images needs an online service; Cursiv only reads them offline.
- **Numbers worked out in code, not guessed:** unit conversions, degrees-minutes-seconds, UTM, distance and
  bearing between GPS points, dilutions, statistics, clock times, bleach doses, the lightning 30-minute rule.
- **Your documents.** Import protocols and SOPs; answers quote them by page, and say when they don't cover
  a question. "Answer only from my documents" refuses anything else (except emergencies).
- **Every answer says where it came from:** Cursiv's offline reference, your documents, Cursiv's
  calculations, or *model knowledge (not checked against a source)*, written by Cursiv, not by the AI.
- **Checks after every answer** for unsupported claims, wrong doses, and answers that contradict themselves.
- **Team sync without internet.** Laptops share their signed logs by USB stick or shared folder; nothing is
  merged or overwritten, and disagreements are shown, not resolved by software.
- **Measured.** A fixed truth benchmark with every failure published ([bench/](bench/)), and an offline
  demonstration with zero outside connections ([OFFLINE-DEMO.md](OFFLINE-DEMO.md)).
- **Try it with sample data:** type `demo`. A walkthrough for showing it to a team: [docs/FIELD-DEMO.md](docs/FIELD-DEMO.md).

Personal features from earlier versions (family letters, a legacy vault, the phone app, coding help, the
council, custom agents, LoRA training) are still there but hidden: Settings → Appearance → *Show personal features*.

**Not yet:** field use by a research team, professional review of the first-aid content, code signing, live GPS.

---

## Cursiv on a USB

Tray menu → **Make a Cursiv USB…** copies Cursiv, its AI engine and your models onto a USB drive. Plug it into any Windows PC and double-click **Start Cursiv** — nothing gets installed, it works offline, and everything it saves stays on the drive.

- Everything together is about **30 GB** — use a **64 GB or bigger** USB 3 drive or USB SSD, formatted **exFAT**.
- By default the USB starts fresh, so you can **give someone their own Cursiv**. Tick *"Include my memories, keys and settings"* to make a private copy of yours.

---

## A note on the guardrails

Cursiv has a local-only login, encrypts your saved AI keys for your Windows account, asks before every file it writes (and never touches its own keys or login files), and has an offline mode (`offline on`) that blocks every connection off your computer.

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

## Privacy, and a demo with sample data

**[PRIVACY.md](PRIVACY.md)** lists what stays on your computer, everything that could leave it and when, and what offline mode blocks. **[docs/FIELD-DEMO.md](docs/FIELD-DEMO.md)** is a 10-minute walkthrough for showing Cursiv to a research group: type `demo` to load a sample stream survey and protocol, kept apart from your own records.

## For developers

**[TECH.md](TECH.md)** explains how Cursiv is built — the desktop app, the chat engine, memory, the council, the login and protections, training, the USB edition — and how to run it from source and build the installer.

---

## About

Cursiv was designed and built by **Joshua Winkler**. It is shared freely: anyone with a computer should be able to have a real AI that runs on their own machine, without subscriptions, without cloud dependency, and without handing their data to anyone.

The world's knowledge should not live in one place. It should be spread across people, machines, homes and schools, so no single failure can take it all down.

Take it. Use it. Build on it. Make it yours.

---

## License

Released under the [MIT License](LICENSE) — you are free to use, modify and share it. Copyright © 2026 Joshua Winkler.
