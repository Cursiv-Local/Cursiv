# Cursiv v3.14-U104 — Field Station preview, team-drive fixes

A preview of Cursiv on a Raspberry Pi, plus fixes the team-drives demo found. The Windows app works as
before. [Complete verification](U104-RELEASE-VERIFICATION.md).

**Cursiv Field Station (preview, not yet tested on a Raspberry Pi)**
- Cursiv's engine served to phones, tablets and laptops over a local network, with no internet: sign in with a
  Cursiv account, and the encrypted notebook stays locked after every restart until someone enters the
  encryption passphrase in the browser.
- The field notebook in the browser: record, correct (the original is never edited), search, check integrity,
  export. Twenty people saving at once still produce one unbroken chain (tested).
- Station health with every reading labelled real, derived, simulated or unavailable. An ordinary USB-C
  power bank shows "battery telemetry unavailable", never an invented percentage. Throttling and undervoltage
  come from the Pi's own firmware flags.
- Hardware simulation scenarios for development, always under a SIMULATED banner. Safe shutdown that never
  powers the machine off unless it's set up to.
- Runs and is tested on 64-bit ARM Linux (the Pi's processor type) on every change. The installer, the
  station's own Wi-Fi, SSD and USB workspaces and local AI on the Pi are planned. See
  [cursiv.us/field-station](https://cursiv.us/field-station) and [the plan](FIELD-STATION-PLAN.md).

**Fixes found by the team-drives demo**
- Import reports name the scientist on every line, not a raw notebook id.
- Make a Cursiv USB: the notebook checklist shows every notebook without scrolling, the name box keeps its
  label, and "1 entry" reads correctly.
- The dissolved-oxygen check now catches a saturation figure given as a range ("12.5–13.0 mg/L") and the
  wording "solubility of oxygen".

**Known limits.** Nothing in the Field Station has run on a Raspberry Pi yet; results will be published as
measured. It uses plain HTTP on the station's own network (protected by the Wi-Fi password, not encrypted by
the page). The outside-review items planned for U104 (a passphrase for drive signing keys, a strict
photo-complete import, a checksum for the voice model, a release-document check) move to U105. Mac packages
are built and self-tested in CI but have never been tested on a real Mac.

The existing independent owner identity authenticates the final package bytes; this is separate from
Windows-trusted Authenticode and Apple notarization.
