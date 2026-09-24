"""Process helpers that differ between POSIX and Windows.

Engines run in their own process group (POSIX) or process tree (Windows) so a cancel
stops the engine and anything it spawned. On Windows they also run without a console
window, which would otherwise flash up for every generation.
"""
import os
import signal
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200


def spawn_kwargs() -> dict:
    """Extra keyword arguments for subprocess / asyncio.create_subprocess_exec."""
    if IS_WINDOWS:
        return {"creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def kill_tree(pid: int) -> None:
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True,
                       creationflags=CREATE_NO_WINDOW)
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


def is_alive(pid: int) -> bool:
    """True while `pid` runs. Never use os.kill(pid, 0) on Windows: it terminates the process."""
    if IS_WINDOWS:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5  # access denied: exists but not ours
        try:
            code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def reveal(path) -> None:
    """Show a file in Finder / Explorer."""
    if sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    elif IS_WINDOWS:
        subprocess.Popen(["explorer", "/select,", str(path)], creationflags=CREATE_NO_WINDOW)
