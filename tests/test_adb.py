import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adbtouch.adb import find_adb, run_adb
from adbtouch.errors import AdbCommandError, AdbNotFoundError


def make_fake_adb(directory: Path, body: str = "#!/bin/sh\nexit 0\n") -> Path:
    path = directory / "fake-adb"
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


class FindAdbTests(unittest.TestCase):
    def test_explicit_path_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp))
            self.assertEqual(find_adb(str(fake)), str(fake.resolve()))

    def test_env_var_is_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp))
            with mock.patch.dict(os.environ, {"ADB_PATH": str(fake)}):
                self.assertEqual(find_adb(), str(fake.resolve()))

    def test_falls_back_to_path_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp))
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch("adbtouch.adb.shutil.which", return_value=str(fake)):
                self.assertEqual(find_adb(), str(fake.resolve()))

    def test_missing_binary_raises_with_guidance(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch("adbtouch.adb.shutil.which", return_value=None), \
             mock.patch("adbtouch.adb.os.path.isfile", return_value=False):
            with self.assertRaises(AdbNotFoundError) as ctx:
                find_adb()
        self.assertIn("ADB_PATH", str(ctx.exception))

    def test_non_executable_candidate_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "adb"
            plain.write_text("not executable")
            plain.chmod(0o644)
            with mock.patch.dict(os.environ, {}, clear=True), \
                 mock.patch("adbtouch.adb.shutil.which", return_value=None):
                with self.assertRaises(AdbNotFoundError):
                    find_adb(str(plain))


class RunAdbTests(unittest.TestCase):
    def test_success_returns_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp), "#!/bin/sh\necho hello\n")
            self.assertEqual(run_adb(str(fake), ["devices"]).stdout.strip(), "hello")

    def test_failure_raises_instead_of_passing_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp), "#!/bin/sh\necho 'device offline' >&2\nexit 1\n")
            with self.assertRaises(AdbCommandError) as ctx:
                run_adb(str(fake), ["shell", "input", "tap", "1", "2"])
        self.assertEqual(ctx.exception.returncode, 1)
        self.assertIn("device offline", str(ctx.exception))

    def test_check_false_swallows_the_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp), "#!/bin/sh\nexit 3\n")
            self.assertEqual(run_adb(str(fake), ["x"], check=False).returncode, 3)

    def test_binary_mode_returns_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = make_fake_adb(Path(tmp), "#!/bin/sh\nprintf 'PNG'\n")
            self.assertEqual(run_adb(str(fake), ["exec-out"], binary=True).stdout, b"PNG")


if __name__ == "__main__":
    unittest.main()
