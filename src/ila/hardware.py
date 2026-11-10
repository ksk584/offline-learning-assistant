"""Hardware detection used to pick a model size that a machine can actually run.

Deliberately dependency-free: ``psutil`` is not installed in the base
environment, so RAM comes from the OS APIs through ``ctypes`` and core counts
from :mod:`os`. Everything is best-effort -- an unknown machine gets the
``balanced`` profile rather than an error.
"""

from __future__ import annotations

import ctypes
import os
import sys
from dataclasses import dataclass
from pathlib import Path

PROFILES = ("potato", "balanced", "full")


def total_ram_gb() -> float:
    """Total physical memory in GiB, or ``0.0`` when it cannot be determined."""
    try:
        if sys.platform == "win32":
            return _windows_ram_gb()
        return _unix_ram_gb()
    except Exception:  # pragma: no cover - platform specific
        return 0.0


def _windows_ram_gb() -> float:
    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("length", ctypes.c_ulong),
            ("memory_load", ctypes.c_ulong),
            ("total_phys", ctypes.c_ulonglong),
            ("avail_phys", ctypes.c_ulonglong),
            ("total_page", ctypes.c_ulonglong),
            ("avail_page", ctypes.c_ulonglong),
            ("total_virtual", ctypes.c_ulonglong),
            ("avail_virtual", ctypes.c_ulonglong),
            ("avail_extended", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.length = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):  # type: ignore[attr-defined]
        return 0.0
    return status.total_phys / (1024**3)


def _unix_ram_gb() -> float:
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / (1024**2)
        return 0.0
    try:  # macOS
        import subprocess

        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, check=True
        )
        return int(out.stdout.strip()) / (1024**3)
    except Exception:
        return 0.0


def physical_cores(logical: int | None = None) -> int:
    """Best-effort physical core count.

    SMT machines report twice the physical count, which is the common case for
    the laptops this project targets. Threads are capped at the physical count
    minus one because the LLM shares the CPU with audio capture.
    """
    logical = logical or os.cpu_count() or 1
    return max(1, logical // 2)


@dataclass(frozen=True, slots=True)
class Hardware:
    ram_gb: float
    logical_cores: int
    physical_cores: int
    platform: str
    suggested_profile: str
    reason: str

    @property
    def summary(self) -> str:
        ram = f"{self.ram_gb:.1f} GB" if self.ram_gb > 0 else "unknown RAM"
        return f"{self.platform} / {ram} / {self.physical_cores}C/{self.logical_cores}T"


def suggest_profile(ram_gb: float, logical_cores: int) -> tuple[str, str]:
    """Return ``(profile, reason)`` for the detected machine.

    The thresholds are intentionally conservative: a wrong guess towards the
    larger model is visible to the user as multi-second per-token latency.
    """
    if ram_gb and ram_gb < 6.5:
        return "potato", f"{ram_gb:.1f} GB RAM is below the 2B model's comfort zone"
    if logical_cores and logical_cores < 4:
        return "potato", f"only {logical_cores} CPU threads available"
    if ram_gb >= 15.5 and logical_cores >= 8:
        return "full", "16 GB+ RAM and 8+ threads can run the 4B model"
    if ram_gb <= 0:
        return "balanced", "RAM could not be detected; using the safe default"
    return "balanced", "8-16 GB RAM runs the 2B model comfortably"


def detect() -> Hardware:
    ram = total_ram_gb()
    logical = os.cpu_count() or 1
    cores = physical_cores(logical)
    profile, reason = suggest_profile(ram, logical)
    return Hardware(
        ram_gb=round(ram, 1),
        logical_cores=logical,
        physical_cores=cores,
        platform=sys.platform,
        suggested_profile=profile,
        reason=reason,
    )
