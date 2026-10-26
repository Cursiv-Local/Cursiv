"""Field Station telemetry and simulation (docs/FIELD-STATION-PLAN.md). No Raspberry Pi needed: the
Linux interfaces are faked with folders shaped like /sys. Passing here doesn't validate real hardware."""
from pathlib import Path

import pytest

from cursiv_engine.station import simulation, telemetry as t


@pytest.fixture(autouse=True)
def no_simulation(monkeypatch):
    monkeypatch.delenv("CURSIV_STATION_SIMULATE", raising=False)
    simulation.activate(None)
    yield
    simulation.activate(None)


def _zone(root: Path, n: int, kind: str, milli) -> None:
    z = root / f"thermal_zone{n}"
    z.mkdir(parents=True)
    (z / "type").write_text(kind + "\n")
    (z / "temp").write_text(f"{milli}\n")


def test_the_cpu_sensor_is_found_by_its_type_not_by_assuming_zone0(tmp_path):
    _zone(tmp_path, 0, "gpu-thermal", 47000)
    _zone(tmp_path, 1, "cpu-thermal", 54321)
    r = t.cpu_temperature(tmp_path)
    assert (r.value, r.unit, r.source) == (54.3, "°C", "real") and "thermal_zone1" in r.note


def test_an_implausible_or_missing_sensor_is_unavailable_never_a_number(tmp_path):
    assert t.cpu_temperature(tmp_path).source == "unavailable"
    _zone(tmp_path, 0, "cpu-thermal", 900000)              # 900 °C: not a real reading
    r = t.cpu_temperature(tmp_path)
    assert r.source == "unavailable" and r.value is None


@pytest.mark.parametrize("temp,status", [(52, "normal"), (65, "elevated"), (74.9, "elevated"), (75, "high"),
                                          (80, "critical"), (None, "unknown")])
def test_thermal_thresholds(temp, status):
    assert t.thermal_status(temp) == status
    assert t.thermal_status(70, {"elevated": 60, "high": 68, "critical": 72}) == "high"   # configurable


def test_throttle_flags_now_and_since_boot():
    d = t.parse_throttled("throttled=0x50005")
    assert d["now"] == ["undervoltage", "throttled"] and d["since_boot"] == ["undervoltage", "throttled"]
    assert t.parse_throttled("throttled=0x0") == {"raw": "0x0", "now": [], "since_boot": []}


def test_no_vcgencmd_is_unavailable(monkeypatch):
    monkeypatch.setattr(t.shutil, "which", lambda name: None)
    assert t.throttling().source == "unavailable"


def test_a_plain_power_bank_reports_nothing_and_nothing_is_invented(monkeypatch, tmp_path):
    monkeypatch.setattr(t.SysfsBattery, "find", staticmethod(lambda root=None: None))
    b = t.battery_provider().read()
    assert b.provider == "unavailable"
    assert all(b.get(f).source == "unavailable" and b.get(f).value is None for f in t.BATTERY_FIELDS)
    assert "can't be determined" in b.get("percent").note
    assert t.battery_status(b) == "unknown"


def test_a_kernel_battery_reports_only_the_files_it_has(tmp_path):
    d = tmp_path / "BAT0"
    d.mkdir()
    (d / "type").write_text("Battery\n")
    (d / "capacity").write_text("78\n")
    (d / "status").write_text("Discharging\n")
    b = t.SysfsBattery.find(tmp_path).read()
    assert b.get("percent").value == 78 and b.get("percent").source == "real"
    assert b.get("charging").value is False
    assert b.get("voltage").source == "unavailable"          # no voltage_now file: not filled in
    assert t.battery_status(b) == "ok"


@pytest.mark.parametrize("pct,status", [(82, "ok"), (25, "low"), (15, "critical"), (10, "prepare shutdown")])
def test_battery_thresholds(pct, status):
    b = t.Battery("x", {"percent": t.Reading(pct, "%", "real", 0)})
    assert t.battery_status(b) == status


def test_readings_go_stale():
    r = t.Reading(50, "°C", "real", at=1000.0)
    assert r.stale(now=1000 + t.STALE_S + 1) and not r.stale(now=1001)
    assert not t.Reading(50, "", "simulated", at=0).stale(now=10**9)


def test_real_snapshot_has_every_section_and_no_simulation(tmp_path):
    s = t.snapshot({"internal": tmp_path})
    assert s["simulated"] is False
    for key in ("device", "cpu_temp", "thermal_status", "throttling", "cpu", "memory", "uptime", "storage", "battery"):
        assert key in s
    assert s["storage"]["internal"]["source"] == "derived"
    assert {s["cpu_temp"]["source"]} <= {"real", "unavailable"}


# ── simulation scenarios (the spec's A-E, plus F undervoltage) ───────────────

def _all_sources(obj):
    if isinstance(obj, dict):
        if "source" in obj:
            yield obj["source"]
        for v in obj.values():
            yield from _all_sources(v)


def test_scenario_a_normal(tmp_path):
    simulation.activate("A")
    s = t.snapshot({"internal": tmp_path, "ssd": tmp_path})
    assert s["simulated"] and s["thermal_status"] == "normal" and s["battery_status"] == "ok"
    assert s["cpu_temp"]["value"] == 52.0 and s["battery"]["percent"]["value"] == 82.0
    assert "real" not in set(_all_sources(s))                  # nothing simulated passes as real


def test_scenario_b_high_temperature():
    simulation.activate("B")
    s = t.snapshot()
    assert s["thermal_status"] == "critical" and "throttled" in s["throttling"]["value"]["now"]


def test_scenario_c_low_battery():
    simulation.activate("C")
    assert t.snapshot()["battery_status"] == "critical"


def test_scenario_d_ssd_removed(tmp_path):
    simulation.activate("D")
    s = t.snapshot({"internal": tmp_path, "ssd": tmp_path})
    assert s["storage"]["ssd"]["source"] == "unavailable" and "removed" in s["storage"]["ssd"]["note"]


def test_scenario_e_no_battery_telemetry_invents_nothing():
    simulation.activate("E")
    s = t.snapshot()
    assert s["battery_status"] == "unknown" and s["battery"]["percent"]["value"] is None
    assert s["battery"]["percent"]["source"] == "unavailable"


def test_scenario_f_undervoltage():
    simulation.activate("F")
    assert t.snapshot()["throttling"]["value"]["now"] == ["undervoltage"]


def test_simulation_is_off_unless_named(monkeypatch):
    assert simulation.active() is None
    monkeypatch.setenv("CURSIV_STATION_SIMULATE", "nonsense")
    assert simulation.active() is None
    monkeypatch.setenv("CURSIV_STATION_SIMULATE", "b")
    assert simulation.active() == "B"
    with pytest.raises(ValueError):
        simulation.activate("Z")
