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

Windows source checks passed **1,636 tests / 1 skip**; Mac passed **1,622 / 15**.
Both tagged frozen applications passed their self-tests. The release dependency
audit and static-security gate passed. Final bytes are authenticated by the
existing owner-signed manifest. [Verification and hashes](U90-RELEASE-VERIFICATION.md).

No new local-model truth benchmark score is claimed. Encryption is optional and
was exercised only with disposable records; the owner's data was not migrated.
Physical USB encrypted-memory persistence and clean-machine installation remain
manual checks; the tagged Mac build passed automated checks.

Release manifests use the existing separately held owner signing key. These are
not Windows-trusted Authenticode signatures or Apple notarization; operating-system
publisher warnings remain. [Signing and recovery](OWNER-RELEASE-SIGNING.md).
[Encryption scope and recovery](ENCRYPTION-MIGRATION-PLAN.md).

## Installer SHA-256

Windows: `d2feae8f3fa18e1195e0555872dba92c1dd907e67023a20a62266c672a7bb4a2`

Mac (Apple Silicon): `6a1bd0baffc929af0ecde9d4a1a1390cc0b83acc956f1b6e8835bcea9a42669a`
