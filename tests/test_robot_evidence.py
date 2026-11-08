"""Robot evidence from Cursiv Robotics: find, trust, verify, import, document library, citation
checks, drive note and chat routing (core/robot_evidence.py).

Verification needs the real verifier (cursiv-verify from Cursiv Robotics): set CURSIV_VERIFY, or
build it with scripts/get_cursiv_verify.py. Tests that need it are skipped without it; CI builds it
from a pinned commit. The fixtures are SYNTHETIC packages signed with simulation keys.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from cursiv_engine.core import documents
from cursiv_engine.core import robot_evidence as rob

FIX = Path(__file__).parent / "fixtures" / "robot_evidence"
NEEDS_VERIFIER = pytest.mark.skipif(rob.verifier() is None, reason="cursiv-verify not available (set CURSIV_VERIFY)")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(rob, "ROOT", tmp_path / "robotics")
    monkeypatch.setattr(documents, "lib_dir", lambda: tmp_path / "documents")
    documents._passages.cache = None
    rob._citation_index.cache = None
    yield
    documents._passages.cache = None


def test_the_verifier_is_present_where_ci_requires_it():
    if os.environ.get("CURSIV_REQUIRE_VERIFIER"):
        assert rob.verifier() is not None, "CI builds cursiv-verify into tools/; it was not found"


def drive(tmp_path) -> Path:
    """A 'USB drive' holding both fixture packages a few folders down."""
    d = tmp_path / "usb"
    shutil.copytree(FIX / "fixture-probe-07", d / "field" / "day-1" / "fixture-probe-07")
    shutil.copytree(FIX / "sample-buoy-1-package", d / "field" / "day-2" / "sample-buoy-1-package")
    return d


def trust_both(tmp_path) -> None:
    merged = json.loads((FIX / "trust.json").read_text())
    other = json.loads((FIX / "sample-trust.json").read_text())
    for kind in ("robots", "stations"):
        merged[kind].update(other[kind])
    p = tmp_path / "station-trust.json"
    p.write_text(json.dumps(merged))
    assert "confirm" in rob.command(f"robot trust add {p}")
    assert not rob.load_trust()["robots"], "a preview saves nothing"
    assert rob.command(f"robot trust add {p} confirm").startswith("Trusted now:")


def test_trust_is_previewed_confirmed_and_never_taken_from_packages(tmp_path):
    assert "No robot evidence keys are trusted yet" in rob.command("robot trust")
    preview = rob.command(f"robot trust add {FIX / 'trust.json'}")
    assert "probe-07" in preview and "station-fixture" in preview and "confirm" in preview
    assert not rob.has_trust()
    rob.command(f"robot trust add {FIX / 'trust.json'} confirm")
    assert rob.has_trust() and "probe-07" in rob.command("robot trust")
    assert "adds no new keys" in rob.command(f"robot trust add {FIX / 'trust.json'} confirm"), "re-adding changes nothing"
    # a package's own key list is never a trust file
    with pytest.raises(ValueError):
        rob.trust_changes(FIX / "fixture-probe-07" / "data" / "keys" / "public-keys.json")
    assert "confirm" in rob.command("robot trust remove probe-07")
    assert "probe-07" in json.dumps(rob.load_trust())
    rob.command("robot trust remove probe-07 confirm")
    assert "probe-07" not in json.dumps(rob.load_trust()["robots"])


def test_without_the_verifier_nothing_is_imported(tmp_path, monkeypatch):
    monkeypatch.setattr(rob, "verifier", lambda: None)
    reply = rob.command(f"robot evidence import {drive(tmp_path)}")
    assert reply.startswith("Nothing was imported") and "cursiv-verify" in reply
    assert not rob.packages() and not documents.library()


def test_the_drive_dialog_lists_packages_without_importing(tmp_path):
    note = rob.drive_note(drive(tmp_path))
    assert "2 package(s)" in note and "fixture-probe-07" in note and "robot evidence import" in note
    assert not rob.packages()
    assert rob.drive_note(tmp_path / "nothing-here") == ""


def test_chat_routes_robot_commands_before_file_requests(tmp_path):
    import chat_commands
    d = drive(tmp_path)
    res = chat_commands.handle_command(f"robot evidence import {d}", {}, [])
    assert res is not None and ("Robot evidence import" in res.text or "Nothing was imported" in res.text), res
    plain = chat_commands.handle_command(f"import the robot data from {d}", {}, [])
    assert plain is not None and ("nothing imported yet" in plain.text or "can't check robot evidence" in plain.text)
    assert not rob.packages(), "plain words only preview"
    assert rob.command("tell me about robots") is None and rob.command("robot arms are neat") is None


@NEEDS_VERIFIER
def test_import_verifies_copies_and_adds_the_summary_to_documents(tmp_path):
    d = drive(tmp_path)
    refused = rob.command(f"robot evidence import {d}")
    assert "no robot or station keys are trusted" in refused and not rob.packages()
    trust_both(tmp_path)
    preview = rob.command(f"robot evidence find {d}")
    assert preview.count("Verified:") == 2 and "nothing imported yet" in preview
    before = sorted((p.relative_to(d), p.read_bytes()) for p in d.rglob("*") if p.is_file())
    reply = rob.command(f"robot evidence import {d}")
    assert reply.count("imported, ") == 2, reply
    assert "SYNTHETIC" in reply and "in your documents" in reply
    after = sorted((p.relative_to(d), p.read_bytes()) for p in d.rglob("*") if p.is_file())
    assert before == after, "the drive is never modified"
    names = [x["name"] for x in documents.library()]
    assert "fixture-probe-07 (robot evidence).md" in names and "sample-buoy-1-package (robot evidence).md" in names
    hits = documents.search("water temperature mean probe", stem=True)
    assert hits and any("fixture-probe-07" in h.name for h in hits)
    listing = rob.command("robot evidence")
    assert "fixture-probe-07: 13 records (13 synthetic)" in listing and "integrity pass" in listing
    again = rob.command(f"robot evidence import {d}")
    assert again.count("imported before; nothing changed") == 2 and len(documents.library()) == 2
    assert rob.command("robot evidence verify fixture-probe-07").count("Verified:") == 1
    assert "# Research summary: fixture-probe-07" in rob.command("robot evidence show fixture-probe-07")


@NEEDS_VERIFIER
def test_tampered_evidence_is_refused_with_a_plain_reason(tmp_path):
    trust_both(tmp_path)
    bad = tmp_path / "bad" / "fixture-probe-07"
    shutil.copytree(FIX / "fixture-probe-07", bad)
    seg = next((bad / "data" / "robots" / "probe-07" / "segments").glob("000001.jsonl"))
    seg.write_bytes(seg.read_bytes().replace(b"A", b"B", 1))
    reply = rob.command(f"robot evidence import {bad}")
    assert "NOT imported" in reply and "NOT VERIFIED" in reply, reply
    assert not rob.packages() and not documents.library()


@NEEDS_VERIFIER
def test_without_trust_is_explicit_and_labelled(tmp_path):
    reply = rob.command(f"robot evidence import {FIX / 'fixture-probe-07'} without trust")
    assert "imported" in reply and "Not fully verified" in reply, reply
    text = (rob.summaries_dir() / "fixture-probe-07 (robot evidence).md").read_text()
    assert "Authenticity not assessed" in text


@NEEDS_VERIFIER
def test_answers_citing_robot_records_are_checked(tmp_path):
    trust_both(tmp_path)
    rob.command(f"robot evidence import {FIX / 'fixture-probe-07'}")
    obs = (rob.workspace() / "views" / "fixture-probe-07" / "observations.csv").read_text().splitlines()[1].split(",")
    real = f"{obs[0]}/{obs[2]}"
    assert rob.citation_problems(f"The first reading (`{real}`) was 12.0 degC.") == []
    bad = rob.citation_problems(f"See `{real}` and `probe-07/probe-07-deadbeef00000000`.")
    assert bad == ["cites robot record probe-07/probe-07-deadbeef00000000, which is not in any imported robot evidence"]
    assert rob.citation_problems("and/or other robot/arms text, http://a/b") == [], "only known robots are checked"


@NEEDS_VERIFIER
def test_a_drive_that_changes_during_import_imports_nothing(tmp_path, monkeypatch):
    from cursiv_engine.core import robot_evidence_import as imp
    trust_both(tmp_path)
    src = tmp_path / "usb" / "fixture-probe-07"
    shutil.copytree(FIX / "fixture-probe-07", src)
    real = imp.verify

    def verify_then_someone_writes(p, t, timeout=None, profile=None):
        out = real(p, t, timeout, profile)
        if Path(p) == src:
            (src / "bag-info.txt").write_text((src / "bag-info.txt").read_text() + "Note: written during import\n")
        return out
    monkeypatch.setattr(imp, "verify", verify_then_someone_writes)
    reply = rob.command(f"robot evidence import {src}")
    assert "NOT imported" in reply and "source changed during import" in reply, reply
    assert not rob.packages() and not documents.library()
    assert not list((rob.workspace() / "packages").glob("*")), "no partial copy is left"


@NEEDS_VERIFIER
def test_a_verifier_that_does_not_finish_imports_nothing(tmp_path, monkeypatch):
    from cursiv_engine.core import robot_evidence_import as imp
    trust_both(tmp_path)
    seen = {}

    def hangs(cmd, **kw):
        seen["timeout"] = kw.get("timeout")
        raise imp.subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    monkeypatch.setenv("CURSIV_VERIFY_TIMEOUT", "7")
    monkeypatch.setattr(imp.subprocess, "run", hangs)
    reply = rob.command(f"robot evidence import {FIX / 'fixture-probe-07'}")
    assert seen["timeout"] == 7.0 and "NOT imported" in reply and "did not finish within 7 s" in reply, reply
    assert not rob.packages() and not documents.library()


@NEEDS_VERIFIER
def test_not_fully_verified_evidence_says_so_everywhere(tmp_path):
    reply = rob.command(f"robot evidence import {FIX / 'fixture-probe-07'} without trust")
    assert "NOT fully verified" in reply and "authenticity not assessed" in reply, reply
    assert "Fully verified." not in reply
    assert "NOT fully verified" in rob.command("robot evidence")
    text = (rob.summaries_dir() / "fixture-probe-07 (robot evidence).md").read_text()
    assert "NOT FULLY VERIFIED" in text and "Authenticity not assessed" in text
    obs = (rob.workspace() / "views" / "fixture-probe-07" / "observations.csv").read_text().splitlines()[1].split(",")
    cite = f"`{obs[0]}/{obs[2]}`"
    notes = rob.citation_caveats(f"The probe read 12.0 degC {cite}.")
    assert len(notes) == 1 and "fixture-probe-07" in notes[0] and "authenticity not assessed" in notes[0]
    assert rob.citation_caveats(f"The probe read 12.0 degC {cite} (not fully verified: authenticity not assessed).") == []
    assert rob.citation_caveats("No robot records cited here.") == []


@NEEDS_VERIFIER
def test_older_workspace_entries_are_assessed_from_their_saved_report(tmp_path):
    trust_both(tmp_path)
    rob.command(f"robot evidence import {FIX / 'fixture-probe-07'}")
    index = rob.workspace() / "workspace.json"
    ws = json.loads(index.read_text())
    for p in ws["packages"]:
        p.pop("fully_verified"), p.pop("caveats")      # as written by the first Cursiv release of this feature
    index.write_text(json.dumps(ws))
    full, caveats = rob.standing(rob.packages()[0])
    assert full is False and caveats and all("authenticity" not in c for c in caveats)


def test_the_self_test_requires_the_verifier_only_in_a_built_app(monkeypatch):
    import selftest
    check = dict(selftest._checks())["robot evidence verifier"]
    monkeypatch.setattr(rob, "verifier", lambda: None)
    assert "source run" in check()
    monkeypatch.setattr(selftest.sys, "frozen", True, raising=False)
    with pytest.raises(RuntimeError, match="not bundled"):
        check()


@NEEDS_VERIFIER
def test_the_self_test_starts_the_bundled_verifier():
    import selftest
    assert "starts" in dict(selftest._checks())["robot evidence verifier"]()


def test_release_builds_refuse_to_build_without_the_verifier(tmp_path, monkeypatch):
    spec = (Path(__file__).parent.parent / "launcher" / "build.spec").read_text(encoding="utf-8")
    block = spec[spec.index("_verify = ROOT"):spec.index("# ── Hidden imports")]
    monkeypatch.delenv("CURSIV_REQUIRE_VERIFIER", raising=False)
    found = {"ROOT": tmp_path, "sys": __import__("sys"), "os": os, "_extra_binaries": []}
    exec(block, found)
    assert found["_extra_binaries"] == [], "a development build without the verifier still builds"
    monkeypatch.setenv("CURSIV_REQUIRE_VERIFIER", "1")
    with pytest.raises(SystemExit, match="cursiv-verify is missing"):
        exec(block, dict(found))
    (tmp_path / "tools").mkdir()
    exe = "cursiv-verify.exe" if os.name == "nt" else "cursiv-verify"
    (tmp_path / "tools" / exe).write_bytes(b"binary")
    present = dict(found, _extra_binaries=[])
    exec(block, present)
    assert present["_extra_binaries"] == [(str(tmp_path / "tools" / exe), "tools")]
    build = (Path(__file__).parent.parent / "scripts" / "build_release.py").read_text(encoding="utf-8")
    assert "get_cursiv_verify.py" in build and "CURSIV_REQUIRE_VERIFIER" in build
    for wf in ("windows-build.yml", "mac-build.yml"):
        assert "rust-toolchain" in (Path(__file__).parent.parent / ".github" / "workflows" / wf).read_text(encoding="utf-8")
