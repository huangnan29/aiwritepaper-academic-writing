#!/usr/bin/env python3
"""A/B控制器隔离、模型标识和断点状态测试。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ab_runner", ROOT / "eval/ab_runner.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ABRunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = Path(self.tmp.name) / "lab"
        self.agents = {"codex": {"binary": "codex", "model": "gpt-test", "skill_root": ".codex/skills"}}
        self.topics = {"topic": {"direction": "general-journal-imrad", "title": "固定题目"}}
        self.versions = {"A": {"label": "v1.9.1", "ref": "v1.9.1"},
                         "B": {"label": "v2.1.0-rc.2", "ref": "v2.1.0-rc.2"}}

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def fake_extract(ref, target):
        target.mkdir(parents=True)
        version = ref.removeprefix("v")
        (target / "SKILL.md").write_text(f'---\nname: aiwritepaper-academic-writing\nmetadata:\n  version: "{version}"\n---\n')

    def initialize(self):
        with patch.object(MODULE, "AGENTS", self.agents), patch.object(MODULE, "TOPICS", self.topics), \
             patch.object(MODULE, "VERSIONS", self.versions), patch.object(MODULE, "extract_ref", self.fake_extract):
            return MODULE.initialize(self.lab, 21)

    def test_init_creates_two_isolated_versions_without_switching_repo(self):
        branch_before = MODULE.subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"], capture_output=True, text=True).stdout
        manifest = self.initialize()
        branch_after = MODULE.subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"], capture_output=True, text=True).stdout
        self.assertEqual(branch_before, branch_after)
        self.assertEqual(len(manifest["cases"]), 2)
        self.assertEqual({case["version"] for case in manifest["cases"]}, {"v1.9.1", "v2.1.0-rc.2"})
        self.assertNotEqual(manifest["cases"][0]["directory"], manifest["cases"][1]["directory"])

    def test_antigravity_command_uses_gemini_38_flash(self):
        case = {"agent": "antigravity", "model": MODULE.AGENTS["antigravity"]["model"], "directory": str(self.lab)}
        self.lab.mkdir()
        (self.lab / "prompt.txt").write_text("测试")
        command = MODULE.case_command(case)
        self.assertIn("gemini-3.8-flash-high", command)
        self.assertEqual(command[0], "agy")
        self.assertIn("--new-project", command)
        self.assertNotIn("--sandbox", command)
        self.assertNotIn("gemini-3.7-flash", command)

    def test_codex_uses_saved_login_and_supported_exec_flags(self):
        self.lab.mkdir()
        (self.lab / "prompt.txt").write_text("测试")
        command = MODULE.case_command({"agent": "codex", "model": "gpt-5.6-sol", "directory": str(self.lab)})
        self.assertEqual(command[:2], ["codex", "-c"])
        self.assertIn('model_reasoning_effort="medium"', command)
        self.assertIn("--search", command)
        self.assertIn("exec", command)
        self.assertIn("workspace-write", command)
        self.assertNotIn("-a", command)
        self.assertNotIn("--ignore-user-config", command)

    def test_status_requires_real_delivery_files(self):
        manifest = self.initialize()
        first = Path(manifest["cases"][0]["directory"])
        (first / "07-paper-full.md").write_text("正文")
        (first / "论文_20260902-120000.docx").write_bytes(b"docx")
        (first / "论文_20260902-120000.pdf").write_bytes(b"pdf")
        (first / "14-adjudicated-status.json").write_text(json.dumps({
            "authoritative_status": {"final_status": "PARTIAL"}
        }))
        result = MODULE.status(self.lab)
        self.assertEqual(result["counts"]["COMPLETE"], 1)
        self.assertEqual(result["counts"]["PENDING"], 1)

    def test_failed_attempt_is_archived_before_retry(self):
        manifest = self.initialize()
        case = manifest["cases"][0]
        directory = Path(case["directory"])
        (directory / "partial.md").write_text("失败残留")
        target = MODULE.archive_previous_attempt(directory, 1)
        self.assertTrue((target / "partial.md").is_file())
        self.assertFalse((directory / "partial.md").exists())
        self.assertTrue((directory / "prompt.txt").is_file())
        self.assertTrue((directory / case["skill_file"]).is_file())

    def test_nested_paper_output_is_detected(self):
        output = self.lab / "paper-output"
        output.mkdir(parents=True)
        (output / "07-paper-full.md").write_text("正文")
        (output / "论文_20260902-120000.docx").write_bytes(b"docx")
        (output / "论文_20260902-120000.pdf").write_bytes(b"pdf")
        (output / "14-adjudicated-status.json").write_text(json.dumps({
            "authoritative_status": {"final_status": "PARTIAL"}
        }))
        result = MODULE.inspect_delivery(self.lab)
        self.assertTrue(result["complete_files"])
        self.assertEqual(result["artifact_root"], "paper-output")


if __name__ == "__main__":
    unittest.main()
