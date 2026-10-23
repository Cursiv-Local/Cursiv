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
import json
import threading
from pathlib import Path

DEMO_KEY = "demo_mode"
_mode_lock = threading.RLock()
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
    ("Comma-format field entry", "log site: North Creek, observation: SAMPLE DATA clear water, temp 14.2 C, sample ID: NC-DEMO-001"),
    ("Inspect that sample", "field log sample NC-DEMO-001"),
    ("Sample history", "field log sample <ID from the entry above>"),
    ("Integrity check", "field log check"),
    ("The report", "field report"),
    ("Offline reference (safety)", "My partner slipped on the rocks and cut his leg, it's bleeding badly"),
    ("Model knowledge, labelled", "What is a riffle in a stream?"),
]


def root() -> Path:
    return Path.home() / ".cursiv" / "demo"


def _settings() -> dict:
    """An unreadable flag must not silently route demo writes into real records."""
    from cursiv_engine.chat import keys
    from .paths import portable_root
    drive = portable_root()
    if drive and not drive.exists():
        raise OSError('Portable drive unavailable')
    try:
        data = json.loads(keys.KEYS_FILE.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    if not isinstance(data, dict) or data.get(DEMO_KEY, '') not in ('', 'on'):
        raise ValueError('Demo setting is unreadable; no notebook destination is assumed')
    return data


def active() -> bool:
    return _settings().get(DEMO_KEY) == 'on'


def _set(on: bool) -> None:
    from cursiv_engine.chat import keys
    from cursiv_engine.core import documents
    from . import atomic
    # The legacy key setter swallows errors and treats damaged JSON as empty.
    # Update only this flag, retaining every unrelated key/value, and verify it.
    with _mode_lock:
        data = _settings()
        if on:
            data[DEMO_KEY] = 'on'
        else:
            data.pop(DEMO_KEY, None)
        atomic.write_text(keys.KEYS_FILE, json.dumps(data, indent=2))
        if _settings() != data:
            raise OSError('Demo setting read-back failed')
    documents._passages.cache = None          # the library folder just changed


def _clear_samples() -> None:
    folder = root()
    expected = Path.home() / '.cursiv' / 'demo'
    if (folder.absolute() != expected.absolute() or folder.is_symlink() or folder.is_junction()
            or folder.resolve().parent != expected.parent.resolve()):
        raise OSError('Demo cleanup refused an unexpected or linked sample directory')
    if folder.exists():
        shutil.rmtree(folder)  # verified exact sample directory; never the real notebook/documents


def load() -> dict:
    """Activate disposable sample data; restore the real view if setup fails."""
    with _mode_lock:
        _settings()  # validate before deleting or redirecting anything
        _clear_samples()
        _set(True)
        try:
            return _load_samples()
        except Exception as exc:
            try:
                _set(False)
            except (OSError, ValueError) as restore:
                raise OSError('Demo setup failed and switching back could not be confirmed. '
                              'Existing real records are untouched; repair the setting before continuing.') from restore
            raise OSError('Demo setup failed; the real notebook/document view was restored. '
                          'Partial sample data may remain in the demo folder.') from exc


def _load_samples() -> dict:
    from cursiv_engine.core import documents, fieldlog
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


def off() -> str:
    """Restore the real view before cleanup; report retained sample files honestly."""
    with _mode_lock:
        _set(False)
        try:
            _clear_samples()
        except OSError as exc:
            return f'Sample cleanup incomplete ({exc}); retained samples are not the active notebook.'
    return ''


def questions_text() -> str:
    lines = ['Type demo to start a separate SAMPLE DATA notebook. Type demo off to return to your own records.',
             "Things to try in the demo, in order (each one is typed in the chat):"]
    for i, (what, q) in enumerate(QUESTIONS, 1):
        lines.append(f"{i}. {what}: {q}")
    lines.append("Turn it off with: demo off. Your real notebook and documents come back unchanged.")
    return "\n".join(lines)


def command(text: str) -> str | None:
    try:
        return _command(text)
    except (OSError, ValueError) as exc:
        return f'Demo change not confirmed: {exc}. No change to real notebook entries was requested.'


def _command(text: str) -> str | None:
    low = (text or "").strip().lower()
    if low in ("demo", "load demo", "demo on", "field demo", "start demo"):
        info = load()
        return (f"Field demo on: {info['entries']} sample field entries (three sites on one stream, one corrected "
                f"entry) and a sample protocol in Your documents. Everything is marked SAMPLE DATA, and your real "
                f"notebook and documents are set aside, untouched, until you type demo off.\n\n" + questions_text())
    if low in ("demo off", "end demo", "stop demo", "leave demo"):
        if not active() and not root().exists():
            return "The demo isn't on."
        warning = off()
        return ('Demo off. Your own field notebook and documents are back; ' + warning if warning else
                'Demo off. Your own field notebook and documents are back; the sample data was removed.')
    if low in ("demo questions", "demo help", "demo script"):
        return questions_text()
    return None
