# Public claim to evidence

These links explain what each README claim establishes and where it stops.
Unit/integration tests use disposable data. The full U84 model run is evidence
for one fixed suite/model/configuration, not a complete product evaluation. See
[U84 verification](U84-RELEASE-VERIFICATION.md) and
[its failure review](../bench/FAILURES-U84.md) for actual checks and missed claims.

| Public claim | Automated evidence | Manual evidence still needed / scope |
|---|---|---|
| Offline mode blocks external connections while local inference works | `test_netgate.py`, `test_offline_process.py`, full tagged U84 local-model run with offline mode on. | Host OS/other applications are outside this gate. Test downloaded releases on clean devices. |
| Persistent, selected-fact memory | `test_memory_intents.py`, `test_autonomous_memory.py`, `test_grounded_chat.py`, `test_persistence.py`. | Does not mean every conversation detail is retained, or that model weights learn from chat. |
| Source and action labels reflect evidence | `test_answer_check.py`, `test_honesty.py`, `test_reliability.py`, `test_verification_hardening.py`, `test_verified_state_changes.py`, `test_restricted_regressions.py`. | Heuristics are bounded; a checker/model verdict is not external fact verification. Live failures and a trust-warning false positive are retained in the maintenance report. |
| Supported restricted-turn prefixes gate retrieval, tools and automatic memory | `test_turn_policy.py`, `test_grounded_chat.py`, `test_restricted_regressions.py`. | Bounded language parser. Memory opt-outs do not disable separately persisted conversation history. |
| Detected reference/dose contradictions withdraw model instructions | `test_answer_check.py`, `test_restricted_regressions.py`. | Uses the supplied reference, not professional validation. Streaming consumers without replacement support see an explicit retraction after the draft. Undetected errors remain possible. |
| Workspace writes are real and authorized | `test_verified_filesystem.py`, `test_file_access.py`, `test_protected_mutations.py`. | OS permissions/races and trusted arbitrary Python are separate boundaries. |
| Notebook chain detects edits and export signatures verify | `test_fieldlog.py`, `test_integrity_attacks.py`, `test_signing.py`, `test_notebook_integration.py`. | Does not establish observation truth, confidentiality or medical approval. |
| Portable data/workspace paths move with a kit | `test_portable_recall_curiosity.py`, `test_trust.py`, `test_usb_licenses.py`, portable filesystem tests. | Two clean Windows PCs and a full day remain unverified; see FIELD-KIT-TEST.md. |
| Fast incremental transcript rendering | `test_chat_rendering.py`, `test_crosscheck.py`; historical `CHAT-RENDERING-PERFORMANCE.md` and JSON measurements. | Total answer/check time depends on model, hardware and optional review; it is distinct from formatting latency. |
| Windows and early Mac artifacts exist | U84 release verification, successful Windows/Mac hosted source tests, expanded frozen full-window checks, Mac screenshots and independently hashed public packages. | Both platforms remain unsigned; clean-machine installation, minimum-OS compatibility and physical USB checks remain open. |
| API-key protection on installed systems | `test_keystore.py`, `test_keychain.py`. | Portable/legacy/fallback plaintext keys can exist. Conversations and memories are not encrypted. |
| Supplied source labels do not depend on model wording | `test_trust_boundary_followup.py`, `test_restricted_regressions.py`, `test_reliability.py`. | Supplied memory is labeled as context; use or factual correctness is not established. Model prose remains untrusted. |
| Failed file-memory writes do not start a memory save | `test_trust_boundary_followup.py`. | A successful file write followed by a failed memory save is reported separately; no cross-store transaction is claimed. |
| Small explicit review budgets and USB key warning | `test_trust_boundary_followup.py`, existing review/USB suites. | Cross-check is a second opinion with 400 output tokens. A private USB may contain readable API keys; physical clean-PC checks remain pending. |
| Phone capture and online photo chat are distinct | Static page regression in `test_trust_boundary_followup.py`, notebook export/import tests. | Explanatory text/links are deployed and publicly checked; neither page runs full desktop AI on a phone. Actual phone hardware/pairing/photo AI was not exercised. |
| MIT license | Repository `LICENSE`. | Third-party model/component licenses are separate; portable license tests cover copied notices. |

README capability/limitation changes should update this mapping, related tests or
an explicitly uncompleted manual checklist in the same change.
