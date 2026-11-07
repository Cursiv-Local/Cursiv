"""
Robot evidence: signed packages from Cursiv Robotics, verified and brought into research.

A robot (or the phone importer, or the virtual lab) records signed observations; its station
exports an evidence package (a BagIt folder with signed records, checkpoints and seals). This
module takes such a package from a drive or folder to something Cursiv can work with:

  find      read-only: which packages are on a drive or folder, and how each verifies
  import    verify with the independent verifier (cursiv-verify), copy into
            ~/.cursiv/robotics/workspace (the source is fingerprinted before and after and never
            modified), re-verify the copy, and add the package's research summary to the
            document library, so questions and write-ups cite its records
  verify    re-check an imported package at any time
  trust     the robot and station keys this computer trusts

Rules:
- Nothing enters unless it passes integrity, structure and attachment checks.
- Authenticity uses only the keys in this computer's robot trust store. Keys are added
  deliberately, from a trust file the person chooses, after a preview and an explicit
  "confirm". Keys found inside a package are never trusted (no trust on first use).
- Without trusted keys, a package is imported only with "without trust", and is then
  labelled as authenticity not assessed.
- Synthetic records stay labelled synthetic. A failed verification is never reported as
  verified.

Commands (exact; plain words such as "import the robot data from E:\\" get a read-only
preview that names the exact command):
  robot evidence                      imported packages
  robot evidence find <folder>        what is there and how it verifies (changes nothing)
  robot evidence import <folder> [without trust]
  robot evidence verify <package>     re-verify an imported package now
  robot evidence show <package>       its research summary
  robot trust                         trusted keys
  robot trust add <trust.json> [confirm]
  robot trust remove <robot or station id> [confirm]

The verifier is the Rust program cursiv-verify from Cursiv Robotics, bundled with Cursiv
(tools/), or found through CURSIV_VERIFY or PATH. Without it nothing is imported.
"""
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path.home() / ".cursiv" / "robotics"
NO_VERIFIER = ("the robot evidence verifier (cursiv-verify) is not installed. It comes with Cursiv releases that "
               "include robot evidence; for a development copy, set CURSIV_VERIFY to cursiv-verify from Cursiv Robotics")
_ID = r"[a-z0-9][a-z0-9._-]{0,63}"
_CITE = re.compile(rf"(?<![\w/.-])({_ID})/({_ID})(?![\w/-])")
_PLAIN_IMPORT = re.compile(
    r"(?i)^(?:please\s+)?(?:import|bring in|load|add|read|get)\s+(?:the\s+|my\s+|our\s+)?(?:robot|robotics|rover|drone|buoy)\s+"
    r"(?:evidence|data|packages?|records?|observations?)\s+(?:from|on|in)\s+(?P<path>.+?)\s*[.!]?$")
_PLAIN_LIST = re.compile(r"(?i)^(?:what|which)\s+robot\s+(?:evidence|data|packages?)\s+(?:do i|do we|have i|have we)\b.*$")


def workspace() -> Path:
    return ROOT / "workspace"


def trust_file() -> Path:
    return ROOT / "trust.json"


def summaries_dir() -> Path:
    return ROOT / "summaries"


# ── the verifier ─────────────────────────────────────────────────────────────

def verifier() -> Path | None:
    exe = "cursiv-verify.exe" if os.name == "nt" else "cursiv-verify"
    env = os.environ.get("CURSIV_VERIFY")
    if env:
        return Path(env) if Path(env).is_file() else None
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    for p in (base / "tools" / exe, Path(sys.executable).resolve().parent / "tools" / exe):
        if p.is_file():
            return p
    found = shutil.which("cursiv-verify")
    return Path(found) if found else None


def verify_report(pkg: Path) -> tuple[int, dict]:
    """The verifier's JSON report for a package, with this computer's trust store."""
    from cursiv_engine.core import robot_evidence_import as imp
    trust = trust_file() if has_trust() else None
    return imp.verify(Path(pkg), trust)


