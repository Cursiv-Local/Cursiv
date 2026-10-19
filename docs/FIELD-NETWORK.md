# Cursiv Field Network: design

Status: **Phase 0's signing is built** (U73: device keys, signed USB shares, signed exports);
the network itself (Phases 1–4) is design only. Research roadmap R11.
Written 2026-10-18 so that what we build now (R4 signing, R9 photos) fits this later.

## The idea in one paragraph

A field team's laptops each keep running Cursiv and its AI locally, as today. One small
computer (a Raspberry Pi with an SSD) becomes the team's **master node** on a local Wi-Fi
network with no internet. Laptops press **Sync with master**: their new field entries go up,
everyone else's come down. The master keeps every laptop's records exactly as recorded,
shows the team lead the whole picture, makes combined reports, and keeps backups. Later the
same exchange can run to a server over the internet. Three ways to run, one protocol:

```
Standalone:     laptop ── its own records
Field network:  laptops ── local Wi-Fi ── master node (Pi + SSD)          no internet
Remote:         laptops / masters ── internet ── institution's master       when available
```

The master does **not** run the AI. It stores, checks, shows and backs up records.

## Principles (non-negotiable)

1. **Nothing is overwritten or merged, ever.** Each laptop's log is its own append-only chain.
   The master stores chains side by side. Two people writing different things about Sample 42
   is history, not a conflict.
2. **Disagreements are shown, never resolved by software.** A lead can add a note ("Sample 42:
   B's sediment reading is after the storm"); the note is a new record with a name and time.
3. **Every record proves where it came from.** Laptops sign what they send; anyone (master,
   reviewer, another laptop) can check a record wasn't changed or forged.
4. **Offline first.** No step needs the internet. The local network is the network.
5. **Only the field record syncs.** Personal memory, conversations, saved AI keys and settings
   never leave a laptop. Documents sync only if the lead publishes them to the team.
6. **Losing the master loses nothing.** Every laptop keeps its own full log; the master can be
   rebuilt from the laptops.

## Today (built, U67+)

- Field log: append-only JSONL per laptop, every entry chained to the previous one by SHA-256
  (`core/fieldlog.py`). Corrections are new entries with a reason.
- Team sync by USB stick or shared folder (`core/fieldsync.py`): a laptop shares its whole
  chain plus a manifest (entry count, last fingerprint); importing checks the chain and
  manifest, keeps one copy per laptop, refuses changed or cut-off copies, keeps both copies
  when histories differ and says so, and flags one sample ID used on two laptops.
- Per-sample history across laptops: `field log sample <id>`; team view and team export.

Limits the network has to fix: a laptop's identity is a hash of its computer name (anyone can
copy it); a share sends the whole chain every time; photos are file paths, not content;
nothing is signed.

## Roles

| Role | Can |
|---|---|
| **Researcher** | Record on their laptop; sync; see the team's records (configurable). |
| **Team lead** (administrator) | Everything a researcher can, plus: pair and retire laptops, add researchers, add notes to any record, publish documents and reference additions to the team, run combined reports, see sync status. Cannot edit or delete anyone's records. |
| **Viewer** | Read-only: reports and records (e.g. a PI back at the institution). |

Accounts live on the master. A laptop is paired to the master once and belongs to one
researcher at a time (a shared laptop is re-assigned by the lead, recorded).

## What is a record

Everything that syncs is a signed, append-only entry in some device's chain:

| Kind | Written by | Example |
|---|---|---|
| `observation` | a laptop | today's field log entry: site, coordinates, measurements, note, sample ID, observer |
| `correction` | a laptop | replaces an earlier entry *in the current view*, with a reason; the original stays |
| `retraction` | a laptop | "entry 14 was recorded at the wrong site": hidden from the current view, kept in history |
| `note` | the lead (on the master's own chain) | a comment on any record or sample |
| `publish` | the lead | a document or reference addition sent to every laptop |
| `device` | the master | a laptop paired, assigned to a researcher, or retired |

Photos and other files are **blobs**, stored once by their SHA-256 and referenced from records
by that hash (so a photo can't be swapped without breaking the record's fingerprint).

## Device identity and signing (Phase 0, also finishes R4): built in U73

As built (`core/devicekey.py`, `core/fieldsync.py`, `core/fieldlog.py`), one deliberate difference
from the plan below: entries keep their existing `device` label (a hash of the computer name), so
older logs and shares keep working. The key is bound to that label instead: every share carries
a signed head, and the first key seen for a laptop is remembered (`team/<laptop>.key.json`);
later shares signed by another key, or unsigned, are refused. Switching the label itself to the
key id is left for Phase 1, where the master can record the link as a `device` record.

Not built yet from Phase 0: incremental bundles (a share still carries the whole chain) and photos
as hashed blobs (needs R9).

The plan:

- On first use each Cursiv installation makes an **Ed25519 key pair** (the `cryptography`
  package Cursiv already ships). The private key never leaves the laptop (Windows: DPAPI-protected
  file; macOS: Keychain). The device ID becomes the first 16 hex characters of the public key's
  SHA-256, replacing today's hostname hash (old entries keep theirs; a `device` record links them).
- Each entry already carries `prev` and `hash`. New: a **signed head**: whenever a laptop shares
  or syncs, it signs `{device, seq, hash, time}` of its latest entry. A signature over the head
  covers the whole chain before it.
- The same signature makes **signed exports** (R4): an export carries the signed head, so a
  reviewer can check it came from that laptop and nothing was added or removed.
- USB sync uses it too: the manifest gains the public key and signed head; import checks them.

## The exchange protocol (one format, three transports)

A **bundle** is today's share, extended: for each device, the entries after a given hash, the
device's public key, its signed head, and any blobs those entries reference. Bundles are what
moves, whether on a USB stick, over local Wi-Fi, or over the internet.

Over the network (HTTPS, JSON):

```
GET  /v1/hello                 master id, name, public key, protocol version
POST /v1/pair                  one-time: pairing code + device public key  ->  device enrolled
GET  /v1/heads                 the master's latest known hash per device
POST /v1/push                  entries after the master's head for this device + signed head + blob list
PUT  /v1/blobs/<sha256>        a photo or file the master doesn't have yet (resumable)
GET  /v1/pull?cursor=<c>       everything the master received since cursor c (other devices,
                               notes, publishes), with their signed heads; returns a new cursor
GET  /v1/blobs/<sha256>        fetch a blob (photos are fetched on demand, not always)
GET  /v1/status                for the lead: devices, last sync, pending, problems
```

A sync is: hello → heads → push (only what's new) → blobs → pull → done. Every step is
idempotent: if the Wi-Fi drops halfway, pressing Sync again resumes. The master answers with:

```
Sync complete · ↑ 17 entries, 3 photos · ↓ 4 entries from 2 laptops · 0 problems · 14:37
```

**What the master checks on every push:** the signature on the head; that the new entries chain
onto the head it already has; each entry's fingerprint; that referenced blobs arrive and match
their hashes. If a laptop's chain doesn't continue the one the master has (a laptop restored from
an old backup, or tampering), the master keeps **both** histories, marks a problem, and tells the
lead. Same rule as today's USB import.

**Problems the lead sees** (none are auto-fixed):
- a device's history differs from what the master had (fork);
- one sample ID recorded by two laptops (could be two samples given one ID);
- a laptop's clock differs from the master's by more than 5 minutes (entries keep the laptop's
  time and the master's receipt time; both are shown);
- a blob referenced but never received;
- a retired device trying to sync.

## Discovery and pairing on a local network

- **Find the master:** the master announces itself on the local network (mDNS / Bonjour,
  `_cursiv._tcp`); the laptop shows "MRS Field Network found". Typing the master's address is
  the fallback (some networks block discovery).
- **Pair once:** the lead's dashboard shows a 6-digit pairing code and the master's key
  fingerprint. The researcher types the code; the laptop pins the master's key, the master
  enrols the laptop's key. From then on both sides know each other; nothing else on the Wi-Fi
  can pose as either.
- **Encryption:** HTTPS with the master's own certificate, pinned at pairing (no certificate
  authority needed offline).

## The master node

**Hardware (first version):** Raspberry Pi 5 (4–8 GB), a USB SSD for the data (never the microSD
card), a small travel router for the team's Wi-Fi, and a USB-C power bank or small UPS. The Pi
draws roughly 5–10 W, so a large power bank runs it for hours; measure before promising a
number. A Jetson (Orin-class, not the old Nano) only if the master should also run AI for the team.

**Software:** the same Python code as Cursiv (`fieldlog`, `fieldsync`, reports), plus a small
HTTPS service and a SQLite index over the stored chains (the chains themselves stay as
append-only files, which are easy to back up and to check). Installed from a ready-made Pi image;
"Make this the Cursiv master" on a laptop is a later convenience.

**Storage:** per-device chain files, a blob store by hash, the master's own chain (notes,
publishes, devices), the index. **Backups:** after every sync, append-only files are copied to a
second drive (or USB stick) and checked; restoring is copying them back and re-indexing.

**Dashboard (web, served by the master):**
- Team: researchers, their laptops, last sync, pending uploads, problems.
- Field data: every observation by site, sample, researcher, date; map of coordinates; photos.
- Samples: each sample's full history across laptops (the Sample 42 view).
- Reports: per researcher, per site, combined; the same printable report as `field report`,
  every entry with its fingerprint and who signed it.
- References: documents and reference additions published to the team.
- Exports: CSV, JSON, GeoJSON, with the signed heads.

## Remote mode (later)

The same protocol to a server over the internet, for two cases: laptops syncing from anywhere,
and a field master syncing to the institution's master when the team gets signal back
(**master-to-master**: the field master pushes its stored chains and its own chain like any
device). Needs proper certificates, rate limits, and an institution deciding where it runs.

## Security

| Threat | Handling |
|---|---|
| Someone else on the team Wi-Fi | Pairing with a code; pinned keys; HTTPS. Unpaired devices get nothing. |
| A forged or altered record | Signed heads and chained fingerprints; the master and every reader check them. |
| A lost or stolen laptop | Its data is on its disk: recommend BitLocker / FileVault. The lead retires the device; later records from its key are refused. |
| A stolen master | Optional full-disk encryption on the SSD (LUKS); laptops still hold their own copies. |
| A misbehaving master | It can't forge laptops' records (no private keys); laptops can verify everything they pull. |
| Personal data leaking | Only field records, notes and published documents are ever in a bundle. |

## Phases

| Phase | What | Done when |
|---|---|---|
| **0 (fits now)** | Device key pairs and signed heads; signed exports (R4); incremental bundles; photos as hashed blobs (with R9). All useful with USB sync alone. | A USB exchange is verified by signature; an export proves its origin. |
| **1 Field network** | Master service on a Pi image; pairing; push/pull/blobs; Sync button and status in Cursiv; read-only team view on the master. | Three laptops and a Pi, no internet, a week of syncing: nothing lost, duplicated or silently changed; a pulled cable mid-sync loses nothing. |
| **2 Team lead tools** | Dashboard: team, samples, problems, notes, combined reports, publishing documents; roles. | A lead runs a field day from the dashboard alone. |
| **3 Deployment** | Pi image, backups to a second drive, power measurements, "make this the master". | Set up from the image in under 30 minutes by someone who isn't the developer. |
| **4 Remote** | Internet server and master-to-master sync. | A field master syncs to an institution master after a trip. |

## Testing plan

- Simulated devices and an in-process master in the test suite (like `tests/test_fieldsync.py`):
  three laptops, interleaved syncs, every permutation of order.
- Fault injection: connection dropped at every step; duplicate pushes; a laptop restored from
  an old backup (fork); clock skew; a blob that never arrives; a tampered entry; an unpaired device.
- A real run: Pi + three laptops + travel router, no internet, for the Phase 1 "done when".
- Published results, as with the benchmark.

## Open questions (for the first team)

- Should researchers see each other's records, or only the lead?
- Which documents should a lead be able to publish (protocols only, or reference additions too)?
- How long do trips run without power for the master?
- Does the institution need data to land on its own servers, and in what format?
- Do photos sync automatically, or only when on mains power / strong Wi-Fi?

## What we are not building

- A master that edits, merges or deletes records.
- A shared AI on the master (unless a team asks; then a separate, Orin-class box).
- Syncing personal memory, conversations, keys or settings.
- Anything that needs the internet to work in the field.
