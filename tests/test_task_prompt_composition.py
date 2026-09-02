#!/usr/bin/env python3
"""任务模块合成的命令行回归测试。"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compose_prompt.py"
BUILD_SCRIPT = ROOT / "scripts" / "build_compiled.py"
DIRECTION = ROOT / "references" / "directions" / "general-journal-imrad.md"
ADAPTER = ROOT / "references" / "integrations" / "universal-terminal.md"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TaskPromptCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.build = load_module(BUILD_SCRIPT, "build_compiled_test")
        self.compose = load_module(SCRIPT, "compose_prompt_test")
        self.compiled = self.root / "general-journal-imrad-full.md"
        self.compiled.write_text(self.build.render_compiled(DIRECTION), encoding="utf-8")
        self.params = self.root / "run-params.md"
        self.output = self.root / "final-execution-prompt.md"
        self.report = self.root / "composition-report.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_selection(self, mode: str, features: list[str], name: str = "selection.json") -> Path:
        path = self.root / name
        path.write_text(json.dumps({
            "schema_version": "1.0", "run_mode": mode,
            "direction_id": "general-journal-imrad", "features": features,
        }), encoding="utf-8")
        return path

    def run_cli(self, selection: Path, *, params_text: str | None = None,
                output: Path | None = None, report: Path | None = None,
                addons: list[Path] | None = None) -> subprocess.CompletedProcess[str]:
        self.params.write_text(
            params_text or "RUN_MODE: FULL_BUILD\nDIRECTION_ID: general-journal-imrad\nTARGET_FIGURES: 1\n",
            encoding="utf-8",
        )
        command = ["uv", "run", "python", str(SCRIPT), "--params", str(self.params),
                   "--compiled", str(self.compiled), "--task-selection", str(selection),
                   "--addon", str(ADAPTER), "--output", str(output or self.output)]
        if report is not None:
            command.extend(["--report", str(report)])
        for addon in addons or []:
            command.extend(["--addon", str(addon)])
        return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)

    def test_full_build_cli(self) -> None:
        result = self.run_cli(self.write_selection("FULL_BUILD", ["figures", "documents"]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("当前任务执行边界：FULL_BUILD", self.output.read_text(encoding="utf-8"))

    def test_figures_only_cli(self) -> None:
        result = self.run_cli(self.write_selection("FIGURES_ONLY", ["figures"]), params_text="RUN_MODE: FIGURES_ONLY\nDIRECTION_ID: general-journal-imrad\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_export_only_allows_document_features(self) -> None:
        result = self.run_cli(self.write_selection("EXPORT_ONLY", ["documents", "formulas"]), params_text="RUN_MODE: EXPORT_ONLY\nDIRECTION_ID: general-journal-imrad\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_audit_only_cli(self) -> None:
        result = self.run_cli(self.write_selection("AUDIT_ONLY", ["figures"]), params_text="RUN_MODE: AUDIT_ONLY\nDIRECTION_ID: general-journal-imrad\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_proposal_only_adds_its_delivery_rule(self) -> None:
        result = self.run_cli(self.write_selection("PROPOSAL_ONLY", []), params_text="RUN_MODE: PROPOSAL_ONLY\nDIRECTION_ID: general-journal-imrad\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("附加交付：开题报告", self.output.read_text(encoding="utf-8"))

    def test_defense_only_adds_its_delivery_rule(self) -> None:
        result = self.run_cli(self.write_selection("DEFENSE_ONLY", []), params_text="RUN_MODE: DEFENSE_ONLY\nDIRECTION_ID: general-journal-imrad\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("附加交付：开题或答辩演示", self.output.read_text(encoding="utf-8"))

    def test_unknown_feature_is_rejected(self) -> None:
        result = self.run_cli(self.write_selection("FULL_BUILD", ["unknown"]))
        self.assertNotEqual(result.returncode, 0)

    def test_duplicate_feature_is_rejected(self) -> None:
        result = self.run_cli(self.write_selection("FULL_BUILD", ["figures", "figures"]))
        self.assertNotEqual(result.returncode, 0)

    def test_run_mode_conflict_is_rejected(self) -> None:
        result = self.run_cli(self.write_selection("AUDIT_ONLY", ["figures"]), params_text="RUN_MODE: FULL_BUILD\nDIRECTION_ID: general-journal-imrad\n")
        self.assertNotEqual(result.returncode, 0)

    def test_direction_conflict_is_rejected(self) -> None:
        selection = self.write_selection("FULL_BUILD", ["figures"])
        result = self.run_cli(selection, params_text="RUN_MODE: FULL_BUILD\nDIRECTION_ID: other-direction\n")
        self.assertNotEqual(result.returncode, 0)

    def test_resume_is_rejected(self) -> None:
        result = self.run_cli(self.write_selection("RESUME", []), params_text="RUN_MODE: RESUME\nDIRECTION_ID: general-journal-imrad\n")
        self.assertNotEqual(result.returncode, 0)

    def test_export_only_rejects_figure_feature(self) -> None:
        result = self.run_cli(self.write_selection("EXPORT_ONLY", ["figures"]), params_text="RUN_MODE: EXPORT_ONLY\nDIRECTION_ID: general-journal-imrad\n")
        self.assertNotEqual(result.returncode, 0)

    def test_positive_target_figures_requires_feature(self) -> None:
        result = self.run_cli(self.write_selection("FULL_BUILD", []))
        self.assertNotEqual(result.returncode, 0)

    def test_unapproved_addon_is_rejected(self) -> None:
        addon = self.root / "unapproved.md"
        addon.write_text("无关生产指令", encoding="utf-8")
        result = self.run_cli(self.write_selection("FULL_BUILD", ["figures"]), addons=[addon])
        self.assertNotEqual(result.returncode, 0)

    def test_output_cannot_overwrite_selection_or_input(self) -> None:
        selection = self.write_selection("FULL_BUILD", ["figures"])
        result = self.run_cli(selection, output=selection)
        self.assertNotEqual(result.returncode, 0)
        result = self.run_cli(selection, output=self.params)
        self.assertNotEqual(result.returncode, 0)

    def test_report_cannot_overwrite_selection_or_input(self) -> None:
        selection = self.write_selection("FULL_BUILD", ["figures"])
        result = self.run_cli(selection, report=selection)
        self.assertNotEqual(result.returncode, 0)
        result = self.run_cli(selection, report=self.compiled)
        self.assertNotEqual(result.returncode, 0)

    def test_report_records_task_selection_hash(self) -> None:
        selection = self.write_selection("FULL_BUILD", ["figures"])
        result = self.run_cli(selection, report=self.report)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertIn(str(selection.resolve()), payload["input_sha256"])

    def test_full_and_compact_are_same_source(self) -> None:
        compact = self.build.render_compact(DIRECTION)
        full = self.build.render_compiled(DIRECTION)
        self.assertLess(len(compact.encode()), len(full.encode()))
        self.assertIn(self.build.compact_source(DIRECTION), compact)
        self.assertIn(self.build.compact_source(DIRECTION), full)
        self.assertEqual(full.count("<!-- task-module:"), full.count("<!-- /task-module -->"))


if __name__ == "__main__":
    unittest.main()
