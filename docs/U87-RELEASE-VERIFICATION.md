# U87 release verification

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
