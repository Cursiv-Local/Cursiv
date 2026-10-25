# Cursiv v3.14-U99 — conversational actions, operational self-knowledge

Released with verified Windows and early Apple Silicon Mac packages. Hosted checks
passed Windows **1,979 / 13 skips** and Mac **1,964 / 28 skips** (the skips include the
live-model evaluation, which runs separately). Both tagged frozen apps passed, and the
Windows package also passed a start from a USB layout.
[Complete verification](U99-RELEASE-VERIFICATION.md).

- **Say it normally.** "Add a note that North Creek was 14.2 C and cloudy today", "work in
  my Field Data folder", "go offline": the local model turns it into one of Cursiv's own
  commands, Cursiv checks every value against what you wrote, and anything that changes
  something waits on a **Save / Edit / Cancel** card. On a held-out set never used for
  tuning: **94.0%** right action, **90.3%** offered correctly, **0 of 19** trick messages
  produced a card (qwen3:4b-instruct). [How it works](CONVERSATIONAL-ACTIONS-U99.md).
- **Cursiv knows what it is.** "Does Cursiv have an updater / online AI / dependencies?"
  is answered from its own capability records and your live settings; a feature that's
  switched off is never called missing.
- **No fake verification.** Cursiv records what it actually read or checked. "I checked
  the source", "verified" or "no correction needed" without a record gets a note; "you
  said X — check it" is answered from the records and says plainly when an earlier answer
  was wrong.
- **Writing is not doing.** Posts, emails and announcements are written, not refused.
  Writing about Cursiv sticks to what it does; absolute privacy promises get the true
  statement under them; fiction about Cursiv is labelled. New requests get new writing.
  [What was wrong and why](SELF-KNOWLEDGE-U99.md).
- `self map <words>` shows where something lives in Cursiv's code.

Known limit: the local model can still write "no cloud"-style lines in posts; the
correction note under them is the protection. The owner is testing U99 in the installed
app after release.

The existing independent owner identity authenticates the final package bytes; this is
separate from Windows-trusted Authenticode and Apple notarization.
