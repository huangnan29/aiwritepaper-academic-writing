#!/usr/bin/env python3
"""paper.py准备入口的真实CLI回归测试。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "paper.py"
ADAPTER = ROOT / "references" / "integrations" / "universal-terminal.md"


class PaperEntryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.request = self.root / "paper-request.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def capabilities(self, *, image: bool = True) -> dict:
        result = {}
        for name in ("image_generation", "visual_inspection", "docx_export", "pdf_export"):
            result[name] = {
                "available": image if name == "image_generation" else True,
                "tools": [name + "-tool"],
                "callers": ["CURRENT_AGENT", "PARENT_AGENT"],
                "evidence": "真实测试环境观察",
            }
        return result

    def write_request(self, **changes) -> None:
        request = {
            "schema_version": "1.0", "observed_at": "2026-08-30T10:00:00-07:00",
            "agent_adapter": "universal-terminal", "model_label": "test-model @ terminal",
            "paper_title": "测试论文", "direction_id": "general-journal-imrad",
            "run_mode": "FULL_BUILD", "features": ["figures"], "target_figures": 1,
            "capabilities": self.capabilities(), "constraints": "只使用真实材料。",
        }
        request.update(changes)
        self.request.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

    def run_cli(self, *, preview: bool = False) -> subprocess.CompletedProcess[str]:
        command = ["uv", "run", "python", str(SCRIPT), "prepare", "--root", str(self.root), "--request", str(self.request)]
        if preview:
            command.append("--preview")
        return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)

    def run_amend(self, payload: dict) -> subprocess.CompletedProcess[str]:
        path = self.root / "prompt-amendment.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return subprocess.run([
            "uv", "run", "python", str(SCRIPT), "prepare", "--amend",
            "--root", str(self.root), "--request", str(path),
        ], cwd=ROOT, text=True, capture_output=True)

    def result(self, **changes) -> dict:
        self.write_request(**changes)
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        return json.loads(completed.stdout)

    def test_prepare_creates_real_preparation_outputs(self) -> None:
        result = self.result()
        self.assertEqual(result["status"], "PREPARED_NOT_EXECUTED")
        self.assertTrue((self.root / "final-execution-prompt.md").is_file())
        manifest = json.loads((self.root / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["preparation_status"], "PREPARED_NOT_EXECUTED")

    def test_missing_observation_remains_unknown_without_fake_gap(self) -> None:
        self.write_request()
        payload = json.loads(self.request.read_text(encoding="utf-8"))
        del payload["capabilities"]
        self.request.write_text(json.dumps(payload), encoding="utf-8")
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        capability = json.loads((self.root / "00-capability-report.json").read_text())
        self.assertIsNone(capability["image_generation"]["available"])

    def test_invalid_direction_is_blocked(self) -> None:
        completed = self.run_after_request(direction_id="not-a-real-direction")
        self.assertEqual(completed.returncode, 2)

    def run_after_request(self, **changes) -> subprocess.CompletedProcess[str]:
        self.write_request(**changes)
        return self.run_cli()

    def test_default_length_is_25000(self) -> None:
        result = self.result()
        self.assertEqual(result["target_length"], 25000)

    def test_preparation_profile_has_complete_schema_fields(self) -> None:
        self.result()
        profile = json.loads((self.root / "00-profile-selection.json").read_text())
        schema = json.loads((ROOT / "references/schemas/profile-selection.schema.json").read_text())
        self.assertTrue(set(schema["required"]).issubset(profile))
        self.assertTrue(set(schema["properties"]["selector"]["required"]).issubset(profile["selector"]))
        self.assertEqual(profile["selector"]["version"], "2.1.0-rc.1")
        manifest = json.loads((self.root / "run-manifest.json").read_text())
        self.assertEqual(manifest["state_contract"], "DERIVED_ONLY")
        self.assertFalse({"research_status", "delivery_status", "final_status"} & set(manifest))

    def test_user_target_length_wins(self) -> None:
        result = self.result(target_length=12345)
        self.assertEqual(result["target_length"], 12345)

    def test_figures_only_does_not_select_full_paper_modules(self) -> None:
        result = self.result(run_mode="FIGURES_ONLY", features=["figures"], target_figures=0)
        self.assertNotIn("literature-and-citation", result["selected_modules"])
        self.assertNotIn("academic-prose-quality", result["selected_modules"])

    def test_export_only_does_not_select_image_module(self) -> None:
        result = self.result(run_mode="EXPORT_ONLY", features=["documents"], target_figures=0)
        self.assertNotIn("academic-figures", result["selected_modules"])
        prompt = (self.root / "final-execution-prompt.md").read_text(encoding="utf-8")
        self.assertNotIn("IMAGE_GENERATION", prompt)

    def test_existing_file_is_never_overwritten(self) -> None:
        self.write_request()
        existing = self.root / "run-params.md"
        existing.write_text("用户已有内容", encoding="utf-8")
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(existing.read_text(encoding="utf-8"), "用户已有内容")

    def test_preview_writes_nothing(self) -> None:
        self.write_request()
        before = {path.name for path in self.root.iterdir()}
        completed = self.run_cli(preview=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual({path.name for path in self.root.iterdir()}, before)

    def test_legacy_capability_is_normalized_to_one_caller(self) -> None:
        self.result()
        capability = json.loads((self.root / "00-capability-report.json").read_text(encoding="utf-8"))
        self.assertEqual(capability["image_generation"]["caller"], "CURRENT_AGENT")

    def test_direction_default_features_apply_without_model_list(self) -> None:
        self.write_request()
        payload = json.loads(self.request.read_text())
        payload.pop("features")
        payload.pop("target_figures")
        self.request.write_text(json.dumps(payload), encoding="utf-8")
        completed = self.run_cli()
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        selection = json.loads((self.root / "task-selection.json").read_text())
        self.assertIn("documents", selection["features"])
        self.assertEqual(selection["feature_source"], "DIRECTION_DEFAULT_WITH_OVERRIDE")

    def test_full_profile_has_no_stage_card(self) -> None:
        self.result()
        self.assertFalse((self.root / "00-execution-checkpoints.json").exists())
        manifest = json.loads((self.root / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["execution_profile"], "FULL_AUTONOMY")

    def test_guided_profile_has_stage_card(self) -> None:
        self.result(execution_profile="GUIDED")
        self.assertTrue((self.root / "00-execution-checkpoints.json").is_file())
        manifest = json.loads((self.root / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["execution_profile"], "GUIDED")

    def test_example_request_is_rejected(self) -> None:
        completed = self.run_after_request(example_only=True)
        self.assertEqual(completed.returncode, 2)

    def test_source_hash_is_recorded_correctly(self) -> None:
        self.result()
        report = json.loads((self.root / "00-prompt-composition.json").read_text(encoding="utf-8"))
        self.assertEqual(report["input_sha256"][str(self.request.resolve())], hashlib.sha256(self.request.read_bytes()).hexdigest())

    def test_prompt_metadata_does_not_claim_completion(self) -> None:
        self.result()
        manifest = json.loads((self.root / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertNotEqual(manifest.get("final_status"), "PASS")
        self.assertEqual(manifest["preparation_status"], "PREPARED_NOT_EXECUTED")

    def test_empty_features_are_blocked_when_target_figures_positive(self) -> None:
        completed = self.run_after_request(features=[])
        self.assertEqual(completed.returncode, 2)

    def test_amend_adds_module_without_overwriting_original_prompt(self) -> None:
        self.result(features=["figures"])
        original = (self.root / "final-execution-prompt.md").read_bytes()
        result = self.run_amend({"schema_version": "1.0", "reason": "正文出现公式",
                                 "add_features": ["formulas"], "remove_features": []})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "final-execution-prompt.md").read_bytes(), original)
        self.assertTrue((self.root / "final-execution-prompt.v2.md").is_file())
        manifest = json.loads((self.root / "run-manifest.json").read_text())
        self.assertEqual(manifest["active_prompt"], "final-execution-prompt.v2.md")

    def test_amend_cannot_remove_module_with_existing_artifact(self) -> None:
        self.result(features=["figures", "documents"])
        (self.root / "figures").mkdir()
        (self.root / "figures/figure-manifest.json").write_text("{}")
        result = self.run_amend({"schema_version": "1.0", "reason": "错误尝试",
                                 "add_features": [], "remove_features": ["figures"]})
        self.assertEqual(result.returncode, 2)

    def test_title_ask_requires_explicit_authorization(self) -> None:
        self.result(features=["figures"], title_policy="ASK")
        result = self.run_amend({"schema_version": "1.0", "reason": "证据不足",
                                 "title_change": {"final_title": "测试论文设计方案",
                                                  "rule_id": "IMPLEMENTATION_TO_DESIGN",
                                                  "evidence_gap": "没有源码"}})
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
