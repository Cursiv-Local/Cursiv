# U83 candidate verification — rejected before publication

U83 remains a draft. Mac run 39856399578 failed while constructing the full
launcher for screenshots: `shell_dialogs.TitleBar` used `theme` without importing
it. The app self-test only built ChatPanel and missed the shell. Two new isolated
regressions reproduced this and a missing `json` import in the extracted notes
command (2 failed in 3.72 s; `%TEMP%/cursiv-maintenance-bogbokox/pytest.log`).
No U83 artifact is published. U84 repairs these defects and expands the self-test;
see [the U84 publication record](U84-RELEASE-VERIFICATION.md). Earlier passed
checks below retain their actual, narrower meaning.


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

## Tagged source and hosted CI

- Immutable tag `v3.14-U83` resolves to
  `167834d601bf4319f8d0eab969b5930ef6b18e27`, pushed to main and the feature branch.
- [Hosted source tests](https://github.com/Cursiv-Local/Cursiv/actions/runs/39856053174)
  succeeded on that commit:
  Windows **1,246 passed, 1 skipped, 113.66 s**;
  macOS **1,236 passed, 11 skipped, 395.60 s**.
  Platform-specific skips are retained, not counted as passes.
- The Windows packaged self-test passed imports, disposable data folders,
  112 offline reference entries, calculations, notebook write/chain/export/
  signature checks, document search and offscreen chat-window construction.
  Ollama availability is reported separately as information, not model accuracy.
- Final Windows packaging uses a disposable environment containing only
  `requirements.txt` dependencies, to avoid including unrelated optional packages
  from the developer's Python environment. No source or public tag is changed
  between packaging attempts. The earlier environment's candidate is not uploaded.
- The [Mac tagged build](https://github.com/Cursiv-Local/Cursiv/actions/runs/39856399578)
  was dispatched against U83 with uploads to the draft release. Completion,
  packaged self-test and exact attached assets must be checked before publication.

## Completed candidate model run

Full unchanged suite 1.5: 153/158 passed, 96.8% overall, 98.1% answerable
accuracy, 1.3% case-marked unsupported claims; 9.7 s/case, 25.6 minutes.
[Raw answers](../bench/results/U83-qwen3_4b-instruct-suite1.5.json) and
[failure review](../bench/FAILURES-U83.md) retain actual errors and likely regex
false positives without editing the frozen scorer or increasing the score.
This is evidence for the rejected candidate, not a U84 model run.
