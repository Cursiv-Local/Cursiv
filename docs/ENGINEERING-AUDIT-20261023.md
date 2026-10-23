# Independent validation of the supplied engineering audit

Review baseline: `32e955fc7bf29b4a45dd96e563da34459785d3f0` (published U87).
Review date: October 23, 2026. U89 work includes the authorized earlier uncommitted
live-transcript repairs. This validates the supplied findings and relevant paths;
it is not a claim that every repository line received a separate manual audit.

## A. Verified findings

| Severity | Finding, cause and impact | Reproduction / affected path |
| --- | --- | --- |
| High | Update download completeness did not authenticate publisher identity; `_run_installer_and_quit` directly launched the downloaded executable. A compromised release could supply different installer bytes. | `launcher/cursiv_launcher.py`, `UpdateChecker._run`, `UpdateDialog._do_download`, `_run_installer_and_quit`. Now delegates to `launcher/update_security.py:39` and `:81`; owner manifest validation in `cursiv_engine/core/release_identity.py:23`. |
| Medium | Notebook keyword classification could consume an explicit source-file read; file parsing could include task clauses in a path; local search could reach web routing. Writes lacked the requested natural forms. | `cursiv_engine/core/notebook_tools.py:136`, `core/file_access.py:401`, `chat/web_search.py:51`, plus the ten exact workspace transcript prompts in `tests/test_workspace_routing.py`. |
| Medium | Signed export verification checked named paths but did not reject every unexpected symlink/object in the discovered export tree. | `cursiv_engine/core/fieldlog.py:605`, `verify_export`; new `core/export_paths.py`, `inventory`. Valid export + an unlisted symlink now fails before following it. |
| Medium | Runtime version ranges and a build from an arbitrary installed environment did not define a reproducible release dependency set. Tagged-source isolation and artifact hashes already existed. | `requirements.txt`, `scripts/build_release.py:main`; new hash-locked release input and provenance check. |
| Medium | A background model-list worker could catch a deleted Qt signal error, then emit on the same deleted signal again. | `launcher/chat_controls.py`, `_load_models`; reproduced by a controlled deleted-signal adapter and observed as a test-thread warning. |
| Test reliability | OS sampling could miss a quickly rejected external TCP control socket, making the positive-control test flaky. | `tests/test_offline_process.py:107`. Control now independently proves the external audit event and a held OS-observable socket; the actual offline no-external-socket assertions remain unchanged. |
| Not a security hash defect | Static analysis flagged two SHA-1 cache/change-detection digests, not signatures or password protection. | `memory/semantic.py:embed`, `launcher/phone_sync.py`. Explicit `usedforsecurity=False` preserves cache data and clarifies intent. |

The supplied “66 test files / PyQt6 unavailable” observation describes a different
review environment, not evidence of failing current Cursiv tests. Actual runs are
recorded below. No supplied numerical engineering score was treated as a measurement.

## B. Changes and rationale

- `core/file_requests.py`: pure natural intent/path/content extraction before
  filesystem resolution. Quoted filenames and explicit ` :: ` payloads remain data.
- `core/workspace_search.py`: existing `search_files` backend gains bounded
  local content/import/line-count modes. Every traversed entry passes the existing
  authorization/link checks; credential-containing files are skipped. Results
  have actual file paths/line numbers, partial-result notices and clear no-match text.
- `core/file_access.py`: natural command dispatch, newline-aware confirmed append,
  real read-back for “you just wrote” claims, safe usage examples and source-excerpt
  outlines. No shell, model continuation or generalized filesystem permissions.
- `core/notebook_tools.py`, `chat/completion.py`, `chat/conversation.py`,
  `chat/web_search.py`, `core/action_gate.py`: explicit file precedence and local
  search handling retain native receipts, restrictions and offline web blocking.
- `core/command_sequence.py`, `memory/intents.py`, `launcher/command_dispatch.py`:
  mixed commands do not become one saved fact; preserve supported memory-only
  sequences. Execute first safe file step and identify unexecuted remaining steps.
  Explicit version + offline-on handles both native actions.
- `core/release_identity.py`, public `release_public_key.json`,
  `launcher/update_security.py`, `launcher/cursiv_launcher.py`: owner authentication,
  strict version/asset selection, bounded download, transition checks, cleanup and
  revalidation before execution. Optional independent Authenticode pinning remains
  available for a real Windows certificate. No release checksum is treated as an
  independent identity proof.
