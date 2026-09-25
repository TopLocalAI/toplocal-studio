"""Hardware detection and the memory tier that decides which features are offered."""
import functools
import os
import platform
import re
import shutil
import subprocess

from . import config


def _sysctl(name: str) -> str:
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _windows_memory() -> int:
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    return status.ullTotalPhys if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else 0


def memory_gb() -> float:
    if config.IS_WINDOWS:
        return _windows_memory() / 1024**3
    if config.IS_MAC:
        raw = _sysctl("hw.memsize")
        if raw.isdigit():
            return int(raw) / 1024**3
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3
    except (ValueError, OSError, AttributeError):
        return 0.0


# Remote-desktop and fallback adapters that are not the GPU doing the work.
_VIRTUAL_GPU = re.compile(r"oray|idd|virtual|basic|remote|parsec|citrix|meta|sunlogin|todesk|rdp", re.I)
_DISCRETE_GPU = re.compile(r"nvidia|geforce|rtx|quadro|radeon|amd|arc", re.I)


def pick_gpu(names: list[str]) -> str:
    """The adapter to show: a discrete GPU first, then any real one, skipping virtual displays."""
    real = [n for n in names if n and not _VIRTUAL_GPU.search(n)]
    return next((n for n in real if _DISCRETE_GPU.search(n)), real[0] if real else "")


def _windows_gpu() -> str:
    """Name of the main display adapter (best effort; used only for display)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name"],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000).stdout
        return pick_gpu([line.strip() for line in out.splitlines()])
    except (OSError, subprocess.SubprocessError):
        return ""


def chip_name() -> str:
    if config.IS_MAC:
        return _sysctl("machdep.cpu.brand_string") or platform.processor()
    if config.IS_WINDOWS:
        return _windows_gpu() or platform.processor() or platform.machine()
    return platform.processor() or platform.machine()


def tier(mem_gb: float) -> str:
    """16 = 16 GB class, 32 = 24–32 GB class, 64 = 48 GB and above (measured thresholds)."""
    if mem_gb >= 46:
        return "64"
    if mem_gb >= 22:
        return "32"
    return "16"


@functools.cache
def _chip() -> str:
    return chip_name()


def info() -> dict:
    mem = memory_gb()
    usage = shutil.disk_usage(config.DATA_DIR if config.DATA_DIR.exists() else config.REPO_DIR)
    return {
        "os": "macOS" if config.IS_MAC else platform.system(),
        "osVersion": platform.mac_ver()[0] if config.IS_MAC else platform.release(),
        "arch": platform.machine(),
        "chip": _chip(),
        "memoryGb": round(mem, 1),
        "tier": tier(mem),
        "diskFreeGb": round(usage.free / 1024**3, 1),
        "diskTotalGb": round(usage.total / 1024**3, 1),
        "backend": config.AUDIOCPP_BACKEND,
    }
