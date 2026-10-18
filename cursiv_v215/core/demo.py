"""
Field demo: sample data for showing Cursiv to a research group, kept apart from
real records.

While the demo is on, the field notebook and the document library use their own
folder (~/.cursiv/demo/); the person's real notebook and documents are untouched
and come back when the demo is turned off. Every sample entry, the sample protocol
and the window badge say "sample data". Memories, keys and settings aren't touched.

    demo / load demo    turn the demo on with fresh sample data
    demo off            back to the real notebook and documents (sample data removed)
    demo questions      things to try, in order
"""
from __future__ import annotations

import shutil
from pathlib import Path

DEMO_KEY = "demo_mode"
OBSERVERS = ("Sample observer A", "Sample observer B")

# A stream water-quality survey: three sites along one stream, written for the demo.
SITES = {
    "Upper Brook (site A)": (44.1234, -71.5678),
    "Mill Pool (site B)": (44.1300, -71.5600),
    "Lower Ford (site C)": (44.1371, -71.5512),
}

ENTRIES = [
    # site, observer, sample?, measurements, note
    ("Upper Brook (site A)", 0, True, [("water temp", "8.40", "C"), ("pH", "7.21", ""),
                                       ("conductivity", "48", "uS/cm"), ("dissolved oxygen", "11.2", "mg/L")],
     "Clear water, riffle, moss on rocks. Bottle rinsed three times."),
    ("Upper Brook (site A)", 1, False, [("air temp", "11.5", "C"), ("turbidity", "1.8", "NTU")],
     "Overcast, light wind."),
    ("Mill Pool (site B)", 0, True, [("water temp", "9.10", "C"), ("pH", "7.05", ""),
                                     ("conductivity", "61", "uS/cm"), ("dissolved oxygen", "9.8", "mg/L")],
     "Slow pool below the old dam, leaf litter, some foam at the edge."),
    ("Mill Pool (site B)", 1, False, [("turbidity", "4.6", "NTU")], "Tannin colour; Secchi disk visible to the bottom."),
    ("Lower Ford (site C)", 0, True, [("water temp", "9.60", "C"), ("pH", "6.94", ""),
                                      ("conductivity", "74", "uS/cm"), ("dissolved oxygen", "9.1", "mg/L")],
     "Below the road crossing; sand bar on the left bank."),
    ("Lower Ford (site C)", 1, False, [("turbidity", "7.9", "NTU")], "Runoff channel from the road enters 20 m upstream."),
]
# One entry is corrected afterwards, to show that corrections never overwrite.
CORRECTION = ("Mill Pool (site B)", "pH", "7.15", "pH meter recalibrated at the truck; first reading drifted")

PROTOCOL_NAME = "SAMPLE Stream Protocol SP-1 (demo).txt"
PROTOCOL = (
    "SAMPLE PROTOCOL FOR DEMONSTRATION ONLY. Written for the Cursiv field demo; not any laboratory's procedure.\n\n"
    "Stream Sampling Protocol SP-1, revision 3.\n\n"
    "1. At each site record water temperature, pH, conductivity and dissolved oxygen with the multiprobe, "
    "and turbidity with the turbidimeter.\n\n"
    "2. Calibrate the pH meter with pH 4 and pH 7 buffers every morning, and again if a reading drifts by more "
    "than 0.1 in two minutes.\n\n"
    "3. Rinse each sample bottle three times with stream water before filling. Label every bottle with the "
    "sample ID, site, date and time.\n"
    "\f"
    "4. Preservation. Keep water samples on ice at 4 degrees C. Do not freeze them. Samples must reach the lab "
    "within 24 hours of collection.\n\n"
    "5. Nitrate samples are acidified with 2 mL of sulfuric acid per liter.\n\n"
    "6. Safety. Do not sample alone. Do not enter the water above knee depth or when it is rising. Stop work "
    "when thunder is heard, and wait 30 minutes after the last thunder before returning to the water.\n"
)

