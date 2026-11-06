"""Robot evidence importer. Vendored from Cursiv-Robotics (python/cursiv_integration/importer.py at
commit 48151c0, MIT License, same author). Changed only where it finds the verifier (Cursiv's bundled
cursiv-verify, see core/robot_evidence.py) and its layout import. Cursiv uses it through
core/robot_evidence.py; the command line entry point below is kept for parity.

Reference importer: Cursiv Robotics evidence packages into a Cursiv research workspace.

Implements steps 4-7 of the integration workflow (docs/CURSIV_INTEGRATION.md) using only the
Python standard library and the `cursiv-verify` binary, so it can be copied into Cursiv as-is:

  4. discover packages on a USB drive, SSD or folder (no symlinks followed, depth-limited);
  5. verify each one independently (integrity, authenticity, completeness, attachments, science);
  6. copy it into the workspace (never moved or edited), re-verify the copy, and write derived,
     clearly labelled views: an index, every observation as CSV, per-robot JSONL and the report;
  7. write a research summary (Markdown) that cites individual records, for Cursiv's
     `add document` and report writing.

Rules: the source is never modified (a fingerprint of every source file is taken before and
after); nothing is imported into the workspace unless integrity passes (`--quarantine` keeps a
failing package separately, marked); synthetic records stay labelled synthetic; AI-authored
findings are shown as interpretations, never as observations.

    py -m cursiv_integration import E:\\ --workspace C:\\Users\\you\\CursivResearch --trust trust.json
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from cursiv_engine.core import robot_evidence_layout as layout

CONTRACT_VERSION = "1"            # the workspace contract (docs/CURSIV_INTEGRATION.md)
SUPPORTED_PACKAGE_VERSIONS = ("1", "2")   # package formats this importer reads (2 = segmented logs)
MANIFEST_TYPE = "application/vnd.cursiv.package-manifest.v1+json"


def _verify_bin() -> Path:
    from cursiv_engine.core import robot_evidence
    found = robot_evidence.verifier()
    if found is None:
        raise FileNotFoundError(robot_evidence.NO_VERIFIER)
    return found


def is_package(d: Path) -> bool:
    """A Cursiv Robotics package: a BagIt bag whose manifest.json is a Cursiv DSSE manifest."""
    try:
        if not (d / "bagit.txt").is_file() or not (d / "data").is_dir():
            return False
        m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        return m.get("payloadType") == MANIFEST_TYPE
    except (OSError, ValueError):
        return False


def discover(root: Path, max_depth: int = 4) -> list[Path]:
    """Packages at or below `root` (a drive or folder). Symbolic links and junctions are not followed."""
    root, found = Path(root), []
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            if d.is_symlink():
                continue
            if is_package(d):
                found.append(d)
                continue
            if depth < max_depth:
                stack += [(c, depth + 1) for c in d.iterdir() if c.is_dir() and not c.is_symlink() and not c.name.startswith(".")]
        except OSError:
            continue
    return sorted(found)


def fingerprint(d: Path) -> str:
    """SHA-256 over every file's relative path, size and content: proves the source was not changed."""
    h = hashlib.sha256()
    for f in sorted(p for p in Path(d).rglob("*") if p.is_file() and not p.is_symlink()):
        h.update(f.relative_to(d).as_posix().encode() + b"\0" + str(f.stat().st_size).encode() + b"\0")
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def verify(pkg: Path, trust: Path | None) -> tuple[int, dict]:
    cmd = [str(_verify_bin()), "package", str(pkg), "--json", "--science"]
    if trust:
        cmd += ["--trust", str(trust)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return out.returncode, json.loads(out.stdout)
    except ValueError:
        return 2, {"error": out.stderr.strip() or "verifier produced no report"}


def records(pkg: Path, unreadable: list | None = None) -> list[dict]:
    """Decoded record bodies. Unreadable lines (possible in quarantined packages) are skipped and
    reported through `unreadable`, never guessed."""
    out = []
    for robot in layout.robots(pkg):
        for n, line in enumerate(layout.record_lines(pkg, robot), 1):
            if not line.strip():
                continue
            try:
                body = json.loads(base64.b64decode(json.loads(line)["payload"]))
                if not isinstance(body, dict) or "observation" not in body:
                    raise ValueError("not a record")
                out.append(body)
            except (ValueError, KeyError, TypeError) as e:
                if unreadable is not None:
                    unreadable.append(f"{robot} record line {n}: {type(e).__name__}")
    return out


def import_package(src: Path, workspace: Path, trust: Path | None, *, quarantine: bool = False) -> dict:
    src, workspace = Path(src), Path(workspace)
    before = fingerprint(src)
    code, rep = verify(src, trust)
    v = (rep.get("verification") or {}).get("verdicts", {})
    # evidence enters the workspace only if it is intact AND not signed by an untrusted key
    # (authenticity "not_assessed", when no trust store is given, is allowed and stated in the summary)
    integrity_ok = (v.get("integrity") == "pass" and v.get("structure") == "pass" and v.get("attachments") == "pass"
                    and v.get("authenticity", "").split(":")[0] in ("pass", "not_assessed"))
    bag_info = (src / "bag-info.txt").read_text(encoding="utf-8", errors="replace") if (src / "bag-info.txt").exists() else ""
    version = next((l.split(":", 1)[1].strip() for l in bag_info.splitlines() if l.startswith("Cursiv-Package-Version:")), None)
    status = {"package": src.name, "source": str(src), "contract_version": CONTRACT_VERSION, "package_version": version, "verify_exit": code,
              "verdicts": v, "imported": False, "imported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if version not in (*SUPPORTED_PACKAGE_VERSIONS, None):
        status["reason"] = f"package version {version} is not supported by this importer (supports {', '.join(SUPPORTED_PACKAGE_VERSIONS)})"
        return status
    if not integrity_ok and not quarantine:
        status["reason"] = ("integrity, structure, attachments or authenticity did not pass: not imported "
                            "(use --quarantine to keep it separately, marked)")
        return status
    area = "packages" if integrity_ok else "quarantine"
    dest = workspace / area / src.name
    if dest.exists():
        status["reason"] = f"{dest} already exists: this package was imported before (nothing changed)"
        status["imported"] = dest.is_dir()
        return status
    tmp = workspace / area / f".importing-{src.name}-{os.getpid()}"
    shutil.copytree(src, tmp, symlinks=False)
    code2, rep2 = verify(tmp, trust)
    if rep2.get("verification", {}).get("verdicts") != rep.get("verification", {}).get("verdicts"):
        shutil.rmtree(tmp, ignore_errors=True)
        status["reason"] = "the copy did not verify like the source (transfer or disk fault): not imported"
        return status
    tmp.rename(dest)
    after = fingerprint(src)
    status["source_unchanged"] = before == after
    if before != after:
        status["reason"] = "WARNING: the source changed during import (another program wrote to it)"
    status.update(imported=True, area=area, path=str(dest))
    views = workspace / "views" / src.name
    views.mkdir(parents=True, exist_ok=True)
    bad_lines: list[str] = []
    recs = records(dest, bad_lines)
    status["unreadable_records"] = bad_lines
    (views / "verification.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    write_views(views, recs)
    summary = research_summary(views, src.name, rep, recs, integrity_ok)
    status["summary"] = str(summary)
    status["missions"] = sorted({r["observation"]["mission_id"] for r in recs})
    status["records"] = len(recs)
    status["synthetic_records"] = sum(r["observation"]["synthetic"] for r in recs)
    index = workspace / "workspace.json"
    ws = json.loads(index.read_text()) if index.exists() else {"format": "cursiv-research-workspace-1", "packages": []}
    ws["packages"].append(status)
    index.write_text(json.dumps(ws, indent=2), encoding="utf-8")
    return status


def write_views(views: Path, recs: list[dict]) -> None:
    """Derived, read-only conveniences. The evidence is the package; these can be regenerated."""
    (views / "README.txt").write_text("Derived views of the evidence package in ../../packages. Regenerate them at will; "
                                      "never treat them as the evidence.\n", encoding="utf-8")
    by_robot: dict[str, list] = {}
    with (views / "observations.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["robot_id", "seq", "observation_id", "mission_id", "observation_type", "synthetic", "source", "sensor_id",
                    "sensor_time", "value", "unit", "uncertainty_kind", "uncertainty", "lat", "lon", "alt_m", "horizontal_accuracy_m",
                    "calibration_valid_until", "attachments", "derived_from", "claim_epistemic", "claim_author_kind"])
        for r in recs:
            o = r["observation"]
            m, l, c = o.get("measurement") or {}, o.get("location") or {}, o.get("claim") or {}
            u = m.get("uncertainty") or {}
            by_robot.setdefault(r["robot_id"], []).append(r)
            w.writerow([r["robot_id"], r["seq"], o["observation_id"], o["mission_id"], o["observation_type"], o["synthetic"],
                        o["provenance"]["source"], o["sensor"]["sensor_id"], o.get("sensor_time") or "", m.get("value", ""), m.get("unit", ""),
                        u.get("kind", ""), u.get("value", ""), l.get("lat", ""), l.get("lon", ""), l.get("alt_m", ""),
                        l.get("horizontal_accuracy_m", ""), ((o["sensor"].get("calibration") or {}).get("valid_until_utc") or ""),
                        ";".join(a["sha256"] for a in o["attachments"]), ";".join(o["provenance"]["derived_from"]),
                        c.get("epistemic", ""), c.get("author_kind", "")])
    for rid, rs in by_robot.items():
        (views / f"{rid}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs), encoding="utf-8")


def research_summary(views: Path, name: str, rep: dict, recs: list[dict], integrity_ok: bool) -> Path:
    ver, sci, rsn = rep.get("verification", {}), rep.get("science") or {}, rep.get("reasoning") or {}
    obs = [r["observation"] for r in recs]
    synth = sum(o["synthetic"] for o in obs)
    md = [f"# Research summary: {name}", ""]
    if synth:
        md.append(f"> **SYNTHETIC DATA:** {synth} of {len(obs)} records are simulated and are not real-world evidence.")
    if not integrity_ok:
        md.append("> **QUARANTINED:** this package failed integrity or authenticity verification. Do not use it as evidence.")
    if str(ver.get("verdicts", {}).get("authenticity", "")).startswith("not_assessed"):
        md.append("> **Authenticity not assessed:** no trust store was given, so who signed these records is not established.")
    md += ["", "> Writers (human or AI): cite records as `robot/observation_id`; keep Known / Inferred / Assumed / Unknown labels; "
           "interpretations below are claims by their authors, not observations.", "", "## Verification", "", "| Question | Result |", "|---|---|"]
    md += [f"| {k} | {str(x).split(':')[0]} |" for k, x in ver.get("verdicts", {}).items()]
    d = rsn.get("derivations", {})
    md += ["", f"Derived results recomputed by the verifier: {d.get('verified', 0)} match, {d.get('mismatch', 0)} mismatch, "
               f"{d.get('not_reproducible', 0)} not reproducible; uncertainties confirmed: {d.get('uncertainty_verified', 0)}.", "",
           "## Missions and platforms", "", "| Mission | Robot | Records | Observation types | Time span (sensor clocks) |", "|---|---|---|---|---|"]
    groups: dict[tuple, list] = {}
    for r in recs:
        groups.setdefault((r["observation"]["mission_id"], r["robot_id"]), []).append(r["observation"])
    for (mission, rid), os_ in sorted(groups.items()):
        ts = sorted(o["sensor_time"] for o in os_ if o.get("sensor_time"))
        md.append(f"| {mission} | {rid} | {len(os_)} | {', '.join(sorted({o['observation_type'] for o in os_}))} | "
                  f"{(ts[0] + ' to ' + ts[-1]) if ts else 'unknown'} |")
    derived = [o for o in obs if o["provenance"]["source"] == "derived" and o.get("measurement")]
    if derived:
        bad = {f["observation_id"] for f in rsn.get("flags", []) if f["severity"] == "error" and f["code"].startswith(("derivation", "uncertainty"))}
        md += ["", "## Results recorded as derived evidence", "", "| Result | Value | Std. uncertainty | Inputs | Recomputed | Citation |", "|---|---|---|---|---|---|"]
        for o in derived[:200]:
            m = o["measurement"]
            u = (m.get("uncertainty") or {}).get("value")
            md.append(f"| {o['observation_type']} | {m['value']:.6g} {m['unit']} | {('%.3g ' % u + m['unit']) if u is not None else 'unknown'} | "
                      f"{len(o['provenance']['derived_from'])} | {'no' if o['observation_id'] in bad else 'yes'} | `{o['robot_id']}/{o['observation_id']}` |")
    if rsn.get("findings"):
        md += ["", "## Interpretations recorded with the evidence (claims, not observations)", "", "| Statement | Author | Label | Status |", "|---|---|---|---|"]
        md += [f"| {f['statement']} | {f['author']} ({f['author_kind']}{', ' + f['model'] if f.get('model') else ''}) | {f['epistemic']} | {f['status']} |"
               for f in rsn["findings"]]
    md += ["", "## Anomalies and unknowns (deterministic checks)", ""]
    per: dict[str, int] = {}
    for f in sci.get("flags", []):
        if per.get(f["code"], 0) < 3 and f["code"] not in ("calibration_unknown", "uncertainty_unknown", "location_unknown", "type_unprofiled"):
            per[f["code"]] = per.get(f["code"], 0) + 1
            md.append(f"- *{f['epistemic']}* `{f['code']}` ({f['robot_id']}; {', '.join('`' + i + '`' for i in f['observation_ids'][:2])}): {f['message']}")
    md += ["", "All counts: " + (", ".join(f"`{k}` {n}" for k, n in sorted(sci.get("counts", {}).items())) or "none"), "",
           "## Provenance", "", f"Evidence: `packages/{name}` (BagIt, RFC 8493; station-signed DSSE manifest). Every observation is in "
           "`observations.csv` with its id, sensor, time, value, unit, uncertainty, location and calibration. Integrity and authenticity "
           "show custody, not scientific correctness.", ""]
    p = views / "research-summary.md"
    p.write_text("\n".join(md), encoding="utf-8")
    return p


def merge_trust(paths: list[Path], workspace: Path) -> Path | None:
    """Several stations' trust stores as one (keys are only added, never changed)."""
    if not paths:
        return None
    if len(paths) == 1:
        return paths[0]
    merged = {"format": "cursiv-trust-1", "robots": {}, "stations": {}}
    for p in paths:
        t = json.loads(Path(p).read_text(encoding="utf-8"))
        for kind in ("robots", "stations"):
            for owner, keys in t.get(kind, {}).items():
                have = merged[kind].setdefault(owner, [])
                have += [k for k in keys if k["key_id"] not in {x["key_id"] for x in have}]
    workspace.mkdir(parents=True, exist_ok=True)
    out = workspace / ".trust-merged.json"
    out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cursiv_integration")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover", help="list evidence packages on a drive or folder")
    d.add_argument("root")
    i = sub.add_parser("import", help="verify and import packages into a research workspace")
    i.add_argument("root", help="a package, or a drive/folder to search")
    i.add_argument("--workspace", required=True)
    i.add_argument("--trust", action="append", default=[], help="trust store (cursiv-trust-1); repeat for several stations; "
                   "without one, authenticity is not assessed")
    i.add_argument("--quarantine", action="store_true", help="keep packages that fail integrity, separately and marked")
    a = ap.parse_args(argv)
    if a.cmd == "discover":
        for p in discover(Path(a.root)):
            print(p)
        return 0
    pkgs = [Path(a.root)] if is_package(Path(a.root)) else discover(Path(a.root))
    if not pkgs:
        print("no Cursiv Robotics evidence packages found")
        return 1
    ok = True
    for p in pkgs:
        trust = merge_trust([Path(t) for t in a.trust], Path(a.workspace))
        s = import_package(p, Path(a.workspace), trust, quarantine=a.quarantine)
        print(json.dumps({k: s.get(k) for k in ("package", "imported", "area", "verdicts", "records", "synthetic_records", "summary", "reason")}, indent=1))
        ok &= bool(s["imported"]) and s.get("area") == "packages"
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
