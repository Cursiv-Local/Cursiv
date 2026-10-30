# Cursiv 3.14-U112 — Unified AI provider and model manager

Always-visible providers and known/manual model IDs; explicit local/cloud automatic modes; exact manual routing; secure device credentials; offline and research-data authorization; owned failure recovery and provider/model provenance. The separate private USB key-export opt-in is preserved.

[Validation and limits](PROVIDER-MANAGER-HANDOFF.md).

Provider protocols are covered by mocked tests. A real Qwen3 4B loopback smoke passed with offline mode enabled. Live cloud access, macOS credential storage, and the desktop comparison view require separate validation. Text adapters never invent tool execution; native research tools keep their workspace and confirmation gates. See the AI Providers guide for setup and retry limits.

[AI Providers guide](AI-PROVIDERS.md).
