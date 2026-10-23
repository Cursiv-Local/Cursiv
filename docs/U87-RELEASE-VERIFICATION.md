# U87 release verification

**Published and publicly verified.** GitHub latest is
[v3.14-U87](https://github.com/Cursiv-Local/Cursiv/releases/tag/v3.14-U87),
published 2026-10-23 03:26:19 UTC (October 22, 11:26 pm Eastern).

The owner authorized committing, pushing, releasing installers and publishing
the website. GitHub latest was verified as U86; remote main was
`82cf6c197419828b5bfbf8e03fc638427fd4eb55` before this release. Work uses
`codex/phone-help-testers`. Existing published tags and binaries remain immutable.

## Scope

- `launcher/phone_help.py`: shared exact strings and HTML/Markdown link helpers.
- `launcher/chat_commands.py`: short Help in both profiles and existing field help.
- `launcher/field_notebook.py`: clickable pointer in the existing explanation.
- `launcher/nav_windows.py`: render pointers outside code examples in Help.
- Existing help/UI regressions assert exact wording, single occurrences, actual
  hrefs, external-link support and unchanged notebook records.
- `website/testers.html`, `website/index.html`, `cloudflare/publish.mjs`: secondary
  tester link, static contact page, allowlisted build, sitemap and page-specific
  no-transform/CSP headers. No forms, endpoints, trackers or required accounts.
- App, launcher and Inno Setup/output versions agree on `3.14-U87`.
- Release notes, README, changelog, handoff and current website evidence are updated.

Only help/presentation, release identity and evidence change. Notebook storage,
import format, chains, model providers and command behavior remain intact.
Personal `test_internals/` and private settings are excluded and preserved.

## Checks

The focused Help/UI run passed **106 tests in 12.94 s** before the version bump.
Final versioned source tests, package jobs and anonymous publication checks are
recorded below after execution; pending checks are not treated as passes.

No fresh full truth benchmark is required to attribute these native strings to
the application. No historical model score is relabeled as U87. Unsigned packages,
known model errors and unverified physical USB persistence remain limitations.

## Final versioned source checks

Full isolated Windows suite: **1,495 passed, 1 skipped in 184.54 s**.
Snapshot/manifest/log: `%TEMP%/cursiv-live-followup-xauw1azn`. The skip requires
a real Mac Keychain. All application/launcher Python files match the passing
snapshot after newline normalization. Application fingerprint:
`c688ea201ae0dc24859e1ae320437979a95dc17086aa30200a7db8979ac3bfe1`.

The untracked personal fixture is preserved/excluded. Its current SHA-256 is
`efb67cb4aa306cbe3daf6dafd432fa918fa91f7e21dd3278cdf2489b84e0cac7`; this differs from the older U86 record,
so that historical hash is not treated as this task’s baseline or restored.
No private data is included in the source commit. Hosted CI, package checks
and public outcomes follow after completion.

## Tagged source and build identity

`v3.14-U87` resolves to `58a6d8d3bfe4cc0a75e3e2fd5fe0a34d6ee0c3b5`.
The Windows builder checkout HEAD and normalized fingerprint match the passing
source snapshot. The build log’s short `f1091a5` identifies the annotated tag
object, not a different application commit. Main/feature/tag were pushed
atomically without moving published tags or force-pushing. The actual updater
comparison offers U87 to U79/U81/U82/U83/U84/U85/U86 and rejects the same U87.

- Source CI: [39893933965](https://github.com/Cursiv-Local/Cursiv/actions/runs/39893933965).
- Tagged Mac build: [39893958360](https://github.com/Cursiv-Local/Cursiv/actions/runs/39893958360).
- Windows build log: `%TEMP%/cursiv-u87-clean-build.log`.

All **20 website tests passed** after the release evidence was populated. The
first website check during report preparation failed because its pending
software-count record did not yet exist; after recording actual results it
passed without weakening the assertion. The static build includes 15 files
plus assets/notebook/privacy; five current pages match the generated output.
After Git normalized source line endings, output was rebuilt before byte comparison.
Existing metadata, primary download links and historical model artifacts remain.

## Exact initial release change inventory

- `CHANGELOG.md`
- `HANDOFF.md`
- `README.md`
- `cloudflare/publish.mjs`
- `cursiv_v215/core/selfknow.py`
- `docs/RELEASE-U87.md`
- `docs/U87-RELEASE-VERIFICATION.md`
- `installer/cursiv_setup.iss`
- `launcher/chat_commands.py`
- `launcher/cursiv_launcher.py`
- `launcher/field_notebook.py`
- `launcher/nav_windows.py`
- `launcher/phone_help.py`
- `tests/test_chat_feedback.py`
- `tests/test_help.py`
- `tests/test_live_test_followup.py`
- `tests/test_ui_redesign.py`
- `website/ai-reliability-testing.html`
- `website/index.html`
- `website/start.html`
- `website/testers.html`
- `website/vision.html`

## Completed Windows and hosted source gates

Hosted source run 39893933965 succeeded at the immutable tag commit:
Windows **1,495 passed, 1 skipped in 123.14 s**; Mac **1,485 passed,
11 skipped in 395.27 s**. Source CI and the tagged Mac package workflow are
separate gates. The successful source logs are retained locally with the report.

The clean Windows build passed its frozen full-window/tray/chat self-test,
notebook read/write/chain/signed-export, documents, calculations and import checks
(`ALL PASSED`). Build report: `%TEMP%/cursiv_release_yhctce5c/frozen-selftest.txt`.
Python 3.13.13, PyInstaller 6.22.3; 37 exact packages are attached as
`U87-build-dependencies.txt`. Inno Setup compiled in 82.906 s. File/product
versions are `3.14-U87`; Authenticode is **NotSigned**.

Both Windows installers have **53,501,231 bytes**, SHA-256
`00a535e37563bd8a70d3f71795313a8bde66a06a3ec20e8b272d1bba38938318`.
The versioned/stable files are identical and both are in `SHA256SUMS.txt`.
Uploaded draft digests agree. No owner installation or data migration occurred.

## Completed tagged Mac package

Mac job 39893958360 succeeded: **1,485 passed, 11 skipped in 407.99 s**,
then frozen full-window/notebook self-test `ALL PASSED`, four window captures,
DMG creation and draft upload. The downloaded main/Notebook/Settings/Tools
captures were inspected; the exact new phone line is visible and fits in the
notebook explanation. This does not establish independent physical Mac/phone use.

The downloaded DMG matches both draft alias digests and `SHA256SUMS-mac.txt`:
**68,546,773 bytes**, SHA-256
`83b8c7de48547c884b41d1514f35991ced377cd364c5c82b84d967c6828cb998`.
Mac is unsigned/unnotarized. All seven expected draft assets are present.
The release remains a draft until these checks are reviewed; anonymous download,
website and tester-page privacy checks are recorded after actual publication.

## Publication and live verification

Evidence commit `828a8c0` followed the immutable application tag with docs/site
copy only. Main and `codex/phone-help-testers` are pushed. The existing Cloudflare
`cursiv-web` Worker was deployed with Wrangler 4.152.0, version
`88365b00-a40a-441f-8658-86db16ba48a6`. Six static assets were uploaded: homepage,
download, direction, test evidence, testers and sitemap. Static privacy headers
are included. Worker source, domains, D1/AI bindings, secrets and schema are unchanged.

All **34 anonymous public release/site checks passed** at 2026-10-23T03:27:46.304602+00:00:

- Latest stable U87 and immutable tag commit match the tested source.
- Both stable installers were downloaded in full without credentials; actual
  bytes/hashes match their aliases, public checksum files and asset digests.
- Nine marketing/policy pages return HTTPS 200 with correct canonical URLs,
  parsed structured data when present, and no noindex. Current generated pages
  match live content after removing only the exact pre-existing Cloudflare beacon
  verified in the pre-deployment baseline; no other differences are ignored.
- The homepage secondary tester button points to `/testers`. The new page matches
  the generated file, retains the literal visible mailto and GitHub issue links,
  and contains no form/input/iframe/script or Cloudflare Insights insertion.
- Actual testers headers include no-transform, script-src none and connect-src
  none. The clear email address is not rewritten. No signup or form handler exists.
- Main social URLs are absolute/unique and the public preview PNG is 1200×630.
- Existing phone app/notebook, health, robots and sitemap work; the sitemap
  includes `/testers`. Private statistics routes reject anonymous requests with
  401/no-store, and the legacy hostname preserves the tested path with 301.

The pre-existing download counter still returns 503/unavailable with `total:null`.
It is recorded separately from the 34 passing publication checks, never as zero
downloads. No counter availability fix or analytics-setting change is claimed.
The normal existing edge beacon remains on older pages; testers is specifically
protected and its absence was verified in the live HTML.

Publishing triggered redundant Mac run 39895019031. It completed as cancelled
before the release-upload step (skipped), preserving the already verified bytes.
The successful tagged Mac job is recorded separately. The public verification
asset is `u87-release-verification.json`; raw public/CI evidence is retained under
`cloudflare/.wrangler/u87-release-review/`.

The owner app was not installed or restarted. U86 and earlier can receive U87
through the normal online update check. Windows remains unsigned and Mac
unsigned/unnotarized; physical USB memory persistence and independent clean-PC
installation remain unverified. No new full truth-benchmark score is claimed.
