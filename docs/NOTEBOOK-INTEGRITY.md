# Field notebook integrity (U102)

The notebook (`core/fieldlog.py`) is append-only: each entry stores the SHA-256 fingerprint of the one
before it, and `field log check` (code, never a model) re-checks every fingerprint and link.

## What a passing check shows, and what it doesn't
It shows no entry was changed, removed, inserted or reordered **after it was recorded**. It doesn't show
who made the entries, or that the whole notebook wasn't rebuilt from scratch with new fingerprints. That's
what signed exports and shares are for (device keys, `core/fieldsync.py`). Cursiv says this whenever the
check passes, and calls the notebook "tamper-evident", never "tamper-proof".

## Scenario results (`tests/test_notebook_integrity_matrix.py`, all passing)

| # | Scenario | Result |
|---|---|---|
| 1 | Valid records | verify passes |
| 2 | Correction | a new linked entry; the original is kept and verifies |
| 3 | A record deleted from the file | "doesn't follow the entry before it" |
| 4 | A historical value edited | "was changed after it was recorded" |
| 5 | Two records swapped | reported |
| 6 | A record duplicated | reported |
| 7 | A link broken | both the link and the edit reported |
| 8 | Power cut mid-entry | only that entry lost, reported; the next entry starts on a new line |
| 9 | Four writers at once (one Cursiv) | 44 entries, unbroken chain, numbers 1-44 |
| 10 | Corrupted bytes | the line reported; the rest still read, never "empty" |
| 11 | Crash during a save | leftover temporary file ignored; notebook reads and verifies |
| 12 | Conflicting imports | both kept, neither chosen (`tests/test_fieldsync.py`) |
| 13 | Export and re-check | a signed export verifies; a changed export doesn't |
| 14 | Whole chain rebuilt consistently | **verifies** (the stated limit) |

No notebook code needed changing in U102: every scenario was already handled. Two Cursiv windows can't
write at once (single-instance lock and data lease).
