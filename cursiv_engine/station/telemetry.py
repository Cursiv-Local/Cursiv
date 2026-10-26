"""
Field Station hardware readings: CPU temperature, throttling and undervoltage, CPU and memory use,
storage, and battery. Every value is a Reading that says where it came from:

  real         read from the operating system or a device just now
  derived      worked out from real readings (a percentage of two real numbers)
  simulated    from a named test scenario (station.simulation); never shown as real
  unavailable  this hardware doesn't report it (an ordinary USB-C power bank has no charge level)

A reading older than STALE_S is marked stale. Nothing here estimates a value it can't read: no battery
percentage from elapsed time or load, no temperature from anything but a sensor.
"""
from __future__ import annotations

import platform
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

STALE_S = 30

# Advisory thresholds (°C) the owner can change; not hardware safety limits. The firmware's own throttle
# flags (vcgencmd get_throttled) say what the Pi is actually doing.
THERMAL_DEFAULTS = {"elevated": 65.0, "high": 75.0, "critical": 80.0}
BATTERY_DEFAULTS = {"low": 25.0, "critical": 15.0, "prepare_shutdown": 10.0}


@dataclass
class Reading:
    value: object = None
    unit: str = ""
    source: str = "unavailable"          # real | derived | simulated | unavailable
    at: float = 0.0
    note: str = ""

    def stale(self, now: float | None = None) -> bool:
        return self.source in ("real", "derived") and (now or time.time()) - self.at > STALE_S

    def as_dict(self, now: float | None = None) -> dict:
        d = asdict(self)
        d["stale"] = self.stale(now)
        return d


def _real(value, unit="", note="") -> Reading:
    return Reading(value, unit, "real", time.time(), note)


def unavailable(note: str) -> Reading:
    return Reading(None, "", "unavailable", time.time(), note)


# ── temperature ───────────────────────────────────────────────────────────────

THERMAL_ROOT = Path("/sys/class/thermal")


def _zone_temp(zone: Path) -> int | None:
    try:
        milli = int((zone / "temp").read_text().strip())
    except (OSError, ValueError):
        return None
    return milli if -40_000 <= milli <= 150_000 else None


def find_cpu_sensor(root: Path = THERMAL_ROOT) -> Path | None:
    """The thermal zone for the CPU: the one whose type names the CPU or SoC (cpu-thermal on a Pi 5),
    else the first zone with a plausible reading. Not every board has zone0, or names it."""
    zones = sorted(root.glob("thermal_zone*")) if root.is_dir() else []
    for z in zones:
        try:
            kind = (z / "type").read_text().strip().lower()
        except OSError:
            continue
        if ("cpu" in kind or "soc" in kind) and _zone_temp(z) is not None:
            return z
    return next((z for z in zones if _zone_temp(z) is not None), None)


def cpu_temperature(root: Path = THERMAL_ROOT) -> Reading:
    zone = find_cpu_sensor(root)
    if zone is None:
        return unavailable("no CPU temperature sensor found on this system")
    milli = _zone_temp(zone)
    if milli is None:
        return unavailable("the CPU temperature sensor gave no plausible reading")
    try:
        kind = (zone / "type").read_text().strip()
    except OSError:
        kind = "unknown type"
    return _real(round(milli / 1000, 1), "°C", f"{zone.name} ({kind})")


def thermal_status(temp_c, limits: dict | None = None) -> str:
    if temp_c is None:
        return "unknown"
    t = limits or THERMAL_DEFAULTS
    if temp_c >= t["critical"]:
        return "critical"
    if temp_c >= t["high"]:
        return "high"
    if temp_c >= t["elevated"]:
        return "elevated"
    return "normal"


# ── throttling (Raspberry Pi firmware) ───────────────────────────────────────
# `vcgencmd get_throttled` prints "throttled=0x50005": bits 0-3 are happening now, 16-19 since boot.

THROTTLE_BITS = {0: "undervoltage", 1: "frequency capped", 2: "throttled", 3: "soft temperature limit"}


def parse_throttled(text: str) -> dict:
    value = int(text.strip().split("=", 1)[1], 16)
    now = [name for bit, name in THROTTLE_BITS.items() if value & (1 << bit)]
    since = [name for bit, name in THROTTLE_BITS.items() if value & (1 << (bit + 16))]
    return {"raw": hex(value), "now": now, "since_boot": since}


def throttling(run=subprocess.run) -> Reading:
    exe = shutil.which("vcgencmd")
    if not exe:
        return unavailable("vcgencmd isn't installed (it comes with Raspberry Pi OS)")
    try:
        out = run([exe, "get_throttled"], capture_output=True, text=True, timeout=3, check=True).stdout
        return _real(parse_throttled(out), "", "vcgencmd get_throttled")
    except (OSError, ValueError, IndexError, subprocess.SubprocessError) as exc:
        return unavailable(f"vcgencmd get_throttled failed ({type(exc).__name__})")


# ── CPU, memory, uptime, storage, board ──────────────────────────────────────

def cpu_percent() -> Reading:
    try:
        import psutil
        return _real(psutil.cpu_percent(interval=None), "%", "psutil")
    except Exception as exc:  # psutil missing or refused: say so, never guess
        return unavailable(f"CPU use couldn't be read ({type(exc).__name__})")


def memory() -> Reading:
    try:
        import psutil
        m = psutil.virtual_memory()
        return _real({"percent": m.percent, "used": m.used, "total": m.total}, "%", "psutil")
    except Exception as exc:  # psutil missing or refused: say so, never guess
        return unavailable(f"memory use couldn't be read ({type(exc).__name__})")


