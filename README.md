# Cursiv

Cursiv is a local-first AI assistant for Windows. It runs compatible language models on your computer and includes tools for field notes, documents, calculations, and offline use.

<p align="center">
  <a href="https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">
    <img src="https://img.shields.io/badge/Download_Cursiv-Windows_10_%2F_11-2255DD?style=for-the-badge&logo=windows&logoColor=white" alt="Download Cursiv for Windows" height="48">
  </a>
</p>

<p align="center">
  <b><a href="https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">Download Cursiv for Windows</a></b> (about 53 MB) ·
  <a href="https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-mac-latest.dmg">Mac, early (Apple Silicon)</a> ·
  <a href="https://github.com/Cursiv-Local/Cursiv/releases/latest">Release notes</a> ·
  <a href="CHANGELOG.md">Changelog</a>
</p>

## 1. Intro

### What It Is

Cursiv is open-source software released under the MIT License. Its default setup uses Ollama to run a compatible AI model locally. With a model and its required files installed, supported features can work without internet access.

Its tools include:

- **Field notebook:** Records observations, sites, coordinates, sample IDs, notes, and photos. Photo entries retain camera time and GPS when available. Measurements are kept as entered. Corrections become new entries with a reason; chained fingerprints make later changes detectable. Exports are signed with the device's key. Export to CSV, JSON, GeoJSON, or a printable field report. `field log verify <folder>` checks exported logs.
- **Calculations:** Computes unit conversions, coordinates, UTM, distance and bearing, dilutions, statistics, clock times, bleach doses, and the lightning 30-minute rule in code.
- **Documents:** Import protocols and SOPs. Answers can quote a document by page, identify when it does not cover a question, or follow “Answer only from my documents” (except emergencies).
- **Offline reference and answer checks:** Cursiv can answer from its bundled reference and label whether an answer came from that reference, your documents, a calculation, or unchecked model knowledge. Cursiv's code adds these source labels. Code checks selected claims, numbers, doses, and contradictions; these checks do not catch every error.
- **Photos:** Attach photos to field entries or ask a compatible vision model to describe them. Reading photos depends on an available local vision model or an online provider; making images requires an online service.
- **Phone notebook:** Capture field records on a phone without signal after opening the [phone notebook](https://cursiv.us/notebook/) once. Transfer its export file to the laptop for import. This has no AI chat and is separate from the online photo app. See [phone notebook details](docs/PHONE-NOTEBOOK.md).
- **Phone photo chat:** Take or choose a picture and ask about visible details or text in the [phone app](https://cursiv.us/app). It accepts general photo questions and text chat, requires internet access, and uses the website's online AI providers. Existing device linking shares the conversation with Cursiv on your computer.
- **Team log sharing:** Move signed field logs between computers using a USB drive or shared folder. Cursiv does not merge or overwrite entries; it reports conflicts.

Older personal features—including family letters, a legacy vault, the phone app, coding help, the council, custom agents, and LoRA training—remain available under **Settings → Appearance → Show personal features**.

### What It Isn't

Cursiv is not a frontier model, and its answers are not guaranteed to be correct. Small local models can be confidently wrong; Cursiv's checks catch some errors but do not eliminate hallucinations. Verify anything important.

Cursiv is not certified for medical or safety-critical use. Its first-aid reference has not been reviewed by a medical professional, and a research team has not yet used Cursiv in the field. The app does not provide live GPS. The Mac build is early and unsigned; there is no Linux version.

### Why It Exists

Cursiv is designed to remain useful when internet access is unavailable or an online service cannot be reached. Its guiding idea is to keep useful tools and knowledge on people's own computers, rather than make every task depend on one service or connection.

## 2. Installation & Deployment

### Windows Installer

**Requirements:** Windows 10 or 11 (64-bit), 8 GB RAM, and about 6 GB of free disk space for one model. Additional models need more space.

1. [Download the latest Windows installer](https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe) and run it.
2. If Windows displays “Windows protected your PC,” select **More info → Run anyway**. The installer is not code-signed yet.
3. Create a local username and password, then set security questions for password recovery.
4. In Setup, install Ollama and download a model. You can start chatting while the model finishes downloading.

The initial Ollama and model downloads need internet access. After a compatible model is installed, local chat and other supported local features can work offline. Updates are offered through the in-app updater, which needs internet access to check GitHub. Alternatively, Setup accepts a Gemini or Groq key; those providers require internet access and receive the content sent in their requests.

### Mac Build (Early)

An early build is available for Apple Silicon Macs (M1 or newer) running macOS 12 or later. Download the [latest Mac release](https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-mac-latest.dmg), then drag Cursiv into Applications. The build is not signed by Apple. On first open, use **System Settings → Privacy & Security → Open Anyway** if macOS blocks it.

Setup installs Ollama into Applications without an administrator password and downloads a model. The Mac build is tested automatically on Apple hardware at GitHub, including the test suite and an app self-test, but no one has yet tested it on their own Mac. Saved AI keys go into the macOS Keychain. The USB edition is Windows-only.

### Portable USB Deployment

From the tray menu, choose **Make a Cursiv USB…**. Cursiv copies the app, Ollama, and your installed models to a USB drive or USB SSD. The portable launcher directs Cursiv's home folder, model files, and Ollama to the drive. On a Windows PC, run **Start Cursiv** from the drive; it does not install Cursiv on that PC.

The complete copy is about 30 GB. Use a USB 3 drive or SSD with at least 64 GB, formatted as exFAT. By default, the USB starts fresh without your memories, keys, or settings. Select **Include my memories, keys and settings** to copy them; a private USB copy keeps saved AI keys readable so they can be used on other PCs. Keep that drive secure.

The USB edition is Windows-only. The project has tested its copy, verification, and update steps, but has not yet completed an end-to-end test on a second clean PC. See the [field kit test checklist](docs/FIELD-KIT-TEST.md) for remaining checks.

### Grounded conversation and memory (U82)

Cursiv can retain selected facts across sessions; this does not retrain the
underlying model or provide complete recall. Automatic learning and manual saves
are separate. Ask "memory status" for saved-record/learning status, or "what do
you remember from the past two weeks" for dated saved facts with record IDs.
Dates describe when facts were saved, not necessarily when events happened.

Clear "just talk", "don't inspect documents" and "don't save memories" requests
restrict that turn's tools and retention. Conversation history still follows its
existing save setting. Operational answers use the active workspace/file flag;
file access being on does not prove a particular read/write succeeded. Source
follow-ups use bounded verified excerpts, and explicit unsupported quotations
are flagged. These checks reduce specific failures; model analysis can still err.

U84 includes these U82 foundations and the trust-boundary repairs below.
Installed copies need the new installer to receive source changes.
Implementation, test evidence, exact file inventory and limitations:
[Grounded chat repair](docs/GROUNDED-CHAT-REPAIR.md).
Published installer hashes, CI and package checks:
[U84 release verification](docs/U84-RELEASE-VERIFICATION.md)
([historical U82 record](docs/U82-RELEASE-VERIFICATION.md)).

## 3. Technical Details

### Privacy

When a local model answers, inference happens on your computer. Conversations, memories, imported documents, and field records are stored locally. Local storage does not mean all files are encrypted: conversations and memories are not encrypted on disk. Saved AI keys have separate protection—Windows DPAPI on Windows and the Keychain on macOS.

Online features work when used or enabled:

- Setup downloads Ollama and models.
- Web search sends search terms when you use `search:` or enable automatic search. `pull <address>` requests the page you specify.
- The local model is used first when available. Saved cloud-provider keys can send a prompt or content to the selected provider when no local model is ready, when you choose that provider, or when a feature needs an online provider, such as image handling.
- Cursiv Cloud is off unless enabled; when enabled, it is used only when no local model is ready.
- Update checks are manual unless you enable automatic checks, which are off by default. A manual check reads GitHub's public release list.
- The phone app uses the website for its conversations and photos. Phone linking requires setup; problem reports send logs only when you submit a report.

Offline mode (`offline on`, or the switch in **Settings → Privacy & internet**) blocks every connection off the computer at the socket level and stays on after restart. Web search, page requests, cloud services, update checks, and model downloads are then unavailable. See [PRIVACY.md](PRIVACY.md) for the full data and network details and [OFFLINE-DEMO.md](OFFLINE-DEMO.md) for the published offline demonstration.

### Guardrails and Limitations

Cursiv includes a local login, confirmed file replacements, and an offline network gate. Login is not disk encryption. Workspace tools deny login/key paths and guardian code. Saved AI keys use Windows DPAPI or macOS Keychain where available; portable, legacy or fallback plaintext keys can exist. Conversations and memories are not encrypted on disk.

See [PRIVACY.md](PRIVACY.md), the [threat model](docs/THREAT-MODEL.md), and
[claim-to-evidence mapping](docs/CLAIM-EVIDENCE.md). A stolen private USB copy or
someone with access to your OS account can expose local data. Optional data
encryption has a [separate migration plan](docs/ENCRYPTION-MIGRATION-PLAN.md).
Including private data in a USB copy exports copied API keys in readable form
for use on other computers. Anyone with the drive can read and use those keys;
the USB maker explains this before copying.

U84 hardening repairs the U82 restricted-turn, filename parsing, source
label and failed-tool continuation issues documented in the
[repair report](docs/U82-RESTRICTED-TURN-REPAIR.md). A no-memory request disables
memory saves/automatic learning for that turn; conversation-history storage is
separate. See the U84 publication record for packaged checks and download hashes.

U84 chat also finishes the draft before optional model review. The default
`check fast` skips ordinary turns and adds a short local review as a follow-up
when eligible. `check off` disables model review; `check full` permits a bounded
review/rewrite/recheck. Pure-code checks stay on in every mode. See the
[answer review report](docs/ASYNC-ANSWER-REVIEW.md) for measurements and limits.

**U85 feedback polish:** quiet state and tool receipts, a progress line
only during reviewer calls, and no extra paragraph for a clean review. Notebook
receipts include a record ID/fingerprint; import summaries count new entries
separately from uploads and duplicates. Turn restrictions do not disable chat
history. See [scope, checks and limitations](docs/CHAT-FEEDBACK.md) and
[U85 release verification](docs/U85-RELEASE-VERIFICATION.md).
The fresh local-model run scored 153/158 (96.8%), below U84's 156/158;
[the failure review](bench/FAILURES-U85.md) includes an unsafe allergy answer
missed by the scorer. Passing patterns do not establish medical safety.

The latest [trust-boundary follow-up](docs/TRUST-BOUNDARY-FOLLOWUP.md) closes
additional policy/source/error gaps. Source labels describe application-supplied
evidence; a memory-context label does not claim the model used or verified it.
These changes are included in the U84 release source.

These controls are intended to help the person using Cursiv manage access, files, and network connections. They do not guarantee answer accuracy, privacy in every data path, or safety for high-risk use. Review the [benchmark cases and results](bench/) alongside the limitations above.

Other practical limits:

- Speed depends on the model, CPU, graphics hardware, memory, and context length. Smaller or older computers may run local models more slowly; an optional online provider key is another choice, if available.
- Accuracy varies by model and task. Check important answers against reliable sources.
- First-aid reference entries are not professionally reviewed.
- The phone notebook stores records in the phone browser. It has been tested in desktop Chromium, not on real iPhones or Android phones. Browsers may clear stored data; send records to the laptop regularly and treat the phone as a capture tool, not the archive. Details and limitations are in [docs/PHONE-NOTEBOOK.md](docs/PHONE-NOTEBOOK.md).

### For Developers

#### Run from Source

On Windows with Python 3.11 or newer:

```bash
pip install -r requirements.txt
python launcher/main.py
```

Install [Ollama](https://ollama.com) and pull the default model:

```bash
ollama pull qwen3:4b-instruct
```

You can also install Ollama and a model through Cursiv's Setup window, or add a Gemini or Groq key. See [TECH.md](TECH.md) for the repository layout and architecture.

#### Build the Windows Installer

The installer uses PyInstaller (in `requirements.txt`) and [Inno Setup 6](https://jrsoftware.org/isdl.php).
Use a fresh virtual environment with only `requirements.txt` for release builds;
retain its exact package versions with the release evidence. This keeps unrelated
optional developer packages out of the installer.

1. Update `launcher/cursiv_launcher.py` (`_CURRENT_VERSION`), `installer/cursiv_setup.iss` (`AppVer` and `OutputBaseFilename`), and `cursiv_v215/core/selfknow.py` (`VERSION`). Use a higher update suffix for each release so installed copies detect it.
2. Commit the reviewed source, pass the regression checks and tag that exact commit.
3. Run `py -3.13 scripts/build_release.py v3.14-U85` (substitute the next tag for future releases). It builds in a clean temporary checkout of the tag and writes the installer/checksums to `installer/Output/`.

#### Release an Update

A Git push does not update installed copies. Publish a GitHub release with the
versioned installer, its identical `Cursiv-Setup-latest.exe` copy and
`SHA256SUMS.txt`. The README, website and updater use that stable installer name.
For each new release, substitute an unused higher version in these examples.

```powershell
Copy-Item installer/Output/Cursiv-Setup-3.14-U85.exe installer/Output/Cursiv-Setup-latest.exe
Copy-Item installer/Output/SHA256SUMS-3.14-U85.txt installer/Output/SHA256SUMS.txt
gh release create v3.14-U85 installer/Output/Cursiv-Setup-3.14-U85.exe installer/Output/Cursiv-Setup-latest.exe installer/Output/SHA256SUMS.txt --title "Cursiv v3.14-U85" --notes-file docs/RELEASE-U85.md --draft --verify-tag --repo Cursiv-Local/Cursiv
```

The updater reads `https://api.github.com/repos/Cursiv-Local/Cursiv/releases/latest`.
It requires a higher version; replacing assets under the same version will not
trigger an update for that version. Offline mode blocks update checks.

Attach the tagged Mac package, stable alias and checksum file through the existing
Mac workflow, then review all gates before publishing the draft as latest.
Publication triggers a second Mac workflow; stop a redundant run before it can
replace already verified public bytes. The release report records the successful
tagged build and any intentional duplicate cancellation separately.

Run the fixed benchmark from the release tag (`scripts/truth_bench.py --source
v3.14-U85 --label U85 --model qwen3:4b-instruct`, substituting the new version),
review every failure, and update the website's current test section from that
artifact. `node --test cloudflare/tests/*.test.mjs` checks analytics and verifies
that release labels, model scores and the separate software-test count match
their recorded evidence. Keep historical runs labeled by their actual version.

#### Publish the Website

```bash
node cloudflare/publish.mjs
```

This builds `cloudflare/dist/` from the website's allowlisted files, then deploys with Wrangler. To build without deploying:

```bash
node cloudflare/publish.mjs --build-only
```

The website uses **Cloudflare Workers with static assets and D1**. Its
download analytics provide a cached public GitHub installer counter and a
password-protected `/admin/downloads/` page. Counts use versioned installer assets;
duplicate “latest” copies, source archives and unrelated files are excluded.
Optional Windows/Mac button-click totals are anonymous aggregates and are never
treated as completed downloads. GPC and Do Not Track are respected.

For a new deployment, apply the additive analytics schema and configure the
separate administrator secret. See [website analytics setup, counting rules,
tests and deployment checks](cloudflare/DOWNLOAD-ANALYTICS.md). The existing site
has the analytics tables and authenticated routes. During U84 preparation the
public counter reported unavailable; installer links remain independent. The
release verification record reports the final production check without inventing
a total or treating an outage as zero.
The homepage copy is tightened to an offline-first introduction, four benefits,
expandable practical details and direct latest-installer download buttons.

#### Included Desktop Improvements

U85 carries forward the U81/U82 Saved Notes viewer, incremental chat rendering, native
Field Notebook chat tools, verified filesystem operations and natural-language
memory handling. It adds grounded operational state, per-message boundaries,
dated recall and source checks. U85 adds quiet status/receipts and notebook
continuity with read-back confirmation. See [U85 release notes](docs/RELEASE-U85.md),
[CHANGELOG.md](CHANGELOG.md), [HANDOFF.md](HANDOFF.md),
[rendering measurements](docs/CHAT-RENDERING-PERFORMANCE.md),
[notebook integration](docs/FIELD-NOTEBOOK-INTEGRATION.md), and
[verified local actions](docs/VERIFIED-LOCAL-ACTIONS.md) for scope and evidence.

U84 extracts chat, command and dialog modules,
makes empty/failed answer checks explicitly unverified, and centralizes protected
filesystem mutations. See [ARCHITECTURE.md](ARCHITECTURE.md),
[verification policy](docs/VERIFICATION-POLICY.md), the
[maintenance report](docs/MAINTENANCE-HARDENING.md), and the
[quality checklist](docs/QUALITY-CHECKLIST.md). Signing, clean-machine USB/Mac
validation and packaged Linux support remain open or unsupported as recorded in
[platform readiness](docs/PLATFORM-READINESS.md). Current test and publication
results are in [U85 verification](docs/U85-RELEASE-VERIFICATION.md).

#### Optional Features

- **LoRA training** needs `torch`, `transformers`, `peft`, `accelerate`, and `datasets` in a normal (non-bundled) Python environment. The Training Data window checks for and installs them in a visible terminal. CPU training works but is slow—roughly six minutes per example per epoch on a typical CPU.
- **Voice** uses `faster-whisper` and `sounddevice` when installed.

### Demo with Sample Data

In Cursiv, type `demo` to load a sample stream survey and sample protocol. The demo is labeled as sample data and kept apart from your own notebook and documents. Type `demo off` to remove the sample data and return to your own records.

For the full walkthrough, including how to enable offline mode and what each example demonstrates, see [docs/FIELD-DEMO.md](docs/FIELD-DEMO.md). The demo shows documented workflows with sample data; it does not establish that Cursiv has been used by a research team in the field.

## 4. Authorship

Cursiv was designed and built by **Joshua Winkler**. The project is shared under the MIT License. The repository does not separately describe AI-assisted contributions.

## 5. License

Cursiv is released under the [MIT License](LICENSE). Copyright © 2026 Joshua Winkler.
