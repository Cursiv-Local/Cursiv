# Cursiv v3.14-U95 — bring USB data back to a computer

Released with verified Windows and early Apple Silicon Mac packages. Hosted
checks passed Windows **1,819 / 1 skip** and Mac **1,804 / 16 skips**. Both
tagged frozen apps passed. [Complete verification](U95-RELEASE-VERIFICATION.md).

- **Bring drive data here** in "Make a Cursiv USB…" brings work done on a Cursiv
  USB (conversations, notebook entries, memories, settings) into Cursiv on this
  computer. Only files that are new or newer on the drive come over; anything
  newer on the computer is kept.
- Files are staged and verified, then applied at the next start before any data
  is read. Replaced files are backed up and a report lists every decision.
- Saved keys are encrypted for this Windows account. Accounts, passwords, logs and
  device identity stay with each computer. Encrypted stores are skipped.
- The website now sends `no-transform` on every page, so Cloudflare no longer
  inserts its Web Analytics script; visitors get exactly the published files.

The installed app still keeps data in two folders (next to the program and in
`~\.cursiv`); combining them is planned separately. The existing independent owner
identity authenticates the final package bytes; this is separate from
Windows-trusted Authenticode and Apple notarization. No new model-accuracy score
is claimed.

## Installer SHA-256

Windows: `44eab0866cdd0f451b91e9f15b61dc1f411a66d456e44da23be720cc57cf4688`

Mac (Apple Silicon): `2c134cf5f88a0e27ace24f0a456851c73abc95df8f699074a4ec781460236b5e`
