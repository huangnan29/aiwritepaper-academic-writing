#!/usr/bin/env python3
"""无评分观察投影器的临时目录测试。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_audit_views.py"


class AuditViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "figures").mkdir()
        (self.root / "figures/f1.png").write_bytes(b"png")
        (self.root / "figures/figure-manifest.json").write_text(json.dumps({
            "figures": [{"figure_id": "f1", "final_embed_file": "figures/f1.png"}]
        }), encoding="utf-8")
        for name, content in {"checked.png": b"png", "receipt.txt": b"receipt"}.items():
            (self.root / name).write_bytes(content)
        (self.root / "run-manifest.json").write_text(json.dumps({
            "direction_id": "electronic-circuit-design", "docx": "paper.docx", "pdf": "paper.pdf"
        }), encoding="utf-8")
        self.qa = {
            "schema_version": "2.1",
            "claims": [{"claim_id": "C1", "location": "结论", "evidence_ids": ["S1"]}],
            "figures": [{"figure_id": "f1", "final_embed_file": "figures/f1.png",
                         "checked_file": "checked.png", "visual_receipt": "receipt.txt",
                         "status": "PASS", "blind_summary": "逐边检查完成"}],
            "document_checks": [{"checkpoint": "cover", "page": 1, "checked_file": "checked.png",
                                 "visual_receipt": "receipt.txt", "status": "PASS"}],
            "issues": [{"severity": "ADVISORY", "location": "摘要", "evidence": "措辞重复",
                        "fix": "压缩一句", "status": "OPEN"}],
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_prepare(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)], capture_output=True, text=True)

    def save(self):
        (self.root / "qa-observations.json").write_text(json.dumps(self.qa, ensure_ascii=False), encoding="utf-8")

    def test_projects_observations_without_scores_or_reviewer_identity(self):
        self.save()
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / "claim-evidence-map.json").is_file())
        self.assertTrue((self.root / "issue-register.json").is_file())
        self.assertFalse((self.root / "15-quality-scorecard.json").exists())
        self.assertFalse((self.root / "09-final-peer-review.json").exists())

    def test_invalid_input_does_not_overwrite_existing_view(self):
        old = self.root / "issue-register.json"
        old.write_text("原文件", encoding="utf-8")
        self.qa["figures"][0]["checked_file"] = "missing.png"
        self.save()
        self.assertNotEqual(self.run_prepare().returncode, 0)
        self.assertEqual(old.read_text(), "原文件")

    def test_stale_checked_hash_rejected(self):
        self.qa["figures"][0]["checked_file_sha256"] = "old"
        self.save()
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_authority_manifest_mismatch_rejected(self):
        self.qa["figures"][0]["final_embed_file"] = "figures/other.png"
        self.save()
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_invalid_relative_path_rejected(self):
        self.qa["document_checks"][0]["checked_file"] = "../outside"
        self.save()
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_missing_manual_status_rejected(self):
        self.qa["figures"][0].pop("status")
        self.save()
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_invalid_issue_severity_rejected(self):
        self.qa["issues"][0]["severity"] = "SCORE_90"
        self.save()
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_capability_view_requires_authority_source(self):
        self.save()
        self.assertEqual(self.run_prepare().returncode, 0)
        self.assertFalse((self.root / "00-capability-report.md").exists())


if __name__ == "__main__":
    unittest.main()
