# Public claim to evidence

These links explain what each README claim establishes and where it stops.
Unit/integration tests use disposable data. The full U85 model run is evidence
for one fixed suite/model/configuration, not a complete product evaluation. See
[U85 verification](U85-RELEASE-VERIFICATION.md) and
[its failure review](../bench/FAILURES-U85.md) for actual checks and missed claims.

The U86 [live-test repairs](LIVE-TEST-FOLLOWUP.md) add deterministic
workflow/status/calculation replies, expandable routine evidence, short verified
notebook receipts and failure-safe demo switching. Their regression evidence is
`test_live_test_followup.py` and `test_notebook_workflows.py`, together with the
existing notebook, import, policy, rendering and portable suites. This does not
replace the published model benchmark or establish physical USB persistence.

The [native trust-boundary follow-up](NATIVE-TRUST-BOUNDARIES.md) adds
`test_native_boundaries.py`: zero-call/write assertions for blocked turns,
native feature/state replies, flow math, supplied-dose conflict refusal and
explicit full-review deferral. Read-only still permits requested reads, as the
owner specified. Bounded parser and model/safety limitations remain.

[Conversation follow-up](CONVERSATION-FOLLOWUP.md) adds exact synthetic prompts,
saved-context callback spies, quote/warning/explicit-dialogue preservation,
philosophical prompt capture and actual Qt dispatch checks. These establish
specific application paths, not subjective conversational quality or general
model accuracy. [U86 verification](U86-RELEASE-VERIFICATION.md) records release
checks; the U85 full model benchmark remains separately labeled historical data.

| Public claim | Automated evidence | Manual evidence still needed / scope |
|---|---|---|
| Offline mode blocks external connections while local inference works | `test_netgate.py`, `test_offline_process.py`, full tagged U85 local-model run with offline mode on. | Host OS/other applications are outside this gate. Test downloaded releases on clean devices. |
| Persistent, selected-fact memory | `test_memory_intents.py`, `test_autonomous_memory.py`, `test_grounded_chat.py`, `test_persistence.py`. | Does not mean every conversation detail is retained, or that model weights learn from chat. U85's passing allergy case misses the seeded fact and begins with unsafe advice; the failure review records this scorer/retrieval gap. |
| Source and action labels reflect evidence | `test_answer_check.py`, `test_honesty.py`, `test_reliability.py`, `test_verification_hardening.py`, `test_verified_state_changes.py`, `test_restricted_regressions.py`. | Heuristics are bounded; a checker/model verdict is not external fact verification. Live failures and a trust-warning false positive are retained in the maintenance report. |
| Supported restricted-turn prefixes gate retrieval, tools and automatic memory | `test_turn_policy.py`, `test_grounded_chat.py`, `test_restricted_regressions.py`. | Bounded language parser. Memory opt-outs do not disable separately persisted conversation history. |
| Detected reference/dose contradictions withdraw model instructions | `test_answer_check.py`, `test_restricted_regressions.py`. | Uses the supplied reference, not professional validation. Streaming consumers without replacement support see an explicit retraction after the draft. Undetected errors remain possible. |
| Workspace writes are real and authorized | `test_verified_filesystem.py`, `test_file_access.py`, `test_protected_mutations.py`, U91 `test_workspace_language.py` and the required workspace gate. | OS permissions/races and trusted arbitrary Python are separate boundaries. |
| Notebook chain detects edits and export signatures verify | `test_fieldlog.py`, `test_integrity_attacks.py`, `test_signing.py`, `test_notebook_integration.py`. | Does not establish observation truth, confidentiality or medical approval. |
| Portable data/workspace paths move with a kit | `test_portable_recall_curiosity.py`, `test_trust.py`, `test_usb_licenses.py`, portable filesystem tests. | Two clean Windows PCs and a full day remain unverified; see FIELD-KIT-TEST.md. |
| Fast incremental transcript rendering | `test_chat_rendering.py`, `test_crosscheck.py`; historical `CHAT-RENDERING-PERFORMANCE.md` and JSON measurements. | Total answer/check time depends on model, hardware and optional review; it is distinct from formatting latency. |
| Quiet review progress and current-turn state | `test_chat_feedback.py`, `test_background_review.py`; `CHAT-FEEDBACK.md` and controlled replay data. | Progress indicates an actual invocation, not percent complete or a truth guarantee. Configured workspace and historical notebook context are not new authorization or current file availability. |
| Notebook save/import receipts describe persisted records | `test_chat_feedback.py`, `test_notebook_integration.py`, `test_end_to_end_field.py`, `test_fieldsync.py`, `test_phone_receive.py`. | Read-back and SHA-256 checks do not prove observation truth. Imported device chains remain separate; unsigned identity and missing-photo warnings are retained. |
| Windows and early Mac artifacts exist | [U91 verification](U91-RELEASE-VERIFICATION.md), successful Windows/Mac hosted source tests, tagged frozen checks and independently hashed packages. | Owner manifests authenticate release bytes; Windows-trusted signing and Mac notarization remain pending; clean-machine installation, minimum-OS compatibility and physical USB checks remain open. |
| API-key protection on installed systems | `test_keystore.py`, `test_keychain.py`. | Portable/legacy/fallback plaintext keys can exist. Conversation/memory encryption is a separate opt-in feature from U90. |
| Optional conversation/memory encryption (from U90) | `test_data_encryption.py`; `core/vault.py`, `vault_migration.py`, `private_store.py`; [scope and recovery](ENCRYPTION-MIGRATION-PLAN.md). | Off by default, introduced in U90. Does not protect notebook data, documents/workspace files, logs, explicit exports/training data, old external copies or an unlocked hostile host. Lost passphrases cannot be recovered. |
| Research profile gates legacy personal operations (from U90) | `test_personal_surface.py`, `test_help.py`; `core/profile.py`, desktop dispatch and `personal_features.py`. | This is a feature-visibility/dispatch choice, not an OS authorization boundary. Enabling personal features retains existing credential/storage checks and data formats. |
| Supplied source labels do not depend on model wording | `test_trust_boundary_followup.py`, `test_restricted_regressions.py`, `test_reliability.py`. | Supplied memory is labeled as context; use or factual correctness is not established. Model prose remains untrusted. |
| Failed file-memory writes do not start a memory save | `test_trust_boundary_followup.py`. | A successful file write followed by a failed memory save is reported separately; no cross-store transaction is claimed. |
| Small explicit review budgets and USB key warning | `test_trust_boundary_followup.py`, existing review/USB suites. | Cross-check is a second opinion with 400 output tokens. A private USB may contain readable API keys; physical clean-PC checks remain pending. |
| Phone capture and online photo chat are distinct | Static page regression in `test_trust_boundary_followup.py`, notebook export/import tests. | Explanatory text/links are deployed and publicly checked; neither page runs full desktop AI on a phone. Actual phone hardware/pairing/photo AI was not exercised. |
| MIT license | Repository `LICENSE`. | Third-party model/component licenses are separate; portable license tests cover copied notices. |

