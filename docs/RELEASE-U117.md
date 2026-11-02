# Cursiv v3.14-U117 — Fixes from the owner's U116 prompt run

The owner ran the test prompts on installed U116 and found failures the mocked tests missed. This release fixes them. No new features.

- **"Forget it" really just drops the topic.** In U116 it could still reach the "Forget this? it" card, and after Yes the reply could claim a memory was removed when nothing was. It no longer reaches the card, and a model reply can no longer claim a memory was saved, changed or removed: any such claim is replaced with "No memory was changed." Check the Memory window for what is actually saved.
- **Notebook search finds what you asked for.** "search my notebook for Site A" searched for the request's own words ("my notebook for Site A"). It now searches for "Site A", and short words such as "A" match whole words only, so Site A no longer matches Site B.
- **Questions about readings are answered, not saved.** "I logged 14.2 C at Site A and 13.8 C at Site B. What's the difference?" became a notebook save. A message ending in a question is now answered unless it asks to log something.
- **Sayings are not memory lookups.** "remember to drink water is good advice" no longer lists your saved notes.
- **Routing questions read the source.** "how do you decide whether to route a question to the notebook?" got the canned decline; it now reads the real routing code.
- **Check for Updates shows its result in Settings.** The update button looked dead because its result went to the main window's status line, behind Settings. Settings → Updates now shows checking, up to date, offline, failed or update available under the button, which says "Check now" instead of "Open" and is disabled while a check runs.

**Correction to U116.** The U116 notes said "forget it" just drops the topic. That was only true of the memory parser; it is fixed in this release.

Validation: see the release verification record. Automated checks used mocked providers only; no real AI calls or live model inference. Real-model behaviour remains an owner manual test.
