# Chat rendering performance — 2026-10-21

## Findings before implementation

The existing `ChatPanel._render_reply()` already selects only the active reply
with a `QTextCursor`. It does **not** reformat the entire conversation. During
streaming, however, every incoming fragment immediately changed the document.
The final callback also synchronously exported and saved the whole conversation.

The initial profile placed the largest GUI stall in `save_conversation()`:
whole-document HTML export, reading existing conversation metadata, JSON encoding
and disk access. Markdown parsing itself took milliseconds. No 30-second Qt
formatting cost was reproduced in the synthetic replay.

`verify.run_pass()` can make four sequential model calls after the answer:
fill a missing assumption ledger, check, revise, and check the revision. These
are existing verification operations, not a separate formatting-only model pass.
A deterministic regression demonstrates that four-call execution path. The owner
confirmed that scrolling and controls remain responsive during the reported wait;
that supports background checking as the likely source of that particular delay.
No live model session was profiled, so its actual checking duration is unknown.

## Implementation

- Batch incoming fragments with a 40 ms GUI timer. Flush before completion,
  replacement, errors, cancellation, images and file-write confirmation.
- Incrementally format completed paragraphs. Incomplete backtick/tilde fenced
  blocks and the unfinished paragraph remain literal text until complete.
  Finished prefixes stay in the document; only the active tail changes.
- Resolve cross-paragraph Markdown, reference links, tables, lists, status chips
  and collapsed reasoning/check details in one final active-message parse.
  Cache the text/theme/document revision to skip an unchanged final parse.
- Notify the GUI when generation ends and checking begins. Finish formatting
  the visible draft immediately, including its last paragraph, and display
  **Checking the answer…**. Later corrections still replace that same message.
- Keep the live `QTextDocument` as the cache for displayed history. No automatic
  `setHtml()`/`setMarkdown()` replacement of the full transcript is introduced.
  Opening a conversation, empty-state display and an explicit theme change
  retain their existing full-document operations.
- Cache the HTML export prefix and export only newly appended blocks for the
  next autosave. Invalidate the prefix if older content changes. Seed it from
  saved HTML when opening a conversation. Strip Qt clipboard fragment markers
  so reopening a cached export preserves all preceding messages.
- Hand immutable message copies and HTML strings to one ordered save worker.
  Stream JSON to the existing temporary file, then replace the existing JSON
  file. The storage fields and history representation remain unchanged.
  Explicit save/open/rename/delete waits for queued saves; normal exit drains
  them. Save errors remain visible, trigger the existing leave confirmation,
  and can be retried with Save. A storage lock prevents a delayed AI title or
  manual rename from overwriting a newer queued snapshot.
- Preserve scroll position and selection when reading older messages, and
  continue following the bottom when the reader was already there.

All Qt document/widget operations remain on the GUI thread. An early candidate
that exported a detached Qt fragment on a worker crashed an isolated test and
was removed. The final worker handles Python data and disk access only. The
measured parsing cost did not justify adding a background Markdown parser or
another Markdown-to-HTML conversion. Qt's existing Markdown renderer is retained.

There are no new model requests, dependencies, frameworks, network permissions,
memory migrations, or changes to verification decisions. The existing checks
can still take seconds. The visible draft no longer waits for them to format.

## Benchmark method

`scripts/benchmark_chat_rendering.py` uses a disposable home and application-data
folder, synthetic content and no model/backend/title requests. It exercises the
actual panel, Qt document, streaming signals and conversation writer. The viewport
is 1100×800, offscreen. Each run preloads 10, 100 or 1,000 rich-text messages and
streams an 898-character response in 16-character fragments every 8 ms.

The response includes headings, bold/italic text, an ordered list, a table, a
fenced code block, a quotation, a link, an assumption ledger and a provider footer.
Three repetitions run per history size; the tables show their medians, including
the first run. Baseline source is the pre-change isolated snapshot of `4d24ffe`
plus the already pending Saved Notes work. Optimized source is the working tree
on `codex/chat-rendering-performance`. The measurements ran without regression
tests running concurrently, on Windows with Python 3.13.

Definitions:

- **End → render:** final source token emitted to the first complete draft render.
- **End → ready:** final token to input controls being enabled. Baseline includes
  synchronous autosave; optimized includes the background-save handoff.
- **End → persisted:** final token to the save finishing. Background work is
  measured separately; rendering completion does not mean the disk write finished.
- **Markdown CPU:** total elapsed time inside Qt Markdown parsing calls during
  the entire stream, including incremental parsing and the final parse.
