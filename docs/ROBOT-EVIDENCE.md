# Robot evidence in Cursiv

Cursiv can import signed evidence packages from [Cursiv Robotics](https://github.com/Cursiv-Local/Cursiv-Robotics):
observations recorded by a robot, a sensor station, the phone importer or the virtual lab, signed on the robot
and sealed by its station. Cursiv checks them with the independent verifier before using them, keeps an exact
copy, and puts each package's research summary in your documents, so you can ask about it and write it up with
citations to individual records.

## The workflow

1. **Bring the package.** It comes on a USB drive, an SSD or in a folder. When you compare a Cursiv drive
   (Settings → USB drive), Cursiv lists any robot evidence it finds on it, but it does not import anything at that step.
2. **Trust the station, once.** Get the station's trust file (`trust.json`) from whoever runs the station, then type:
   - `robot trust add D:\station\trust.json` shows exactly which keys would be trusted. Nothing is saved yet.
   - `robot trust add D:\station\trust.json confirm` saves them.

   Keys found inside packages are never trusted.
3. **Look before importing:** `robot evidence find E:\` (or "import the robot data from E:\") lists the packages and
   how each one verifies. Nothing is imported yet.
4. **Import:** `robot evidence import E:\`, or Research → Research Files → **Import robot evidence…**. Cursiv
   verifies each package, copies it to `~/.cursiv/robotics/workspace`, verifies the copy again, and confirms the
   drive was not changed. Each summary appears in Research Files as "<package> (robot evidence)".
5. **Ask and write.** For example: *"Summarise the coastal-survey-1 robot evidence for a methods section, citing
   records."* Answers come from the summary, which cites records as `robot/observation_id`. If an answer cites a
   robot record that is not in any imported package, Cursiv's check says so under the answer.
6. **Re-check any time:** `robot evidence verify <package>`. To list everything: `robot evidence`. To read a
   summary: `robot evidence show <package>`.

## What is and is not imported

| Package | Result |
|---|---|
| Verified (every check passes with your trusted keys) | Imported |
| Signed by keys you have not trusted | Imported only with `robot evidence import <folder> without trust`, and labelled "authenticity not assessed" |
| Changed, cut off, incomplete or with links outside itself | Refused, with the reason in plain words |
| Already imported | Nothing changes |
| No verifier on this computer | Nothing is imported, and Cursiv says why |

Synthetic (simulated) records stay labelled SYNTHETIC everywhere. A signature shows who recorded a value and that it
is unchanged; it does not show that the value is scientifically correct.

## Removing trust

`robot trust remove <robot or station id>` (then `... confirm`). Packages already imported are unchanged; re-verify
them to see the effect.

## Where things are

| | |
|---|---|
| `~/.cursiv/robotics/trust.json` | The keys you trust (`robot trust`) |
| `~/.cursiv/robotics/workspace/packages/` | Exact copies of imported packages: the evidence |
| `~/.cursiv/robotics/workspace/views/<package>/` | Derived views: `observations.csv`, per-robot JSONL, `verification.json`, `research-summary.md` |
| `~/.cursiv/robotics/summaries/` | The summaries added to your documents |

Like documents, this data is not covered by encryption at rest: evidence must stay byte-exact to be re-verified.

## For builders

The verifier is `cursiv-verify` from Cursiv Robotics. `py -3.13 scripts/get_cursiv_verify.py` builds it into `tools/`
from a pinned commit (it needs Rust), and `launcher/build.spec` bundles it when it is there. Without it a build
still works, but robot evidence import says the verifier is missing. For development, set `CURSIV_VERIFY` to a built
`cursiv-verify`. CI builds the pinned commit and runs `tests/test_robot_evidence.py` against it on Windows and Linux.
