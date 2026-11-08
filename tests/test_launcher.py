"""Smoke tests for the POSIX launcher, independent of the actual app backend."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def test_incomplete_installation_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copyfile(ROOT / "run.sh", root / "run.sh")
            (root / "server.py").write_text("print('server started')", encoding="utf-8")
            (root / "vvz_dump.py").write_text("", encoding="utf-8")
            (root / "web").mkdir()
            (root / "web" / "index.html").write_text("", encoding="utf-8")
            result = subprocess.run(["sh", str(root / "run.sh")],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("guidelines/cse-guidelines.json", result.stderr)
            self.assertIn("git clone", result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(sys.version_info >= (3, 10), "Needs Python >=3.10")
    def test_complete_installation_starts_from_its_own_directory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copyfile(ROOT / "run.sh", root / "run.sh")
            (root / "server.py").write_text(
                "from pathlib import Path\nimport sys\nprint('STARTED', Path.cwd(), sys.argv[1:])\n",
                encoding="utf-8",
            )
            (root / "vvz_dump.py").write_text("", encoding="utf-8")
            (root / "web").mkdir()
            (root / "web" / "index.html").write_text("", encoding="utf-8")
            (root / "guidelines").mkdir()
            (root / "guidelines" / "cse-guidelines.json").write_text("{}", encoding="utf-8")
            result = subprocess.run(["sh", str(root / "run.sh"), "--no-browser"],
                                    cwd=Path("/"), capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("STARTED", result.stdout)
            self.assertIn(str(root), result.stdout)
            self.assertIn("--no-browser", result.stdout)


if __name__ == "__main__":
    unittest.main()
