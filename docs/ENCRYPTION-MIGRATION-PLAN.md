# Optional conversation and memory encryption

**Status:** included from U90, off by default; not included in U89. Development used disposable records. The owner's actual data was not migrated.
This replaces the earlier design-only plan, following explicit owner authorization.

## Enable, unlock and keep a recovery copy

1. Close every Cursiv process, including the tray copy. Back up your existing data
   to a drive you control. That pre-existing backup is plaintext unless you protect it.
2. From source run `python launcher/main.py --encrypt-data`. For a build of this
   source run `Cursiv.exe --encrypt-data`; on Mac use the executable inside
   `Cursiv.app/Contents/MacOS/`. Read the scope notice, then set and confirm a
   **separate encryption passphrase of at least 16 characters**. Do not type it
   into a chat, shell argument, environment variable or issue report.
3. Migration obtains an OS-held lease for all active data roots. The normal desktop
   holds the same lease. It inventories covered records, refuses links/hard links,
   and makes encrypted, authenticated exact-byte recovery copies before replacing
   any original. Normal readers/writers cannot use a migrating or locked root.
4. After success, open Cursiv normally and enter that passphrase at startup. The
   existing login remains separate. Canceling unlock quits before chat/background
   storage loads. A wrong passphrase leaves all records intact.
5. Back up the entire data roots, including `data-vault.json` and `.vault-recovery/`,
   to a separate drive. Keep the passphrase separately. Private USB kits copy the
   ciphertext and metadata; a fresh kit still excludes private data. Root-relative
   path bindings permit drive-letter changes. Do not move individual ciphertext
   records to different relative paths.

If interrupted, keep every file and rerun `--encrypt-data` using the same passphrase.
The authenticated recovery manifest distinguishes unchanged originals and already
converted files; changed files are refused. Never delete the vault marker to
"turn it off". There is intentionally no in-app switch that silently decrypts
all records, password reset bypass, or automatic lost-passphrase recovery.
To recover originals, an experienced operator can authenticate the marker with
`vault.authenticate`, decrypt `.vault-recovery/manifest.enc` with `vault.unpack`,
and decrypt the listed recovery files into a separate chosen directory. Their
SHA-256 hashes must match the manifest. Do not overwrite a working vault during
recovery. These originals represent the activation-time snapshot, not later edits.

## Exact coverage

Each active app-data, user-data and (when packaged) program-data root gets its own
salt and marker, using the same chosen passphrase. The plaintext payload format
is unchanged inside the encrypted envelope.

The passphrase protects installation data across local profiles; it does not
create a separate cryptographic identity for each login. Someone with that
passphrase and filesystem access can decrypt all covered profiles.

| Covered | Existing producer/read boundary |
|---|---|
| Saved conversations, titles, rendered HTML, pending legacy temporary copies | `launcher/conversations.py` |
| Semantic facts, superseded/removed/unreadable records, memory settings, embeddings, migration backups/checksums | `memory/semantic.py` |
| Session logs and temporal memory | `memory/session_log.py`, `core/memory.py` |
| Saved notes/strands and territory labels | `core/strand_store.py`, `launcher/saved_notes.py` |
| Project/style notes, curiosity journal, presence preferences and their verified backups | `core/state_store.py` |
| Coding profile/lessons and council memory | `coding/brain.py`, `council/council_memory.py` |
| Legacy rated-exchange store and recognized backup/temporary filenames | `core/vault.py` coverage classifier |

The classifier covers those folders/names, not arbitrary user-named files. Covered
plaintext records are limited to 64 MB each; oversized stores must be archived
before activation. Authenticated-encryption operations hold a file in memory;
appends to encrypted JSONL rewrite that file atomically. This is a deliberate
small implementation, unsuitable for unbounded logs. Failed replacements retain
the old ciphertext; temporary writes contain ciphertext only. An OS lease prevents
simultaneous migrations/desktops, but does not sandbox arbitrary external writers.

## Outside coverage

Notebook observations/photos/exports, imported documents, workspace files, explicit
training saves and trained adapters, explicit exported packs/Obsidian notes, logs,
login/settings, plugin/agent definitions, older external copies and cloud copies
remain under their existing rules. Saving a response to training or exporting it
can create plaintext even when the original conversation is encrypted. Previously
uploaded or deleted plaintext is not recalled or securely erased. OneDrive history,
backups, swap, crash dumps and hibernation need OS/drive and backup controls.
API keys keep their existing DPAPI/Keychain/portable rules. Notebook chain/signing
formats and the independent release-signing private key are unchanged.

## Cryptography and limits

Uses the already required `cryptography` package's Fernet authenticated encryption,
with scrypt N=131072, r=8, p=1, a random 16-byte salt and a 32-byte derived key.
See the [library's password-based encryption guidance](https://cryptography.io/en/latest/fernet/#using-passwords-with-fernet).
KDF parameters/version are fixed and validated; metadata cannot request arbitrary
KDF work. Ciphertext authenticates the root-relative filename and original bytes.
No passphrase/derived key is written to disk. The process retains keys and decrypted
caches until exit; Python cannot promise secure memory erasure. File metadata is
visible, and valid old records can be replayed. A lost passphrase is unrecoverable.
This is application-level confidentiality for copied covered files, not whole-device
encryption or protection against a hostile unlocked host.

## Evidence

`tests/test_data_encryption.py` checks default plaintext compatibility, exact-byte
migration (including Unicode/malformed lines), encrypted recovery snapshots,
wrong/missing keys, tampering, record swapping, failed migration/resume, state
backups, actual memory/conversation reads and writes, subprocess restart/relocation,
exclusive leases and hard-link denial. Existing offline, restricted-turn, notebook,
portable and storage regression tests remain the compatibility checks. Test results
for this development change are recorded in `CHANGELOG.md`; historical release
results remain labeled by their actual release.
