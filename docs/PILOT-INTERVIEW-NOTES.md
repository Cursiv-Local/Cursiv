# Pilot interview notes

Briefing for a video call with a research group that might pilot Cursiv. Every number here comes
from a file in this repository, named next to it, so you can open it on screen if asked.
As of v3.14-U71 (2026-10-18).

---

## 1. The 30-second version

Cursiv is an AI assistant that runs entirely on a laptop, with the internet blocked if you want,
built for field research. It keeps a tamper-evident field notebook, does field calculations in
code instead of letting the AI guess, answers from your own protocols with page numbers, and labels
every answer with where it came from. We measure it with a fixed 153-question test after every
release and publish every failure. It is free and open source. What we don't have yet is a real
field season with a research team. That is what the pilot is for.

---

## 2. What it is

- A Windows desktop app. The AI model (qwen3 4B Instruct) runs on the laptop through Ollama,
  a free open-source engine. No account with any AI company is needed.
- Runs from an installer or from a USB drive / SSD that holds the app, the engine and the model
  (about 30 GB; a 64 GB drive is enough). Nothing is installed on a laptop when run from the drive.
- Free, MIT licence, source on GitHub: github.com/winklersllc2026-bit/Cursiv.
- Made by Joshua Winkler. Built and tested on an ordinary laptop (i5, 32 GB RAM, 4 GB RTX 2050).

---

## 3. What it can do, and how

| Capability | How it works | Where to check |
|---|---|---|
| **Local only** | Offline mode refuses every connection off the laptop at the socket level, for the whole program. The header says *LOCAL ONLY · internet blocked*. | `PRIVACY.md`, `OFFLINE-DEMO.md` |
| **Field notebook** | Observations saved exactly as typed (12.40 stays 12.40), with site, coordinates, sample ID, observer, time. Append-only: a correction is a new entry with a reason; the original stays. Every entry carries a SHA-256 fingerprint chained to the previous one, so a changed, removed or reordered entry is detected. The AI never writes to it. | `core/fieldlog.py`, `field log check` |
| **Sample IDs** | Generated per site and day (NT-20261018-001); per-sample history; printable labels. | `field log sample <id>` |
| **Exports** | CSV, JSON (everything, including corrected entries), GeoJSON, a printable field report (summary by site, every entry with its fingerprint, corrections with reasons). | Field Notebook → Export / Report |
| **Team sync without internet** | Each laptop shares its log to a USB stick or shared folder; others import it. Each laptop's chain is kept separately. A changed or cut-off copy is refused; differing histories are kept side by side and reported, never silently merged; the same sample ID on two laptops is reported. Only the field log moves. | `core/fieldsync.py`, `tests/test_fieldsync.py` |
| **Calculations in code** | Unit conversions, degrees-minutes-seconds, UTM, distance and bearing between GPS points (Vincenty, WGS84), dilutions (C1V1 = C2V2), mean / SD / 95% CI, clock times including 24-hour, bleach doses for water. The model is given the computed result, and the answer is checked against it. | `core/fieldcalc.py`, `core/calc.py` |
| **Your documents** | Import PDFs or text (protocols, SOPs, permits). Answers quote the page; a page the answer cites that wasn't given gets a note. "Answer only from my documents" refuses anything they don't cover (except emergencies). If you ask about "our protocol" and nothing matches, it says it searched and found nothing. | `core/documents.py` |
| **Offline reference** | 112 entries (first aid, survival, science). The matching card is shown word for word above the answer, with its source and date. | `docs/REFERENCE.md` |
| **Source on every answer** | A line written by Cursiv (not the AI) from what it actually gave the model: offline reference, your documents (pages), Cursiv's calculations, web results, saved memories, or *model knowledge (not checked against a source)*. | any answer |
| **Checks after the answer** | A second pass looks for unsupported claims, changed numbers, and doses that don't match the card; an answer that says "yes, safe" and then "don't go" gets a warning on top. Claims to have searched databases that weren't searched get a note. | `core/verify.py`, `core/answer_check.py` |
| **Works when the AI engine fails** | It says so, then gives what it has without the model: the calculation, the reference card, the matching document pages. | `chat_app._without_model` |
| **Phone notebook (new, not yet field-tested on phones)** | Record on a phone with no signal; everything stays on the phone; one file goes to the laptop by USB, AirDrop or Quick Share and is imported with the same checks (same format, fingerprints, the phone's own signature). Storage on phones isn't proven yet: send daily. | `docs/PHONE-NOTEBOOK.md` |
| **Demo with sample data** | `demo` loads a sample stream survey and protocol, kept apart from real records. | `docs/FIELD-DEMO.md` |

---

## 4. How we get the numbers

### The truth benchmark (accuracy)
- **153 fixed questions** in 9 categories: numerical 35, general 21, adversarial 20, reasoning 17,
  reference 17, unknown 13, safety 12, memory 10, ambiguous 8. (`bench/truth_cases.py`)
- **Scored by code, not by an AI judge.** Each question has checks: the right number within a
  tolerance, required phrases, phrases that would mean an invented or unsafe claim, whether it
  admits it can't know, whether it asks when the question is unclear. (`bench/scoring.py`)
- **Run on a clean copy**: fresh install, empty home folder, no keys, no memories, offline mode on.
- **Frozen per version.** The questions and checks are hashed. A check changes only if it was
  wrong, the reason is written down (`bench/SUITE.md`), and older releases are re-run on the new
  version. We never change a question because a release failed it.
- **Every failure gets a written cause** (`bench/FAILURES-suite1.4.md`), including the ones that
  are the checker's fault.
- Categories that matter for the pitch: *adversarial* = false premises, made-up studies, two
  sources that disagree; *unknown* = questions it cannot know (a neighbour's name, tomorrow's price);
  *safety* = emergencies where it must say call 911, not give unsafe advice.

### Offline proof
- `scripts/offline_demo.py` runs 15 tasks on a fresh copy with every outbound connection refused,
  and counts connection attempts using Python's audit hook (it sees every socket and DNS lookup the
  program makes). Result: 15 of 15 as expected, **0 attempts**. (`OFFLINE-DEMO.md`, re-run for U70)
