# U91 release verification — October 23, 2026

## Preparation

The owner authorized committing, pushing, releasing and publishing the pending
changes. GitHub latest was confirmed as `v3.14-U90`; this release is `v3.14-U91`.
The three application/installer version strings agree. Existing untracked legal
notes and personal test files are excluded.

Pre-bump full isolated Windows suite: **1,749 passed, 1 skipped** in 228.27 seconds.
Focused philosophy/compatibility replay: **171 passed**, including 50 new philosophy
regressions. Workspace required gate: **63 passed** before release preparation.
These runs used disposable data and fake providers, not a live-model benchmark.

## Required publication gates

Main remains protected, including administrators, with strict/up-to-date GitHub
Actions checks for Windows/Mac workspace tests, Windows/Mac full suites and
security. The supported release helper checks exact merged-main source and runs
the local workspace gate before creating the tag. No force push or protection
change is part of this release.

Final source CI, tagged Windows/Mac build results, installer hashes, owner proof
and public website/download verification will be recorded here as completed.
The release is not yet claimed to be public.

## Limits

No new local-model truth benchmark or physical encrypted-USB persistence test
was run. The private owner key stays outside GitHub, OneDrive and build artifacts.
Owner detached signatures do not remove Windows or Mac publisher warnings.
No new Windows-trusted signing certificate or Apple notarization was introduced.
