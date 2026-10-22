# U84 release verification

## Why U84

The owner authorized source publication, version bump, installer release and
website deployment. U83 was prepared first, but its Mac screenshot job exposed
a missing import in the extracted full-window title bar. The candidate remained
a draft; its public Git tag was preserved. U84 is a fresh tag/source build after
the repair. [The U83 record](U83-RELEASE-VERIFICATION.md) preserves the failed gate.

Read-only follow-up found a missing JSON import in the extracted notes command
and annotation dependencies in extracted files. Two deterministic regressions
failed against the candidate before fixing the runtime imports. The packaged
self-test now builds the entire launcher/title bar/tray/chat panel instead of
only ChatPanel. No unrelated behavior or data format is changed by this repair.
A focused undefined-name scan passed on 21 extracted/related modules.

## Source identity

Application/launcher normalized Python fingerprint after the fixes/version bump:
`e1957d918a246173fa7ad99595becd3f246238c6f5711b81ed6602ffdeb5130a`.
All three versions and the Inno output name agree on `3.14-U84`.
Only intended source/docs/tests/website files are included; personal
`test_internals/`, private configuration, compiled binaries and model data are
excluded from source and website uploads.

## Gates to record

Final isolated regression tests, tagged commit/hosted CI, clean-environment
Windows build/frozen check, Mac package job, exact uploaded hashes, unauthenticated
stable downloads and production website tests are recorded after they complete.
A started or prepared operation is not a passed gate.

## Final versioned source tests

- Full isolated Windows suite: **1,248 passed, 1 skipped in 197.19 s**.
  Log: `%TEMP%/cursiv-maintenance-5_z9e1ek/pytest.log`.
  The skip requires a real Mac Keychain. This run includes both new reproductions
  and the externally observed offline self-test with complete-window coverage.
- The existing screenshot script succeeded on this Windows source snapshot with
  Qt offscreen and synthetic demo data: main window, Tools, Settings and Notebook.
  Files: `%TEMP%/cursiv-maintenance-5_z9e1ek/window-shots/`. The script's `mac-`
  filename prefix does not turn this into a physical Mac test.
- The 18 website analytics checks passed during preparation; final generated HTML
  and production endpoints are checked separately after the current results land.
- Frozen suite 1.5 cases/scoring remain unchanged. Personal test data is excluded.

## Limits retained

Installers are unsigned. Automated checks do not establish a clean-machine
installation, physical second-PC portable-drive use, real-phone behavior,
professional safety validation or independent field use. Local conversations and
memories remain unencrypted. Readable private USB key exports are explained in
app. No owner installation, schema migration or personal-data migration is done.

## Tagged source

`v3.14-U84` resolves to `eede54a79b83c74186275ed4f1aff83bde788739`.
The tag was pushed with the source to main and `codex/maintainability-hardening`.
The fresh full Truth Benchmark explicitly selects this tag with `--source`,
rather than relying on later working-tree documentation edits. The normalized
application fingerprint matches the passing U84 source regression snapshot.

Hosted source CI: [run 39859055762](https://github.com/Cursiv-Local/Cursiv/actions/runs/39859055762).
Mac tagged package: [run 39859098510](https://github.com/Cursiv-Local/Cursiv/actions/runs/39859098510).
Results are recorded below only once the jobs complete.

## Windows artifact

The clean-environment tagged build succeeded with Python 3.13.13, PyInstaller
6.22.3, PyQt6 6.11.0 / Qt 6.11.2 and Inno Setup 6.7.3. Log:
`%TEMP%/cursiv-u84-clean-build.log`. The expanded frozen app self-test returned
`ALL PASSED`, including the full launcher/title bar/tray/chat window, notebook
chain and signed export verification. Report:
`%TEMP%/cursiv_release_574w6dv4/frozen-selftest.txt`.

Both installer names contain exactly **53,451,310 bytes**:

- `Cursiv-Setup-3.14-U84.exe`
- `Cursiv-Setup-latest.exe`

SHA-256 for both:
`9e37cb6fa2c091642ee34794b542b81ffb3ea8badd35e838901e0556a8ac10ae`.
`SHA256SUMS.txt` lists both names. Embedded file/product version is `3.14-U84`;
Authenticode reports `NotSigned`. No signing claim is made.

The builder reported a missing legacy optional `httpx` hidden import; the clean
SDK dependencies include `httpx2`. Required imports and the frozen checks passed.
No dependency was added just to silence a build warning.

An in-memory archive check matched the immutable tag's complete Python
fingerprint to the working application and tested snapshot. The actual updater
version functions offer U84 to U79/U81/U82/U83 and reject same-version U84.
Offline mode still blocks update requests. No installed owner copy was changed.

## Hosted source and Mac package results

Source CI run 39859055762 succeeded on the tagged commit:

- Windows: **1,248 passed, 1 skipped, 123.56 s**.
- macOS: **1,238 passed, 11 skipped, 390.51 s**.

Mac build run 39859098510 succeeded, including its source tests, PyInstaller app,
expanded frozen full-launcher self-test, all four screenshots, DMG construction
and draft-release uploads. This is automation on GitHub's Apple Silicon runner,
not a clean installation on an owner's Mac or a minimum-OS compatibility test.

Both Mac names contain exactly **68,545,849 bytes**:

- `Cursiv-3.14-U84-mac-arm64.dmg`
- `Cursiv-mac-latest.dmg`

SHA-256 for both:
`259e753ca59125a174dfca27f867df6714c6652f9d494040d6535ebb2be2b872`.
`SHA256SUMS-mac.txt` lists both names. An authenticated draft download of the
versioned DMG was independently hashed and matched the uploaded checksum and
GitHub's reported digest. Stable public downloads are checked after publication.
The Mac package remains unsigned/unnotarized.

## Completed current-release model run

The full unchanged suite 1.5 ran from `v3.14-U84`: **156/158 passed (98.7%
overall)**, 100% answerable-case accuracy, 0% case-marked unsupported claims,
9.3 s/case, 24.6 minutes. Source fingerprint matches the tag and passing tests.
[Raw replies](../bench/results/U84-qwen3_4b-instruct-suite1.5.json) and
[failure analysis](../bench/FAILURES-U84.md) retain both failures.

Manual review also identifies an undetected safety implication about contaminated
water in adv-011, the contradictory opening of adv-016, and unsupported reassurance
in passing saf-010. Pattern scores do not establish absence of hallucinations or
medical safety. The prior U83 candidate run is retained separately; score changes
are not attributed to GUI/import repairs. No case, scorer or historical run was
edited to improve the score. Timings include eligible synchronous checks in the
headless harness and concurrent build activity; desktop ready-time replay is separate.

## Final website checks before publication

All **20 Node website tests passed**: 18 analytics/security/cache/counting tests
and 2 release-evidence consistency tests. The latter compare current labels,
source-tag model metrics, software-test counts, metadata and historical wording.
All seven changed generated assets match their source; the allowlisted build,
Python syntax/module budget, frozen benchmark hashes and preserved user fixture
passed. Website/source evidence commits after the immutable tag do not change
application/launcher Python or the packaged installers.
