# Field demo: a 10-minute walkthrough

For showing Cursiv to a research group. Everything below runs on the laptop with the
internet blocked. The demo uses **sample data** (a stream survey and a sample protocol
written for the demo), kept apart from real records and labelled as samples everywhere.

## Before the meeting

- [ ] Install the latest release (or use the Cursiv USB). Check the installer against
      `SHA256SUMS.txt` on the release page if anyone asks how to verify it.
- [ ] Open Cursiv once with the internet on, so the local model is downloaded (Setup).
- [ ] Turn on offline mode: Settings → Privacy & internet → **Offline mode (LOCAL ONLY)**, or type
      `offline on`. The header should say **LOCAL ONLY · internet blocked**.
- [ ] Turn off Wi-Fi too, if you want to show it visibly.
- [ ] Type `demo`. The header shows **SAMPLE DATA · demo on**. Your own notebook and
      documents are set aside, untouched.
- [ ] Ask one throwaway question so the model is loaded (the first answer takes longest).

## The walkthrough

Type each line in the chat. What to point out is under each.

1. **`status`**
   *LOCAL ONLY · internet blocked*, the model answering on this computer, no cloud keys,
   the notebook intact. Settings → Privacy & internet shows what stays on the machine and what could leave.

2. **`How long can our water samples stay on ice before they reach the lab?`**
   The answer quotes the sample protocol by page. Under it, Cursiv's own source line:
   *Sources: Your documents (SAMPLE Stream Protocol SP-1 (demo).txt p. 2)*. Source lines are
   written by Cursiv from what it actually gave the model, never by the model.

3. **`What does our protocol say about phosphorus samples?`**
   It doesn't. Cursiv says it searched the documents and found nothing, instead of inventing
   a procedure.

4. **`What is the distance and bearing from 44.1234, -71.5678 to 44.1371, -71.5512?`**
   About 2,020 m at 41°, worked out in code (Vincenty, WGS84), not guessed by the model.
   Source line: *worked out by Cursiv's code*.

5. **`Convert 9.6 C to F`**: 49.28 °F, again computed in code.

6. **`log site: Upper Brook (site A); sample: auto; water temp 8.6 C; pH 7.18; note: demo entry`**
   A structured observation with a generated sample ID and a fingerprint. Values are kept
   exactly as typed. Open **Field Notebook** in the sidebar to show the same entry in a form.

7. **`field log sample <the ID it printed>`**: that sample's history.

8. **`field log check`**: every entry is fingerprinted and chained; a changed, removed or
   reordered entry would be reported.

9. **Field Notebook → Report…** (or `field report`)
   A printable report: summary by site, every entry with its fingerprint, and the one
   correction with its reason (a pH reading corrected after recalibration; the original
   stays in the log). It says nothing in it was written by the AI.

10. **Field Notebook → Export…**: CSV, JSON and GeoJSON, plus the report and sample labels.
    **Share with team…** puts the log on a USB stick; **Import from team…** on another
    laptop brings it in, refusing changed copies and reporting conflicts.

11. **`My partner slipped on the rocks and cut his leg, it's bleeding badly`**
    The offline reference card comes first (U.S. sources, named and dated), with 911 at the
    top. Say plainly: the first-aid entries are sourced but **not yet professionally reviewed**.

12. **`What is a riffle in a stream?`**
    An ordinary answer, labelled *model knowledge (not checked against a source)*. That
    label is the point: you can always tell what was looked up and what wasn't.

13. **`demo off`**: sample data removed, real notebook and documents back.

## Questions you may get, and straight answers

- *Does anything leave the laptop?* Not with offline mode on: every connection off the
  computer is refused at the socket level. `PRIVACY.md` lists every online feature and when
  it could connect; `OFFLINE-DEMO.md` is the test (15 of 15, 0 connection attempts).
- *How accurate is it?* The truth benchmark: 153 fixed questions, scored by code, every
  failure published (`bench/RESULTS.md`, `bench/FAILURES-suite1.4.md`). U68: 149 of 153.
  The model still makes mistakes; the checks catch some and say so under the answer.
- *Is the medical content reviewed?* Not yet. Entries name their public sources; a
  professional review is planned (`docs/PROFESSIONAL-REVIEW.md`).
- *Has it been used in the field?* Not by a research team yet. That is what a pilot is for
  (`docs/RESEARCH-ROADMAP.md`, R10).
- *Live GPS?* Not yet; coordinates are typed or pasted. Distance, bearing and UTM are
  computed in code.
- *Why does Windows warn about the installer?* It isn't code-signed yet. The SHA-256 is
  published with every release, and the installer is built from the public source at the
  release's tag.
