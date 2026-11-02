# Cursiv v3.14-U116 — Audit fixes: cleaner chat bar, safer memory, fewer false warnings

A focused review of U115 and the chat window. No new features.

- **Cleaner chat bar.** The "AI Providers…" button no longer sits permanently under the chat box. It appears beside a provider failure (with "Retry preserved request" when the request was kept) and disappears at the next message. Settings → AI Providers is unchanged.
- **Safer memory.** "Forget it", "forget about it" and "never mind, forget it" now just drop the topic. Before, they could silently delete the saved memory that matched your previous message. "Forget that", when Cursiv has to work out what "that" means from the conversation, now shows the exact saved memory and deletes it only after you reply 1 or yes ("no" or "cancel" keeps it). "Forget that my dog is called Biscuit" now finds that memory. Talking about a saying ("remember to drink water is good advice") is no longer saved as a memory.
- **Fewer false science warnings.** The "repeat the measurement, check the calibration" note now needs a measurement or a science, health, safety or field topic. Casual questions (a toaster noise, a pet's name, a landlord) no longer get it; creek water, rashes, mushrooms and thermometer readings still do.
- **Model menu** shows its full label instead of cutting it off.

**Correction (November 1, 2026).** The "forget it" fix above covered only the memory parser. In the U116 app, the confirm-card route can still offer "Forget this? it", and the reply after Yes can falsely say a memory was removed. Check the Memory window for what is actually saved. This is fixed for the next release.

Validation: see the release verification record. Automated checks used mocked providers only; no real AI calls or live model inference. Real-model behaviour remains an owner manual test (docs/U116-AUDIT-HANDOFF.md, section 8).
