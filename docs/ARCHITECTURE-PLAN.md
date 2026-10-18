# Cursiv: phased plan (2026-10-18)

The rule above everything: **when the internet is off, Cursiv is complete. When it's on,
Cursiv gets more capabilities.** Online never makes it less private.

Each phase has to show its result before the next starts. They follow the five
things that would make someone take Cursiv seriously: reliable answers, genuine
offline operation, traceable knowledge, resilience, and a field demonstration.

| Phase | What | Goal | Done when |
|---|---|---|---|
| A | Model comparison, then Standard / Deep Think in the menu (all models under Advanced). Fix the three real benchmark failures: a time and arithmetic tool, a dose cross-check against the reference card, asking what "it" means. Re-run the six Phase 1 prompts. Run and publish the offline demo. | Reliable answers, offline | Comparison and fixes in `bench/`, Phase 1 results recorded, OFFLINE-DEMO.md |
| B | No new features. An architecture document; tests for the boundaries (only the network gate opens connections, personal memory never in an export, every outbound path checks offline mode). Split `ui/chat_app.py` into intent, routing, tools and checks. | Trust | Boundary tests in CI; chat_app.py split with no behavior change |
| C | Knowledge packs: medical, survival, science as versioned packs with source, check date, review status, checksum and a publisher signature (Ed25519; the current per-install HMAC can't prove who made a pack). Install by USB or download. | Traceable knowledge | Packs install, verify and show their source in the Knowledge window |
| D | Resilience: restarts, interrupted downloads, corrupted files, a full disk. | Resilience | A resilience test suite that passes |
| E | Someone who didn't build Cursiv uses it for a real problem and judges it. | Field demo | Written result, including what failed |
| F | Only if needed: encrypted backup with keys only the person holds; then sync of public packs; then two installations exchanging approved packs. | — | Decided after E |

## Data, three kinds
| Kind | Default |
|---|---|
| Personal memory, conversations, family letters | Stays on the computer. Never in a sync or export unless the person picks it. |
| Backups and family-shared data | Only with explicit permission, encrypted before it leaves, keys held by the person. |
| Public knowledge packs, benchmark suites, updates | Can be shared. |

## Kept separate
- Coding (Qwen Coder, DeepSeek Coder) stays its own mode, with write approval.
- Online AI (OpenAI, Anthropic, xAI, Gemini) is opt-in per provider, explained before the first request, never a silent fallback.

## Not now
Discovery and trust between strangers' installations, agent "nodes", Council / Evolve
conversions. Revisit after E. Existing pieces to build on rather than replace:
`agents/offline_queue.py`, `core/strand_federation.py` (USB packs), `core/plugins.py`
(approved-hash plugins), `core/netgate.py`.

Words in the app and on the site stay plain: "knowledge packs", "your other Cursiv computers".
