"""gfx kit JavaScript checks: each doc_renderer/gfx_kit/tests/*.test.cjs is a Node script that exits non-zero on failure.

Run one script with GFX_JS=<stem>, e.g. GFX_JS=motion python -m unittest tests.test_gfx_kit_js -v
"""

from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = sorted((ROOT / "doc_renderer/gfx_kit/tests").glob("*.test.cjs"))


class GfxKitJsTest(unittest.TestCase):
    def test_scripts(self) -> None:
        only = os.environ.get("GFX_JS")
        scripts = [s for s in SCRIPTS if not only or s.name.split(".")[0] in only.split(",")]
        self.assertTrue(scripts, "no gfx kit test scripts matched")
        for script in scripts:
            with self.subTest(script=script.name):
                r = subprocess.run(["node", str(script)], capture_output=True, text=True, encoding="utf-8", timeout=600)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