- `scripts/owner_release.py`: DPAPI-protected local owner signing, public manifest
  verification, password-encrypted recovery backup and fingerprint-checked restore.
  No private key or recovery password enters GitHub/OneDrive/website/installer.
- `core/export_paths.py`, `core/fieldlog.py`: inventory containment/type checks for
  signing and verification; no notebook format or integrity migration.
- `requirements-release.in`, `requirements-release.lock`, `scripts/release_provenance.py`,
  `scripts/build_release.py`, `.github/workflows/tests.yml`, `mac-build.yml`:
  hashed release environments, dependency-version checks, provenance and security
  jobs. Mac automatic upload cannot overwrite already owner-signed assets.
- `launcher/chat_controls.py`: ignore late delivery to a destroyed window.
- `memory/semantic.py`, `launcher/phone_sync.py`: identify non-security cache hashes.
- Version files (`core/selfknow.py`, launcher and Inno Setup), release docs,
  changelog, README, handoff and website signing/test evidence record U89 accurately.
  Earlier live-transcript changes and their exact files are separately listed in
  `docs/LIVE-TRANSCRIPT-GAPS.md`.

## C. Test evidence

All local application tests use isolated copied sources, temporary HOME/app data,
Qt offscreen and no automatic engine startup. Personal `test_internals/` is excluded.

- Pre-repair baseline: 232 focused tests passed, 17.56 s.
- Initial new routing run: 250 passed, 2 failed. Preserved memory-only multi-action
  sequences were incorrectly stopped by the new compound gate; that was repaired.
- Engineering-focused run: 166 passed, 35.99 s.
- First broad runs exposed 9 parser compatibility failures; the locked run also
  exposed the OS positive-control timing issue. Neither failure was excluded.
- Corrected regression subset: 141 passed, 21.61 s, with one observed late Qt worker
  warning. The actual worker error received a narrow production fix and regression.
- Final complete source, hosted CI, package and website counts are recorded in
  the U89 verification report after each run finishes.
- Final U89 local suite: **1,594 passed, 1 skipped**, 175.16 s. Hosted Windows:
  **1,594/1**, 155.74 s; hosted Mac: **1,580/15**, 380.97 s. Both packaged
  self-tests passed, including owner-key presence and notebook signed exports;
  all **21 website tests passed**. The tag/source/provenance and final hashes are
  in `docs/U89-RELEASE-VERIFICATION.md`.
- Locked dependency audit: **no known vulnerabilities found**, October 23, 2026,
  `pip-audit 2.10.1 -r requirements-release.lock --no-deps --disable-pip`.
- Bandit 1.9.4 full scan initially reported 272 findings: two high/high-confidence
  cache-hash classifications, clarified above. The high/high gate now passes with
  zero findings. Lower-severity findings have not all received manual disposition;
  a clean high-severity gate is not a claim of a vulnerability-free application.

Layered checks can be reproduced separately:

```text
python -m pytest tests/test_owner_release.py tests/test_update_security.py -q
python -m pytest tests/test_workspace_routing.py tests/test_export_paths.py tests/test_memory_intents.py -q
python -m pytest tests/test_chat_rendering.py tests/test_chat_feedback.py -q
python -m pytest tests/test_network_isolation_process.py tests/test_offline_process.py tests/test_netgate.py -q
python -m pytest tests -q
node --test cloudflare/tests/*.test.mjs
```

The native routes are exercised with controlled local/cloud provider selection;
no live paid provider request or new full truth benchmark was made. Actual files,
memory restart, notebook chains and cryptographic failures use backend evidence.

The U88 candidate was not published after Mac validation exposed native reverse-DNS/proxy lookup in the new HTTP test fixture. The corrected U89 fixture uses direct loopback TCP and no proxy discovery; no test or network assertion was removed. The candidate tag remains unchanged.

## D. Remaining risks and owner actions

1. Owner signatures are independent release signatures, not Windows CA trust or
   Mac notarization. First-install trust must be established independently; a
   website hash on its own does not establish identity.
2. The owner must create and test an encrypted offline signing-key recovery backup.
   DPAPI is tied to this Windows account. Compromise of the signed-in owner account
   could still expose/use the key. No signing key is available to CI.
3. GitHub reported `main` is not protected. Account MFA/passkeys, collaborators,
   token scope and protected main/release tags require owner review; not changed.
