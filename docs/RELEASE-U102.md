# Cursiv v3.14-U102 — reliability: OS-enforced isolation, verified calculations, recovery

An engineering reliability release. No new features: the existing ones are harder to break, and each
claim is backed by a test. [Complete verification](U102-RELEASE-VERIFICATION.md).

**Isolation the operating system enforces**
- Plugins, Forge self-tests and Codex test runs now run inside a Windows Job Object as well as the
  Python guard: they can't start any other program, use unlimited memory or CPU, or read the clipboard,
  and they stop when Cursiv does. Tested with the Python guard switched off: Windows alone stopped all
  of these. If the limits can't be applied, nothing runs.
- Code runs no longer see your environment variables (where API keys can live).
- macOS and Linux get resource limits only; see [supported platforms](SUPPORT-MATRIX.md).

**Calculations checked against published values**
- 237 cases from NIST unit definitions, the APHA oxygen and conductivity methods, IUPAC atomic weights
  and hand-worked statistics, including inputs Cursiv must refuse and questions it must leave alone.
- Six defects found and fixed: temperatures below absolute zero, negative dissolved oxygen, negative
  dilution volumes, impossible dilutions, a rounded knot factor, conductivity measured at 25 °C. Now
  237/237, and the benchmark runs on every change.

**Records you can recover**
- The field notebook's integrity scenarios are tested together ([results](NOTEBOOK-INTEGRITY.md)). A
  passing check now says what it shows: nothing was changed after recording. It doesn't show who made
  the entries; a signed export does.
- A full disk or a damaged encrypted file is reported, never read as empty, and the copies made at
  encryption can be written out to a new file ([recovery procedures](RECOVERY.md)).

**Known limits.** Plugins and code runs still run as your Windows user (reading files you can read is
stopped by the Python guard, not Windows). Mac packages are built and self-tested in CI but have never
been tested on a real Mac. The local model can still word explanations too confidently.

The existing independent owner identity authenticates the final package bytes; this is separate from
Windows-trusted Authenticode and Apple notarization.
