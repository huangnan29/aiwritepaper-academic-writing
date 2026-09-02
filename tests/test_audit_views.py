#!/usr/bin/env python3
"""canonical审计输入的临时目录测试。"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_audit_views.py"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuditViewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "figures").mkdir()
        (self.root / "figures/f1.png").write_bytes(b"png")
        (self.root / "figures/figure-manifest.json").write_text(json.dumps({"figures": [{"figure_id": "f1", "final_embed_file": "figures/f1.png"}]}), encoding="utf-8")
        for name, content in {"checked.png": b"png", "receipt.txt": b"receipt", "review.txt": b"review"}.items():
            (self.root / name).write_bytes(content)
        (self.root / "07-paper-full.md").write_text("正文", encoding="utf-8")
        (self.root / "paper.docx").write_bytes(b"docx")
        (self.root / "paper.pdf").write_bytes(b"pdf")
        (self.root / "run-manifest.json").write_text(json.dumps({
            "direction_id": "electronic-circuit-design", "docx": "paper.docx", "pdf": "paper.pdf"
        }), encoding="utf-8")
        self.qa = {
            "schema_version": "1.1",
            "claims": [{"location": "结论", "importance": "CONCLUSION", "evidence_ids": ["S1"]}],
            "figures": [{"figure_id": "f1", "final_embed_file": "figures/f1.png", "checked_file": "checked.png",
                          "visual_receipt": "receipt.txt", "status": "PASS", "blind_summary": "人工记录"}],
            "document_checks": [{"checkpoint": "cover", "page": 1, "checked_file": "checked.png",
                                  "visual_receipt": "receipt.txt", "status": "PASS"}],
            "review": {"status": "REVIEWED", "reviewer_mode": "SELF", "issues": {"critical_open": 0, "important_open": 0, "items": []},
                       "alignment": {"title_supported": True, "research_question_answered": True,
                                     "method_result_consistent": True, "abstract_conclusion_consistent": True},
                       "reviewer_source": {"path": "review.txt"}},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_prepare(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)], capture_output=True, text=True)

    def test_projects_without_inventing_score(self):
        (self.root / "qa-review.json").write_text(json.dumps(self.qa, ensure_ascii=False), encoding="utf-8")
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        score = json.loads((self.root / "15-quality-scorecard.json").read_text())
        self.assertNotIn("scores", score)
        self.assertNotIn("total", score)
        review = json.loads((self.root / "09-final-peer-review.json").read_text())
        self.assertEqual(review["reviewer_source"]["sha256"], sha(self.root / "review.txt"))
        self.assertEqual((self.root / "figures/figure-manifest.md").read_text().count("figure_id"), 1)
        self.assertEqual((self.root / "figures/figure-manifest.md").read_text().count("final_embed_file"), 1)

    def test_invalid_input_does_not_overwrite_outputs(self):
        old = self.root / "15-quality-scorecard.json"
        old.write_text("原文件", encoding="utf-8")
        self.qa["figures"][0]["checked_file"] = "missing.png"
        (self.root / "qa-review.json").write_text(json.dumps(self.qa), encoding="utf-8")
        self.assertNotEqual(self.run_prepare().returncode, 0)
        self.assertEqual(old.read_text(), "原文件")

    def prepare_with(self, mutate):
        mutate(self.qa)
        (self.root / "qa-review.json").write_text(json.dumps(self.qa, ensure_ascii=False), encoding="utf-8")
        return self.run_prepare()

    def test_stale_checked_hash_rejected(self):
        result = self.prepare_with(lambda q: q["figures"][0].update({"checked_file_sha256": "old"}))
        self.assertNotEqual(result.returncode, 0)

    def test_authority_manifest_mismatch_rejected(self):
        result = self.prepare_with(lambda q: q["figures"][0].update({"final_embed_file": "figures/other.png"}))
        self.assertNotEqual(result.returncode, 0)

    def test_invalid_relative_path_rejected(self):
        result = self.prepare_with(lambda q: q["document_checks"][0].update({"checked_file": "../outside"}))
        self.assertNotEqual(result.returncode, 0)

    def test_missing_manual_status_rejected(self):
        result = self.prepare_with(lambda q: q["figures"][0].pop("status"))
        self.assertNotEqual(result.returncode, 0)

    def test_missing_alignment_rejected(self):
        result = self.prepare_with(lambda q: q["review"].pop("alignment"))
        self.assertNotEqual(result.returncode, 0)

    def test_capability_view_requires_authority_source(self):
        (self.root / "qa-review.json").write_text(json.dumps(self.qa), encoding="utf-8")
        self.assertEqual(self.run_prepare().returncode, 0)
        self.assertFalse((self.root / "00-capability-report.md").exists())

    def test_derived_visual_hash_is_used(self):
        old_visual = self.root / "16-document-visual-audit.json"
        old_visual.write_text("old", encoding="utf-8")
        (self.root / "qa-review.json").write_text(json.dumps(self.qa), encoding="utf-8")
        self.assertEqual(self.run_prepare().returncode, 0)
        review = json.loads((self.root / "09-final-peer-review.json").read_text())
        self.assertEqual(review["reviewed_artifacts"]["16-document-visual-audit.json"], sha(self.root / "16-document-visual-audit.json"))

    def test_scored_self_projects_issue_lists_without_defaults(self):
        self.qa["review"]["scores"] = {"evidence": 25, "content": 20, "structure": 15, "figures": 15, "documents": 10, "integrity": 10}
        self.qa["review"]["total"] = 95
        self.qa["review"]["issues"]["items"] = []
        (self.root / "qa-review.json").write_text(json.dumps(self.qa), encoding="utf-8")
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stdout)
        score = json.loads((self.root / "15-quality-scorecard.json").read_text())
        self.assertEqual(score["important"], [])
        verify = Path(__file__).resolve().parents[1] / "scripts/verify_quality_package.py"
        check = subprocess.run([sys.executable, str(verify), "--root", str(self.root)], capture_output=True, text=True)
        report = json.loads((self.root / "17-quality-verification.json").read_text())
        self.assertNotIn("FINAL_PEER_REVIEW_HASH", report["errors"])
        self.assertNotIn("IMPORTANT_SHAPE", report["errors"])
        self.assertEqual(report["metrics"]["ninety_plus_verified"], False)


if __name__ == "__main__":
    unittest.main()
