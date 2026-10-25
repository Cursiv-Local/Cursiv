# Cursiv v3.14-U100 — records you can trust, memory you can see

Built from the owner's U99 test run: every failure in it was traced to its cause and fixed in
Cursiv's own code, each with a test that reproduces the original failure.
[Complete verification](U100-RELEASE-VERIFICATION.md).

**Field notebook**
- "Record field observation: ORION-742, sample W-001, 18.6°C, 12:40, site Willow Basin" is shown
  on a **Save / Edit / Cancel** card exactly as Cursiv read it (sample W-001, site Willow Basin,
  temperature 18.6 °C). Before, it was saved straight away as "ORION = −742", so a lookup by
  sample found nothing.
- A code like W-003 is never put in *site* unless you call it a site.
- "Verify … ORION-742 observations" runs the real chain check and lists the records it found;
  none found is said plainly, never "verified".
- "Correct W-001 temperature from 18.6 °C to 18.9 °C" checks the old value, then adds a
  correction linked to the original. The original is never changed, and the history shows both.

**Conversation and memory**
- "What did I ask three messages ago?" is answered from this conversation's stored messages.
  Exchanges from your other conversations no longer leak into an ongoing one (that was where
  the invented checklist and the invented ORION-742 readings came from).
- "Correction: …, not …" updates the saved memory and keeps the old value as history.
- **Remember this?** cards for things Cursiv picks up about you now actually appear, and only
  a confirmed one is saved. On a held-out test: 20% → 90% of lasting facts offered on the first
  run; health, money and passwords are never offered.
- Each conversation keeps a short **session note** of where you left off, in your own words
  (`session note` shows it). `memory folder` gives your memory as readable files.
- "when I say the creek I mean North Creek" teaches Cursiv your words.

**Numbers**
- A correct median is no longer withdrawn (it was being checked against the mean).
- "To six decimal places" gives six decimal places and never calls a rounded figure exact.
- Oxygen saturation uses the standard Benson & Krause equation (APHA Standard Methods 4500-O):
  9.35 mg/L at 18.6 °C. A made-up formula or a figure that disagrees gets a note.
- Invented example numbers and impossible coordinates are labelled.

**Known limits.** The local model can still be overconfident in explanations (it called a
0.4 °C thermometer difference "normal"); that's guidance to the model, not a code check, and it
isn't fully followed yet. Entries already saved wrongly in a notebook stay as they are (the
notebook is append-only); correct them in the Field Notebook window. The app now uses
https://cursiv.us.

The existing independent owner identity authenticates the final package bytes; this is
separate from Windows-trusted Authenticode and Apple notarization.
