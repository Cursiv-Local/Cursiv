# U83 release verification

## Release preparation

The owner explicitly authorized committing, pushing, a higher installer version,
release publication and website deployment after the trust-boundary work. This
supersedes earlier no-publication instructions in the historical reports.
Published U82 was checked through GitHub's public API before choosing U83.

Source baseline: main `8831241da3ffdaf14d181d3a0c2b4587b6a945e8`.
The implementation was developed on `codex/maintainability-hardening`.
Personal `test_internals/` data is excluded from source commits, tests, builds
and website uploads. No personal memory/notebook migration or app installation
on the owner's machine is part of publication.

The final versioned test run, tag, hosted CI, frozen-app report, exact artifact
hashes, public download verification and Cloudflare deployment are recorded below
as each succeeds. Preparation alone is not evidence of a published release.

## Evidence before version preparation

- Full isolated Windows source suite: **1,246 passed, 1 skipped, 299.62 s**.
  Log: `%TEMP%/cursiv-maintenance-s8vnolr0/pytest.log`.
  The skip requires a real Mac Keychain. Source fingerprint before the version
  bump: `15985868d5d3bcb9fbff8aad9955b5f46f05376a094573d9d016ed137683e278`.
- Deterministic 16-case replay: 8/8 seeded failures detected, zero alarms on 8
  controls. U82 baseline: 7/8 detected and 2/8 false alarms. This is a bounded
  pure-code check, separate from the Truth Benchmark.
- Earlier six-case live subsets and controlled rendering measurements remain
  dated source-snapshot evidence. They are not relabeled as U83 runs.

## Remaining independent checks

Authenticode, Apple signing/notarization, a clean installed Windows session,
two physical Windows PCs with a portable drive, physical phones and independent
field use are not established by CI or the packaged self-test. Readable USB key
exports and unencrypted local conversation/memory storage remain documented.

## Final U83 source checks

- Isolated Windows suite: **1,246 passed, 1 skipped in 213.72 s**.
  Snapshot/log: `%TEMP%/cursiv-maintenance-qkk67b_u/pytest.log`.
  All 254 application, launcher, test and script Python files still matched the
  test snapshot before committing. The skip requires a real Mac Keychain.
- U83 application/launcher normalized Python fingerprint:
  `1fbef0a82faea512361183b9d964f0356a1bf67e26b137905498ab6926672bbf`.
- Website analytics suite: **18 passed**, including alias exclusion, cache and
  failure handling, authentication and build/SEO checks.
- Python syntax, 1,200-line production-module budget, `git diff --check`, frozen
  Truth Benchmark hashes and the preserved personal test fixture passed.
- Three version fields and the Inno output name are `3.14-U83`. The source
  commit does not include compiled files, secrets or `test_internals/`.

The full 158-case live benchmark is running against a disposable copy with this
same Python fingerprint and the installed `qwen3:4b-instruct` model. Its result
will be recorded after completion; the run does not alter frozen cases/scoring.
