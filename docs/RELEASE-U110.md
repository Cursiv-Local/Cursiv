# Cursiv v3.14-U110 — natural-language self-inspection and notebook reliability

U110 starts from published U109. It fixes how Cursiv recognizes plain-language
requests to inspect its own code, and ships the U109 post-release reliability
repairs. [Release verification](U110-RELEASE-VERIFICATION.md) is written after the
tagged packages are built.

- A self-inspection request still routes when it follows an instruction or a
  sentence of conversation. Safety wording, user repositories and workspaces,
  fiction requests and turns that forbid reading keep their existing routes.
- Asking which function decides self-inspection returns the actual resolver,
  `prepare` and the conversation handoff before model inference, with declaration
  lines, rather than unrelated startup or file-access functions.
- Specific "which function / identify the function" questions prefer matching
  declaration names over words that only appear in a file path.
- Notebook records can be read, verified and exported with natural wording;
  corrections stay linked to the original reading. Memory fragments resolve to one
  saved fact with a preview before editing. Saved presentation preferences reach
  the reply style. Code-computed answers are no longer flagged as unsupported
  observations. Details: [U109 post-release validation](U109-POSTRELEASE-VALIDATION.md).

No new agents, models, dependencies, cloud fallback or workspace permissions are
added; self-inspection stays read-only and offline. The full Windows source suite
passed **2,664 tests, 15 skips and 19 subtests** before tagging; the USB gate passed
45 tests. Function lookup is still keyword-based, and the model's own explanation
of checked source remains an inference, not a runtime trace.
