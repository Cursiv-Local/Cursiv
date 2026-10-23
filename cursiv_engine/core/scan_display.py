"""
Rolling scan display — slow scrolling log of system activity.
Prints one line per event to stdout. No cursor control.
Used by chat_app.py's rate limiter to log activity.
"""
from __future__ import annotations

import sys

GOLD   = "\033[38;5;220m"   # Egyptian gold — routing, icons
LGOLD  = "\033[38;5;136m"   # Deep antique gold — frames
SILVER = "\033[38;5;253m"   # Bright silver
SILV2  = "\033[38;5;245m"   # Dim silver — file paths, secondary
LAPIS  = "\033[38;5;27m"    # Lapis lazuli — agent awake
LAPIS2 = "\033[38;5;69m"    # Light lapis
CREAM  = "\033[38;5;230m"   # Ivory cream
DIM    = "\033[2m"
RED    = "\033[38;5;196m"
GREEN  = "\033[38;5;82m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def _tpm_bar(used: int, target: int, width: int = 12) -> str:
    pct    = min(used / max(target, 1), 1.0)
    filled = int(pct * width)
    bar    = "█" * filled + "░" * (width - filled)
    color  = GREEN if pct < 0.70 else (LGOLD if pct < 0.90 else RED)
    return f"{color}{bar}{RESET}"


def _trunc(path: str, maxlen: int = 55) -> str:
    return ("…" + path[-(maxlen - 1):]) if len(path) > maxlen else path


class ScanDisplay:
    """
    Accepts an optional rate_limiter reference (TokenRateLimiter).
    If provided, appends a live TPM bar to each status line.
    """

    def __init__(self, rate_limiter=None) -> None:
        self._rl = rate_limiter

    def _tpm_suffix(self) -> str:
        if not self._rl:
            return ""
        used   = self._rl.current_tpm()
        target = self._rl.target
        bar    = _tpm_bar(used, target)
        return f"  {bar}  {DIM}{used:,} / {target:,} tpm{RESET}"

    def _emit(self, line: str) -> None:
        print(line, flush=True)

    def routing(self, provider: str) -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {GOLD}⟳{RESET}  Routing to {GOLD}{BOLD}{provider}{RESET}...{sfx}")

    def guardian_scan(self, result: str = "clean") -> None:
        color = GREEN if result == "clean" else RED
        sfx   = self._tpm_suffix()
        self._emit(f"  {LAPIS}◈{RESET}  Guardian: {color}{result}{RESET}{sfx}")

    def agent_wake(self, name: str) -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {LAPIS}⬢{RESET}  {GOLD}{BOLD}{name}{RESET} awakening...{sfx}")

    def agent_sleep(self, name: str) -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {SILV2}⬡  {name} complete{RESET}{sfx}")

    def file_scan(self, path: str) -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {SILV2}▸  reading {_trunc(path)}{RESET}{sfx}")

    def dir_scan(self, path: str) -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {SILV2}▸  scanning {_trunc(path)}/{RESET}{sfx}")

    def throttling(self, used: int, target: int) -> None:
        bar = _tpm_bar(used, target)
        self._emit(
            f"  {GOLD}⚠{RESET}  Rate gate — pacing...  "
            f"{bar}  {SILV2}{used:,} / {target:,} tpm{RESET}"
        )

    def nexus_record(self) -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {SILV2}◉  Nexus recording{RESET}{sfx}")

    def complete(self, label: str = "Strand complete") -> None:
        sfx = self._tpm_suffix()
        self._emit(f"  {GREEN}✔{RESET}  {label}{sfx}")

    def blocked(self, reason: str = "Guardian blocked") -> None:
        self._emit(f"  {RED}⛔  {reason}{RESET}")


# Default singleton with no limiter.
# A caller can replace this after importing the rate limiter:
#   from cursiv_engine.core.rate_limiter import limiter
#   from cursiv_engine.core.scan_display import ScanDisplay
#   scan = ScanDisplay(limiter)
display = ScanDisplay()