def _plain(rep: dict) -> list[str]:
    """The verifier's own plain-language summary, or one built from the verdicts."""
    v = rep.get("verification") or {}
    if v.get("summary"):
        return list(v["summary"])
    verdicts = {k: str(x).split(":")[0] for k, x in (v.get("verdicts") or {}).items()}
    if not verdicts:
        return [f"Not verified: {rep.get('error', 'the verifier gave no report')}."]
    robots = v.get("robots") or {}
    records = sum(r.get("records", 0) for r in robots.values())
    synthetic = sum(r.get("synthetic_records", 0) for r in robots.values())
    bad = [k for k, x in verdicts.items() if x == "fail"]
    if bad:
        out = ["NOT VERIFIED: " + ", ".join(bad) + " failed. Do not use this package as evidence until that is explained."]
    elif all(x == "pass" for x in verdicts.values()):
        out = [f"Verified: {records} record(s) from {len(robots)} robot(s) passed every check."]
    else:
        out = ["Not fully verified: " + ", ".join(f"{k} {x.replace('_', ' ')}" for k, x in verdicts.items() if x != "pass") + "."]
    if synthetic:
        out.append(f"{synthetic} of {records} record(s) are SYNTHETIC (simulated), not real-world evidence.")
    return out


# ── trust store (operator-managed; never from packages) ─────────────────────

def load_trust() -> dict:
    try:
        t = json.loads(trust_file().read_text(encoding="utf-8"))
        if t.get("format") == "cursiv-trust-1":
            return t
    except (OSError, ValueError):
        pass
    return {"format": "cursiv-trust-1", "robots": {}, "stations": {}}


def has_trust() -> bool:
    t = load_trust()
    return bool(t.get("robots") or t.get("stations"))


def _save_trust(t: dict) -> None:
    from cursiv_engine.core import atomic
    trust_file().parent.mkdir(parents=True, exist_ok=True)
    atomic.write_text(trust_file(), json.dumps(t, indent=2))


def _read_trust_file(path: Path) -> dict:
    t = json.loads(Path(path).read_text(encoding="utf-8"))
    if t.get("format") != "cursiv-trust-1":
        raise ValueError("not a Cursiv Robotics trust store (format cursiv-trust-1)")
    for kind in ("robots", "stations"):
        for owner, keys in (t.get(kind) or {}).items():
            if not re.fullmatch(_ID, owner):
                raise ValueError(f"invalid {kind[:-1]} id {owner!r}")
            for k in keys:
                if not isinstance(k, dict) or not k.get("key_id") or not k.get("public_key"):
                    raise ValueError(f"a key for {owner} is missing key_id or public_key")
    return t


def trust_changes(path: Path) -> list[str]:
    """What adding a trust file would change (nothing is written)."""
    new, have = _read_trust_file(path), load_trust()
    lines = []
    for kind in ("robots", "stations"):
        for owner, keys in (new.get(kind) or {}).items():
            known = {k["key_id"] for k in have.get(kind, {}).get(owner, [])}
            for k in keys:
                if k["key_id"] not in known:
                    lines.append(f"{kind[:-1]} {owner}: key {k['key_id']} ({k.get('status', 'active')})")
    return lines


def trust_add(path: Path) -> list[str]:
    """Add keys from a trust file. Existing keys are never replaced or reactivated."""
    new, t = _read_trust_file(path), load_trust()
    added = trust_changes(path)
    for kind in ("robots", "stations"):
        for owner, keys in (new.get(kind) or {}).items():
            have = t.setdefault(kind, {}).setdefault(owner, [])
            ids = {k["key_id"] for k in have}
            have += [dict(k, note=(k.get("note") or "") + f" (added {time.strftime('%Y-%m-%d')} from {Path(path).name})".strip())
                     for k in keys if k["key_id"] not in ids]
    _save_trust(t)
    return added


def trust_remove(owner: str) -> bool:
    t = load_trust()
    gone = False
    for kind in ("robots", "stations"):
        if owner in t.get(kind, {}):
            del t[kind][owner]
            gone = True
    if gone:
        _save_trust(t)
    return gone


