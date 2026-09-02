#!/usr/bin/env python3
"""执行Profile选择器的隔离测试。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "select_execution_profile.py"
SPEC = importlib.util.spec_from_file_location("select_execution_profile", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class SelectProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.capability = {
            "schema_version": "1.0", "agent_adapter": "test",
            "docx_export": {"available": True}, "pdf_export": {"available": True},
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prior(
        self, name: str, model: str, final: str, delivery: str = "PASS",
        *, issues=None, adapter: str = "test",
    ):
        path = self.root / name
        path.write_text(json.dumps({
            "run_identity": {"model_label": model, "agent_adapter": adapter},
            "authoritative_status": {
                "final_status": final, "delivery_status": delivery,
                **({"execution_issues": issues} if issues is not None else {}),
            },
        }), encoding="utf-8")
        return path, json.loads(path.read_text(encoding="utf-8"))

    def test_default_preserves_strong_autonomy(self) -> None:
        profile, source, reasons, _ = MODULE.select_profile(
            self.capability, "strong-model", None, []
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertEqual(source, "DEFAULT_STRONG_PRESERVING")
        self.assertIn("NO_WEAK_SIGNAL", reasons)

    def test_user_override_has_highest_priority(self) -> None:
        prior = self.prior("failed.json", "same-model", "FAIL")
        profile, source, _, matched = MODULE.select_profile(
            self.capability, "same-model", "FULL_AUTONOMY", [prior]
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertEqual(source, "USER_OVERRIDE")
        self.assertEqual(matched, [])

    def test_same_model_prior_failure_selects_weak(self) -> None:
        profile, source, reasons, matched = MODULE.select_profile(
            self.capability, "same-model", None,
            [self.prior("failed.json", "same-model", "FAIL", issues=["BODY_MISSING"])],
        )
        self.assertEqual(profile, "WEAK_MODEL")
        self.assertEqual(source, "PRIOR_ADJUDICATION")
        self.assertIn("SAME_MODEL_PRIOR_FAIL", reasons)
        self.assertEqual(len(matched), 1)

    def test_same_model_prior_partial_selects_guided(self) -> None:
        profile, _, _, _ = MODULE.select_profile(
            self.capability, "same-model", None,
            [self.prior("partial.json", "same-model", "PARTIAL", "PARTIAL", issues=["STRUCTURE_INVALID"])],
        )
        self.assertEqual(profile, "GUIDED")

    def test_other_model_history_does_not_downgrade(self) -> None:
        profile, _, _, matched = MODULE.select_profile(
            self.capability, "new-model", None,
            [self.prior("failed.json", "other-model", "FAIL")],
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertEqual(matched, [])

    def test_missing_document_tool_selects_guided(self) -> None:
        self.capability["docx_export"] = {"available": False}
        profile, source, reasons, _ = MODULE.select_profile(
            self.capability, "model", None, []
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertEqual(source, "DEFAULT_STRONG_PRESERVING")
        self.assertIn("CAPABILITY_GAP_DOCX_EXPORT", reasons)

    def test_partial_research_status_does_not_downgrade(self) -> None:
        profile, _, reasons, _ = MODULE.select_profile(
            self.capability, "same-model", None,
            [self.prior("research.json", "same-model", "PARTIAL", "PARTIAL")],
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertIn("NO_WEAK_SIGNAL", reasons)

    def test_design_protocol_and_quota_gaps_do_not_downgrade(self) -> None:
        for index, issue in enumerate(("DESIGN_ONLY", "PROTOCOL_ONLY", "QUOTA_EXCEEDED")):
            profile, _, _, _ = MODULE.select_profile(
                self.capability, "same-model", None,
                [self.prior(f"non-execution-{index}.json", "same-model", "FAIL", issues=[issue])],
            )
            self.assertEqual(profile, "FULL_AUTONOMY")

    def test_fail_without_explicit_execution_issue_does_not_downgrade(self) -> None:
        profile, _, reasons, _ = MODULE.select_profile(
            self.capability, "same-model", None,
            [self.prior("unclassified.json", "same-model", "FAIL")],
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertIn("NO_WEAK_SIGNAL", reasons)

    def test_legacy_report_errors_can_supply_execution_signal(self) -> None:
        prior_path, prior_payload = self.prior("legacy.json", "same-model", "FAIL")
        prior_payload["reports"] = {"delivery": {"errors": ["FINAL_FILE_MISSING: final.docx"]}}
        prior_path.write_text(json.dumps(prior_payload), encoding="utf-8")
        profile, _, reasons, _ = MODULE.select_profile(
            self.capability, "same-model", None, [(prior_path, prior_payload)]
        )
        self.assertEqual(profile, "WEAK_MODEL")
        self.assertIn("FINAL_FILE_MISSING", reasons)

    def test_same_model_different_client_does_not_match(self) -> None:
        profile, _, _, matched = MODULE.select_profile(
            self.capability, "same-model", None,
            [self.prior("other-client.json", "same-model", "FAIL", issues=["BODY_MISSING"], adapter="other")],
        )
        self.assertEqual(profile, "FULL_AUTONOMY")
        self.assertEqual(matched, [])


if __name__ == "__main__":
    unittest.main()
