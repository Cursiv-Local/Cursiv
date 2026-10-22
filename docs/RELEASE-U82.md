# Cursiv v3.14-U82

U82 improves how Cursiv describes its current state, respects conversation-only
requests, recalls saved facts and grounds code discussion in actual source.
It includes the earlier U80/U81 memory, notebook, verified-file and chat-rendering
improvements.

## Changes

- Clear "just talk", "don't inspect" and "don't save memories" requests restrict
  that turn's inspection, actions and automatic retention. Read-only requests
  keep source reads available while blocking changes and unknown plugin hooks.
- Direct operational answers use the active session's workspace/file-access
  settings. Persistent saved-fact memory is described separately from automatic
  learning, full conversation recall and training model weights.
- "What do you remember from the past two weeks" (including "passed 2 weeks")
  retrieves dated saved facts with actual IDs, counts and explicit scope.
  Unavailable records are reported as unavailable instead of invented history.
- Source follow-ups reauthorize and reread bounded excerpts. Explicit unsupported
  source quotations and concrete false capability claims receive application
  corrections, including after a model's answer-checking revision.
- Mac test/self-test scratch paths use canonical directories. Failed-write
  regression tests exercise the actual Windows/POSIX file-commit operation.
  Workspace authorization and symlink/junction protections are preserved.
- Installer project links point to cursiv.us and Cursiv-Local/Cursiv.

## Install/update

Use Cursiv-Setup-3.14-U82.exe or its identical Cursiv-Setup-latest.exe copy for
Windows. Compare the downloaded file's SHA-256 with SHA256SUMS.txt.

U82 is higher than U81, so the existing updater can offer it when online update
checks are allowed. Offline mode blocks the GitHub check. This update preserves
existing data formats; no memory/notebook migration is introduced. A compatible
Ollama model is still required for local model answers.

The Mac workflow builds its own platform package and checksum file from this
release tag. Only use a Mac package when it is actually attached to this release;
the Windows executable is not a Mac installer.

## Verification and limits

The implementation's full isolated Windows regression suite passed 1,080 tests
with one macOS Keychain skip before release preparation. Release-version and
platform checks are also run during publication; the GitHub Actions results and
release verification record identify those exact runs.

Provider output is mocked for deterministic action-boundary tests. These checks
do not establish that a live small model never hallucinates. Dated recall searches
active saved facts, not all conversations or event history. Saved dates are not
necessarily event dates. No subjective-awareness, autonomous self-modification or
perfect-recall claim is made.
