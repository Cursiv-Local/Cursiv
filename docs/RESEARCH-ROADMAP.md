# Cursiv for field science: roadmap (2026-10-18)

Main goal from U65 on: a dependable offline tool for scientific field work, where
recording data correctly matters more than clever answers. Each phase ends with
something a reviewer can check. Claims stay exactly as strong as the tests behind them.

| Phase | What | Done when |
|---|---|---|
| **R1 Field notebook** | Structured observations (time, place, observer, measurement + unit, notes), kept apart from anything the AI infers. Append-only: a correction is a new entry pointing at the old one. Export to CSV, JSON, GeoJSON. | A day of observations logged offline exports with every value exactly as entered. |
| **R2 Calculations in code** | Unit conversions, dilutions, concentrations, coordinates (DMS, decimal, UTM), basic statistics, sample size and area. The model explains; code computes; answers are checked against the computed number. | A field-calculation benchmark category passes 100%. |
| **R3 The team's documents** | Protocols, SOPs, permits and field guides loaded offline; answers quote page numbers; a "documents only" mode; each document fingerprinted. | Protocol questions answered from the right page; uncovered ones get "not in your documents". |
| **R4 Integrity and chain of custody** | Chained fingerprints on every entry (started in R1), sample IDs and printable QR labels, daily signed export, clock source and device recorded; attributable, legible, contemporaneous, original, accurate. | Altering any past entry is detected; a reviewer can trace a sample from collection to export. |
| **R5 Hardware and endurance** | Measured speed without a graphics card, battery-saver mode, the small model benchmarked, power-loss-safe writes, restart and full-disk tests, the SSD build tested on two clean laptops. | A day on battery; pulling the plug mid-entry loses nothing; speed documented per hardware class. |
| **R6 Team sync without internet** | Laptops merge observations by USB or local network, duplicates and conflicts shown, never silently resolved; personal memory never syncs; opt-in upload to the institution when back online. | Three laptops log separately for a week and merge with nothing lost or duplicated. |
| **R7 Expedition safety pack** | Wilderness medicine, cold water, altitude, heat, wildlife by region, weather interpretation, the NIOSH chemical guide; a printable emergency card. Sourced, dated, professional review as the target. | Every entry sourced; a professional review recorded. |
| **R8 Discipline packs** | Public-domain or open sources only: GBIF taxonomic backbone (CC0) for species names, USGS mineral and rock tables, EPA water-quality methods, NOAA references. Versioned like today's packs. | Each pack listed in REFERENCE.md with its licence. |
| **R9 Hands-free capture** | Offline speech-to-text for voice notes, photos with their GPS and time, read-back before saving. | A voice note becomes a correct entry without typing. |
| **R10 Field pilot** | One team on a real trip. Measure entries logged, errors found at export, answers corrected, battery uptime. Publish everything, including failures. | The written pilot report. |
| **R11 Field network** | A master node (Raspberry Pi + SSD) on the team's local Wi-Fi: laptops sync signed, append-only records to it with no internet; nothing is merged or overwritten; the team lead sees every record, sample history, problems and combined reports; later the same protocol to an institution's server. Design: `docs/FIELD-NETWORK.md`. | Three laptops and a Pi, no internet, a week of syncing: nothing lost, duplicated or silently changed. |

Order: R1, R2, R5 first (the strongest pilot), then R4 and R3, with R7 and R8 continuous,
R6 when a team has several laptops, R9 last. R11 after a pilot has used USB sync; its Phase 0
(device keys, signed heads and exports, photos as hashed files) is built with R4 and R9.

Not claimed: certification of any kind; professional review of the reference (none yet);
code signing (not yet). Personal memory stays on the computer and never syncs.

## Status (2026-10-18, after U66; not yet released)

- **R1 Field notebook: built and tested** (U66). Not yet used by a field team.
- **R2 Calculations: built and tested** (U66). Since then: distance and bearing between GPS points
  (Vincenty, WGS84) and 24-hour clock times. Field cases in the truth benchmark (suites 1.3 and 1.4).
- **R3 The team's documents: built and tested.** PDFs and text imported offline, answers quote the page,
  a check that cited pages were among those supplied, and a documents-only mode (never during an emergency).
- **R4 Integrity: started.** Entries are fingerprinted and chained; sample IDs, per-sample history and
  printable labels are built. Signed exports are next.
- **R5 Hardware: started.** Battery saver, power-loss-safe saves, speed measured with and without a graphics card (`docs/HARDWARE.md`). Still to do: the SSD kit on two clean laptops, a full day on battery, full-disk behaviour.
- **R6 Team sync: built and tested** with three simulated laptops on one USB drive (`tests/test_fieldsync.py`):
  nothing lost or duplicated, changed or cut-off copies refused, differing histories kept side by side,
  the same sample ID on two laptops reported. Not yet tried by a team on real laptops. Upload to an
  institution is not built.
- **R7 Safety pack: started.** 37 entries from public U.S. government sources (`docs/REFERENCE.md`); none professionally reviewed yet.
- R8, R9, R10: not started.
- **R11 Field network: designed** (`docs/FIELD-NETWORK.md`), not built. Builds on R6's
  per-laptop chains; Phase 0 overlaps R4 (signing) and R9 (photos).
