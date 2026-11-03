# Cursiv v3.14-U118 — Conversation saves no longer fail on Windows

One fix. No new features.

- **Saving a conversation no longer fails with "Access is denied".** Windows refuses to swap a new file into place while anything has the old one open. Cursiv could do that to itself: opening or listing conversations read a chat file at the moment a save was replacing it, and the save failed. Opening and listing now wait for a save in progress. The swap also retries for about half a second while something outside Cursiv, such as antivirus or the search indexer, has the file open. If a file stays locked, the save still reports the failure instead of losing it silently.

Validation: see the release verification record. Automated checks used mocked providers only; no real AI calls or live model inference. The owner has not yet re-run the prompt set on U117 or U118.
