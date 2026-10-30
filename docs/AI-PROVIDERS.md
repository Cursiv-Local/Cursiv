# Choose your AI

Use the provider selector above chat. Every provider remains visible, including
ones without keys or running servers. Choose an exact model from the adjacent
list, or enter an ID from your provider. Manual requests use that selection;
failures do not switch to another model.

- **Automatic · local only** uses an available local Ollama, LM Studio or local
  custom endpoint. It never selects cloud AI. Upgrading does not enable cloud AI.
- **Cloud Automatic · opt-in** considers only providers you explicitly authorize
  in Settings → AI Providers. Keys alone do not authorize this mode. A failed
  chosen provider is reported without automatic failover.
- **Manual** means choosing a named provider and exact model ID.

Lists distinguish live discovery, cached IDs, catalog IDs and manually entered
IDs. Cached/catalog IDs do not prove current installation, provider availability
or account access. Refresh tests discovery only; it never downloads a model.
Unknown capabilities and context sizes are not guessed.

## Settings → AI Providers

Add, replace or remove credentials; test connections and refresh model lists.
Saving a key does not make a paid inference call or validate account access.
Tests list models using each provider's native API. Offline mode blocks remote
discovery, authentication checks and inference, while providers stay visible.

Ollama defaults to `http://127.0.0.1:11434`; LM Studio defaults to
`http://127.0.0.1:1234/v1`. Start the server in the relevant application.
Custom endpoints accept a display name, base URL, optional key, exact model ID
and timeout. Remote URLs require HTTPS; loopback URLs may use HTTP. Locality
comes from URL validation, not a user label. Redirects are rejected and changing
a custom endpoint removes its saved key. Do not use an endpoint you do not trust.

Windows credentials use DPAPI in device storage; macOS uses Keychain. If secure
storage fails or is unavailable, a new key lasts for this process only. Cursiv
does not save that key as plaintext desktop configuration. Existing older keys
remain readable for compatibility. Remove/replace uses a device override.

**USB option retained by owner request:** the separate “Also copy my AI keys”
checkbox deliberately exports readable credentials to a private USB copy.
Anyone with that drive can use them. This is separate from a normal data export;
without the opt-in new device credentials are not copied. Existing drive keys
are preserved. Credential containers and device routing grants are not copied.

## Privacy and recovery

Cloud generation needs a separate confirmation for that request's prompt,
conversation and relevant retrieved notebook/memory/document context. Selecting
a cloud model or adding a key does not authorize research-data sharing. Mark a
workspace local only in AI Providers to block cloud inference for it.

Errors preserve the prompt in conversation history and keep the request context
in memory for **Retry preserved request**. Errors are not assistant successes.
Retry calls inference only, never notebook/file/command dispatch. Changing the
destination requires confirmation. Partial responses are withdrawn on transport
failure; requests with uncertain cost are never automatically resent. Retry
context lasts for the current process and is scoped to its conversation,
person and workspace. Restarted conversations retain saved prompts/error metadata
but do not restore the in-memory assembled retry snapshot.

Response metadata distinguishes requested model, attempted provider, responding
provider and reported model. If no model ID was reported, the label explicitly
calls the ID requested and unverified. Native research tools still run in Cursiv
and keep their existing workspace checks and confirmation cards. The adapters handle text and embedded-image input using each native protocol. The
selected model must support vision; catalogs do not claim that an account/model
has it. Unsolicited tool calls return unsupported-capability errors without tool
execution. Generating new images uses the exact selected image model through OpenAI or a
compatible custom image endpoint. Select an image model ID, then use `image <prompt>`.
Other providers/models return an explicit unsupported-capability error. Generated
images are verified in the native cache; Retry reuses identical cached bytes. No
other image service/model is selected automatically. The older Cloudflare-specific
image helper remains in source but is outside the unified provider integrations.

## Local models and comparisons

All discovered Ollama IDs remain selectable. AI Providers supports explicitly
approved downloads with progress and cancellation, and confirmed model removal.
Downloads are blocked offline. Cancel closes the request at the next received
event; blocked I/O is bounded by the configured timeout, and server-side download
cancellation depends on Ollama. RAM/GPU/disk inspection and model-size tiers are
estimates, not performance guarantees. Qwen3 4B remains sufficient for normal
research functions.

The read-only comparison engine is prepared in `chat/provider_comparison.py`:
two to eight exact destinations, frozen logical text/context, no tool execution,
explicit cloud consent, context hash, responses/errors, timing, usage and code
verification warnings. No scores are invented. A desktop side-by-side comparison
view is deferred; this is not yet a user-facing benchmark tool.

## Validation limits

Automated provider checks use mocked APIs. Live cloud inference requires the
owner's separate authorization and valid credentials; mocked success does not
prove account/model access. Platform packaging and macOS Keychain behavior require
their respective platform checks. No dependencies were added. The owner authorized the U112 release; production AI credentials remain untouched.
