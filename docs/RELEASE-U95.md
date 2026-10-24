# Cursiv v3.14-U95 — bring USB data back to a computer

Prepared 2026-10-24. Not yet published: installer hashes, owner signatures and
hosted Mac results are added when the release is verified.

- **Bring drive data here** in "Make a Cursiv USB…" brings work done on a Cursiv
  USB (conversations, notebook entries, memories, settings) into Cursiv on this
  computer. Only files that are new or newer on the drive come over; anything
  newer on the computer is kept.
- Files are staged and verified, then applied at the next start before any data
  is read. Replaced files are backed up and a report lists every decision.
- Saved keys are encrypted for this Windows account. Accounts, passwords, logs and
  device identity stay with each computer. Encrypted stores are skipped.

The installed app still keeps data in two folders (next to the program and in
`~\.cursiv`); combining them is planned separately.
