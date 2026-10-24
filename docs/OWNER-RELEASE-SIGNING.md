# Owner release signatures

Starting with U89, the installed app pins Joshua Winkler / Cursiv's Ed25519
release public key. This key is independent of the notebook's per-device keys.
U88 was an unpublished validation candidate; its tag was preserved rather than moved.

Public-key SHA-256 fingerprint:

`f9e12af95f7e983f1a4521c1bc9a77cb96090635277de24ec1e73341e9b9f5e7`

The only repository key file is public: `cursiv_engine/core/release_public_key.json`.
The private seed is protected with Windows DPAPI for the owner's current Windows
account, at `%LOCALAPPDATA%/CursivReleaseSigning/owner-release-key.dpapi`.
It is outside GitHub and OneDrive and is not installed with Cursiv. Workspace file
tools deny this directory. Do not upload it, put it in CI secrets, or copy it into
an installer. DPAPI protection is not protection against compromise of this
Windows account while it is signed in.

A reviewed signing-tool copy is also installed outside the checkout at
`%LOCALAPPDATA%/CursivReleaseSigning/signer/scripts/owner_release.py`, with its
public-key/verification module and a `trusted-tool-manifest.json` of source hashes
from commit `e9828f605e7da08fdb3b59fe3d3bd198ddf4a177`. Use that copy for owner
operations. Do not replace it merely because GitHub supplies a different script:
running an attacker-modified signing script as the owner could expose the key.
The independent copy verified the final Windows release successfully.

**Where `%LOCALAPPDATA%` actually points.** The key and signer were created from the
Codex desktop app, which Windows runs as a packaged app with its own redirected
folder. On the owner's PC they are under
`%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\CursivReleaseSigning`,
not `%LOCALAPPDATA%\CursivReleaseSigning`. From any other shell, set `LOCALAPPDATA`
to that `...\LocalCache\Local` folder for the signing command only; never copy the
key. U94 was signed this way after the signer's hashes matched its manifest.

## What is authenticated

`owner-release.json` signs the release version, tagged source commit, artifact
names, exact sizes and SHA-256 hashes. `scripts/owner_release.py sign` reads the
local protected private key, signs the canonical payload and independently
verifies every artifact before writing the public manifest.

The updater verifies the manifest using its installed public key before trusting
release metadata, checks the downloaded bytes, and verifies them again immediately
before launching. Missing proof, a different signer, modified metadata, an altered
installer, an incomplete download or a version mismatch prevents execution.
Failed downloads are removed. GitHub can still remove assets or deny availability.

An attacker with GitHub write access cannot create an accepted new manifest
without the independent owner key. This protects clients that already possess
the genuine pinned key. A new user who obtains both a malicious first installer
and its claimed key from a compromised site has a bootstrap-trust problem.
Compare this fingerprint through an independently trusted channel. A matching
hash posted on the same compromised site alone does not establish ownership.
U87 and older updaters do not enforce this new owner proof. Verify the first U89
installer independently; installing the genuine pinned-key app establishes the
check used for subsequent updates.

## Windows signing status

Owner signatures are detached release signatures, not Windows CA-issued
Authenticode signatures. Windows can still show unknown-publisher/SmartScreen
warnings. No Windows trust-store entry was added or self-signed certificate made
trusted. SignPath or a trusted code-signing certificate remains the next step.
The updater also supports independently pinned Authenticode certificate
thumbprints when that is configured; it never adopts a certificate from GitHub
metadata. No real Cursiv Windows certificate was available in either certificate
store when checked, and no SignPath integration was configured.

## Recovery: owner action still required

The key was generated successfully, but **a password-protected recovery backup
has not been created**: only the owner should enter and retain its password.
Until then, loss of this Windows profile could mean loss of release-signing
ability. Existing clients would require a separately authenticated recovery or
manual reinstall; do not silently replace the pinned key.

In a local terminal, choose a removable/offline location outside the repository
and OneDrive, then run:

```powershell
py -3.13 "$env:LOCALAPPDATA\CursivReleaseSigning\signer\scripts\owner_release.py" backup E:\Cursiv-owner-release-recovery.pem
```

The script prompts locally twice, requires at least 16 characters, writes an
encrypted PKCS8 backup, and refuses to overwrite a file. Keep the password
separately. Never paste it into chat or a command line. Replace `E:` with your
actual offline backup drive.

On a replacement Windows account with the genuine source/public-key file:

```powershell
py -3.13 "$env:LOCALAPPDATA\CursivReleaseSigning\signer\scripts\owner_release.py" restore E:\Cursiv-owner-release-recovery.pem
```

Restore verifies the public fingerprint before saving a new DPAPI-protected
copy and refuses to overwrite an existing key. Recovery has automated primitive
coverage, but a physical-drive recovery drill by the owner remains outstanding.

## Repository and release controls

The original U89 audit found `main` unprotected. During the U91 follow-up,
required Actions checks were enabled and independently confirmed: Windows/Mac
workspace gates, Windows/Mac full suites and security, with strict/up-to-date
checks and administrator enforcement. Force pushes and branch deletion are
disabled. Use a PR and passing merged-main checks; the supported release helper
then validates that exact source before creating the tag.

Account passkeys/2FA, collaborator/token review and release-tag protection remain
owner controls; this release does not claim to have configured them. Owner
signing does not prevent malicious source commits; the owner must review the
exact tagged source before signing.
Never place the owner private key in a GitHub Action that a repository attacker
could edit. CI builds Mac artifacts; the owner signs their downloaded final bytes
locally before publication.
