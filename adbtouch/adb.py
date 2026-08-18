"""Locating and invoking the ``adb`` executable in a portable way."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .errors import AdbCommandError, AdbNotFoundError

__all__ = ["find_adb", "run_adb", "popen_adb", "no_window_kwargs"]

#: Locations checked after ``PATH``, so the tool works on a machine where the
#: Android SDK was installed but never added to the shell environment.
_FALLBACKS = {
    "win32": [
        r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe",
        r"%PROGRAMFILES%\Android\android-sdk\platform-tools\adb.exe",
        r"%PROGRAMFILES(X86)%\Android\android-sdk\platform-tools\adb.exe",
    ],
    "darwin": [
        "~/Library/Android/sdk/platform-tools/adb",
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
    ],
    "linux": [
        "~/Android/Sdk/platform-tools/adb",
        "~/android-sdk/platform-tools/adb",
        "/usr/lib/android-sdk/platform-tools/adb",
        "/snap/bin/adb",
    ],
}


def _platform_key() -> str:
    if sys.platform.startswith("win"):
        return "win32"
    if sys.platform == "darwin":
        return "darwin"
    return "linux"


def no_window_kwargs() -> dict:
    """Keyword arguments that stop Windows from flashing a console window.

    Returns an empty dict everywhere else, so callers can splat it unconditionally.
    """
    if sys.platform.startswith("win"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": startupinfo, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    return {}


def find_adb(explicit: str | None = None) -> str:
    """Return a usable path to ``adb``.

    Resolution order: explicit argument, ``ADB_PATH`` environment variable,
    ``PATH``, a bundled binary next to the current working directory, then the
    default SDK location for the running platform.

    Raises:
        AdbNotFoundError: if no candidate exists.
    """
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    env = os.environ.get("ADB_PATH")
    if env:
        candidates.append(env)

    on_path = shutil.which("adb")
    if on_path:
        candidates.append(on_path)

    for local in ("adb", "adb.exe"):
        candidates.append(str(Path.cwd() / local))

    for raw in _FALLBACKS[_platform_key()]:
        candidates.append(os.path.expandvars(os.path.expanduser(raw)))

    for candidate in candidates:
        if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)

    raise AdbNotFoundError(
        "Could not find the 'adb' executable. Install Android platform-tools, "
        "or point the ADB_PATH environment variable at it."
    )


def run_adb(adb_path: str, args, *, timeout: float | None = 30.0, check: bool = True, binary: bool = False):
    """Run ``adb`` with *args* and return the :class:`subprocess.CompletedProcess`.

    Unlike a bare ``subprocess.run`` this raises :class:`AdbCommandError` on a
    non-zero exit status, so failures surface instead of being silently ignored.
    """
    cmd = [adb_path, *[str(a) for a in args]]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=not binary,
        timeout=timeout,
        **no_window_kwargs(),
    )
    if check and proc.returncode != 0:
        stderr = proc.stderr if not binary else proc.stderr.decode("utf-8", "replace")
        raise AdbCommandError(args, proc.returncode, stderr)
    return proc


def popen_adb(adb_path: str, args) -> subprocess.Popen:
    """Start a long-running ``adb`` command and return the live process."""
    cmd = [adb_path, *[str(a) for a in args]]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **no_window_kwargs(),
    )
