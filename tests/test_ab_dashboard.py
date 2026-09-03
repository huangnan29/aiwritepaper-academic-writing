#!/usr/bin/env python3
"""A/B动态进度推断测试。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ab_dashboard", ROOT / "eval/ab_dashboard.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.case = {"case_id": "c", "directory": str(self.root), "status": "RUNNING",
                     "agent_label": "Antigravity CLI", "title": "题目", "version": "v2.1.0-rc.2"}

    def tearDown(self):
        self.tmp.cleanup()

    def test_pending_and_delivery_progress(self):
        self.assertEqual(MODULE.infer({**self.case, "status": "PENDING"})["progress"], 0)
        (self.root / "final-execution-prompt.md").write_text("prompt")
        (self.root / "03-evidence-matrix.csv").write_text("source_id")
        (self.root / "07-paper-full.md").write_text("正文")
        evidence = self.root / "evidence"
        evidence.mkdir()
        (evidence / "source.pdf").write_bytes(b"evidence")
        self.assertLess(MODULE.infer(self.case)["progress"], 86)
        (self.root / "paper.docx").write_bytes(b"docx")
        (self.root / "paper.pdf").write_bytes(b"pdf")
        self.assertEqual(MODULE.infer(self.case)["progress"], 90)

    def test_adjudication_means_complete(self):
        (self.root / "14-adjudicated-status.json").write_text(json.dumps({"status": "ADJUDICATED_PARTIAL"}))
        self.assertEqual(MODULE.infer(self.case)["progress"], 99)
        self.case["status"] = "COMPLETE"
        self.assertEqual(MODULE.infer(self.case)["progress"], 100)

    def test_running_failed_adjudication_is_repairing(self):
        (self.root / "14-adjudicated-status.json").write_text(json.dumps({
            "authoritative_status": {"final_status": "FAIL"}
        }))
        result = MODULE.infer(self.case)
        self.assertEqual(result["progress"], 97)
        self.assertEqual(result["phase"], "返修与复验")

    def test_nested_output_updates_progress(self):
        output = self.root / "paper-output"
        output.mkdir()
        (output / "07-paper-full.md").write_text("正文")
        result = MODULE.infer(self.case)
        self.assertEqual(result["progress"], 68)
        self.assertEqual(result["artifact_root"], "paper-output")


if __name__ == "__main__":
    unittest.main()
