# Cursiv v3.14-U85 — Quiet feedback and notebook continuity

## What changed

- Keep streamed drafts usable while optional local reviews run. A small progress
  line appears only around reviewer calls. Clean checks leave the answer alone;
  findings show a short note count or an explicitly suggested revision.
- Show application-owned tool/file/memory/notebook receipts, independent of
  model prose. Keep failed actions unconfirmed and visible.
- Surface configured workspace, file access and current talk-only/read-only
  limits. Retain the last recorded notebook site in this conversation, including
  when reopening it. Historical context is not a fresh permission or access check.
- Use restrained response guidance, shorter restriction notes and precise
  persistent-memory confirmations. Dated recall leads with count and scope.
  Conversation-history settings remain separate from memory restrictions.
- Include record/sample IDs and fingerprints in notebook confirmations. Verify
  graphical saves and imported copies by reading them back. Count new imported
  entries separately from uploads and duplicates; preserve signature, photo and
  clock warnings. Keep existing append-only records and schemas.

## Install or update

Windows: `Cursiv-Setup-3.14-U85.exe` or its identical `Cursiv-Setup-latest.exe`
alias; verify against `SHA256SUMS.txt`. Apple Silicon Mac uses the versioned DMG
or `Cursiv-mac-latest.dmg` and `SHA256SUMS-mac.txt`.

U85 is higher than U84, so existing U84 copies can detect it with the normal
updater when online checks are allowed. Offline mode blocks GitHub requests.
No personal-data/schema migration or automatic installation on the owner's
computer is performed. Local model answers still need a compatible installed
Ollama model. Windows/Mac installers remain unsigned; Mac is not notarized.

## Tests and limits

The final versioned Windows source suite passed 1,267 tests with one Mac
Keychain skip. Hosted CI, packaged self-tests, fresh
158-case model results and actual public-download hashes are recorded only
after completion in [U85 verification](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/U85-RELEASE-VERIFICATION.md)
and the [test page](https://cursiv.us/ai-reliability-testing#u85).

The controlled 10/100/1,000-message rendering replay kept zero full-document
rebuilds and median final-token-to-ready times of 17/22/76 ms. It used a simulated
one-second review wait, not a measurement of model speed. The worst observed
GUI gap was 138 ms in the 1,000-message case. [Method and raw data](https://github.com/Cursiv-Local/Cursiv/blob/main/docs/CHAT-FEEDBACK.md).

A clean bounded check does not guarantee factual accuracy. Small models can
still invent details or give contradictory/unsafe advice; signatures establish
integrity/device-key continuity, not truth of observations. Memory is selected
stored facts, not model retraining, complete recall or subjective awareness.
Local conversations and memories remain unencrypted on disk. Physical
clean-machine, second-PC USB, phone and independent field checks remain necessary.
