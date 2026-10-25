# Good first issues (drafts)

Five small, self-contained tasks for a new contributor. Each says where to look, what done
means and how it's tested. Drafted 2026-10-25; the owner posts them as GitHub issues.

---

## 1. Phone notebook CSV: add the `project` column

**Why.** U100 added an optional `project` field to notebook entries (e.g. `ORION-742`). The desktop
CSV export now has a `project` column at the end; the phone notebook's export doesn't, so the two
files no longer line up.

**Where.** `website/notebook/core.js` (the CSV writer), compare `CSV_FIELDS` in
`cursiv_engine/core/fieldlog.py`. Tests: `tests/test_phone_notebook.py`, `cloudflare/tests/`.

**Done when.** The phone CSV has the same columns in the same order as the desktop one, entries without
a project leave it empty, and a test compares the two header rows.

---

## 2. A second held-out set for suggested memories

**Why.** `bench/memory/suggest_heldout.py` was used once and then two rules were written from its
misses, so it's no longer a clean test. A held-out set only means something if it was written by
someone who hasn't seen the filter. That's you.

**Where.** Add `bench/memory/suggest_heldout2.py` (copy the format: 20 messages, labelled `card`,
`none` or `safe`). Don't read `cursiv_engine/memory/formation.py` first. Run
`python scripts/suggest_bench.py --set suggest_heldout2` (the `--set` choices need one line added).

**Done when.** The file is in, the script accepts it, and the PR description has the score it got on its
first run, before anything is changed.

---

## 3. Document how to write your own profile

**Why.** The starter profiles (`cursiv_engine/agents/starters/*.md`) show the format, but nothing
explains it: the `name`, `title` and `reads:` lines, what `reads:` can contain, and why a profile can
never save anything.

**Where.** New `docs/PROFILES.md`; facts from `cursiv_engine/agents/custom.py` and
`cursiv_engine/agents/profile_context.py`. Add it to `docs/README.md`.

**Done when.** Someone who has never seen the code could write a working profile file from it, and
every claim in it matches the code (`reads:` accepts only `notebook`, `documents`, `calculations`).

---

## 4. Flag impossible degrees-minutes-seconds coordinates

**Why.** `core/science_check.py` flags decimal coordinates like `73.9°F`, but not
degrees-minutes-seconds written wrongly, such as `44°75'10"N` (there are only 60 minutes).

**Where.** `coordinate_note()` in `cursiv_engine/core/science_check.py`; the pattern `_DMS` in
`cursiv_engine/core/fieldcalc.py` already reads DMS. Tests: `tests/test_science_audit.py`.

**Done when.** Minutes or seconds of 60 or more, or degrees over 90/180, give the note; valid DMS like
`44°07'24"N 71°34'04"W` gives none; both are tests.

---

## 5. List the starter profiles in `help`

**Why.** `help` doesn't mention @field, @checker, @report, @protocol or @writer, so most people won't
find them.

**Where.** The help text (search for the `help` command in `launcher/` and `cursiv_engine/core/`), and
`tests/test_help.py`.

**Done when.** `help` shows the five profiles with one line each, taken from the profile files themselves
(`custom.starters()`), so a new starter appears without editing the help text; a test checks it.
