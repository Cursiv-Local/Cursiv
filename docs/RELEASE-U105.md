# Cursiv v3.14-U105 — fixes from an outside review

Four fixes an outside review asked for. [Complete verification](U105-RELEASE-VERIFICATION.md).

**A drive's signing key can be protected with a passphrase**
- On a Cursiv drive, the key that signs a notebook's shares and exports is stored where anyone holding the
  drive can read it. In the Field Notebook, Signing key… now protects it with a passphrase. It's the same
  key, so main computers that already know it keep accepting its shares.
- After each start the key is locked until the passphrase is entered. Entries still save; shares and
  exports wait. A locked key is never quietly replaced by a new one.
- Making a drive for a named person now says that its key is readable until protected.

**Imports that are complete, or nothing**
- A new strict import (Import from team… > every photo required, or `field log import --strict <folder>`)
  refuses a scientist's whole notebook if any photo is missing or doesn't match its fingerprint, and copies
  nothing from it. The usual import still keeps the entries and names missing photos, for recovering a
  damaged drive.

**Safer downloads**
- The voice model (Vosk) is checked against its published-file checksum before it's used.
- Downloaded zips (the voice model and the Ollama engine) are unpacked with limits: no file names that leave
  the folder, no links, caps on file count and size counted while unpacking, and all or nothing.

**Release documents checked on every change**
- A test now catches release notes, verification documents, the README and the website's signed manifests
  falling out of step.

**Known limits.** The Field Station preview still hasn't run on a Raspberry Pi. Mac packages are built and
self-tested in CI but have never been tested on a real Mac.

The existing independent owner identity authenticates the final package bytes; this is separate from
Windows-trusted Authenticode and Apple notarization.
