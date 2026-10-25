# Cursiv threat model

## Assets and trust boundaries

Private assets include conversations, selected facts, archived/corrected facts,
documents, field observations/photos, workspace files, login hashes, saved API
keys and the notebook signing key. The model's output and documents it reads are
untrusted input. Native backends establish completed operations through receipts.

| Threat | Current protection | Residual risk |
|---|---|---|
| Someone using the keyboard | Local login, account-specific password recovery, owner controls. | Login is not encryption and does not stop an OS administrator. |
| Someone copying local files | Windows DPAPI / macOS Keychain for saved API keys where available. Since U97, conversations/memories and covered derived stores/backups are always passphrase-encrypted on a computer. | A Cursiv USB drive stays readable by design (use drive encryption). Since U98 the field notebook (entries, photos, team logs) is encrypted too. Documents, workspace files, logs and explicit exports/training data remain readable. Legacy/fallback plaintext keys can exist. |
| A stolen private USB copy | Private content is excluded by default when making a fresh kit; explicit inclusion is warned about. | Portable keys are deliberately readable across computers. A private drive exposes copied keys, login hashes and personal data. Revoke copied cloud keys after loss. |
| Model-directed file access | Explicit workspace, turn limits, sensitive-name/content checks, traversal/link/hard-link checks, confirmed replacement and verified writes. | These are application checks, not OS isolation from other programs or a local attacker racing filesystem changes. |
| Changing login/key/security files through native file tools | Shared backend denies private data/credential paths and guardian code, even with confirmation. Provider adapters cannot grant an exception. | Legitimate login/setup/settings flows necessarily write their own stores. Since U98, plugins (and Forge's test runs) run in their own process with a cleaned environment and an audit hook refusing network, other programs, native code and files outside their data folder; it is not an OS sandbox (same Windows user). External helpers are not sandboxed by the file-tool guard. |
| Network use in offline mode | Existing network gate/backstop; local Ollama remains available over loopback. | It does not turn off Windows networking, audit unrelated software or establish that downloaded model weights are trustworthy. Explicit online use sends data to selected providers. |
| Altering a notebook | Existing append-only chain verification and signed export checks. | A chain is tamper evidence, not confidentiality or proof that an observation was true. Losing/compromising signing keys affects trust. |

## Portable key storage

`core/keystore.py` intentionally disables account-bound DPAPI/Keychain storage in
portable mode. A private kit needs readable keys to run on another computer;
account-encrypted keys from an installed copy cannot simply be moved and expected
to work there. A fresh kit omits personal records and credentials. Use a separate
field identity/key budget if online access is needed. OS/filesystem encryption
can protect a lost powered-off drive, but unlocked data is accessible to the host.

The same-account attacker, malware, a compromised administrator and a malicious
installed Python plugin remain outside Cursiv's confidentiality guarantees.

## Optional conversation/memory encryption

The current source implements opt-in encryption; no real owner records were
migrated during development. [Coverage, migration and recovery](ENCRYPTION-MIGRATION-PLAN.md)
are explicit. A separate passphrase derives a Fernet key with scrypt. Random salts
and authenticated, path-bound envelopes protect covered bytes against disclosure
or unnoticed modification when copied without the passphrase. Filenames, lengths,
timestamps and the existence of a vault are visible. Envelopes do not prevent
deletion or replay of an older valid file. Notebook integrity remains a separate
append-only SHA-256/signature pathway; since U98 the notebook is also encrypted.

Startup holds an OS data lease and unlocks before loading chat stores. Migration
requires the same lease, backs up exact original bytes in encrypted recovery files,
verifies replacements and leaves interrupted roots unavailable until resumed.
Wrong keys/authentication failures never permit a plaintext fallback or empty-store
overwrite. Passphrases are entered through password fields, never model prompts,
command arguments, environment variables or saved settings. Login reset does not
reset the encryption passphrase; there is no lost-passphrase recovery.

This protects an offline copy of covered files, including a lost portable copy.
It does not protect an unlocked process from malware, an administrator, plugins,
memory dumps, swap/hibernation, screen capture or intentional export. It cannot
erase plaintext disk remnants, previous external backups or OneDrive history.
Use OS/full-drive encryption as a complementary control. No Windows trust-store,
release signing key, provider order or network policy changes are involved.

See [PRIVACY.md](../PRIVACY.md), [security tests and findings](MAINTENANCE-HARDENING.md),
and [public claim evidence](CLAIM-EVIDENCE.md).
