"""Exception types raised by :mod:`adbtouch`."""

__all__ = ["AdbTouchError", "AdbNotFoundError", "AdbCommandError", "DeviceNotConnectedError", "TouchDeviceNotFoundError"]


class AdbTouchError(Exception):
    """Base class for every error raised by this library."""


class AdbNotFoundError(AdbTouchError):
    """The ``adb`` executable could not be located on this machine."""


class AdbCommandError(AdbTouchError):
    """An ``adb`` invocation exited with a non-zero status."""

    def __init__(self, args, returncode, stderr=""):
        self.args_list = list(args)
        self.returncode = returncode
        self.stderr = (stderr or "").strip()
        detail = f": {self.stderr}" if self.stderr else ""
        super().__init__(f"adb {' '.join(self.args_list)} failed with code {returncode}{detail}")


class DeviceNotConnectedError(AdbTouchError):
    """An operation needed a device but none was attached."""


class TouchDeviceNotFoundError(AdbTouchError):
    """No touchscreen input device could be detected on the device."""
