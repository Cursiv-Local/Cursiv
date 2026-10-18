# Phase 1: results, causes and fixes

The Phase 1 conversation (15 messages, the owner's original U62 session) replayed in
order on fresh, offline copies with no saved memories, using `scripts/phase1_replay.py`.

- Original answers, unedited: [ORIGINAL-U62.md](ORIGINAL-U62.md)
- Replays: [RERUN-7f28f61.md](RERUN-7f28f61.md) (during the fixes), [RERUN-U65.md](RERUN-U65.md) (release v3.14-U65)
- A replay with someone's saved memories can be run with `--memory`; those outputs aren't committed.

Status: **fixed** = the U65 answer is right and a test covers the cause. **Open** = still wrong in U65.

| # | Message | Defect in U62 | Cause | Fix | U65 | Test |
|---|---|---|---|---|---|---|
| 1 | Winterize a chicken coop | Heat lamp advice, tarp over the coop, "the user is managing a farm", ledger, "practice question" offer | No reference entry (model only); saved guesses recalled as facts; persona asked for a ledger on every answer | Ledger only when needed; learned memories marked as guesses and repaired; no follow-up offers | **Open**: no ledger or invented situation, but still suggests a heat lamp and closing vents in cold snaps | `test_learner_skips_cursivs_own_words`, `test_one_time_repair_of_learned_memories` |
| 2 | Well pump vs city water table | "a setup like the one you're managing", overgeneralised "safer for most homes", ledger | Saved guesses recalled; persona ledger rule | As 1 | Fixed: a plain table, no invented situation | as 1 |
| 3 | 17% of 2,450 | Correct (416.5) but "feed costs" assumed and a ledger | As 1 | As 1; arithmetic checked in code | Fixed | `test_thousands_separators_in_shown_arithmetic` |
| 4 | Purify creek water | Old card (unsourced, iodine and SODIS numbers), "99.9%", "only proven way" | Hand-written entry | Entry rewritten from the EPA page, source on the card | Fixed: EPA steps, chemicals warning | `test_water_entry_has_epa_doses_and_limits` |
| 5 | Son's leg bleeding badly | **"Do NOT use a tourniquet unless trained", "Do NOT use a bandage"** under a card that recommends both | Unsourced card; nothing checked the answer against it | Card from Stop the Bleed; a check flags advice against a card's steps; medical emergency handled separately from a crisis | Fixed: press, pack, tourniquet 2-3 in above, note the time | `test_answer_that_contradicts_the_bleeding_card_is_flagged`, `test_heavy_bleeding_is_a_medical_emergency_with_the_bleeding_card` |
| 6 | Husband hypothermia | Rigid temperature bands; the check called "You said your husband fell in the creek" unsupported | Unsourced card; hypothermia not recognised as an emergency, so the slow check ran | Card from CDC; hypothermia is a medical emergency (no slow check) | Fixed: CDC steps, CPR if no pulse | `test_hypothermia_entry_follows_cdc_without_temperature_bands`, `test_more_medical_emergencies_are_recognised` |
| 7 | Neighbor's name | Fine; odd "even if you tell me" | Model wording | Not changed | Fine | `unk-001` (benchmark) |
| 8 | Fake 1987 study | Claimed it wasn't in "any public database ... I have access to"; the check said "missing ledger" although one was there | Model claim; ledger reader missed "✅ Known:" | Ledger reader fixed; a check flags claimed database searches | **Partly open**: says it doesn't know, but ends "No record of such a study in verified public databases", a check that never happened; the claims check doesn't catch this wording yet | `test_claimed_database_search_is_flagged_when_nothing_was_searched` |
| 9 | Einstein relativity Nobel | Said relativity "came later"; invented a quote that Einstein was "not satisfied" with relativity | Model knowledge | None specific (model unchanged); answers now shorter and without "bonus facts" | Fixed in this run: correct, no invented quote | `adv-` cases (benchmark) |
| 10-11 | Remember the well depth, then ask | The answer was only a Known/Inferred list, never a direct answer | Persona ledger rule | Ledger only when needed | Fixed: "Our well is 180 feet deep." | `test_a_note_and_offline_mode_survive_a_restart` |
| 12-14 | offline off / on, search | Worked | — | Message now says "Cursiv won't connect to the internet" (what's enforced) | Fine | `test_netgate.py` |
| 15 | Translate into Spanish | Labelled "Translate → English" | The parser didn't handle the language named first | Parser fixed | Fixed: "English → Spanish". "hice" is grammatical; "creé" would be a better word | `test_translate_with_the_language_first` |

Also found by the replays and fixed: pasted text losing its line breaks; "1. Step" with its text on the next line shown as extra steps; a correct sum ("2,450 × 0.17") flagged wrong and that note repeated under the next answer; offers to "help find the nearest hospital"; a late-night break note (now a setting).

## Open

1. **Coop advice (1):** needs a sourced entry. Federal sources on poultry housing and barn fire safety are still to be found; university extension guides are copyrighted.
2. **Claimed database check (8):** extend `answer_check.unsupported_actions` to "no record ... in (verified|public) databases".
