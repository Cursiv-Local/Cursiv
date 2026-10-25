# Operational self-knowledge (U99)

What Cursiv knows about itself, where it comes from, and what backs a claim. Written
after the U98 conversation in which Cursiv refused to draft an X post, invented product
features and privacy guarantees, denied having an updater, online services or
dependencies, and then called that denial "fully substantiated by the live report and
source code".

## Root causes (with file references)

| Failure | Cause found |
|---|---|
| Refused to draft an X post, even after "I will copy and paste it" | `cursiv_engine/codex/system_prompt.md` said Cursiv can't "make calls or send messages, so don't offer to", with nothing separating *writing* a message from *sending* one. In addition, `core/turn_policy.py` read "Without asking me any questions, **write** the single best X post…" as a per-turn ban on writing (the "without" clause ran to the full stop), so the turn ran with changes and memory disabled. `chat/response_style.drop_false_refusal` only recognised stories, poems and the like as creative requests. |
| Invented product capabilities and absolute privacy promises | Writing requests about Cursiv got no grounded list of what Cursiv does; nothing checked the result. The fact sheet (`core/cursiv_facts.md`) was stale and contradicted itself and the code: "encryption is optional and off by default" (false since U97), file writes "only with a paid key" (false since native file actions), "automatic updates", a "Guardian" that "checks messages for jailbreak attempts" (no such check exists), family letters (removed). |
| Denied the updater, online services and dependencies | Capability questions ("does Cursiv have an update mechanism?") didn't match the self-question detector (`core/selfknow._SELF_RE` had no update/online/dependency words), so they reached the general model. The updater, its signature check and the dependency list weren't in any document the model received. The live report described the provider order backwards ("paid keys … then local") and had no offline/encryption/update state, so "offline right now" was read as "no online features". |
| "Fully substantiated by the live report and source code … no correction is needed" | Nothing recorded what Cursiv actually read, and nothing checked verification claims. The self-knowledge prompt supplies a live report and source excerpts, so the model treated *being given* text as *having verified* a claim, and its own earlier answer as evidence. |
| The same post again and again | Measured on the real model: `chat/conversation.py` added **session memory** (the last 4 exchanges of the latest session, from any conversation) to every turn's instructions. With an earlier post in it, a request for "a completely new X post" reused **73%** of the old post's three-word phrases on 5 of 5 tries; without it, **0–8%** (`scratchpad` probe, qwen3:4b-instruct). Outputs were also identical across the 5 tries: Cursiv sets no sampling temperature, so this is the model's default behaviour, left unchanged. |
| A fictional announcement presented invented services as real | No label separated fiction from real features. |

## What changed

- **One capability inventory** — `core/capabilities.py`: what Cursiv supports (built in /
  optional / removed / not something it does), how each feature relates to the internet,
  the modules and tests behind it (checked to exist by `tests/test_self_knowledge.py`),
  its limits, and a live reading of its current state that returns "unknown" when it
  can't be read, never "off". Used by native answers, the self-knowledge prompt, writing
  guidance and custom agents. The fact sheet now only adds context and defers to it.
- **Capability questions answered by Cursiv, not the model** — "does Cursiv have an
  updater / support online AI / have dependencies / work offline / encryption …?"
  (`core/native_answers.py` → `capabilities.answer`). "How does …" questions keep their
  reviewed workflow answers; requests ("can you translate 'hola' …") are not intercepted.
- **An evidence log** — `core/evidence_log.py`: what Cursiv itself read or checked this
  session (source searches and reads, capability look-ups). Excerpts handed to the model
  for a question about Cursiv are recorded as *supplied*, not as an inspection. The model
  can't write to it.
- **Verification claims need a record** — `core/claim_evidence.py`: "I checked the source
  code", "verified by the live report", "the tests prove", "fully verified", "no
  correction is needed" get a "Cursiv's check" note under the answer when this answer has
  no matching record. "Have you inspected your source code?" and "you previously said … —
  check that claim" are answered from the evidence log and the capability records,
  stating plainly when an earlier answer was wrong.
- **Writing is not doing** — persona rules for drafting, writing about Cursiv (only what
  the records say, no absolute promises) and fiction; per-turn writing guidance
  (`chat/response_style.writing_guidance`); a one-time retry when a writing request comes
  back as nothing but "I don't post"; the turn-policy fix above.
- **Model-free notes** under answers that make absolute privacy promises about Cursiv
  (with the true statement and the current offline setting) and under fictional writing
  about Cursiv.
- **No session memory for writing and creative requests.**
- **Agents** — each agent's prompt states what it may use, from the inventory; questions
  about an agent's access are answered by Cursiv's code. Today agents get no tools.

## Tests and results

- Deterministic (`tests/test_self_knowledge.py`, 31 tests): the real failures as fixtures
  — acceptance tests B (updater), C (online AI with offline on), D (dependencies),
  E (internet now), F (source inspection), G (the real recheck prompt → three "False"
  corrections; the real defence → flagged), H (agent permissions), J (unknown
  capabilities), the drafting guidance and retry trigger, privacy and fiction notes, the
  turn-policy fix, and that requests aren't swallowed by capability answers.
- Live model (`tests/test_self_knowledge_live.py`, `CURSIV_LIVE=1`, qwen3:4b-instruct,
  through `chat()` with `replace_draft`, isolated data): **12/12 passed** — A (three
  writing requests, none refused), I (a new post overlaps the previous one 4%; an old
  session post 0%), fiction labelled, privacy promise corrected, and B, C, D, G, F
  through the full chat path. Results: `reports/self-knowledge-live.json`.

## Limits that remain

- The local model **still writes absolute privacy lines** ("No data leaves", "No cloud")
  in posts about Cursiv despite the instructions; the protection is the model-free note
  under the answer, not the model's behaviour.
- The verification check matches common phrasings; a paraphrase it doesn't recognise can
  slip through. It only checks whether a check happened, not whether a claim is true.
- Only the live paths above were tested; optional online providers were not exercised
  (no keys in the isolated test install).
- Sampling settings are unchanged: identical prompts can give identical answers.
- Agents get no tools yet; granting limited tools is U100 work and must use the same
  inventory.
