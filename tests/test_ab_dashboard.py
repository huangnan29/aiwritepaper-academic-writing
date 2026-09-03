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

    def test_case_manifest_overrides_central_status(self):
        (self.root / "case-manifest.json").write_text(json.dumps({**self.case, "status": "RUNNING"}))
        result = MODULE.infer({**self.case, "status": "PENDING"})
        self.assertEqual(result["status"], "RUNNING")
        self.assertEqual(result["progress"], 4)

    def test_lean_scope_selects_fixed_benchmark_set(self):
        cases = []
        for case_id in [
            "grok__review__B", "grok__apos__B", "grok__circuit__B",
            "antigravity__apos__B", "antigravity__review__B", "antigravity__circuit__B",
            "grok__review__A",
        ]:
            directory = self.root / case_id
            directory.mkdir()
            agent = case_id.split("__", 1)[0]
            cases.append({"case_id": case_id, "directory": str(directory), "status": "PENDING",
                          "agent_label": agent, "title": "题目", "version": "v2.1.0-rc.2"})
        (self.root / "ab-manifest.json").write_text(json.dumps({
            "cases": cases, "randomized_order": [case["case_id"] for case in reversed(cases)]
        }))
        result = MODULE.snapshot(self.root, "lean")
        self.assertEqual(len(result["cases"]), 6)
        self.assertEqual(result["cases"][0]["case_id"], "grok__review__B")
        self.assertNotIn("grok__review__A", {row["case_id"] for row in result["cases"]})


if __name__ == "__main__":
    unittest.main()
