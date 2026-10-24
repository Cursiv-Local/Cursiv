# Cursiv v3.14-U93 — readable chat code and website polish

Release preparation. Final test counts and package hashes will be recorded after
the protected checks and tagged builds succeed.

Locked isolated Windows source: **1,805 passed / 1 platform skip**. Focused
font/rendering checks: **86 passed**. Required workspace gate: **63 passed**.

- Inline commands and code blocks use a distinct monospace font at normal chat
  size. Windows prefers Consolas; Mac and other environments have local fallbacks.
- Apply the font during streaming, completed replies and reopening older chats.
  Preserve text, links, bold formatting and the existing message cache.
- Record the published website changes: the tester invitation below the homepage
  hero buttons, download buttons after the tester page's closing thanks, and the
  existing custom 404 page.

No model behavior, storage format, notebook chain, workspace authorization or
offline policy is changed. No migration of user data is performed.

The existing independent owner identity will authenticate the final package bytes.
This is separate from Windows-trusted Authenticode and Apple notarization; their
publisher warnings remain. No new model-accuracy score is claimed.
