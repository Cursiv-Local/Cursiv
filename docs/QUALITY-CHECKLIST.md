# What a 95+ codebase would need

This is a readiness checklist, not a calculated rating. No score follows
automatically from line counts or a passing test run.

- [x] No production Python module above 1,200 physical lines in the application/launcher;
  a regression check enforces the budget.
- [x] Documented module boundaries, compatibility entry points and answer policy.
- [x] Deterministic findings have codes/severity; empty/failed checkers fail closed;
  one constrained rewrite maximum, with evidence rechecks.
- [x] Fixed regression replay and unchanged-suite live subset results are retained.
- [x] Shared native/provider filesystem backend protects login/key/guardian paths.
- [x] Exact restricted-turn regressions cover dispatch/lookup/retention gates,
  clean paths, execution-owned source labels and failed-tool exits.
- [x] Detected dose/reference contradictions withdraw the model instructions
  and display the original supplied reference without another model rewrite.
- [x] Honest threat model and public-claim evidence mapping.
- [ ] Replace legacy shared per-turn records with isolated explicit turn state before
  supporting concurrent chat sessions.
- [ ] Signed Windows public artifacts, verified after download.
- [ ] Signed/notarized Mac artifact and clean-machine installation evidence.
- [ ] USB kit checklist completed on two clean Windows PCs, including a full day and failures.
- [ ] Separately reviewed encryption migration covering backups and derived stores.
- [ ] Repeat stable benchmark/field results over multiple releases and environments;
  no unexplained regressions, hidden failures or unsupported readiness claims.

See [maintenance status](MAINTENANCE-HARDENING.md) for exact runs, limitations and
remaining owner actions.
