# Unified provider/model manager — working handoff

Starting state: uncommitted U111 on `codex/u111-reliability`, HEAD `ee9b1cf`.
Preserve that work and owner exclusions. The owner authorized commit, push and release after completion on October 30; production AI credentials remain untouched. No added agents or dependencies. All execution uses the locked
interpreter and redirected disposable homes/data before imports.

## Audit

- Existing desktop: chat_controls → chat_panel → chat completion/conversation;
  U111 model_selection pins six providers (Ollama, OpenAI, Claude, xAI, Groq, Gemini).
- All six are visible without keys, but cloud model IDs require manual entry;
  selector state is only in the panel config and is not persisted.
- Existing Automatic retains the legacy local/cloud cascade; it needs an explicit
  local-only default and separately opted-in cloud automatic mode.
- OpenRouter, LM Studio and custom endpoints are not implemented yet.
- Existing cloud adapters have distinct Gemini/Anthropic/OpenAI-compatible schemas,
  but return text/errors rather than a normalized result. Shared errors need
  provider-owned identity rather than inference from an OpenAI-compatible API shape.
- API keys use keystore DPAPI/Keychain, but legacy portable mode may store/export
  readable keys. The manager needs a strict device credential boundary and exports
  must omit AI credentials under this request (supersedes old private-copy opt-in).
- Failed output currently becomes ordinary assistant history; no retry snapshot or
  persistent requested/attempted/responding provenance is attached.
- Network gate denies off-machine sockets offline. Keep it and layer strict URL,
  redirect, credential-host and explicit cloud-data checks above it.

## Plan / status

1. Registry, typed requests/results/errors, safe persistent non-secret settings.
2. Authenticated discovery/cache/catalog/manual IDs; always-visible UI/status.
3. Provider-specific streaming adapters and strict endpoint/credential boundaries.
4. Retry/provenance integration, explicit local/cloud automatic routing, research consent.
5. Central AI Providers settings, explicit Ollama management, comparison preparation.
6. Mocked protocol/security/UI regressions, real local smoke if available, full suite,
   USB and scoped credential audit. No live cloud inference without explicit authorization.

Official API references checked: OpenAI Models/Chat Completions, Groq compatibility,
Gemini Models/generateContent, Anthropic Models/Messages, OpenRouter API,
LM Studio compatibility and Ollama API. Catalog availability is not account access.
No background command running at this initial checkpoint.

## Implementation checkpoint

Registry, typed requests/results/errors, OS-secured device credential store,
no-redirect HTTP, native Gemini/Anthropic/Ollama streams, compatible API streams,
catalog/cache/live discovery, local/cloud automatic modes, persistent header
selection, AI Providers settings and owned inference-only Retry are implemented.
The first focused run: **92 passed** (`PROVIDER-MANAGER-core.xml`), mocked APIs only.
An affected routing run was interrupted to restore the compatibility callers'
existing optimized local path while removing their implicit cloud fallback.
No live cloud request has been authorized or made.

**Owner correction:** retain the explicit USB key-export option. It is restored,
with the existing readable-key warning and separate opt-in. Device credentials
are included only in that explicitly chosen private export; normal exports omit
new keys. This instruction supersedes the initial worksheet's blanket export ban.
No owner credentials/configuration have been accessed or modified by development.

Next: desktop recovery/privacy tests, export regression checks, full suite,
source-index/docs refresh, real local smoke and scoped secret audit. Advanced
comparison/download features remain after core validation. No background command
running at this checkpoint.

Further checks: affected engine/U111/credential regressions **252 passed**;
desktop/recovery/core/credential selection **73 passed**. Receipts are under
`bench/results/PROVIDER-MANAGER-*.xml`. The first desktop/map run found a real
selection-persistence bug (fixed) and an expected stale source map (refresh due).
Command surfaces now use the manager instead of the implicit cloud cascade;
background titles/reviewers no longer upload through free-key fallback.
Ollama management supports explicit pull/progress/cancel and confirmed delete;
hardware inspection reuses the existing code. A read-only comparison preparation
API is implemented; desktop side-by-side presentation remains deferred. No live
cloud inference or actual model download/delete has been run.


## Owner release authorization — 2026-10-30

The owner explicitly authorized commit, push and release of U111 and the provider update (U112) after completion. U111 public source was recovered from the prior audit mirror with all 70/70 manifest hashes matching before version preparation. Protected main CI, USB gates, native packaging, owner signatures and secret scans remain required before publication. No release has been published at this checkpoint.

## Release candidate checkpoint

U111 merged through PR63 at 932d95d06578c73621d32565346b460fd8d26762; exact-main CI41004166516 and both tagged native builds passed. U112 final targeted checks: 294 passed (U112-final-targeted.xml), mocked cloud APIs only. Endpoint consent is bound to provider/model/URL; in-flight origin changes fail before transmitting credentials. Request budgets cover native streams; retries replay inference without redispatching writes. Local Qwen transport passed earlier; repeat against final source pending. Full tests, secret scan and U112 protected/native release gates remain. No cloud success claim is made.

## Final candidate validation

Isolated full source run: 2831 passed,15 skipped,19 passing subtests, two obsolete
test seams failed (U112-full-final.xml, retained locally). They expected an attempted
Grok label on a code-owned native answer and the superseded photo transport.
Updated behavioral assertions and native protocol fixtures passed165 affected
checks (U112-repaired-contracts.xml). Training-note conversion now also uses the
unified exact destination, consent and no-fallback path. CI will run the complete
candidate suite on Windows, Mac and Linux before merge/tag.
Real final Qwen transport and full application chat passed offline on loopback
(U112-local-final.json); the application smoke used1843 input/38 output tokens.
No cloud inference, owner-data access, model download or model deletion occurred.
Side-by-side comparison desktop UI is deferred; the read-only comparison engine
is tested. Linux or failed secure-store persistence is session-only. Live account
access and macOS Keychain require owner/platform validation and are not claimed.

Final candidate provider/source/workspace/release gates: 284 passed (U112-release-gates.xml). Anonymous U111 download/readback verified all11 files and8 owner signatures (U111-public-downloads.json). U112 source is prepared for protected CI; no live cloud success is claimed.


Website proof is deferred to the post-build publication PR, per the release runbook. PR64 included a website manifest too early and was superseded by the source-only candidate; no website guard was weakened. The subsequent self-inspection worksheet is being audited separately and additional changes remain uncommitted for owner review.

Final candidate provider/source/workspace/release gates: 284 passed (U112-release-gates.xml). Anonymous U111 download/readback verified all11 files and8 owner signatures (U111-public-downloads.json). U112 source is prepared for protected CI; no live cloud success is claimed.

Final candidate provider/source/workspace/release gates: 284 passed (U112-release-gates.xml). Anonymous U111 download/readback verified all11 files and8 owner signatures (U111-public-downloads.json). U112 source is prepared for protected CI; no live cloud success is claimed.
