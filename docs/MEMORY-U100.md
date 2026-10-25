# Memory you can see and steer (U100)

## What's new

- **Session notes** (`memory/session_notes.py`) — Cursiv's own CLAUDE.md for each
  conversation: goal, what was done, what was decided, what's open, the next step.
  "Done" lines come only from Cursiv's records in the conversation (a notebook save with its
  record ID, a saved memory, a file written); goal / decided / open / next are summarised
  by the local model every few exchanges and labelled as such. When a conversation is
  reopened the note goes first in the instructions and a "Picking up: …" line appears.
  Stored encrypted in `session_notes/`.
- **Suggested memories** (`memory/suggestions.py`) — the model's guesses about the person
  ("Jw prefers a warm, grounded tone…") are no longer saved silently; they wait as
  "Remember this?" with **Save / No**, and only a confirmed one is saved, through the same
  verified save as `remember …`. Things said outright are still saved directly.
- **Show my memory folder** (`memory/markdown.py`) — `memory folder` writes one `.md` per
  memory (kind, where it came from, date, ID) plus a `MEMORY.md` index, style rules and
  project summaries. On a Cursiv USB drive it's the drive's `memory-files` folder; on a
  computer, where memory is encrypted, Cursiv asks where to put a readable copy and says so.
- **Guidance files** (`core/guidance.py`) — "when I say the creek I mean North Creek" saves a
  hint in `how-i-talk.md`; `workspace map` drafts a `CURSIV.md` folder map from the
  workspace's real folders and saves it only on Save. Both are given to the conversational
  action step; the hint's meaning counts as the person's words when a proposal is checked.
  They teach words and layout only: actions, checks and the confirm card stay in code.

## A decision to review: the store is still the source of truth

The markdown folder is a **readable copy**, not where memory lives. Memory itself stays in
Cursiv's existing store (`memory_facts.jsonl` with origin tags, safety precedence, matching
by meaning and the verified save/forget paths). Changes are made with `remember …`,
`forget …` or the "What I remember" window; editing a copied `.md` file changes nothing.

Why: moving the source of truth to editable markdown would mean re-building how memory is
saved, matched, encrypted and kept from overriding safety rules, and deciding what happens
when a hand-edited file conflicts with the store. That deserves its own release and the
owner's decision, not an overnight change. A two-way sync (edit the file, Cursiv picks it
up) is the natural next step if wanted.

## Not done

- No Agents window yet; custom agents still talk only.
- Existing inferred memories aren't migrated or removed; `memory cleanup` still lists the
  misleading ones for the person to remove.
- Grouping `core/` into sub-folders (planned for U100 "if there's room") was not started.