QUESTIONS = [
    ("Local only", "status"),
    ("Sources, from the protocol", "How long can our water samples stay on ice before they reach the lab?"),
    ("Not in the protocol", "What does our protocol say about phosphorus samples?"),
    ("Distance between sites", "What is the distance and bearing from 44.1234, -71.5678 to 44.1371, -71.5512?"),
    ("Calculation in code", "Convert 9.6 C to F"),
    ("A field entry", "log site: Upper Brook (site A); sample: auto; water temp 8.6 C; pH 7.18; note: demo entry"),
    ("Sample history", "field log sample <ID from the entry above>"),
    ("Integrity check", "field log check"),
    ("The report", "field report"),
    ("Offline reference (safety)", "My partner slipped on the rocks and cut his leg, it's bleeding badly"),
    ("Model knowledge, labelled", "What is a riffle in a stream?"),
]


def root() -> Path:
    return Path.home() / ".cursiv" / "demo"


def active() -> bool:
    try:
        from cursiv_v215.chat import keys
        return keys.saved_key(DEMO_KEY) == "on"
    except Exception:
        return False


def _set(on: bool) -> None:
    from cursiv_v215.chat import keys
    from cursiv_v215.core import documents
    keys.store_key(DEMO_KEY, "on" if on else "")
    documents._passages.cache = None          # the library folder just changed


def load() -> dict:
    """Turn the demo on with fresh sample data. Returns what was loaded."""
    from cursiv_v215.core import documents, fieldlog
    shutil.rmtree(root(), ignore_errors=True)
    _set(True)
    made = []
    for site, who, with_sample, meas, note in ENTRIES:
        lat, lon = SITES[site]
        e = fieldlog.add(observer=OBSERVERS[who], site=site, lat=lat, lon=lon, location_source="typed (sample data)",
                         measurements=[{"name": n, "value": v, "unit": u} for n, v, u in meas],
                         note="SAMPLE DATA. " + note,
                         sample_id=fieldlog.new_sample_id(site) if with_sample else "")
        made.append(e)
    site, name, value, reason = CORRECTION
    old = next(e for e in made if e["site"] == site and any(m["name"] == name for m in e["measurements"]))
    meas = [dict(m, value=value) if m["name"] == name else m for m in old["measurements"]]
    fieldlog.correct(old["id"], reason, measurements=meas)
    doc_path = root() / PROTOCOL_NAME
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text(PROTOCOL, encoding="utf-8")
    documents.add(doc_path)
    return {"entries": len(fieldlog.entries()), "documents": 1, "folder": str(root())}


def off() -> None:
    """Back to the real notebook and documents; the sample data is removed."""
    _set(False)
    shutil.rmtree(root(), ignore_errors=True)


def questions_text() -> str:
    lines = ["Things to try in the demo, in order (each one is typed in the chat):"]
    for i, (what, q) in enumerate(QUESTIONS, 1):
        lines.append(f"{i}. {what}: {q}")
    lines.append("Turn it off with: demo off. Your real notebook and documents come back unchanged.")
    return "\n".join(lines)


def command(text: str) -> str | None:
    low = (text or "").strip().lower()
    if low in ("demo", "load demo", "demo on", "field demo", "start demo"):
        info = load()
        return (f"Field demo on: {info['entries']} sample field entries (three sites on one stream, one corrected "
                f"entry) and a sample protocol in Your documents. Everything is marked SAMPLE DATA, and your real "
                f"notebook and documents are set aside, untouched, until you type demo off.\n\n" + questions_text())
    if low in ("demo off", "end demo", "stop demo", "leave demo"):
        if not active():
            return "The demo isn't on."
        off()
        return "Demo off. Your own field notebook and documents are back; the sample data was removed."
    if low in ("demo questions", "demo help", "demo script"):
        return questions_text()
    return None
