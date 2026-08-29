#!/usr/bin/env python3
"""最终权威状态裁决器的隔离测试。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "adjudicate_status.py"
SPEC = importlib.util.spec_from_file_location("adjudicate_status", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AdjudicateStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "figures").mkdir()
        (self.root / "equations").mkdir()
        self.manifest = {
            "research_claim_level": "DESIGN_ONLY",
            "research_status": "PASS", "delivery_status": "PASS", "final_status": "PASS",
            "evidence_verification_report": "04-evidence-verification.json",
            "figure_verification_report": "figures/figure-verification.json",
            "formula_verification_report": "equations/formula-verification.json",
            "delivery_verification_report": "13-delivery-verification.json",
        }
        self.reports = {
            "evidence": {"status": "EVIDENCE_OK"},
            "figure": {"status": "STRUCTURE_OK", "mechanical_status": "PASS", "visual_status": "PASS"},
            "formula": {"status": "FORMULA_OK"},
            "delivery": {"status": "DELIVERY_OK"},
        }
        (self.root / "artifact.txt").write_text("稳定输入", encoding="utf-8")
        self.write_all()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def report_path(self, name: str) -> Path:
        spec = MODULE.REPORT_SPECS[name]
        return self.root / spec["default"]

    def write_all(self) -> None:
        (self.root / "run-manifest.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8"
        )
        for name, payload in self.reports.items():
            spec = MODULE.REPORT_SPECS[name]
            script = MODULE.SKILL_ROOT / "scripts" / spec["script"]
            complete = dict(payload)
            complete["verifier"] = {
                "name": spec["script"], "sha256": MODULE.sha256(script), "version": "1.4.0",
            }
            complete["input_sha256"] = {"artifact.txt": MODULE.sha256(self.root / "artifact.txt")}
            path = self.report_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(complete, ensure_ascii=False), encoding="utf-8")

    def adjudicate(self):
        adjudicator = MODULE.StatusAdjudicator(self.root)
        manifest = adjudicator.load_manifest(self.root / "run-manifest.json")
        adjudicator.load_reports(manifest)
        derived = adjudicator.derive(manifest)
        return adjudicator, derived

    def test_design_only_caps_research_at_partial(self) -> None:
        adjudicator, derived = self.adjudicate()
        self.assertEqual(derived, {
            "research_status": "PARTIAL", "delivery_status": "PASS", "final_status": "PARTIAL",
        })
        self.assertTrue(any("research_status" in item for item in adjudicator.conflicts))

    def test_observed_study_can_pass(self) -> None:
        self.manifest["research_claim_level"] = "OBSERVED_STUDY"
        self.write_all()
        adjudicator, derived = self.adjudicate()
        self.assertEqual(adjudicator.errors, [])
        self.assertEqual(derived["final_status"], "PASS")

    def test_evidence_failure_forces_final_failure(self) -> None:
        self.reports["evidence"]["status"] = "EVIDENCE_FAIL"
        self.write_all()
        _, derived = self.adjudicate()
        self.assertEqual(derived["research_status"], "FAIL")
        self.assertEqual(derived["final_status"], "FAIL")

    def test_visual_partial_caps_delivery(self) -> None:
        self.manifest["research_claim_level"] = "OBSERVED_STUDY"
        self.reports["figure"]["visual_status"] = "PARTIAL"
        self.write_all()
        _, derived = self.adjudicate()
        self.assertEqual(derived["delivery_status"], "PARTIAL")
        self.assertEqual(derived["final_status"], "PARTIAL")

    def test_stale_verifier_hash_forces_failure(self) -> None:
        self.write_all()
        path = self.report_path("formula")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["verifier"]["sha256"] = "0" * 64
        path.write_text(json.dumps(payload), encoding="utf-8")
        adjudicator, derived = self.adjudicate()
        self.assertTrue(any("REPORT_VERIFIER_STALE" in item for item in adjudicator.errors))
        self.assertEqual(derived["final_status"], "FAIL")

    def test_changed_report_input_forces_failure(self) -> None:
        self.write_all()
        (self.root / "artifact.txt").write_text("检查后被修改", encoding="utf-8")
        adjudicator, derived = self.adjudicate()
        self.assertTrue(any("REPORT_INPUT_STALE" in item for item in adjudicator.errors))
        self.assertEqual(derived["final_status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