4. Python hooks enforce Cursiv's application-level network boundary. The real
   socket/DNS/HTTP/loopback process harness and existing cloud/background tests do
   not prove OS-wide isolation of every native library, subprocess or external
   Ollama process. No machine firewall policy was installed or altered.
5. Physical second-PC/USB memory persistence, installed upgrade behavior, signing
   recovery and clean-machine installation are not substituted by source tests or
   the frozen self-test. They remain manual checks, as do live model reliability
   questions. A SHA-256 chain is tamper-evident relative to a trusted checkpoint;
   an unknown export key alone does not establish historical authorship.
6. Hash-locked dependencies and tagged clean builds support functional
   reproducibility. They do not claim byte-identical cross-machine installers;
   timestamps/platform tooling differ. Build provenance identifies the actual inputs.

## E. Qualitative readiness assessment

These are judgment scores for the reviewed evidence, not automated measurements
or a new model-accuracy score. Missing real deployment/security validations limit
the assessment; implementing a check does not itself earn a perfect score.

| Area | Score / 100 | Basis |
| --- | ---: | --- |
| Architecture | 80 | Focused native boundaries; remaining large modules and adapter duplication. |
| Functionality | 81 | Broad existing regressions plus exact transcript fixes; model limitations remain. |
| Security | 70 | Independent owner authenticity and export guards; bootstrap/account/CA-trust risks remain. |
| Privacy | 78 | Tested application gates; plaintext local data and native-process boundary remain. |
| Data integrity | 87 | Append-only verification preserved; export paths hardened; recovery drill outstanding. |
| Testing | 82 | Full/targeted/GUI/process tests and artifact self-tests; physical workflows incomplete. |
| Release engineering | 76 | Locked builds/provenance/owner manifests; no Windows CA signing or Mac notarization. |
| Documentation | 88 | Explicit evidence and remaining risks; historical sections intentionally retained. |
| Overall production readiness | 78 | Useful tested field/research software; not yet a fully validated high-assurance product. |

## Complete changed-file inventory

Repository paths relative to the reviewed U87 baseline; generated private keys,
ignored build output and personal test files are excluded.

```text
.github/workflows/mac-build.yml
.github/workflows/tests.yml
CHANGELOG.md
HANDOFF.md
README.md
cloudflare/tests/download-analytics.test.mjs
cloudflare/tests/release-evidence.test.mjs
cursiv_engine/chat/completion.py
cursiv_engine/chat/conversation.py
cursiv_engine/chat/web_search.py
cursiv_engine/core/action_gate.py
cursiv_engine/core/answer_evidence.py
cursiv_engine/core/calc.py
cursiv_engine/core/command_sequence.py
cursiv_engine/core/export_paths.py
cursiv_engine/core/fieldlog.py
cursiv_engine/core/fieldmath.py
cursiv_engine/core/file_access.py
cursiv_engine/core/file_requests.py
cursiv_engine/core/native_answers.py
cursiv_engine/core/notebook_tools.py
cursiv_engine/core/phone_help.py
cursiv_engine/core/presence.py
cursiv_engine/core/release_identity.py
cursiv_engine/core/release_public_key.json
cursiv_engine/core/selfknow.py
cursiv_engine/core/workspace_search.py
cursiv_engine/memory/intents.py
cursiv_engine/memory/semantic.py
docs/ENGINEERING-AUDIT-20261023.md
docs/LIVE-TRANSCRIPT-GAPS.md
docs/OWNER-RELEASE-SIGNING.md
docs/RELEASE-U88.md
docs/RELEASE-U89.md
docs/U89-RELEASE-VERIFICATION.md
installer/BEFORE-INSTALL.txt
installer/cursiv_setup.iss
launcher/chat_controls.py
launcher/chat_feedback.py
launcher/chat_panel.py
launcher/command_dispatch.py
launcher/cursiv_launcher.py
launcher/phone_help.py
launcher/phone_sync.py
launcher/selftest.py
launcher/update_security.py
requirements-release.in
requirements-release.lock
scripts/build_release.py
scripts/owner_release.py
scripts/release_provenance.py
tests/test_export_paths.py
tests/test_model_lookup_shutdown.py
tests/test_network_isolation_process.py
tests/test_offline_process.py
tests/test_owner_release.py
tests/test_u86_remaining_gaps.py
tests/test_update_security.py
tests/test_workspace_routing.py
website/ai-reliability-testing.html
website/assets/cursiv-owner-release-U89.json
website/assets/cursiv-owner-release-key.json
website/index.html
website/start.html
website/vision.html
```
