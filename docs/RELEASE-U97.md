# Cursiv v3.14-U97 — trust fixes, encryption always on, removals

Released with verified Windows and early Apple Silicon Mac packages. Hosted checks
passed Windows **1,887 / 1 skip** and Mac **1,872 / 16 skips**. Both tagged frozen apps
passed, and the Windows package also passed a start from a USB layout.
[Complete verification](U97-RELEASE-VERIFICATION.md).

- **No pretend file actions.** "Add a line to notes.txt saying …" really adds it (after
  you approve); "Delete notes.txt" is answered by Cursiv, which never deletes files. A
  model reply claiming a save, update or delete without a real result is replaced.
- **More answers without the AI model:** unit conversions, speed × time, and averages
  of your field-log measurements are worked out by Cursiv and say so.
- **No self-certified answers:** the model's own "Verified: Yes" and "no model was used"
  lines are removed.
- **"What day is it?"** comes from your computer's clock.
- **Encryption is always on** for conversations and memories on a computer. The first
  start asks you to choose a passphrase (16+ characters) and encrypts what is already
  there. **Write the passphrase down: a lost passphrase cannot be recovered.** A Cursiv
  USB drive stays readable, and moving data to or from it keeps working.
- **Removed:** family letters, the legacy vault, personal letters, the public board, the
  mailbox and the council. Nothing already saved on your computer was deleted.
- **Plain MIT license.**

The existing independent owner identity authenticates the final package bytes; this is
separate from Windows-trusted Authenticode and Apple notarization. No new model-accuracy
score is claimed.

## Installer SHA-256

Windows: `b3ecc0f59df4220574ce20551f649f7c2a3e268bc51bf1ec0d7fdef63b708c4a`

Mac (Apple Silicon): `3433290d0fb8c2588263e11847fcffd2cbc90b92ace7857e615963abefab59c7`
