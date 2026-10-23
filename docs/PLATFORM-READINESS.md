# Packaging and platform readiness

U87 is published as latest. Source/package checks and 34 anonymous public
release/site checks passed; [U87 verification](U87-RELEASE-VERIFICATION.md) records
installer hashes and the live website version. [U86 verification](U86-RELEASE-VERIFICATION.md)
retains the previous release evidence.
The previous U85 tagged packages, hosted source checks and anonymous public-download
hashes remain recorded in [U85 verification](U85-RELEASE-VERIFICATION.md).
[U84 verification](U84-RELEASE-VERIFICATION.md) and
[U82 verification](U82-RELEASE-VERIFICATION.md) retain historical evidence.
Automated package checks and remaining physical/signing gates are separate.

Owner update, 2026-10-22: basic physical USB operation works; USB memory
persistence/restart/second-PC retrieval remain unverified. A second clean PC is
available to the owner. [Focused checklist](USB-PERSISTENCE-CHECK.md).
Windows signing is deferred until next month at the owner's request; approval
is hoped for, not confirmed. The current-user store has no valid code-signing
certificate with a private key. Current public packages remain unsigned.

| Platform / gate | Current evidence | Remaining action |
|---|---|---|
| Windows build | U87 hosted source CI and frozen full-launcher self-test passed; identical installer aliases/checksums are recorded in the release verification. | Clean-machine install/upgrade and portable persistence checks remain unverified. |
| Windows Authenticode | U87 reports NotSigned. The website retains its unsigned warning and SignPath support note. | Owner must obtain/configure signing access. No signed installer was created or released by this task. |
| macOS Apple Silicon | U87 hosted source/package tests, frozen self-test, four inspected screenshots and DMG checksum/digest checks succeeded. Existing API keys use the login Keychain. | Independent clean-machine installation and minimum-OS compatibility checks remain open. |
| macOS signing | Build spec currently sets `codesign_identity=None`; public guidance says unsigned. | Developer ID, hardened-runtime signing, notarization and stapling must be configured/tested. |
| USB kit | Automated portable/copy/retrieval/integrity regressions; owner reports basic physical operation works. | Memory saves, restart and second-PC retrieval are unverified. Complete the focused persistence and full field-kit checklists; record actual devices/times/failures. |
| Linux | No Linux release artifact or Linux CI/package path. | Explicitly unsupported for packaged distribution for now; source use is experimental and not a compatibility promise. |

The Linux decision reflects missing validation for credential storage, engine
startup, desktop integration and packaging on Linux; the project prioritizes the
existing Windows and early Mac paths until those checks exist.

## Windows signing gate

Use an organization-controlled signing certificate/service (including SignPath if
approved). Sign application executables and the final installer according to that
service's process. Verify Authenticode trust, publisher identity and timestamp on
the exact output bytes. Only then generate the public checksums and stable alias.
Re-download the published installer and verify both signature and checksum.

Microsoft documents SHA-256 file/timestamp algorithms and signature verification
in [SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool).
This repository does not contain signing credentials. Do not alter the website or
README's unsigned warning until a signed public artifact has been verified.

## Mac signing/notarization plan

1. Obtain the owner's Apple Developer ID Application identity and provision it in
   a temporary build keychain through protected CI secrets. Keep API-key storage
   in the user's login Keychain; it is unrelated to developer signing identities.
2. Configure PyInstaller signing and hardened-runtime entitlements for the actual
   bundle and nested binaries. Validate the signature on a disposable build.
3. Submit the signed distribution with Apple's supported notary tooling; wait for
   acceptance, inspect any failure log, staple and validate the resulting ticket.
4. Test the downloaded, quarantined artifact on a clean Apple Silicon Mac. Test
   install, login, Ollama setup, offline use, memory/notebook persistence, update
   replacement and Keychain round-trip/denial. CI self-test is not this manual test.

See Apple's [Developer ID](https://developer.apple.com/developer-id/) and
[notarization documentation](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
Do not describe this staged plan as completed signing/notarization.

## Build reliability changes in this branch

The tagged Windows builder now isolates inherited DLL/plugin search paths, requires
the frozen app's self-test before staging an installer, and produces identical
versioned/latest files with matching checksums. The U82 DLL collision motivated
this guard. Helper tests use disposable mock artifacts. U84 additionally passed actual tagged
Windows/Mac builds and full-window frozen checks; both unsigned public packages
were downloaded and hashed. Exact Windows dependency versions are attached to
the release. The earlier U83 candidate was rejected after its screenshot failure;
its narrower self-test was expanded before U84 publication.

## Physical kit checklist

Use [FIELD-KIT-TEST.md](FIELD-KIT-TEST.md) on two never-installed Windows machines.
Record release/tag, hardware, drive filesystem, cold start, three response times,
cross-machine notebook read/verification, battery duration and failure recovery.
No result is entered until a person has actually completed the step.
