# Cursiv v3.14-U87 — Phone Help links and tester feedback

- Add the exact phone-notebook and separate photo-chat pointers to short Help
  in both profiles. Replace the existing `help field` phone mention with the
  offline-capture/export/import instructions rather than duplicating it.
- Show a clickable phone-capture link in the existing Field Notebook explanation.
  Keep the graphical Help links outside code examples so they open in the system
  browser. These are application-owned strings, independent of model responses.
- Preserve notebook storage, import format, append-only chains and command behavior.
  No pop-ups, new tabs or automatic browser prompts were added.
- Add a quiet homepage “Help test Cursiv” button and `/testers`, with the requested
  email/GitHub contact options. There is no form, signup requirement or new
  analytics code. Page-specific headers prevent script/network instrumentation.

## Install or update

Windows: `Cursiv-Setup-3.14-U87.exe` or the identical `Cursiv-Setup-latest.exe`,
with `SHA256SUMS.txt`. Apple Silicon Mac uses the versioned DMG or stable
`Cursiv-mac-latest.dmg`, with `SHA256SUMS-mac.txt`.
U87 is higher than U86 and can be offered by the normal updater when online
checks are allowed. Offline mode blocks update requests. The owner's installed
application is not automatically replaced by publishing a release.

## Evidence and limits

The isolated versioned Windows suite passed **1,495 tests with one Mac-only
skip**. The earlier focused Help/UI run passed 106 tests. Hosted/package and
public verification outcomes are recorded after execution. Hosted source CI
passed **1,495/1 on Windows** and **1,485/11 on Mac** (passed/skipped).
Both tagged packages passed their frozen app/notebook self-tests. The static
website build and all **20 website tests passed**.

[U87 verification](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/U87-RELEASE-VERIFICATION.md)
records actual source/package tests, artifact hashes and publication checks.
The [website test page](https://cursiv.us/ai-reliability-testing#u87) distinguishes
software regressions from historical model results. No new full model score is
claimed for these Help/presentation changes.

Installers remain unsigned; Mac is not notarized. Known small-model verbosity,
closing-question and memory-description problems remain documented in U86's
unscored replay. USB memory persistence/second-PC retrieval and independent
clean-machine installation remain unverified; no storage migration was performed.

## Publication

Published as latest with verified public Windows/Mac downloads. All **34 public
release/site checks passed**, including the live testers page, visible contact
links and absence of injected analytics scripts. The website is deployed to
the existing Worker. Detailed outcomes are attached as `u87-release-verification.json`.
The pre-existing unavailable download counter remains separate from functional
installer downloads.
