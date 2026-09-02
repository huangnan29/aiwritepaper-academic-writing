#!/usr/bin/env python3
"""Profile感知提示词合成器测试。"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compose_prompt.py"


class ComposePromptProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "run-params.md").write_text("参数", encoding="utf-8")
        (self.root / "topic-full.md").write_text("完整提示词", encoding="utf-8")
        (self.root / "topic-compact.md").write_text("紧凑提示词", encoding="utf-8")
        (self.root / "adapter.md").write_text("适配层", encoding="utf-8")
        (self.root / "staged-assistance.md").write_text("分阶段任务卡", encoding="utf-8")
        (self.root / "execution-checkpoints-template.json").write_text(
            '{"schema_version":"1.0","stages":{}}', encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def selection(self, profile: str) -> Path:
        path = self.root / f"{profile}.json"
        path.write_text(json.dumps({
            "schema_version": "1.0", "selected_profile": profile,
        }), encoding="utf-8")
        return path

    def run_compose(self, *extra: str, output: str = "out.md"):
        command = [
            sys.executable, str(SCRIPT),
            "--params", str(self.root / "run-params.md"),
            "--compiled", str(self.root / "topic-full.md"),
            "--addon", str(self.root / "adapter.md"),
            "--output", str(self.root / output),
            *extra,
        ]
        return subprocess.run(command, capture_output=True, text=True)

    def test_full_profile_keeps_legacy_prompt_bytes(self) -> None:
        legacy = self.run_compose(output="legacy.md")
        current = self.run_compose(
            "--profile-selection", str(self.selection("FULL_AUTONOMY")), output="current.md"
        )
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertEqual(
            (self.root / "legacy.md").read_bytes(), (self.root / "current.md").read_bytes()
        )

    def test_guided_requires_guided_rules(self) -> None:
        result = self.run_compose(
            "--profile-selection", str(self.selection("GUIDED")),
            "--addon", str(self.root / "execution-checkpoints-template.json"),
            "--profile-rules", str(self.root / "staged-assistance.md"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("分阶段任务卡", (self.root / "out.md").read_text(encoding="utf-8"))

    def test_guided_without_rules_fails(self) -> None:
        result = self.run_compose(
            "--profile-selection", str(self.selection("GUIDED")),
        )
        self.assertNotEqual(result.returncode, 0)

    def test_weak_requires_compact_prompt(self) -> None:
        result = self.run_compose(
            "--profile-selection", str(self.selection("WEAK_MODEL")),
            "--profile-rules", str(self.root / "staged-assistance.md"),
        )
        self.assertNotEqual(result.returncode, 0)

    def test_weak_compact_composition_succeeds(self) -> None:
        command = [
            sys.executable, str(SCRIPT),
            "--params", str(self.root / "run-params.md"),
            "--compiled", str(self.root / "topic-compact.md"),
            "--addon", str(self.root / "adapter.md"),
            "--addon", str(self.root / "execution-checkpoints-template.json"),
            "--profile-selection", str(self.selection("WEAK_MODEL")),
            "--profile-rules", str(self.root / "staged-assistance.md"),
            "--output", str(self.root / "weak.md"),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (self.root / "weak.md").read_text(encoding="utf-8")
        self.assertIn("紧凑提示词", text)
        self.assertIn("分阶段任务卡", text)


if __name__ == "__main__":
    unittest.main()
