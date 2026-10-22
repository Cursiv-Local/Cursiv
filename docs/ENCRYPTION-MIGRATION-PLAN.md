# Optional encryption: separate migration plan

**Status:** design only. The owner explicitly chose to document this separately
on 2026-10-22. Existing data formats and personal files are unchanged.

## Why a primary-file switch would be unsafe

Conversations are not a single read/write pair. `launcher/conversations.py` has
ordered background saves, title updates, listing, rename and direct JSON reads.
Memory facts are JSONL; `memory/semantic.py` also preserves unreadable lines,
removed records, correction history, migration backups and embeddings. Session,
project, coding, saved-note and curiosity stores can retain related text. Exported
files and backups can contain copies that app-level encryption cannot revoke.

Changing only `_write_facts()` and conversation Save would leave readable copies,
miss existing read paths, and risk treating a locked file as empty/corrupt data.
The existing conversation loader catches read failures as `None`; a locked-store
exception must never fall through that behavior and overwrite an existing record.

## Proposed smallest safe feature

1. Complete an inventory of primary stores, all backup/archive/quarantine paths,
   derived stores, exports, portable copying and every reader/writer. Define exact
   coverage publicly; use synthetic records and inspect the resulting files.
2. Use a versioned authenticated-encryption envelope around the existing JSON/
   JSONL payload, retaining IDs, ordering and original plaintext schemas after
   decryption. A portable passphrase vault needs a reviewed password KDF, random
   salts/nonces and a session unlock key. Never silently return plaintext after
   crypto failure. Account-bound DPAPI is a separate installed-Windows option.
3. Add distinct **locked**, **missing**, **corrupt**, **unavailable drive** and
   **permission denied** results throughout readers. Disabled/locked encryption
   must prevent retention/autosave and explain why; never create an empty view.
4. Provide explicit opt-in, passphrase confirmation, unlock, lock and recovery
   guidance. Do not promise recovery of a lost passphrase. Login credentials and
   vault passphrases must have clearly distinct purposes.
5. Pause/drain background writers before migration. Back up bytes and record a
   manifest/hash before changing stores. Verify every encrypted copy by decrypting
   and comparing exact original bytes. Atomically commit a migration manifest.
   Resume safely after a crash; retain the original until verification succeeds.
6. Explain that retained plaintext backups remain sensitive. Require a separate
   explicit choice for their disposition; do not silently delete existing data.
   Secure erasure on SSDs is not guaranteed by ordinary file deletion.
7. Prevent derived stores from writing plaintext while encryption is enabled.
   Define export and portable-copy behavior before enabling the UI switch.

## Required acceptance tests

- Fresh opt-in, existing-data opt-in, restart/unlock, lock during idle and during
  queued autosave, wrong passphrase and unavailable account-bound key.
- Exact-byte recovery of existing JSON/JSONL including Unicode and malformed lines;
  all prior IDs and notebook integrity tests remain valid.
- Duplicate/correction history, missing store versus locked store, failed reads,
  partial writes, disk full, abrupt shutdown and resumable migration/rollback.
- Portable drive relocation, disconnect/reconnect, private/fresh kit copying,
  backups/quarantine/embeddings and explicit export confidentiality.
- Search synthetic markers across all covered primary and derived files;
  report every intentional plaintext exception.

Do not advertise encrypted conversations or memories until the complete pathway,
recovery behavior and independently inspected on-disk results pass these tests.
