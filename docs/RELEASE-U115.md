# Cursiv v3.14-U115 — Interrupt continuity and optional personality

Stop frees the input promptly, keeps the visible partial response and ignores late output from the cancelled turn. Use the small paused-task selector to Resume or Dismiss, or say “continue” after changing topics. Saved conversations retain bounded checkpoints; defaults are8 tasks for14 days, configurable in Settings.

Resume uses the selected provider and the existing offline/consent controls. It continues text and does not replay notebook operations, file writes or tool calls. New actions need a separate request and the usual confirmation. Original scientific questions still drive evidence checks during continuation.

Optional Professional, Playful and Sassy presentation, humor frequency and answer detail are in Settings → How Cursiv answers. Current defaults and learned rules remain. Sensitive contexts suppress humor; ordinary casual conversation avoids unrelated measurement/calibration notes. No extra model call creates a checkpoint or personality hint.

Validation: 2,884 source tests passed,33 skipped,19 passing subtests under the strict offline guard, including60 new regressions. Synthetic UI Stop median6.44ms; this is not a model/server benchmark. Hosted platform and native-package evidence is recorded in the release verification receipt after those gates complete.

Limits: remote cancellation is best effort; connection setup/uncancellable work may occupy the serialized backend slot while input stays available. Resume context is bounded to8,000 characters plus route budget. Real Ollama/OpenAI/Groq continuation quality and server cancellation remain owner manual tests. No real AI calls or live model inference were used during automated validation. Website publication is deferred at the owner's request.