- `scripts/net_audit.py`: a fresh install with **default settings** (offline mode off) made **0
  connections** off the laptop during real conversations (run 2026-10-18).

### Speed
- `scripts/hardware_check.py`, 120-word answer, model already loaded (`docs/HARDWARE.md`):
  4 GB graphics card **3.7 s**; processor only **13.4 s**.
- Whole answer including the check pass, averaged over the benchmark: **12.5 s** (graphics card).
  Not yet measured: the full answer time on a laptop with no graphics card (expect noticeably longer).

### Calculations
- UTM checked against an independent method (Krüger series) to within half a metre.
- Distance and bearing match the published Vincenty example (Flinders Peak to Buninyong,
  54,972.271 m) to the millimetre.
- 433 automated tests run on every change (`tests/`).

### Model choice
- Four local models on the same 40 questions (`bench/MODEL-COMPARISON.md`): qwen3 4B Instruct
  40/40 at about 10 s; gemma3 4B and llama3.1 8B 35/40; qwen3 8B "deep think" 38/40 at 50 s and
  invented a treaty. So the smallest model that passed everything is the default.

---

## 5. The numbers to quote

| | Value | Source |
|---|---|---|
| Benchmark, latest scored release (U68, suite 1.4) | **149 of 153** passed | `bench/RESULTS.md` |
| Accuracy on answerable questions | **97.0%** | same |
| Safety questions | **100%** (12 of 12) | same |
| Unsupported claims | **0.7%** (1 answer) | same |
| Says when it can't know | 95% | same |
| Previous release on the same test (U66) | 145 of 153 | same |
| Offline demonstration | 15 of 15, **0 connection attempts** | `OFFLINE-DEMO.md` |
| Fresh install, default settings | 0 outside connections | `scripts/net_audit.py` |
| Answer time | 3.7 s (GPU) / 13.4 s (CPU) for 120 words; 12.5 s average with checks (GPU) | `docs/HARDWARE.md` |
| Offline reference | 112 entries; 37 from named U.S. government sources; **0 professionally reviewed** | `docs/REFERENCE.md` |
| Automated tests | 433 | `tests/` |

Say it this way: *"On our fixed test of 153 questions it gets 149 right. It's scored by code, the
questions don't change between releases, and every miss is published with its cause."*
U69–U71 changed the interface and labelling, not how answers are produced; the test hasn't been
re-run on U71 yet.

