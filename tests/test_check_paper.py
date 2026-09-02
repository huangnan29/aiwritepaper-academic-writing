"""验收编排测试；真实检查器负例与模拟子进程状态传递分开验证。"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_paper as checker


class CheckPaperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "paper"
        self.root.mkdir()
        self.manifest = {"run_mode": "FULL_BUILD", "execution_profile": "FULL_AUTONOMY", "research_claim_level": "DESIGN_ONLY"}
        self.save()

    def save(self):
        (self.root / "run-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "scripts/paper.py"), "check", "--root", str(self.root), *args], capture_output=True, text=True)

    def test_plan_uses_skill_scripts_without_copying_them_to_paper(self):
        result = self.invoke("--plan")
        self.assertEqual(result.returncode, 0, result.stdout)
        data = json.loads(result.stdout)
        self.assertEqual([x["category"] for x in data["commands"]], ["evidence", "figure", "formula", "delivery", "adjudication"])
        for step in data["commands"]:
            self.assertEqual(step["command"][0], sys.executable)
            self.assertEqual(Path(step["command"][1]).parent, ROOT / "scripts")
        self.assertFalse((self.root / "scripts").exists())
        self.assertFalse((self.root / ".audit-logs").exists())

    def test_plan_with_paths_does_not_write_manifest(self):
        (self.root / "new.pdf").write_bytes(b"%PDF-test")
        original = (self.root / "run-manifest.json").read_bytes()
        self.assertEqual(self.invoke("--plan", "--pdf", "new.pdf").returncode, 0)
        self.assertEqual((self.root / "run-manifest.json").read_bytes(), original)

    def test_real_missing_inputs_cannot_reuse_old_pass(self):
        (self.root / "14-adjudicated-status.json").write_text('{"authoritative_status":{"final_status":"PASS"}}')
        (self.root / "04-evidence-verification.json").write_text('{"status":"EVIDENCE_OK"}')
        result = self.invoke()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "FAIL")
        self.assertTrue(list((self.root / ".audit-logs").glob("*/upstream/14-adjudicated-status.json")))
        self.assertTrue(data["failed_categories"])

    def test_figure_only_does_not_research_or_export(self):
        self.manifest["run_mode"] = "FIGURES_ONLY"; self.save()
        steps = json.loads(self.invoke("--plan").stdout)["commands"]
        self.assertEqual(next(s for s in steps if s["category"] == "figure")["action"], "RUN")
        self.assertIn("--skip-documents", next(s for s in steps if s["category"] == "figure")["command"])
        for category in ("evidence", "formula", "delivery"):
            self.assertEqual(next(s for s in steps if s["category"] == category)["action"], "SKIPPED_NOT_APPLICABLE")

    def test_explicit_figure_reexport_checks_formula_and_documents(self):
        self.manifest.update(run_mode="FIGURES_ONLY", reexport_documents=True); self.save()
        steps = json.loads(self.invoke("--plan").stdout)["commands"]
        for category in ("figure", "formula", "delivery"):
            self.assertEqual(next(s for s in steps if s["category"] == category)["action"], "RUN")

    def test_actual_figure_only_generates_skips_not_empty_claims(self):
        self.manifest["run_mode"] = "FIGURES_ONLY"; self.save()
        self.invoke()
        payload = json.loads((self.root / "04-evidence-verification.json").read_text())
        self.assertEqual(payload["status"], "SKIPPED_NOT_APPLICABLE")
        self.assertIn("run-manifest.json", payload["input_sha256"])

    def test_audit_copy_does_not_touch_source(self):
        (self.root / "note.md").write_text("源稿不可修改")
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        destination = self.base / "audit"
        result = self.invoke("AUDIT_ONLY", "--audit-dir", str(destination))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertTrue((destination / "12-final-qa-report.md").is_file())
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_nested_or_existing_audit_directory_rejected(self):
        self.assertEqual(self.invoke("AUDIT_ONLY", "--audit-dir", str(self.root / "audit")).returncode, 2)
        self.assertFalse((self.root / "audit").exists())
        self.assertEqual(self.invoke("AUDIT_ONLY", "--audit-dir", str(self.base)).returncode, 2)

    def test_log_symlink_cannot_write_outside(self):
        other = self.base / "other"; other.mkdir()
        (self.root / ".audit-logs").symlink_to(other, target_is_directory=True)
        self.assertEqual(self.invoke().returncode, 2)
        self.assertEqual(list(other.iterdir()), [])

    def test_report_cannot_overwrite_manuscript(self):
        (self.root / "07-paper-full.md").write_text("保留正文")
        self.manifest["figure_verification_report"] = "07-paper-full.md"; self.save()
        self.assertEqual(self.invoke().returncode, 2)
        self.assertEqual((self.root / "07-paper-full.md").read_text(), "保留正文")

    def test_mode_conflict_is_not_silently_applied(self):
        original = (self.root / "run-manifest.json").read_bytes()
        self.assertEqual(self.invoke("EXPORT_ONLY").returncode, 2)
        self.assertEqual((self.root / "run-manifest.json").read_bytes(), original)

    def test_zero_exit_can_still_mean_partial(self):
        # 只模拟子检查器的输出以验证编排状态传递，不当作真实论文验收。
        def fake_run(command, **kwargs):
            filename = command[command.index("--report") + 1]
            path = self.root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            if "adjudicate_status.py" in command[1]:
                payload = {"authoritative_status": {"research_status": "PARTIAL", "delivery_status": "PARTIAL", "final_status": "PARTIAL"}}
            else:
                payload = {"status": "OK", "errors": [], "warnings": []}
            path.write_text(json.dumps(payload))
            return SimpleNamespace(returncode=0, stdout="fixture", stderr="")
        steps = checker.make_plan(self.root, self.manifest, "FULL_BUILD")
        checker.preflight_outputs(self.root, self.manifest, steps)
        with patch.object(checker.subprocess, "run", side_effect=fake_run):
            result = checker.run_checks(self.root, self.manifest, steps)
        self.assertEqual(result["status"], "PARTIAL")

    def test_unchanged_requires_real_upstream(self):
        with self.assertRaises((ValueError, OSError)):
            checker.verify_upstream(self.root, "evidence", self.root / "missing.json")


if __name__ == "__main__":
    unittest.main()
