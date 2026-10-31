# Paused responses and conversational preferences

U115 feature guide. Release publication is tracked in U115-HANDOFF.md.

Press **Stop** to stop displaying the current response and use the input again.
The text received by the window stays in the transcript. An interrupted model
response gets a small **Paused response · Resume** row above the conversation.
Select an older paused task there, choose **Resume**, or **Dismiss** it. You can
also say “continue,” “finish that explanation,” or “resume the previous task.”
Those short requests use the latest paused task when one exists.

Resume supplies the original request and already displayed text to the existing
selected provider. It continues the text; it does not replay notebook commands,
file writes, confirmations or other tools. Request any new action separately.
Existing notebook integrity, memory permissions, workspace restrictions, cloud
consent and offline restrictions continue to apply. An interrupted answer is
unfinished conversation text, not proof that a tool ran or a fact was verified.

The selected destination is shown before continuing. When automatic selection
has not changed and a previous exact backend was recorded, that backend is pinned
for the continuation. If it is unavailable, an error leaves the paused task
available; Cursiv does not silently choose a replacement. Changing the selector
deliberately continues with that new selection and its normal permissions.

Paused tasks are saved inside existing conversation files if chat autosave is
on or the conversation was already saved. With autosave off, a new conversation
keeps them in this window until explicitly saved. The same encryption/storage
boundary covers message metadata. No separate model call, embedding, summary or
hidden reasoning is used to create a checkpoint. Disk errors preserve the task
in the window and report that Save needs retrying.

By default, a conversation retains **8** resumable tasks for **14 days**. Change
these limits in **Settings → How Cursiv answers** (1–20 tasks; 1–90 days). Expired/excess
checkpoint metadata is removed when the chat is accessed and the next snapshot
persists that cleanup. Dismissal and expiry retain the original transcript text.
The resume context has an 8,000-character cap, with an additional route-budget
check; oversized contexts ask you to select a shorter excerpt. Missing/stale
context cannot restore hidden model state. No repeated scientific text is
automatically deleted; exact repeated paragraphs are recorded in metadata.

In **Settings → How Cursiv answers**, optionally choose **Professional**, **Playful**, or
**Sassy**, set humor frequency, and choose **Concise**, **Balanced**, or **Detailed**.
The default keeps the current style without adding personality instructions.
Existing learned rules remain. The current request for more or less detail
takes priority. Humor is optional; a short topic-change acknowledgment may be
included in the next normal answer, with no extra inference request. Medical,
safety, distress and recently sensitive conversation context suppress humor.
These are bounded presentation hints, not a guarantee of real-model behavior.

Stop immediately rejects local output and signals cancellation. An opened
supported inference stream is closed on a separate thread. Remote servers can
still finish or charge for accepted requests; connection setup or uncancellable
work may retain the existing serialized model slot until it returns or times out.
The input remains usable meanwhile. An approved atomic write is allowed to finish;
Stop does not roll back a committed notebook record or interrupt its hash chain.

Manual checks: interrupt before text and mid-sentence; ask an unrelated question;
resume Task A; interrupt Task B too and select either; switch providers and verify
the displayed destination/footer; restart a saved conversation; test offline
cloud failure and retry through Resume; try an approved disposable write; check
humor disabled and suppressed during a serious discussion. Real Ollama/OpenAI/Groq
quality and server cancellation need owner testing; automated tests use mocks.