### The four U68 misses (know them, say them)
- Said 10 days after Wednesday is Friday (it's Saturday). Day-of-week sums aren't in the calculator yet.
- Said 3 of 4 frogs surviving beats 60 of 100: it doesn't flag tiny samples on its own.
- Worked "250 ÷ 12.5 = 20" and trailed off before the right answer (21 quadrats).
- Invented a population ("a few dozen") for a tiny unincorporated town.
- And one passed only because of a guard: on "safe to go back on the lake 10 minutes after
  thunder?" the model opens "Yes, it's safe" every time. Since then (unreleased at the time of
  writing) Cursiv counts the 30-minute rule itself and shows "Not yet: wait about 20 more minutes"
  above the model's answer, only for questions about going back out (never for getting to safety).

---

## 6. What it cannot do (say these before they find them)

- **Not field-tested by a research team.** Everything is tested on the developer's laptop. That is the pilot.
- **No professional review** of the first-aid and survival content. 43 of 80 of those entries have
  no published source yet. Entries say so on the card, and the AI is told they're unverified. Five entries are
  held back from chat until reviewed (including an unsourced antibiotic dose and "all insects are safe if cooked").
- **The AI is small** (4 billion parameters). It's good at plain answers and following the
  reference; it is not a substitute for a domain expert, and it still makes mistakes (see above).
  The design assumes it will, which is why calculations are done in code and sources are labelled.
- **No live GPS.** Coordinates are typed or pasted. Distance, bearing and UTM are computed.
- **Photos are new and untested in the field.** The paperclip attaches photos to an entry (camera
  time and GPS kept, stored by fingerprint, exported and signed) and asks the local image model about
  a photo. The image model's reading can be wrong. Cursiv can't make images offline.
- **Voice input** exists (local speech-to-text) but hasn't been tested for field use.
- **Windows first; Mac is early.** The Mac version (Apple Silicon, macOS 12+) is built and tested automatically
  on Apple hardware at GitHub (the full test suite plus a self-test of the built app), but nobody has used it on
  their own Mac yet, and it isn't signed by Apple (first open needs "Open Anyway"). The USB drive is Windows-only.
  No Linux, tablet or phone version for field use.
- **Not code-signed.** Windows warns "unknown publisher". The SHA-256 of every installer is published
  and the installer is built from the public source at the release tag.
- **Not certified** for anything, and not a medical device. No HIPAA/clinical claims.
- **Not encryption.** The login keeps people at the keyboard out; it doesn't encrypt the disk. Use
  BitLocker for that. Saved AI keys are the exception (encrypted per Windows user).
- **Signed exports are built** (U73): each laptop has its own signing key; an export carries a
  signature over the log and every exported file, and `field log verify <folder>` checks it. A
  laptop's USB shares are signed too, so another machine can't add records under its name. There
  is no master node / network sync yet (designed: `docs/FIELD-NETWORK.md`).
- **Speed on old laptops without a graphics card** is slower (about 13 s for 120 words before checks).

---

## 7. Privacy and data (`PRIVACY.md`)

- Stays on the laptop, always: conversations, memories, field notebook, documents, login, reference, the model.
- Can leave only if someone turns it on: web search (`search:`), reading a web page, a cloud AI key
  someone saved (only used if they pick that AI, paste an image, or no local model is ready),
  Cursiv Cloud (only with no local model), update checks, Setup's one-time downloads.
- Offline mode blocks all of it. A Cursiv USB starts with offline mode on.
- No telemetry on a normal install: nothing is sent to the developer. "Report a problem" sends error
  logs only when someone clicks it. (A developer-only status ping exists but runs only if two special
  environment variables are set; offline mode blocks it too. `PRIVACY.md` lists it.)
- Team sync moves only the field log, and only to a folder or drive the user picks.

---

## 8. Getting it running

- Windows 10/11 64-bit, 8 GB RAM minimum (16 GB better), about 6 GB disk for one model.
  A 4 GB graphics card makes it about 3–4 times faster but isn't required.
- Installer: about 80 MB, installs to the user folder without admin rights; first run downloads the
  engine and model once (needs internet once).
- Field kit: Tools → Make a Cursiv USB copies everything to a 64 GB+ USB 3 drive or SSD (exFAT).
  Plug into any Windows laptop and double-click Start Cursiv; nothing installs, everything saves to the drive.

---

## 9. The pilot: what we'd propose

- **One team, one real trip or field season.** A few laptops or a few Cursiv drives.
- **One researcher per drive (or laptop), one account in that person's name**, plus one for the
  team lead, who imports everyone's logs. A drive can hold several accounts, but the notebook,
  documents and the signing key belong to the drive, not the person: one person per drive keeps
  "this export came from this drive" meaning "from this person". Sharing a drive works if they're
  short of hardware; each person then signs in as themselves and checks the Observer field.
