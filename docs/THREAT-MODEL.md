# Cursiv threat model

## Assets and trust boundaries

Private assets include conversations, selected facts, archived/corrected facts,
documents, field observations/photos, workspace files, login hashes, saved API
keys and the notebook signing key. The model's output and documents it reads are
untrusted input. Native backends establish completed operations through receipts.

| Threat | Current protection | Residual risk |
|---|---|---|
| Someone using the keyboard | Local login, account-specific password recovery, owner controls. | Login is not encryption and does not stop an OS administrator. |
| Someone copying local files | Windows DPAPI / macOS Keychain for saved API keys where available. | Conversations, memories, archives and other personal stores remain readable. Legacy/fallback plaintext keys can exist. |
| A stolen private USB copy | Private content is excluded by default when making a fresh kit; explicit inclusion is warned about. | Portable keys are deliberately readable across computers. A private drive exposes copied keys, login hashes and personal data. Revoke copied cloud keys after loss. |
| Model-directed file access | Explicit workspace, turn limits, sensitive-name/content checks, traversal/link/hard-link checks, confirmed replacement and verified writes. | These are application checks, not OS isolation from other programs or a local attacker racing filesystem changes. |
| Changing login/key/security files through native file tools | Shared backend denies private data/credential paths and guardian code, even with confirmation. Provider adapters cannot grant an exception. | Legitimate login/setup/settings flows necessarily write their own stores. Trusted Python plugins/external helpers are not sandboxed by the file-tool guard. |
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

## Encryption status

The owner selected a separately documented encryption migration on 2026-10-22.
This work does not encrypt, migrate, rewrite or back up real personal stores.
The [migration plan](ENCRYPTION-MIGRATION-PLAN.md) covers copies/derived data and
unlock/recovery requirements before any such change can be enabled.

See [PRIVACY.md](../PRIVACY.md), [security tests and findings](MAINTENANCE-HARDENING.md),
and [public claim evidence](CLAIM-EVIDENCE.md).
