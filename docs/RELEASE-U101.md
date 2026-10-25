# Cursiv v3.14-U101 — starter profiles, field formulas, safer storage

[Complete verification](U101-RELEASE-VERIFICATION.md).

**Five starter profiles, ready to use**
- **@field** (Field assistant), **@checker** (Data checker), **@report** (Report writer), **@protocol**
  (Protocol helper) and **@writer** (Writing helper). Type `agents` to see them.
- Each one reads only what its file allows (your field notebook, your imported documents, a calculation),
  fetched by Cursiv's code. No profile can save, change or delete anything.
- @checker's findings (duplicate sample IDs, missing units, values that aren't numbers, entries with no
  site or sample) are worked out by code. @protocol answers only from your documents, with page numbers,
  and says so when they don't cover the question.
- Numbers or units in a profile's answer that aren't in your records get a note under it.

**Field formulas worked out by code**
- Conductivity corrected to 25 °C (APHA 2510 B), stream discharge (with the 0.85 surface-float
  correction), percent oxygen saturation, µS/cm ↔ mS/cm and molar solutions, each naming its method.
- On 14 field calculations through the full chat with the local model: 9 right before, 14 after, and none
  of 4 trick questions calculated.

**Safer storage**
- Login files can't be half-written by a power cut; the accounts list keeps a backup and is never read as
  "no accounts".
- On an encrypted computer, phone uploads are kept encrypted (one too big to encrypt is set apart and
  listed), and imports are unpacked encrypted, never in the system's temp folder.
- Damaged lines in saved notes or session history are kept and shown in `status`.
- Code that Codex test-runs now runs under the same guard as plugins: no network, programs or outside
  files, even when the code tries to hide it.

**Also:** the test suite runs on Linux in CI; the contributor guide has a code map and five starter tasks.

**Known limits.** The local model can still word explanations too confidently, and @report can still
add an interpretation of its own; the note under the answer flags numbers it adds. A Linux app isn't
packaged yet (the tests run on Linux).

The existing independent owner identity authenticates the final package bytes; this is separate from
Windows-trusted Authenticode and Apple notarization.
