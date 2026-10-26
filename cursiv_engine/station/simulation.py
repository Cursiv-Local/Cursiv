"""
Named hardware scenarios for developing and testing the Field Station without a Raspberry Pi
(docs/FIELD-STATION-PLAN.md section 4). Switched on only by name: CURSIV_STATION_SIMULATE=<A-F>, or
activate() in tests. Every value carries source "simulated" and the snapshot says simulated: True, so the
interface can show a fixed SIMULATED banner. Nothing here is ever mixed into real readings.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from cursiv_engine.station import telemetry as t

SCENARIOS = {
    "A": dict(title="Normal operation", temp=52.0, cpu=18.0, mem=41.0, battery=82.0, charging=False,
              power_w=6.8, ssd=True, network="offline local access point", throttled=[]),
    "B": dict(title="High temperature", temp=81.0, cpu=96.0, mem=63.0, battery=70.0, charging=False,
              power_w=11.9, ssd=True, network="offline local access point",
              throttled=["soft temperature limit", "throttled"]),
    "C": dict(title="Low battery", temp=49.0, cpu=12.0, mem=38.0, battery=12.0, charging=False,
              power_w=6.1, ssd=True, network="offline local access point", throttled=[]),
    "D": dict(title="Storage removed", temp=55.0, cpu=22.0, mem=44.0, battery=64.0, charging=False,
              power_w=7.2, ssd=False, network="offline local access point", throttled=[]),
    "E": dict(title="No battery telemetry", temp=53.0, cpu=20.0, mem=40.0, battery=None, charging=None,
              power_w=None, ssd=True, network="offline local access point", throttled=[]),
    "F": dict(title="Undervoltage", temp=58.0, cpu=40.0, mem=45.0, battery=None, charging=None,
              power_w=None, ssd=True, network="offline local access point", throttled=["undervoltage"]),
}

_active: str | None = None


def activate(name: str | None) -> None:
    global _active
    if name is not None and name not in SCENARIOS:
        raise ValueError(f"unknown scenario {name!r}; choose one of {', '.join(SCENARIOS)}")
    _active = name


def active() -> str | None:
    if _active is not None:
        return _active
    name = os.environ.get("CURSIV_STATION_SIMULATE", "").strip().upper()
    return name if name in SCENARIOS else None


def _sim(value, unit="", note="") -> t.Reading:
    return t.Reading(value, unit, "simulated", time.time(), note or f"scenario {active()}")


class SimulatedBattery:
    name = "simulated"

    def read(self) -> t.Battery:
        s = SCENARIOS[active()]
        if s["battery"] is None:                                   # E/F: a power bank that reports nothing
            return t.NoBattery().read()
        r = {"detected": _sim(True), "model": _sim("Simulated UPS"), "percent": _sim(s["battery"], "%"),
             "charging": _sim(s["charging"]), "power_w": _sim(s["power_w"], "W"),
             "external_power": _sim(s["charging"])}
        return t.Battery(self.name, r)


def snapshot(paths: dict[str, Path] | None = None) -> dict:
    name = active()
    s = SCENARIOS[name]
    batt = SimulatedBattery().read()
    storage = {}
    for k, p in (paths or {}).items():
        if k == "ssd" and not s["ssd"]:
            storage[k] = t.unavailable(f"scenario {name}: the external SSD was removed").as_dict()
        else:
            storage[k] = {**t.disk(Path(p)).as_dict(), "source": "simulated",
                          "note": f"scenario {name}: sizes are this computer's, shown as simulated"}
    flags = s["throttled"]
    return {
        "simulated": True, "scenario": name, "scenario_title": s["title"],
        "device": _sim("Raspberry Pi 5 Model B (simulated)").as_dict(),
        "os": "Raspberry Pi OS 64-bit (simulated)",
        "cpu_temp": _sim(s["temp"], "°C").as_dict(), "thermal_status": t.thermal_status(s["temp"]),
        "throttling": _sim({"raw": "simulated", "now": flags, "since_boot": flags}).as_dict(),
        "cpu": _sim(s["cpu"], "%").as_dict(),
        "memory": _sim({"percent": s["mem"], "used": None, "total": None}, "%").as_dict(),
        "uptime": _sim(3600).as_dict(),
        "storage": storage, "network": _sim(s["network"]).as_dict(),
        "battery": batt.as_dict(), "battery_status": t.battery_status(batt),
    }
