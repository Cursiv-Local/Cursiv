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