# ── packages ─────────────────────────────────────────────────────────────────

def packages() -> list[dict]:
    try:
        ws = json.loads((workspace() / "workspace.json").read_text(encoding="utf-8"))
        return [p for p in ws.get("packages", []) if p.get("imported")]
    except (OSError, ValueError):
        return []


def find(root: Path | str) -> list[tuple[Path, list[str]]]:
    """Packages under a folder or drive and how each verifies. Read-only."""
    from cursiv_engine.core import robot_evidence_import as imp
    root = Path(str(root).strip().strip('"'))
    pkgs = [root] if imp.is_package(root) else imp.discover(root)
    return [(p, _plain(verify_report(p)[1])) for p in pkgs]


def import_from(root: Path | str, *, without_trust: bool = False) -> list[dict]:
    """Verify and import every package under `root`. Returns one status per package."""
    from cursiv_engine.core import robot_evidence_import as imp
    if verifier() is None:
        raise FileNotFoundError(NO_VERIFIER)
    if not has_trust() and not without_trust:
        raise PermissionError("no robot or station keys are trusted on this computer yet. Add the station's trust file "
                              "first (robot trust add <trust.json>), or import without trust to keep authenticity "
                              "marked as not assessed")
    root = Path(str(root).strip().strip('"'))
    pkgs = [root] if imp.is_package(root) else imp.discover(root)
    out = []
    for p in pkgs:
        s = imp.import_package(p, workspace(), trust_file() if has_trust() else None)
        if s.get("imported") and "imported before" in (s.get("reason") or ""):
            before = next((x for x in packages() if x["package"] == s["package"]), {})
            s.update({k: before[k] for k in ("area", "records", "synthetic_records", "document", "path", "summary") if k in before})
        try:
            s["plain"] = _plain(json.loads((workspace() / "views" / s["package"] / "verification.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            # refused before any view was written: ask the verifier again for the full explanation
            s["plain"] = _plain(verify_report(p)[1])
        if s.get("imported") and s.get("area") == "packages" and s.get("summary") and not s.get("document"):
            s["document"] = _add_summary(s)
            _remember_document(s)
        out.append(s)
    _citation_index.cache = None
    return out


def _add_summary(status: dict) -> str | None:
    """Put the research summary in the document library under the package's name."""
    from cursiv_engine.core import documents
    summaries_dir().mkdir(parents=True, exist_ok=True)
    target = summaries_dir() / f"{status['package']} (robot evidence).md"
    text = Path(status["summary"]).read_text(encoding="utf-8")
    note = (f"\n\nImported into Cursiv on {status.get('imported_at', '')} from {status.get('source', '')}. Verification: "
            + " ".join(str(x) for x in status.get("plain", [])) + "\n")
    target.write_text(text + note, encoding="utf-8")
    try:
        return documents.add(target)["name"]
    except (OSError, ValueError):
        return None


def _remember_document(status: dict) -> None:
    index = workspace() / "workspace.json"
    try:
        ws = json.loads(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for p in ws.get("packages", []):
        if p.get("package") == status["package"] and p.get("imported_at") == status.get("imported_at"):
            p["document"] = status["document"]
    from cursiv_engine.core import atomic
    atomic.write_text(index, json.dumps(ws, indent=2))


def _named(name: str) -> dict | None:
    name = name.strip().strip('"')
    pk = packages()
    return next((p for p in pk if p["package"] == name), None) or next((p for p in pk if name.lower() in p["package"].lower()), None)


# ── citations in answers ─────────────────────────────────────────────────────

def _citation_index() -> tuple[set[str], set[str]]:
    """(known "robot/observation_id" pairs, robot ids) from every imported package."""
    marker = workspace() / "workspace.json"
    try:
        stamp = marker.stat().st_mtime_ns
    except OSError:
        return set(), set()
    if _citation_index.cache and _citation_index.cache[0] == stamp:
        return _citation_index.cache[1]
    ids, robots = set(), set()
    for p in packages():
        f = workspace() / "views" / p["package"] / "observations.csv"
        try:
            with f.open(encoding="utf-8", newline="") as fh:
                for row in csv.DictReader(fh):
                    ids.add(f"{row['robot_id']}/{row['observation_id']}")
                    robots.add(row["robot_id"])
        except (OSError, KeyError, csv.Error):
            continue
    _citation_index.cache = (stamp, (ids, robots))
    return ids, robots


_citation_index.cache = None


def citation_problems(answer: str) -> list[str]:
    """Robot records the answer cites that are not in any imported package."""
    ids, robots = _citation_index()
    if not robots:
        return []
    bad = []
    for robot, obs in _CITE.findall(answer or ""):
        key = f"{robot}/{obs}"
        if robot in robots and key not in ids and key not in bad:
            bad.append(key)
    return [f"cites robot record {k}, which is not in any imported robot evidence" for k in bad[:5]]


# ── drives ───────────────────────────────────────────────────────────────────

def drive_note(root: Path) -> str:
    """For the drive import dialog: evidence packages on the drive (read-only, never imported here)."""
    try:
        from cursiv_engine.core import robot_evidence_import as imp
        found = imp.discover(Path(root), max_depth=3)
    except Exception:
        return ""
    if not found:
        return ""
    names = ", ".join(p.name for p in found[:5]) + (" …" if len(found) > 5 else "")
    return (f"Robot evidence on this drive: {len(found)} package(s) ({names}). They are not copied by this step; "
            f"to verify and import them, type in chat: robot evidence import {root}")


# ── chat commands ────────────────────────────────────────────────────────────

def _describe(s: dict) -> str:
    plain = " ".join(s.get("plain") or [])
    if s.get("imported") and s.get("area") == "packages":
        doc = f" Its research summary is in your documents as \"{s['document']}\"." if s.get("document") else ""
        synth = f", {s.get('synthetic_records', 0)} synthetic" if s.get("synthetic_records") else ""
        again = " (imported before; nothing changed)" if "imported before" in (s.get("reason") or "") else ""
        return f"- {s['package']}: imported{again}, {s.get('records', '?')} records{synth}. {plain}{doc}"
    return f"- {s['package']}: NOT imported. {s.get('reason', '')} {plain}".rstrip()


def command(text: str) -> str | None:
    t = (text or "").strip()
    low = t.lower().rstrip(".?!")
    if not low.startswith(("robot evidence", "robot trust")):
        m = _PLAIN_IMPORT.match(t)
        if m:
            return _preview(m.group("path"))
        if _PLAIN_LIST.match(t):
            return command("robot evidence")
        return None
    try:
        return _command(t, low)
    except FileNotFoundError as exc:
        return f"Nothing was imported: {exc}."
    except PermissionError as exc:
        return f"Nothing was imported: {exc}."
    except (OSError, ValueError) as exc:
        return f"That didn't work: {exc}. Nothing was changed."


def _preview(path: str) -> str:
    if verifier() is None:
        return f"I can't check robot evidence here: {NO_VERIFIER}."
    found = find(path)
    if not found:
        return f"No robot evidence packages were found in {path.strip()}. Nothing was changed."
    lines = [f"Robot evidence in {path.strip()} (checked, nothing imported yet):"]
    lines += [f"- {p.name}: {' '.join(plain)}" for p, plain in found]
    lines.append(f"To import, type: robot evidence import {path.strip()}")
    return "\n".join(lines)


def _command(t: str, low: str) -> str:
    rest = t.split(None, 2)[2] if len(t.split(None, 2)) > 2 else ""
    if low in ("robot evidence", "robot evidence list"):
        pk = packages()
        if not pk:
            return ("No robot evidence imported yet. Plug in the drive or open the folder with the package, then type: "
                    "robot evidence find <folder>. Trusted keys: " + ("yes" if has_trust() else "none yet (robot trust add <trust.json>)"))
        return "Robot evidence on this computer:\n" + "\n".join(
            f"- {p['package']}: {p.get('records', '?')} records ({p.get('synthetic_records', 0)} synthetic), missions "
            f"{', '.join(p.get('missions') or []) or 'unknown'}, imported {p.get('imported_at', '')}; "
            f"{', '.join(f'{k} {str(v).split(chr(58))[0]}' for k, v in (p.get('verdicts') or {}).items())}"
            + (f"; summary in documents: {p['document']}" if p.get("document") else "") for p in pk)
    if low.startswith("robot evidence find "):
        return _preview(t[len("robot evidence find "):])
    if low.startswith("robot evidence import "):
        arg = t[len("robot evidence import "):].strip()
        without = arg.lower().endswith(" without trust")
        if without:
            arg = arg[: -len(" without trust")]
        results = import_from(arg, without_trust=without)
        if not results:
            return f"No robot evidence packages were found in {arg}. Nothing was changed."
        return "Robot evidence import:\n" + "\n".join(_describe(s) for s in results)
    if low.startswith("robot evidence verify "):
        p = _named(rest[len("verify "):] if rest.lower().startswith("verify ") else rest)
        if not p:
            return "No imported package by that name. Type robot evidence to list them."
        _, rep = verify_report(Path(p["path"]))
        return f"{p['package']} (imported copy, checked now):\n" + "\n".join(f"- {line}" for line in _plain(rep))
    if low.startswith("robot evidence show "):
        p = _named(rest[len("show "):] if rest.lower().startswith("show ") else rest)
        if not p or not p.get("summary"):
            return "No imported package by that name. Type robot evidence to list them."
        text = Path(p["summary"]).read_text(encoding="utf-8")
        lines = text.splitlines()
        return "\n".join(lines[:80]) + ("\n…(the full summary is in your documents)" if len(lines) > 80 else "")
    if low in ("robot trust", "robot trust list"):
        t_ = load_trust()
        rows = [f"- {kind[:-1]} {owner}: " + ", ".join(f"{k['key_id']} ({k.get('status', 'active')})" for k in keys)
                for kind in ("robots", "stations") for owner, keys in sorted((t_.get(kind) or {}).items())]
        return ("Trusted robot evidence keys:\n" + "\n".join(rows)) if rows else (
            "No robot evidence keys are trusted yet. Add the station's trust file: robot trust add <trust.json> "
            "(you'll see the keys before anything is saved).")
    if low.startswith("robot trust add "):
        arg = t[len("robot trust add "):].strip()
        confirm = arg.lower().endswith(" confirm")
        path = Path((arg[: -len(" confirm")] if confirm else arg).strip().strip('"'))
        changes = trust_changes(path)
        if not changes:
            return f"{path.name} adds no new keys. Nothing was changed."
        if not confirm:
            return ("Adding this trust file would trust these keys on this computer:\n" + "\n".join(f"- {c}" for c in changes)
                    + "\nOnly add keys you got from the station's operator directly. To add them, type: robot trust add "
                    + f"{path} confirm")
        added = trust_add(path)
        return "Trusted now:\n" + "\n".join(f"- {c}" for c in added)
    if low.startswith("robot trust remove "):
        arg = t[len("robot trust remove "):].strip()
        confirm = arg.lower().endswith(" confirm")
        owner = (arg[: -len(" confirm")] if confirm else arg).strip()
        t_ = load_trust()
        if not any(owner in (t_.get(k) or {}) for k in ("robots", "stations")):
            return f"No trusted keys for {owner}. Nothing was changed."
        if not confirm:
            return (f"Removing {owner} means its packages no longer verify as authentic on this computer. "
                    f"To remove it, type: robot trust remove {owner} confirm")
        trust_remove(owner)
        return f"Removed {owner} from the trusted keys. Imported packages are unchanged; re-verify them to see the effect."
    return ("Robot evidence commands: robot evidence · robot evidence find <folder> · robot evidence import <folder> · "
            "robot evidence verify <package> · robot evidence show <package> · robot trust · robot trust add <trust.json> · "
            "robot trust remove <id>")
