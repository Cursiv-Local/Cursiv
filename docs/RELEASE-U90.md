# Cursiv v3.14-U90 — clearer structure and optional private storage encryption

- Renamed the historical engine package to `cursiv_engine` throughout source,
  tests, builds and documentation. Existing data locations and notebook formats stay intact.
- Added opt-in, default-off passphrase encryption for conversations, memories and
  covered derived stores/backups. Unlock happens before chat loads. Explicit
  app-closed migration creates encrypted recovery snapshots and verifies exact bytes.
- Kept workspace documents, notebook observations/photos, logs and explicit exports
  outside this encryption scope. Login is separate; a lost passphrase cannot be reset.
- Consolidated shared command types and isolated personal dialogs. Existing personal
  records remain intact; their entry points respect Show personal features.
- Shortened README, updated contributor and architecture guidance, and moved technical
  details into TECH.md. Removed the unavailable public website download counter.
- Preserved the homepage's Help test Cursiv button and `/testers` page.

## Evidence and limits

The pre-release Windows source suite passed 1,636 tests with one platform skip.
The development frozen bundle passed its full self-test. Final tagged build,
CI and publication checks will be recorded here when complete.

No new local-model truth benchmark score is claimed. Encryption is optional and
was exercised only with disposable records; the owner's data was not migrated.
Physical USB encrypted-memory persistence and clean-machine installation remain
manual checks. Mac behavior requires the tagged Mac workflow to pass.

Release manifests use the existing separately held owner signing key. These are
not Windows-trusted Authenticode signatures or Apple notarization; operating-system
publisher warnings remain. [Signing and recovery](OWNER-RELEASE-SIGNING.md).
[Encryption scope and recovery](ENCRYPTION-MIGRATION-PLAN.md).
