# Professional review of the offline reference

Research roadmap R7. Today no entry has been reviewed by a qualified professional, and Cursiv
says so on every first-aid card. This is how a review is run and recorded, so that "reviewed"
means something specific and can be checked.

## Who

- First-aid and medical entries: a licensed clinician with emergency or wilderness experience
  (EMT/paramedic, emergency or wilderness-medicine physician, nurse, or a wilderness first
  responder instructor). Record the qualification, not just the name.
- Survival and outdoor entries: a wilderness medicine or search-and-rescue instructor.
- One reviewer can cover only what is within their expertise; "outside my expertise" is a valid
  answer and leaves the entry unreviewed.

## Before

- [ ] Fix every entry that has no published source first, or mark it clearly: a reviewer's time
      is best spent on entries that will stay. Today 43 of 80 medical and survival entries have none.
- [ ] Print the sheet: `py -3.13 scripts/review_sheet.py` (medical and survival entries, each
      word for word, with its source and boxes to mark). Keep the fingerprint it prints.
- [ ] Explain what the reference is for (shown offline, often in an emergency, to people who
      may have no training) and that the review is unpaid / paid at ____ (agree this first).
- [ ] Ask whether they agree to be named. If not, only the qualification is recorded.

## The review

- [ ] The reviewer marks each entry: correct as written / needs a change / remove /
      outside my expertise, with notes.
- [ ] Nothing is reworded on their behalf without showing them the new text.

## After

- [ ] Keep the signed sheet (scan or photo) outside the repository, with the date.
- [ ] Entries marked **correct as written**, and whose fingerprint still matches the sheet:
      set `"reviewed": true` in `cursiv_engine/reference_data/sources.json` (an entry without a
      published source needs one added there first, or stays unreviewed).
- [ ] Entries marked **needs a change**: rewrite, send the new text back for review, and only
      then mark reviewed. **Remove**: remove it, or hold it back from chat (`NOT_IN_CHAT`).
- [ ] Add a section to this file: date, the reviewer's qualification (and name, if agreed), the
      sheet's fingerprint and commit, and how many entries were marked each way.
- [ ] Regenerate `docs/REFERENCE.md` (`py -3.13 scripts/reference_report.py`) and update the
      website's evidence page with the same numbers.
- [ ] A changed entry is no longer reviewed: its fingerprint won't match. Review it again.

## What is never claimed

- Not "certified" or "approved" by anyone. A named review of specific entries on a specific date
  is what we can say.
- Not that a review covers entries it didn't mark.

## Reviews

None yet.