- **GUI gap:** p95/max gap in a 5 ms GUI heartbeat, observed through disk completion.
- **Memory:** native process working set (Python + Qt), sampled every 5 ms by a
  separate sampler. Peaks are sampled estimates, not allocator-exact bounds.
- **Rebuilds:** full transcript `setHtml()`/`setMarkdown()` calls during the measured
  turn. Initial history loading is outside the measured interval.

This isolates rendering and saving; model generation and real verification time,
the full main window/sidebar, startup, conversation loading and theme switching
are outside this replay. An installed-app timing claim requires a new installer
and an on-device check. No installer was built in this task.

## Before → after measurements

All timings below are milliseconds.

| History messages | End → render | End → ready | End → persisted | Markdown CPU |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 16.5 → 14.3 | 59.0 → 18.7 | 59.0 → 53.6 | 1.46 → 1.72 |
| 100 | 14.3 → 15.4 | 103.9 → 30.4 | 103.9 → 96.6 | 2.11 → 2.05 |
| 1,000 | 26.6 → 18.0 | 493.2 → 71.5 | 493.2 → 349.1 | 5.36 → 2.05 |

| History messages | GUI gap p95 | GUI gap max | Document edits | Full-document rebuilds |
| ---: | ---: | ---: | ---: | ---: |
| 10 | 8.3 → 10.3 | 51.8 → 14.5 | 67 → 12 | 0 → 0 |
| 100 | 8.4 → 9.9 | 96.6 → 21.3 | 67 → 12 | 0 → 0 |
| 1,000 | 9.3 → 10.3 | 487.9 → 65.4 | 67 → 12 | 0 → 0 |

| History messages | Peak working set, MiB | Working-set growth during turn, MiB |
| ---: | ---: | ---: |
| 10 | 57.1 → 57.7 | 0.57 → 0.57 |
| 100 | 68.5 → 68.9 | 4.45 → 2.75 |
| 1,000 | 166.8 → 173.2 | 32.54 → 25.51 |

Incremental rendering uses 8–9 small Markdown parses instead of one final parse.
Total parsing time remains small. The number of document edits falls about 82%.
The export cache increases resident memory: the 1,000-message peak rises about
6.4 MiB. It avoids repeated full Qt exports; streaming JSON reduces temporary
encoding allocations. A complete cached HTML prefix is still linear in history
size, and disk files continue to contain the full conversation.

The under-250 ms goal is met for both rendering and readiness in this corpus.
The p95 heartbeat gap is slightly higher, while the worst stalls fall sharply.
These are bounded synthetic results, not a guarantee for every machine, very
large reply, slow storage device, or model verification request.

### Controlled checking-delay experiment

A second replay inserts an explicitly simulated 1,000 ms pause after the final
source token. No model is called. With 10 messages and three repetitions:

| Metric | Before | After |
| --- | ---: | ---: |
| Final token → visible draft formatted | 1,015.5 ms | 14.8 ms |
| Final token → input ready | 1,064.4 ms | 1,013.7 ms |

This demonstrates separation of formatting from checking. It does not claim that
verification itself became faster. A correction can still arrive after checking;
its active message is then formatted again as required.

## Raw measurements and reproduction

- [Baseline, 10/100/1,000 messages](../bench/results/chat-rendering-20261021-before.json)
- [Optimized, 10/100/1,000 messages](../bench/results/chat-rendering-20261021-after.json)
- [Baseline, simulated check pause](../bench/results/chat-check-delay-20261021-before.json)
- [Optimized, simulated check pause](../bench/results/chat-check-delay-20261021-after.json)

From the repository root with Python 3.13/PyQt6 installed:

```powershell
py -3.13 -B scripts/benchmark_chat_rendering.py --output chat-rendering.json
py -3.13 -B scripts/benchmark_chat_rendering.py --counts 10 --check-delay-ms 1000 --output check-delay.json
py -3.13 -B scripts/benchmark_chat_rendering.py --profile --repeats 1
```

Run baseline and optimized copies sequentially, with the same benchmark script
and no competing tests/model jobs. Generated reports contain only synthetic text
and performance measurements. Do not time a real conversation by exporting
private prompts into a report.

## Regression coverage

`tests/test_chat_rendering.py` covers batched delivery, GUI-thread operations,
incomplete and nested fences, rich Markdown, tables/reference links, cached final
renders, unchanged history at all three sizes, replacement drafts, text selection
and copying, scroll preservation/following, cancellation/errors, literal commands,
export/reopen equality, cache invalidation, theme switching, images, background
save handoff, ordering, rename/delete, delayed titles, write failures/retry, and
formatting before answer checks finish. The original UI, verification, revised
draft and Saved Notes tests also run.

The complete suite result and final scope review are recorded in `HANDOFF.md`.
