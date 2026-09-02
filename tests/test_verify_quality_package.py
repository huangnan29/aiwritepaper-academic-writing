#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_quality_package.py"
PNG = b"\x89PNG\r\n\x1a\n" + b"test-page-image"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "figures").mkdir()
        (self.root / "checked.png").write_bytes(PNG)
        (self.root / "receipt.txt").write_text("视觉工具已检查页面", encoding="utf-8")
        (self.root / "07-paper-full.md").write_text("# 正文\n研究内容", encoding="utf-8")
        (self.root / "paper.docx").write_bytes(b"docx")
        (self.root / "paper.pdf").write_bytes(b"%PDF-test")
        artifact = {
            "checked_file": "checked.png", "checked_file_sha256": digest(self.root / "checked.png"),
            "visual_receipt": "receipt.txt", "visual_receipt_sha256": digest(self.root / "receipt.txt"),
        }
        manifest = {
            "direction_id": "electronic-circuit-design", "docx": "paper.docx", "pdf": "paper.pdf",
            "delivery_verification_report": "13-delivery-verification.json",
        }
        (self.root / "run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (self.root / "13-delivery-verification.json").write_text(json.dumps({"status": "DELIVERY_OK", "warnings": []}), encoding="utf-8")
        (self.root / "claim-evidence-map.json").write_text(json.dumps({
            "claims": [{"location": "结论", "importance": "CONCLUSION", "evidence_ids": ["S1"]}],
        }, ensure_ascii=False), encoding="utf-8")
        (self.root / "figures/figure-manifest.json").write_text(json.dumps({"figures": [{"figure_id": "f1"}]}), encoding="utf-8")
        (self.root / "figures/figure-semantic-audit.json").write_text(json.dumps({
            "figures": [{"figure_id": "f1", "status": "PASS", "blind_summary": "电路关系", **artifact}],
        }, ensure_ascii=False), encoding="utf-8")
        checks = [{"checkpoint": name, "status": "PASS", "page": 1, **artifact} for name in [
            "cover", "primary_abstract", "toc", "complex_table", "complex_formula",
            "representative_figure", "references", "last_page",
        ]]
        (self.root / "16-document-visual-audit.json").write_text(json.dumps({"checks": checks}), encoding="utf-8")
        self.scores = {"evidence": 23, "content": 18, "structure": 14, "figures": 14, "documents": 14, "integrity": 9}
        reviewed = {
            relative: digest(self.root / relative)
            for relative in ["07-paper-full.md", "figures/figure-manifest.json", "16-document-visual-audit.json", "paper.docx", "paper.pdf"]
        }
        review = {
            "schema_version": "1.0", "direction_id": "electronic-circuit-design",
            "status": "PASS", "reviewer_mode": "ISOLATED",
            "issues": {"critical_open": 0, "important_open": 0},
            "alignment": {
                "title_supported": True, "research_question_answered": True,
                "method_result_consistent": True, "abstract_conclusion_consistent": True,
            },
            "scores": self.scores, "total": 92, "reviewed_artifacts": reviewed,
        }
        (self.root / "09-final-peer-review.json").write_text(json.dumps(review), encoding="utf-8")
        score = {
            "direction_id": "electronic-circuit-design", "scores": self.scores,
            "critical": [], "important": [], "total": 92,
            "reviewer_report": "09-final-peer-review.json",
            "reviewer_report_sha256": digest(self.root / "09-final-peer-review.json"),
        }
        (self.root / "15-quality-scorecard.json").write_text(json.dumps(score), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_quality(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root)], capture_output=True, text=True)

    def report(self):
        return json.loads((self.root / "17-quality-verification.json").read_text())

    def test_quality_ok(self):
        self.assertEqual(self.run_quality().returncode, 0)
        self.assertEqual(self.report()["status"], "QUALITY_OK")

    def test_critical_fails(self):
        path = self.root / "15-quality-scorecard.json"
        payload = json.loads(path.read_text())
        payload["critical"] = ["错误"]
        path.write_text(json.dumps(payload))
        self.assertNotEqual(self.run_quality().returncode, 0)

    def test_open_important_fails(self):
        path = self.root / "15-quality-scorecard.json"
        payload = json.loads(path.read_text())
        payload["important"] = [{"status": "OPEN"}]
        path.write_text(json.dumps(payload))
        self.assertNotEqual(self.run_quality().returncode, 0)
        self.assertIn("IMPORTANT_NOT_RESOLVED", self.report()["errors"])

    def test_whole_pdf_cannot_be_page_image(self):
        path = self.root / "16-document-visual-audit.json"
        payload = json.loads(path.read_text())
        payload["checks"][0]["checked_file"] = "paper.pdf"
        payload["checks"][0]["checked_file_sha256"] = digest(self.root / "paper.pdf")
        path.write_text(json.dumps(payload))
        self.assertNotEqual(self.run_quality().returncode, 0)
        self.assertIn("DOCUMENT_VISUAL_CHECKED_FILE_NOT_PAGE_IMAGE", self.report()["errors"])

    def test_invalid_direction_fails(self):
        path = self.root / "run-manifest.json"
        payload = json.loads(path.read_text())
        payload["direction_id"] = "invented-direction"
        path.write_text(json.dumps(payload))
        self.assertNotEqual(self.run_quality().returncode, 0)
        self.assertIn("DIRECTION_ID_INVALID", self.report()["errors"])

    def test_score_cannot_change_after_final_review(self):
        path = self.root / "15-quality-scorecard.json"
        payload = json.loads(path.read_text())
        payload["scores"]["content"] = 19
        payload["total"] = 93
        path.write_text(json.dumps(payload))
        self.assertNotEqual(self.run_quality().returncode, 0)
        self.assertIn("FINAL_PEER_REVIEW_SCORE_MISMATCH", self.report()["errors"])

    def test_alignment_failure_blocks_quality(self):
        review_path = self.root / "09-final-peer-review.json"
        review = json.loads(review_path.read_text())
        review["alignment"]["title_supported"] = False
        review_path.write_text(json.dumps(review))
        score_path = self.root / "15-quality-scorecard.json"
        score = json.loads(score_path.read_text())
        score["reviewer_report_sha256"] = digest(review_path)
        score_path.write_text(json.dumps(score))
        self.assertNotEqual(self.run_quality().returncode, 0)
        self.assertIn("FINAL_PEER_REVIEW_ALIGNMENT_FAIL", self.report()["errors"])

    def test_target_undershoot_caps_quality_at_partial(self):
        delivery_path = self.root / "13-delivery-verification.json"
        delivery_path.write_text(json.dumps({
            "status": "DELIVERY_OK", "warnings": ["BODY_TARGET_UNDERSHOOT: 实际18000，建议19000"],
        }), encoding="utf-8")
        self.assertEqual(self.run_quality().returncode, 0)
        self.assertEqual(self.report()["status"], "QUALITY_PARTIAL")

    def test_excessive_conclusion_ratio_is_warning(self):
        paper = self.root / "07-paper-full.md"
        paper.write_text(
            "# 第1章 绪论\n" + "正文论证。" * 60 + "\n# 第7章 结论\n" + "重复结论。" * 80,
            encoding="utf-8",
        )
        review_path = self.root / "09-final-peer-review.json"
        review = json.loads(review_path.read_text())
        review["reviewed_artifacts"]["07-paper-full.md"] = digest(paper)
        review_path.write_text(json.dumps(review))
        score_path = self.root / "15-quality-scorecard.json"
        score = json.loads(score_path.read_text())
        score["reviewer_report_sha256"] = digest(review_path)
        score_path.write_text(json.dumps(score))
        self.assertEqual(self.run_quality().returncode, 0)
        self.assertIn("CONCLUSION_RATIO_EXCESSIVE", self.report()["warnings"])


if __name__ == "__main__":
    unittest.main()
