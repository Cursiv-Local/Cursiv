# Failures: U66 (v3.14-U66, 2026-10-18), suite 1.3

qwen3:4b-instruct, offline, no keys, run from the release tag, each case run the way the chat
window does (commands first). **132 of 133 passed (99.2%)**; accuracy on answerable questions 100%;
unsupported claims 0%; average answer 11.8 s.

U65 on the same suite: 126 of 133 (94.7%). Four of its misses are the new field calculations
(num-022 UTM, num-025 statistics, num-026 pressure, and ref-002), which U66 computes in code.
Results files: `results/U65-qwen3_4b-instruct-suite1.3.json`, `results/U66-qwen3_4b-instruct-suite1.3.json`.

| Case | What happened | Cause | Next |
|---|---|---|---|
| adv-011 (two sheets give different bleach doses) | Compared them ("Sheet B says 8 drops, which is more than the county flyer") and chose 4 drops from the EPA card, which is right; but also said Sheet A "references a standard EPA guideline", which it doesn't | Model added a justification the document doesn't contain. The check only accepts words like "differ" or "conflict", so it missed the comparison | A known-claims check against the supplied document (Phase B); widen the check's wording in the next suite |

Real failures: 1 (minor: an invented justification; the dose given was correct).
