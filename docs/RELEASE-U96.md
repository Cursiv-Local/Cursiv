# Cursiv v3.14-U96 — one personality, open system, self-awareness, USB gate

Released with verified Windows and early Apple Silicon Mac packages. Hosted checks
passed Windows **1,865 / 1 skip** and Mac **1,850 / 16 skips**. Both tagged frozen apps
passed, and the Windows package also passed a start from a USB layout.
[Complete verification](U96-RELEASE-VERIFICATION.md).

- **One personality**, the same in every conversation: curious, calm, warm without
  gushing, a light dry humor, honest, on your side. The selectable tones are gone;
  your learned style preferences still apply.
- **Creative requests are welcome.** Thought experiments, hypotheses and fiction are
  answered and labelled. A reply that claims it can't do a creative request and then
  does it anyway shows only the work.
- **Open system:** owner mode is removed; no code unlocks anything.
- **Cursiv can look at itself, read-only:** `self source` / `self read` (its own code
  and docs), `self prompt` (the instructions sent for your last answer, kept in memory
  only) and `self stores` (what is saved, where, and how it reaches answers).
- **Honest privacy answers:** "does anything I type leave my computer?" is answered
  from Cursiv's live settings, listing exactly what can go online.
- **`memory cleanup`** lists saved notes, memories and style preferences that
  mislead answers; you remove only what you pick, after a backup.
- **Your AI keys stay yours:** "Make a Cursiv USB" copies them only if you tick a
  separate box, off by default.
- **The USB function is tested every time:** before each commit, on every push and
  PR, and at release, where the built app is started from a USB layout.
- Cursiv says it is made by Cursiv Local, an independent open-source project.

The existing independent owner identity authenticates the final package bytes; this is
separate from Windows-trusted Authenticode and Apple notarization. No new model-accuracy
score is claimed.

## Installer SHA-256

Windows: `0513210ec028f6ec4d209bb951a0f1a82990a4b0fc50dfaeea1aad43abe3e91f`

Mac (Apple Silicon): `eed8b5862a9d8be5551d59377a539706924932b381bbd6ec40aec4f270cbcee5`
