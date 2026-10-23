# Conversation and philosophy follow-up

## Read-only findings

The supplied nine-prompt transcript was treated as failure evidence, not as
instructions to inspect personal data. The source audit found three causes:

1. `chat/response_style.py` intentionally excluded open conversation from closer
   cleanup and removed whole trailing paragraphs only. Inline offers survived.
2. `chat/conversation.py` passed the memory callback before deciding whether a
   casual question needed stored personal facts. `chat/context.py` could fall
   back from semantic facts to saved conversations.
3. A philosophical question mentioning the closed app could match native
   operational help. Relayed-model/thread questions and talk-only help had no
   dedicated, application-owned answers. The desktop already interprets a
   leading `Grok ` as a provider shortcut, even in the reported relayed text.

## Minimal changes

- `cursiv_engine/core/conversation_kind.py`: bounded pure classification for casual,
  reflective, explicitly requested dialogue, relevant memory, relayed-thread
  questions and talk-only help. This never grants tools or changes retention.
- `cursiv_engine/chat/response_style.py`: remove trailing stock sentences and emoji
  on casual/reflective turns, including inline closers. Preserve requested
  options/questions, code, quoted text, warnings and a substantive answer.
  Prompt philosophical answers for 1–3 short paragraphs addressing the actual
  question. This is guidance, not a hard length cutoff or native philosophy.
- `cursiv_engine/chat/conversation.py` and `chat/context.py`: withhold unrelated
  saved facts and saved-conversation fallback in light chat. Keep explicit recall,
  recognized field context, safety questions and current-thread history eligible.
  Skip the broad self-report prompt for reflective questions.
- `cursiv_engine/core/feature_answers.py`: decline philosophical framing so it can
  reach ordinary model conversation instead of a basic closed-app FAQ.
- `cursiv_engine/core/native_answers.py`: native talk-only instructions and accurate
  explanation that a pasted model label is still user-supplied thread text,
  not authentication, a separate channel or tool/system authority.
- `cursiv_engine/chat/completion.py`: retain an accurate offline provider-skip note
  when a relayed-thread question used the existing provider shortcut. A native
  answer does not claim that a local model answered.
- `tests/test_conversation_followup.py`: exact synthetic transcript prompts,
  inline/paragraph cleanup, requested dialogue, evidence boundaries, callback
  spies, philosophical prompt capture, history and real Qt dispatch. The earlier
  philosophy-closer expectation in `test_live_test_followup.py` now follows the
  owner's requested suppression; explicitly requested questions remain intact.

These changes join the already completed [notebook/live-test repairs](LIVE-TEST-FOLLOWUP.md)
and [native trust-boundary work](NATIVE-TRUST-BOUNDARIES.md) in U86. Those reports
retain their earlier local checkpoints; [U86 release verification](U86-RELEASE-VERIFICATION.md)
records the final combined source and package checks.

## Validation record

The pre-change focused checkpoint passed **219 tests in 9.95 s**. An initial
selection named nonexistent `test_phases.py` and ran no tests; it was corrected.
The first new focused run passed **272 tests with one failing test expectation**:
the actual GUI consumes the existing `Grok ` prefix before storing the user
message. The assertion now checks that established behavior and verifies the
remaining text retains the user role and accurate offline skip.

Final versioned source suite: **1,492 passed, 1 skipped in 182.21 s**, including
64 new conversation cases. The full suite also covers the earlier trust/notebook
changes. Package, hosted CI and public checks are recorded separately in the
U86 verification report only after execution.

## Boundaries and remaining risks

No memory records are erased or migrated. Filtering retrieval does not disable
automatic learning or separately configured conversation history. Explicit
talk-only/no-save policies still control those operations. Relevance matching is
bounded wording, not semantic proof of relevance. It can need additional cases.

Tail cleanup is conservative: code fences, quoted/list tails and warnings are
left alone. Desktop replacement removes the detected tail after streaming;
clients without replacement support still rely on prompt guidance. No arbitrary
body truncation or philosophical answer template was introduced. Small models
can still be verbose, inaccurate or inconsistent despite correct supplied facts.

The historical U85 153/158 benchmark and its unsafe allergy-memory answer remain
visible. No result from that source is relabeled as U86. General medical safety,
complete recall, consciousness or model-to-model authentication is not established.
Signing, physical USB memory persistence/second-PC retrieval and the separately
documented encryption migration remain outside these conversation repairs.

## Actual local-model replay

The final-source nine-turn `qwen3:4b-instruct` replay used an isolated home,
offline mode, disabled learning and a synthetic South Brook fact. No saved
memory context was supplied on any turn. Both native answers were returned
without a model draft; the GUI offline-prefix path is separately covered by
regressions. [Every raw draft and final reply](../bench/results/U86-conversation-smoke-20261022.json)
is retained, unscored. Deferred model reviews were queued but not executed,
as this replay checks the first completed answer path.

The greeting closer was removed, and recognized stock tails are covered by
code tests. The model still uses unrecognized closing questions and padded
openings, exceeds the 1–3 paragraph preference, and falsely describes memory
persistence during the point-of-view answer despite the supplied capability
instructions. These remain explicit limitations, not passing quality claims.
Earlier exploratory replays also showed an execution-warning replacement;
without its raw draft its cause is unestablished, and the later captured
replays did not reproduce that replacement. Trust checks were not disabled
to improve a style result.