- **We provide:** the drives or installers, setup help over video, the sample-data demo for training,
  fixes during the pilot, and a written report.
- **We'd measure** (research roadmap R10, `docs/RESEARCH-ROADMAP.md`): entries logged; errors found at
  export; answers the team had to correct or didn't trust; how often the AI engine failed; battery
  life with battery saver on; anything that didn't work offline.
- **We publish the results, including failures**, with the group's permission on what is named.
- **What we'd ask of them:** use the notebook for real entries alongside their usual method for a
  stretch (so errors can be compared), note any answer they disagree with, one short call a week,
  and a debrief.
- **Cost:** none. It's open source.
- **Their data stays theirs**: nothing leaves their laptops; we see only what they choose to send.

---

## 10. Questions they may ask, and straight answers

- **"Does anything leave the laptop?"** Not with offline mode on: every outbound connection is
  refused for the whole program, and we test it (0 attempts in 15 tasks). With defaults, a fresh
  install also made 0 connections in our audit.
- **"How do you know it's accurate?"** A fixed 153-question test, scored by code, frozen per
  version, every failure published. 149 of 153 on the latest scored release. It still makes
  mistakes, which is why numbers come from code and every answer says where it came from.
- **"What if it makes something up?"** Several layers: it's told to say when it doesn't know, and
  the test checks that (95–100%); a check after each answer flags claims the evidence doesn't
  support; claims to have searched something that wasn't searched get a note; the source line shows
  when an answer is just model knowledge.
- **"Can it replace our protocol / field guide?"** No. Import your protocol and it answers from it,
  with pages. It doesn't replace the people who wrote it.
- **"Is the data defensible?"** Entries are append-only and fingerprinted; corrections keep the
  original and the reason; `field log check` proves nothing was altered; exports are signed by the
  laptop's own key and `field log verify` checks the signature and every file.
- **"Can several people use it?"** Each laptop keeps its own log; logs merge by USB or a shared
  folder without internet, conflicts reported, never silently resolved.
- **"What about medical content?"** Sourced from U.S. government pages where possible, dated on
  every card, and not yet professionally reviewed. We're looking for a reviewer.
- **"Why not ChatGPT?"** It needs the internet, and the data goes to a third party. Cursiv works
  where there's no signal and keeps the data on the laptop. It's also much smaller and less capable
  as a general chatbot; it's built for reliability on a narrow job.
- **"Who maintains it?"** One developer today. Open source, so the group can keep a copy of the exact
  version they used (every release is tagged and checksummed).
- **"What does it run on?"** Windows laptops; a USB drive version needs no install.
- **"Mac?"** An early version for Apple Silicon Macs. It passes the same tests on Apple hardware, but a pilot
  would be its first real use on a person's Mac. Unsigned for now.

---

## 11. The live demo

Follow `docs/FIELD-DEMO.md` (about 10 minutes): `status` → a protocol question with pages → a question
the protocol doesn't cover → distance between sites → a unit conversion → a field entry with a sample
ID → `field log check` → the field report → a first-aid question (reference card, 911 first) →
a plain question labelled *model knowledge* → `demo off`.

Before the call: offline mode on (badge says LOCAL ONLY), `demo` loaded, one throwaway question asked
so the model is warm. Share the Cursiv window, not the whole screen.

---

## 12. Don't say

- "Certified", "validated", "approved", "clinically", "HIPAA", "secure" without the specifics.
- "It never makes mistakes" or "100% accurate". Quote the measured number and the misses.
- "Field-tested". It isn't yet.
- "Reviewed by a doctor / medic". It isn't yet.
- That it has live GPS (coordinates are typed, pasted or read from a photo), or a master node / network sync.
- That Cursiv can locate or track people. It records where an observation was made; it is not a
  locating, tracking or safety tool. Teams keep their own GPS and tracking systems.
- Anything about a company, staff or customers that doesn't exist.

---

## 13. Questions to ask them

- What do you record in the field today, and on what (paper, a tablet, a spreadsheet)?
- Where does data go wrong now: transcription, lost sheets, units, sample labels, merging teams?
- How much connectivity do you have at sites? How long are trips? Power?
- What protocols or SOPs would you import?
- What would make you stop using it on day two?
- Who would be the point person, and how many laptops/people?
- What would a successful pilot look like to you?
- Any rules on software or AI tools from your institution (IT approval, data policies)?
