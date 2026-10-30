# Cursiv

Cursiv is a **free, open-source local AI assistant with tamper-evident notebooks**, offline document
retrieval and portable Windows USB/SSD workspaces. Its SHA-256 record chain and linked corrections help
preserve observation history and detect changes against a trusted record; they do not prove an observation
was true. Built for researchers, technicians, independent workers and anyone keeping detailed records.

Local language models run on your PC through Ollama. Cursiv is an application, not a new language model;
model licenses are separate from its MIT license. Supported local features work offline after setup.
[Local AI guide](https://cursiv.us/local-ai) · [Compare local AI tools](https://cursiv.us/compare) ·
[Documentation and evidence](https://cursiv.us/documentation)

<p align="center">
  <a href="https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-Setup-latest.exe">
    <img src="https://img.shields.io/badge/Download_Cursiv-Windows_10_%2F_11-2255DD?style=for-the-badge&logo=windows&logoColor=white" alt="Download Cursiv for Windows" height="48">
  </a>
</p>

[Mac build (early)](https://github.com/Cursiv-Local/Cursiv/releases/latest/download/Cursiv-mac-latest.dmg) · [Website](https://cursiv.us) · [Release notes](https://github.com/Cursiv-Local/Cursiv/releases/latest)

## What you can do

- **Keep tamper-evident notes:** Record observations, photos and sample IDs. Verify the record chain and add corrections that preserve original entries. See [notebook integrity and its limits](docs/NOTEBOOK-INTEGRITY.md).
- **Work with documents:** Import protocols and field guides, then ask questions about them with page references where available.
- **Check calculations:** Convert units, work out distances and times, and calculate dilutions or statistics.
- **Work with workspace files:** Create, read, append and search using plain requests inside a folder you authorize.
- **Keep useful context:** Save selected facts and notes to find again later. Memory is selective, not a complete record of everything you say.
- **Check answers:** See labels for supplied references, documents and calculations, alongside unchecked model replies.

## Get started

**Windows 10 or 11, 64-bit.** Allow at least 8 GB RAM and roughly 6 GB of free space for an initial model; requirements vary by model.

1. Download and run the Windows installer above.
2. Create a local account.
3. Use Setup to install Ollama and download a model. Once it is ready, start chatting.

The initial downloads need internet access. Type `offline on` to block Cursiv's internet connections afterward.

Windows may show an unrecognized-publisher warning; Windows-trusted signing and Apple notarization are still pending. Read [how to verify a download](docs/OWNER-RELEASE-SIGNING.md) before continuing.

Ask **“What can Cursiv do?”** for a short built-in guide with examples.

To explore without using your own records, type `demo`. Type `demo off` to return to your data, or `help` to see the available commands.

## Phone and USB options

- **[Phone notebook](https://cursiv.us/notebook):** Open it online once, then capture observations without signal. Export the file and import it into Cursiv. Export regularly—browser storage can be cleared.
- **[Phone photo chat](https://cursiv.us/app):** A separate online page for questions about photos. It needs internet access.
- **Portable Windows kit:** Choose **Make a Cursiv USB…** from the tray menu to include the app, Ollama runtime and selected model files. The host still needs compatible Windows hardware and drivers. See [what travels, privacy limits and physical-test boundaries](https://cursiv.us/portable-workspace).

See [phone and portable setup](TECH.md#phone-and-portable-use) for instructions and limits. The Mac build is early; there is no Linux installer.

## Privacy and limits

Local chat runs on your computer. Optional online services can receive the content sent to them when used or enabled. [Privacy details](PRIVACY.md).

On a computer, conversations, memories and (from U98) the field notebook are always encrypted with a passphrase you choose at first start; a lost passphrase can't be recovered. A Cursiv USB drive stays readable by design (use drive encryption if it could be lost). The login only keeps people at your keyboard out; the passphrase is the real protection. [Coverage and recovery](TECH.md#conversation-and-memory-encryption-always-on).

AI answers can be confidently wrong. Cursiv's checks catch some mistakes, not all of them. Verify important results. Cursiv is not certified for medical or safety-critical use, and its first-aid reference has not been professionally reviewed.

## Releases, evidence and development

Latest release: **[U113](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U113)**. See the [release notes](docs/RELEASE-U113.md) and [changelog](CHANGELOG.md).


- [Tests and evidence](docs/CLAIM-EVIDENCE.md): what has been checked and what remains unverified.
- [Help test Cursiv](https://cursiv.us/testers): send a clear report of what you tried and what happened.
- [Contributor quick start](CONTRIBUTING.md): setup and checks.
- [Architecture](ARCHITECTURE.md) and [TECH.md](TECH.md): code layout, storage, builds and release details.

Built by **Joshua Winkler**. Released under the [MIT License](LICENSE).
