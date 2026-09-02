#!/usr/bin/env python3
"""独立评审包边界测试。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/build_review_package.py"


class ReviewPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.paper = self.base / "paper"
        self.paper.mkdir()
        (self.paper / "figures").mkdir()
        for name in ["07-paper-full.md", "03-evidence-matrix.csv", "12-final-qa-report.md", "14-adjudicated-status.json", "paper.docx", "paper.pdf"]:
            (self.paper / name).write_bytes(name.encode())
        (self.paper / "figures/figure-manifest.json").write_text('{"figures":[]}')
        (self.paper / "run-manifest.json").write_text(json.dumps({
            "direction_id": "general-journal-imrad", "docx": "paper.docx", "pdf": "paper.pdf"
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, output):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.paper), "--output", str(output)],
                              capture_output=True, text=True)

    def test_freezes_outside_without_scores(self):
        output = self.base / "eval/review-package.json"
        result = self.run_cli(output)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(output.read_text())
        self.assertIsNone(payload["writer_declared_scores"])
        self.assertEqual(len(payload["artifacts"]), 7)

    def test_refuses_output_inside_paper(self):
        self.assertNotEqual(self.run_cli(self.paper / "review-package.json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
