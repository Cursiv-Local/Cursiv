# Cursiv v3.14-U103 — team field drives, overconfidence check, silent-error lint

Team field work on drives, plus a safety and honesty pass finishing the codebase review.
[Complete verification](U103-RELEASE-VERIFICATION.md).

**A team on field drives, one main computer**
- Each scientist gets a Cursiv drive made in their name. Their field notebook is theirs on any PC they plug
  it into, the main computer included. Cursiv keeps a team copy at the top of the drive, updated when it
  starts and quits.
- On the main computer, plug the drives in one at a time and use Import from team (or Bring drive data
  here). Each person's entries and photos go into the team view in their name; the main computer's own
  notebook is never replaced. Team exports say whose each entry and photo is. Nothing is encrypted per
  person: anyone signed in on the main computer can read the team's work.
- Making a drive, choose which scientists' notebooks it carries; none is included unless ticked.
- Before this release a drive used on two PCs was refused at import, work typed on the main computer was
  skipped as the computer's own, and Bring drive data let each drive's notebook replace the last.
- Checked on every change: 20 drives with 1,200 entries and photos arrive byte for byte; damage on a drive
  is refused whole; a drive pulled mid-import leaves nothing half-written; importing again changes nothing.

**Answers that settle too much**
- Ask about one reading, a look or one sample, and the local model sometimes settles it anyway: "No, your
  meter isn't broken", "Yes, you can drink the spring water without treating it". Cursiv now adds a line under
  such an answer saying what it rests on and how to confirm it (repeat the reading, check calibration, or a
  certified lab for safety). It never rewrites the answer.
- Measured on qwen3:4b-instruct with 50 questions, every answer read by hand: 7 were overconfident. On the 30
  the rule was tuned on it noted 6 of 6 with no false notes; on 20 written afterwards it noted 1 of 1 and
  gave 2 false notes, both fixed with tests. [Results](../bench/overconfidence/RESULTS.md).
- The dissolved-oxygen check no longer mistakes your own reading for a saturation figure.

**Errors that were being ignored**
- Code that stores your data must now say why whenever it ignores an error; a test enforces it. It found
  three real problems, all fixed: a damaged territories file was overwritten (now moved aside), Start over
  could leave a locked login file behind while looking successful, and a removed account's security answers
  could stay behind. Security answers are now saved atomically.
- Guessing security answers is slowed down: after 5 wrong tries, a wait that doubles up to an hour, kept
  across restarts.

**Phone and USB**
- A memory containing a key, token or password is never put in the summary the phone app keeps on
  cursiv.us. A failed upload says so. Only real images from the phone are shown.
- Removed an unused function that could erase a USB drive's personal data.

**Also:** chat lookups and notebook reads word results the same way; tests for the problem report, the
confirm card and the phone sync; the new Cursiv logo is the app icon.

**Known limits.** A drive already used on two different PCs before this release labels its entries by PC and is still refused at import (each log may hold only its own notebook's entries, so nobody's work can be shown under another name); drives made or first used from this release keep one label on every PC. The overconfidence note catches a settled verdict at the start of an answer; it misses one
inside a structured answer, and it can't tell whether a stated reference range is right. 50 questions from one
model is a small sample. Mac packages are built and self-tested in CI but have never been tested on a real Mac.

The existing independent owner identity authenticates the final package bytes; this is separate from
Windows-trusted Authenticode and Apple notarization.
