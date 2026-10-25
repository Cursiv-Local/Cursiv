# Cursiv v3.14-U98 — plugins isolated, notebook encrypted, clearer chat

Released with verified Windows and early Apple Silicon Mac packages. Hosted checks
passed Windows **1,915 / 1 skip** and Mac **1,900 / 16 skips**. Both tagged frozen apps
passed, including the new plugin-isolation check, and the Windows package also passed a
start from a USB layout. [Complete verification](U98-RELEASE-VERIFICATION.md).

- **Plugins never run inside Cursiv.** Every plugin call, and every Forge test of a new
  plugin, runs in its own short-lived process that can't reach the network, start other
  programs, load native code or open files outside the plugin's own folder. The installed
  app does this itself; no separate Python is needed.
- **Your field notebook and custom agents are encrypted** with your conversations and
  memories. Reports, exports and shares stay readable. If you're on U97, Cursiv encrypts
  them at your next start, after making recovery copies.
- **A clearer chat:** starter cards in a new chat; answers worked out by Cursiv say so
  ("Worked out by Cursiv · no AI model"); saves show as receipt cards; a short tour after
  your first AI answer; errors say what happened and what to do next.
- **Fixes:** `file list` with no folder lists your workspace; agent instructions no longer
  mention "his family"; failed session-log writes are recorded.
- **Tested on real hardware:** moving data computer → USB → another computer.

The existing independent owner identity authenticates the final package bytes; this is
separate from Windows-trusted Authenticode and Apple notarization. No new model-accuracy
score is claimed.

## Installer SHA-256

Windows: `1f62566b3af118ab816042b82a78f2bab31aece7fb79be28b6f3315c3998492a`

Mac (Apple Silicon): `4c7fc38bd30a4e476bb220e25172bd57aee45b2430e7ea1cb2bc3fadd35a1b3e`
