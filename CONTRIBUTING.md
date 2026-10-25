# Quick start for contributors

Read these three files first:

1. [ARCHITECTURE.md](ARCHITECTURE.md): message flow and module ownership.
2. [TECH.md](TECH.md): data locations, setup, packaging and release safeguards.
3. [cursiv_engine/ui/chat_app.py](cursiv_engine/ui/chat_app.py): compatible chat
   facade; follow its calls into `chat/conversation.py` and `chat/completion.py`.

Looking for a specific thing? [docs/CODE-MAP.md](docs/CODE-MAP.md) lists every module in one
line, grouped by job, and a test keeps it complete. A first task to pick up:
[docs/GOOD-FIRST-ISSUES.md](docs/GOOD-FIRST-ISSUES.md).

## The one rule behind the code

Cursiv is for people who need to trust what it says. So anything that must be right (a saved record,
a calculation, a lookup, what Cursiv can do) is done by code and checked, and the AI model only words
it. If a change makes the model do more and the code check less, it's the wrong change. New behaviour
lands only with a test that would have caught the old failure, and model-facing changes with a
measured before/after (see `scripts/*_bench.py`).

## Run and check

Use a dedicated checkout and a Python 3.13 virtual environment. Install the exact
release dependencies with `python -m pip install --require-hashes -r requirements-release.lock`.
Run `python launcher/main.py` from the repository root. Ollama is optional for
unit tests; real local-model use requires its separate installation and a model.

Before committing, run `python scripts/check_workspace_files.py`. This focused
workspace/language/release gate uses a disposable home and no GUI windows or model
calls. Then run the full suite below. Both gates must pass; do not push failing work.
GitHub main protection requires `workspace-files (windows-latest)`,
`workspace-files (macos-latest)`, both `test (...)` jobs and `security`, all from
GitHub Actions, with an up-to-date branch and no administrator bypass. Push a
feature branch and use a PR; the updated workflow must be present in that PR.
For releases use `scripts/prepare_release.py` after main CI passes; see TECH.

**The USB function must work every time.** `python -m pytest tests -m usb` runs the
USB gate (about 10 seconds): the whole make-drive → start from the drive → move it →
bring data back cycle (`tests/test_usb_end_to_end.py`) plus the sync, migration and
license tests. It runs before every commit once you enable the hook with
`git config core.hooksPath .githooks`, as its own step in the required `test` job on
every push and PR, and in `scripts/build_release.py`, which also starts the built
app from a USB layout and refuses to package it unless portable mode works.

Run `python -m pytest tests -q` in a disposable checkout/profile without personal
records, production keys or installed-app data. Fixtures redirect storage and
assert watched user data is unchanged. Qt tests use offscreen rendering and never
start Ollama automatically. Use synthetic data for encryption/migration tests;
never enable a test vault on someone else's records.

Website-only checks: `node cloudflare/publish.mjs --build-only`, then run the
`cloudflare/tests/*.test.mjs` files with Node's test runner. On PowerShell pass the
expanded filenames, for example `node --test (Get-ChildItem cloudflare/tests -Filter '*.test.mjs').FullName`.
Build-only does not deploy. The existing PyInstaller specification and
`scripts/build_release.py` define packaging; package renames must update both.

## Boundaries to preserve

- Launcher owns widgets, desktop lifecycle and entry points. Engine owns policy,
  calculations, providers, receipts, notebook and memory backends. See the flagged
  legacy ownership exceptions in ARCHITECTURE rather than copying their design.
- Native results establish execution. Model text never authorizes a tool or proves
  a save. Keep read-only reads, talk-only blocks and memory restrictions tested.
- Do not change the local-first cascade or bypass `core/netgate.py`.
- Notebook chains are append-only; corrections are new entries. Keep signing,
  sample-ID collision, imports and portable path tests intact.
- Protected data writes use the explicit storage boundary. Never add plaintext
  temporary copies, backups, caches or logging of passphrases/messages around it.
- Keep release private keys out of the repository, OneDrive and CI. Existing owner
  signatures and immutable release evidence must remain verifiable.

## Keep documentation reviewable

Update the changelog, relevant architecture/privacy guidance and existing evidence
index with behavior changes. Link README claims to [CLAIM-EVIDENCE](docs/CLAIM-EVIDENCE.md).
Record actual commands/results and distinguish source tests, model benchmarks,
packaged checks and physical testing. Historical results retain their release/model
labels. Prefer updating these documents over adding a new micro-repair report.

Make focused commits; do not include local data, generated reports, signing keys,
installers or unrelated user work. Pushes, releases and deployment require the
owner's current authorization.
