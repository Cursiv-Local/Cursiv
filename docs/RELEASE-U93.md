# Cursiv v3.14-U93 — readable chat code and website polish

Released with verified Windows and early Apple Silicon Mac packages. Hosted
checks passed Windows **1,805 / 1 skip** and Mac **1,791 / 15 skips**. Both
tagged frozen apps passed. [Complete verification](U93-RELEASE-VERIFICATION.md).

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

The existing independent owner identity authenticates the final package bytes.
This is separate from Windows-trusted Authenticode and Apple notarization; their
publisher warnings remain. No new model-accuracy score is claimed.

## Installer SHA-256

Windows: `8d749ecec18dce87a63638a5a5e89fa522476179b082fdb577aba92371775821`

Mac (Apple Silicon): `6d39ec3fc6db551d698147101271afcbae30d898e8c55046e1bf91a7502f2e15`