README capability/limitation changes should update this mapping, related tests or
an explicitly uncompleted manual checklist in the same change.

## U87 native phone Help

`test_help.py`, `test_ui_redesign.py` and `test_chat_feedback.py` assert exact
phone URLs/wording, one occurrence, actual rich-text hrefs and external-link
support, with unchanged notebook records. The text is shared application code,
not a model response. No physical phone caching/import claim follows from help
text checks. [U87 verification](U87-RELEASE-VERIFICATION.md) records packaging
and actual deployed tester-page privacy/contact checks separately.

## U91 workspace and philosophical policy

**U92 live-transcript follow-up:** `test_u91_transcript_followup.py` adds
native punctuated state replies, placeholder preservation in actual Qt streaming
and final rendering, document-miss hard stops, bounded argument/context replies,
and current brief-style prompt capture across local/OpenAI/xAI/Claude paths.
Compaction tests cover repeated calls and many standing rules. Attachment and
talk-only tests retain their respective model/material and no-inspection paths.
These tests use synthetic data/fake providers; they do not establish general
model accuracy, brief-mode compliance in every live session, or a new release.

`test_feature_overview.py` covers the native “What can Cursiv do?” guide, zero
model/tool/save callbacks, restricted turns, and actual new-chat link behavior
across personal/research and setup states. Examples prefill the input; they do
not send or execute. Conversation history retains its separate save setting.

Natural file context uses confirmed receipts and unique bounded name lookup, not model save claims. `test_workspace_language.py` covers exact create/append/search/read requests and authorization; `test_workspace_release_gate.py` checks that failed or missing gates prevent tagging. `test_philosophy_policy.py` covers balanced native overviews, perspective requests, provider prompts, compaction and restricted turns. Broader model wording remains dependent on compliance; no new live-model accuracy score is claimed. [U91 verification](U91-RELEASE-VERIFICATION.md).
