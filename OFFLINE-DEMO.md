# Cursiv offline demonstration

Run 2026-10-18 06:53 with `scripts/offline_demo.py`: a fresh copy of Cursiv, no keys, offline mode on, and every connection off this computer refused at the socket level.

Local model: `qwen3:4b-instruct`. Connection attempts off this computer: **0**.

| | What was tried | Result | Time |
|---|---|---|---|
| ✅ | Chat with the local AI model (should work) — `In one sentence, why do we rotate crops?` | as expected | 4.0 s |
| ✅ | Answer from the offline first-aid reference (should work) — `my son cut his leg and it's bleeding badly` | as expected | 9.0 s |
| ✅ | Save a memory (should work) — `remember our well is 180 feet deep` | as expected | 0.0 s |
| ✅ | Use that memory in an answer (should work) — `How deep is our well?` | as expected | 15.6 s |
| ✅ | Translate (should work) — `translate good morning, how are you? into Spanish` | as expected | 1.9 s |
| ✅ | Math from the local model (should work) — `What is 17 times 23?` | as expected | 14.4 s |
| ✅ | Status shows offline mode (should work) — `status` | as expected | 0.0 s |
| ✅ | Record a field observation (should work) — `log site: North transect; water temp 12.40 C; pH 7.2; 44.1234, -71.5678; note: turbid` | as expected | 0.0 s |
| ✅ | Field log is intact (should work) — `field log check` | as expected | 0.0 s |
| ✅ | Export the field log (CSV, JSON, GeoJSON) (should work) — `field log export` | as expected | 0.0 s |
| ✅ | Field calculation done in code (should work) — `Convert 44°07'24.4"N 71°34'04.1"W to decimal degrees.` | as expected | 17.6 s |
| ✅ | Answer "are you offline?" from the real state (should work) — `Are you offline right now?` | as expected | 7.9 s |
| ✅ | Web search is refused, not attempted (should be refused) — `search: county burn ban today` | as expected | 0.0 s |
| ✅ | Reading a web page is refused (should be refused) — `pull example.com` | as expected | 0.0 s |
| ✅ | Cursiv Cloud is not used (should be refused) — `cloud status` | as expected | 0.0 s |

**Overall: PASS**
