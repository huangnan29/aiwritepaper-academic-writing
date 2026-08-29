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
            "execution_profile": "FULL_AUTONOMY",
            "run_mode": "FULL_BUILD",
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
                "name": spec["script"], "sha256": MODULE.sha256(script), "version": "1.6.0",
            }
            complete["input_sha256"] = {"artifact.txt": MODULE.sha256(self.root / "artifact.txt")}
            path = self.report_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(complete, ensure_ascii=False), encoding="utf-8")

    def adjudicate(self):
        adjudicator = MODULE.StatusAdjudicator(self.root)
        manifest = adjudicator.load_manifest(self.root / "run-manifest.json")
        adjudicator.validate_execution_checkpoints(manifest)
        adjudicator.validate_revision_impact(manifest)
        adjudicator.load_reports(manifest)
        derived = adjudicator.derive(manifest)
        return adjudicator, derived

    def write_skip(self, name: str, status: str, mode: str) -> None:
        path = self.report_path(name)
        payload = {
            "schema_version": "1.0", "status": status, "category": name, "mode": mode,
            "reason": "测试模式不适用", "inherited": None,
            "input_sha256": {"artifact.txt": MODULE.sha256(self.root / "artifact.txt")},
            "verifier": {
                "name": "write_skipped_report.py",
                "version": "1.6.0",
                "sha256": MODULE.sha256(MODULE.SKILL_ROOT / "scripts/write_skipped_report.py"),
            },
        }
        path.write_text(json.dumps(payload), encoding="utf-8")

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

    def test_guided_requires_closed_hashed_checkpoints(self) -> None:
        self.manifest["execution_profile"] = "GUIDED"
        checkpoint_output = self.root / "stage.md"
        checkpoint_output.write_text("阶段产物", encoding="utf-8")
        stages = {}
        for name in ["EVIDENCE", "OUTLINE", "DRAFT", "FIGURES", "DOCUMENTS", "VALIDATION"]:
            stages[name] = {
                "status": "PASS", "summary": "完成", "errors": [],
                "outputs": [{"file": "stage.md", "sha256": MODULE.sha256(checkpoint_output)}],
            }
        (self.root / "00-execution-checkpoints.json").write_text(json.dumps({
            "schema_version": "1.0", "execution_profile": "GUIDED", "stages": stages,
        }), encoding="utf-8")
        self.write_all()
        adjudicator, derived = self.adjudicate()
        self.assertEqual(adjudicator.errors, [])
        self.assertEqual(derived["delivery_status"], "PASS")

    def test_open_weak_checkpoint_forces_failure(self) -> None:
        self.manifest["execution_profile"] = "WEAK_MODEL"
        (self.root / "00-execution-checkpoints.json").write_text(json.dumps({
            "schema_version": "1.0", "execution_profile": "WEAK_MODEL",
            "stages": {"EVIDENCE": {"status": "IN_PROGRESS", "outputs": []}},
        }), encoding="utf-8")
        self.write_all()
        adjudicator, derived = self.adjudicate()
        self.assertTrue(any("EXECUTION_CHECKPOINT" in item for item in adjudicator.errors))
        self.assertEqual(derived["final_status"], "FAIL")

    def test_figures_only_allows_not_applicable_reports(self) -> None:
        self.manifest["run_mode"] = "FIGURES_ONLY"
        self.write_all()
        for name in ["evidence", "formula", "delivery"]:
            self.write_skip(name, "SKIPPED_NOT_APPLICABLE", "FIGURES_ONLY")
        adjudicator, derived = self.adjudicate()
        self.assertEqual(adjudicator.errors, [])
        self.assertEqual(derived["delivery_status"], "PASS")

    def test_full_build_rejects_skipped_report(self) -> None:
        self.write_all()
        self.write_skip("evidence", "SKIPPED_NOT_APPLICABLE", "FULL_BUILD")
        adjudicator, derived = self.adjudicate()
        self.assertTrue(any("REPORT_SKIP_NOT_ALLOWED" in item for item in adjudicator.errors))
        self.assertEqual(derived["final_status"], "FAIL")

    def test_revision_requires_impact_file(self) -> None:
        self.manifest["run_mode"] = "REVISE_ONLY"; self.write_all(); adjudicator,derived=self.adjudicate(); self.assertTrue(any("REVISION_IMPACT_MISSING" in item for item in adjudicator.errors)); self.assertEqual(derived["final_status"],"FAIL")


if __name__ == "__main__":
    unittest.main()
