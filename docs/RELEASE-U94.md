# Cursiv v3.14-U94 — USB startup fix and drive check/update

Released with verified Windows and early Apple Silicon Mac packages. Hosted
checks passed Windows **1,812 / 1 skip** and Mac **1,797 / 16 skips**. Both
tagged frozen apps passed. [Complete verification](U94-RELEASE-VERIFICATION.md).

- A Cursiv USB made with "Include my memories" stopped on every start because its
  first start found two different versions of the same data files. The newer copy
  of each file is now kept, a replaced file is backed up first, and startup goes on.
- "Make a Cursiv USB…" can **Check drive** (read only) and **Update USB**: program
  files that changed are copied, and personal data is compared file by file. Newer
  data on the drive is kept; a drive file is backed up before it is replaced.
- The program copy no longer carries data folders into `<drive>\Cursiv\`.

Data moves one way in this release, from a computer to the drive. Drive contents
are not encrypted by Cursiv. The existing independent owner identity authenticates
the final package bytes; this is separate from Windows-trusted Authenticode and
Apple notarization, whose publisher warnings remain. No new model-accuracy score
is claimed.

## Installer SHA-256

Windows: `0863df1ded070f315db084e2f5f35ed517c0aa14f52b7b0369bb99e438b7f9a7`

Mac (Apple Silicon): `daf6ce9d8a874a3846677341ff77983371eb6fc0fcc9d3cdb2160bfaef053a96`
