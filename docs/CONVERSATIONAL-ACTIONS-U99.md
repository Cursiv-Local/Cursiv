# Conversational actions (U99)

Say it normally; Cursiv works out the action. The model never acts.

## How it works

1. Exact commands (`log site: …`, `remember …`, `file read …`, `workspace …`, `offline on`)
   still go straight to Cursiv's native routes, with no model.
2. A message they don't recognise that *might* be an action (a cheap pattern check, so plain
   chat never waits for this) goes to the **local** model only — never an online one — with
   a fixed list of actions (`cursiv_engine/core/intent.py`).
3. The model can only answer with one of Cursiv's own canonical commands and its details.
   Cursiv checks the proposal against the person's words: every number must be one they
   wrote, file names and folders must be ones they named, files must be inside the
   workspace, the text to write must be theirs, and "forget" must be a request to forget.
4. Read-only actions (search or average the notebook, read or list a file) run at once,
   shown as "Understood as: …". Anything that changes something — a notebook entry, a
   memory, a file, the workspace, offline mode — waits on a card with **Save / Edit /
   Cancel**, and Save runs exactly the command on the card through the same native code
   that gives receipts. A proposal that fails a check shows why and offers only **Edit**.
5. "Work in my Field Data folder" is matched to a real folder (home, Documents, Desktop,
   OneDrive) and confirmed as `workspace <path> and files on`.

Memory recall ("what do you remember about Sam?") isn't in the list: memory's own route
answers it first.

## Measured (qwen3:4b-instruct, this PC, no data executed)

| Set | Cases | Right action | Offered correctly | Traps that produced an offer | Median time |
|---|---|---|---|---|---|
| Held-out (`bench/intent/heldout.py`, never used for tuning) | 50 | **94.0%** | **90.3%** | **0 of 19** | 1.7 s |
| Development (`bench/intent/phrasings.py`, used while tuning) | 88 | 97.7% | 96.8% | 0 of 25 | 1.8 s |

Publish the held-out row. Every held-out miss went the safe way: no action was proposed and
the message was answered as ordinary chat. Re-run with
`python scripts/intent_bench.py --set heldout` after any change to the prompt or checks.

## Limits

- A 4B model sometimes chooses "none" for a plainly worded observation ("Mud Flats salinity
  12 ppm, low tide"); the person then says it more directly or uses `log …`.
- A request it misreads is shown on the card before anything happens; it can't save,
  change or delete anything on its own.
- Folder matching looks one and two levels deep in the usual places; otherwise it asks for
  the full path.
