"""
Running untrusted code under limits the operating system enforces (U102).

Plugins, Forge's plugin self-test and Codex test runs already run in their own process under a
Python audit hook (core/plugin_runner.py). An audit hook is not a sandbox: code that finds a way
round it, or simply uses too much memory or CPU, isn't stopped by it. This adds limits enforced
outside Python.

Windows: the child starts SUSPENDED, is placed in a Job Object, and only then runs. The job allows
no further processes (so no shell, no other program, even if the hook were bypassed), caps memory
and CPU time, blocks the clipboard and other desktop access, and kills the child when Cursiv's job
handle closes. If any step fails the child is killed and nothing runs: there is no fallback to an
unconfined run.

macOS and Linux: resource limits (CPU time, file size, address space where supported) set in the
child before it starts. These are weaker (there is no "no child processes" limit here that doesn't
also count the person's other programs), and docs/THREAT-MODEL.md says so.
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass

CREATE_SUSPENDED = 0x00000004
CREATE_NO_WINDOW = 0x08000000


class ConfinementError(OSError):
    """The OS limits couldn't be applied, so the code was not run."""


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str
    limit: str = ""            # which OS limit stopped it, when one did ("memory", "time", ...)


# ── Windows Job Objects ──────────────────────────────────────────────────────

def _windows_job(memory_mb: int, cpu_seconds: int):
    import ctypes
    from ctypes import wintypes

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in ("ReadOperationCount", "WriteOperationCount",
                    "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class BASIC(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong), ("PerJobUserTimeLimit", ctypes.c_longlong),
                    ("LimitFlags", wintypes.DWORD), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class EXTENDED(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    class UI(ctypes.Structure):
        _fields_ = [("UIRestrictionsClass", wintypes.DWORD)]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    k32.SetInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD)
    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise ConfinementError(f"CreateJobObject failed ({ctypes.get_last_error()})")
    info = EXTENDED()
    b = info.BasicLimitInformation
    b.LimitFlags = (0x00000002      # PROCESS_TIME
                    | 0x00000008    # ACTIVE_PROCESS
                    | 0x00000100    # PROCESS_MEMORY
                    | 0x00000400    # DIE_ON_UNHANDLED_EXCEPTION
                    | 0x00002000)   # KILL_ON_JOB_CLOSE
    b.ActiveProcessLimit = 1
    b.PerProcessUserTimeLimit = int(cpu_seconds * 10_000_000)       # 100-ns units
    info.ProcessMemoryLimit = int(memory_mb) << 20
    if not k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info)):     # ExtendedLimit
        err = ctypes.get_last_error()
        k32.CloseHandle(job)
        raise ConfinementError(f"SetInformationJobObject (limits) failed ({err})")
    ui = UI(0x000000FF)              # handles, clipboard read/write, system parameters, desktop, display, exit, atoms
    if not k32.SetInformationJobObject(job, 4, ctypes.byref(ui), ctypes.sizeof(ui)):        # BasicUIRestrictions
        err = ctypes.get_last_error()
        k32.CloseHandle(job)
        raise ConfinementError(f"SetInformationJobObject (UI) failed ({err})")
    return k32, job


def _run_windows(cmd, *, input, timeout, env, cwd, memory_mb, cpu_seconds) -> Result:
    import ctypes
    k32, job = _windows_job(memory_mb, cpu_seconds)
    ntdll = ctypes.WinDLL("ntdll")
    p = None
    try:
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, encoding="utf-8", errors="replace", env=env, cwd=cwd,
                             creationflags=CREATE_SUSPENDED | CREATE_NO_WINDOW)
        handle = int(p._handle)                      # the process handle Popen keeps (CPython, Windows)
        if not k32.AssignProcessToJobObject(job, handle):
            raise ConfinementError(f"AssignProcessToJobObject failed ({ctypes.get_last_error()})")
        if ntdll.NtResumeProcess(ctypes.c_void_p(handle)) != 0:
            raise ConfinementError("the confined process couldn't be started")
        try:
            out, err = p.communicate(input=input, timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
            raise
        limit = ""
        if p.returncode == 0xC0000044:                            # STATUS_QUOTA_EXCEEDED: the CPU-time cap
            limit = "time"
        elif p.returncode != 0 and "MemoryError" in (err or ""):
            limit = "memory"
        return Result(p.returncode, out or "", err or "", limit)
    except BaseException:
        if p is not None and p.poll() is None:
            p.kill()                                 # never left running, suspended or not
        raise
    finally:
        k32.CloseHandle(job)                         # KILL_ON_JOB_CLOSE: anything still in the job ends here


# ── POSIX resource limits ────────────────────────────────────────────────────

def _posix_limits(memory_mb: int, cpu_seconds: int):
    def apply():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))
        try:
            resource.setrlimit(resource.RLIMIT_AS, (memory_mb << 20, memory_mb << 20))
        except (ValueError, OSError):
            pass                                     # macOS doesn't enforce an address-space limit
        os.setsid()                                  # its own session: never part of Cursiv's terminal
    return apply


_REAL: dict[str, str] = {}


def real_python(exe: str) -> str:
    """The interpreter that actually runs, not a launcher. A venv's python.exe and the `py` launcher
    start the real python.exe as a second process, which the Job Object's one-process limit refuses.
    Asked once per launcher with fixed code (nothing untrusted runs here)."""
    if exe in _REAL:
        return _REAL[exe]
    probe = "import sys; print(getattr(sys, '_base_executable', '') or sys.executable)"
    out = subprocess.run([exe, "-I", "-c", probe], capture_output=True, text=True, timeout=20,
                         creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0).stdout.strip()
    _REAL[exe] = out if out and os.path.isfile(out) else exe
    return _REAL[exe]


def run(cmd: list[str], *, input: str = "", timeout: float = 20, env: dict | None = None, cwd: str | None = None,
        memory_mb: int = 768, cpu_seconds: int | None = None) -> Result:
    """Run cmd confined. Raises subprocess.TimeoutExpired, or ConfinementError when the limits
    can't be applied (then nothing ran)."""
    cpu = int(cpu_seconds or max(2, timeout))
    if os.name == "nt":
        return _run_windows(cmd, input=input, timeout=timeout, env=env, cwd=cwd, memory_mb=memory_mb, cpu_seconds=cpu)
    p = subprocess.run(cmd, input=input, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout, env=env, cwd=cwd, preexec_fn=_posix_limits(memory_mb, cpu))
    return Result(p.returncode, p.stdout or "", p.stderr or "")


def describe() -> str:
    """What this computer enforces, for docs and `self` answers."""
    if os.name == "nt":
        return ("Windows Job Object: no child processes, memory and CPU-time caps, no clipboard or desktop access, "
                "killed with Cursiv; plus the Python audit hook.")
    return ("Resource limits (CPU time, file size, memory where the system enforces it) plus the Python audit hook; "
            f"{sys.platform} has no 'no child processes' limit here.")