def uptime() -> Reading:
    try:
        import psutil
        return _real(int(time.time() - psutil.boot_time()), "s", "psutil")
    except Exception as exc:  # psutil missing or refused: say so, never guess
        return unavailable(f"uptime couldn't be read ({type(exc).__name__})")


def disk(path: Path) -> Reading:
    try:
        u = shutil.disk_usage(path)
    except OSError as exc:
        return unavailable(f"{path} isn't available ({exc.strerror or type(exc).__name__})")
    return Reading({"total": u.total, "used": u.used, "free": u.free,
                    "percent": round(u.used * 100 / u.total, 1) if u.total else None},
                   "bytes", "derived", time.time(), str(path))


def device_model() -> Reading:
    """The board's own name (a Pi writes it to the device tree), else the OS's machine type."""
    for p in (Path("/proc/device-tree/model"), Path("/sys/firmware/devicetree/base/model")):
        try:
            return _real(p.read_text().strip("\x00\n "), "", str(p))
        except OSError:
            continue
    return _real(f"{platform.system()} {platform.machine()}", "", "platform (not a Raspberry Pi device tree)")


# ── battery ──────────────────────────────────────────────────────────────────

BATTERY_FIELDS = ("detected", "model", "percent", "voltage", "current", "power_w", "charging",
                  "external_power", "runtime_min")


@dataclass
class Battery:
    provider: str
    readings: dict = field(default_factory=dict)        # field -> Reading

    def get(self, name: str) -> Reading:
        return self.readings.get(name) or unavailable("this power source doesn't report it")

    def as_dict(self) -> dict:
        now = time.time()
        return {"provider": self.provider, **{f: self.get(f).as_dict(now) for f in BATTERY_FIELDS}}


NO_TELEMETRY = ("Battery telemetry unavailable. An external power source may be connected, but its charge "
                "can't be determined.")


class NoBattery:
    """An ordinary USB-C power bank: it powers the Pi but tells it nothing."""
    name = "unavailable"

    def read(self) -> Battery:
        return Battery(self.name, {f: unavailable(NO_TELEMETRY) for f in BATTERY_FIELDS})


class SysfsBattery:
    """A battery the Linux kernel knows about (/sys/class/power_supply/<name>/), as some UPS boards for
    the Pi register. Only the files present are reported; nothing is filled in."""
    name = "linux power_supply"

    def __init__(self, folder: Path):
        self.folder = folder

    @staticmethod
    def find(root: Path = Path("/sys/class/power_supply")) -> "SysfsBattery | None":
        for d in sorted(root.glob("*")) if root.is_dir() else []:
            try:
                if (d / "type").read_text().strip().lower() == "battery":
                    return SysfsBattery(d)
            except OSError:
                continue
        return None

    def _num(self, name: str, scale: float = 1.0):
        try:
            return float((self.folder / name).read_text().strip()) * scale
        except (OSError, ValueError):
            return None

    def read(self) -> Battery:
        r: dict[str, Reading] = {"detected": _real(True, "", str(self.folder))}
        try:
            r["model"] = _real((self.folder / "model_name").read_text().strip())
        except OSError:
            pass
        for key, file, unit, scale in (("percent", "capacity", "%", 1.0), ("voltage", "voltage_now", "V", 1e-6),
                                       ("current", "current_now", "A", 1e-6), ("power_w", "power_now", "W", 1e-6)):
            v = self._num(file, scale)
            if v is not None:
                r[key] = _real(round(v, 2), unit, f"{self.folder.name}/{file}")
        try:
            status = (self.folder / "status").read_text().strip()
            r["charging"] = _real(status.lower() == "charging", "", f"status: {status}")
        except OSError:
            pass
        return Battery(self.name, r)


def battery_provider():
    from cursiv_engine.station import simulation
    if simulation.active():
        return simulation.SimulatedBattery()
    return SysfsBattery.find() or NoBattery()


def battery_status(b: Battery, limits: dict | None = None) -> str:
    """Advice from a real (or labelled simulated) charge level only; 'unknown' without one."""
    p = b.get("percent")
    if p.source not in ("real", "simulated") or p.value is None:
        return "unknown"
    t = limits or BATTERY_DEFAULTS
    if p.value <= t["prepare_shutdown"]:
        return "prepare shutdown"
    if p.value <= t["critical"]:
        return "critical"
    if p.value <= t["low"]:
        return "low"
    return "ok"


# ── one snapshot for the Health page ─────────────────────────────────────────

def snapshot(paths: dict[str, Path] | None = None) -> dict:
    """Everything the Health page shows. Simulation (if on) replaces the hardware readings only."""
    from cursiv_engine.station import simulation
    if simulation.active():
        return simulation.snapshot(paths)
    temp = cpu_temperature()
    batt = battery_provider().read()
    now = time.time()
    return {
        "simulated": False,
        "device": device_model().as_dict(now),
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "cpu_temp": temp.as_dict(now), "thermal_status": thermal_status(temp.value),
        "throttling": throttling().as_dict(now),
        "cpu": cpu_percent().as_dict(now), "memory": memory().as_dict(now), "uptime": uptime().as_dict(now),
        "storage": {k: disk(Path(p)).as_dict(now) for k, p in (paths or {}).items()},
        "battery": batt.as_dict(), "battery_status": battery_status(batt),
    }
