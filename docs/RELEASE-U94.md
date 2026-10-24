# Cursiv v3.14-U94 — USB startup fix and drive check/update

Prepared 2026-10-24. Not yet published: installer hashes, owner signatures and
hosted Mac results are added when the release is verified.

- A Cursiv USB made with "Include my memories" stopped on every start because its
  first start found two different versions of the same data files. The newer copy
  of each file is now kept, a replaced file is backed up first, and startup goes on.
- "Make a Cursiv USB…" can **Check drive** (read only) and **Update USB**: program
  files that changed are copied, and personal data is compared file by file. Newer
  data on the drive is kept; a drive file is backed up before it is replaced.
- The program copy no longer carries data folders into `<drive>\Cursiv\`.

Data still moves one way, from a computer to the drive. Changes made on the drive
are not copied back into a computer's installed Cursiv by this release. Drive
contents are not encrypted by Cursiv.
