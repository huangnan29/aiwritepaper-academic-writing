"""评分退出写作流后的完整边界回归。"""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeReviewBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "figures").mkdir()
        (self.root / "figures/f.png").write_bytes(b"png")
        (self.root / "checked.png").write_bytes(b"checked")
        (self.root / "receipt.txt").write_text("真实查看记录")
        (self.root / "figures/figure-manifest.json").write_text(json.dumps({
            "figures": [{"figure_id": "f1", "final_embed_file": "figures/f.png"}]
        }))
        (self.root / "run-manifest.json").write_text(json.dumps({"direction_id": "general-journal-imrad"}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_observation_projection_never_creates_numeric_score(self):
        payload = {
            "schema_version": "2.1", "claims": [],
            "figures": [{"figure_id": "f1", "final_embed_file": "figures/f.png",
                         "checked_file": "checked.png", "visual_receipt": "receipt.txt",
                         "status": "PASS", "blind_summary": "核对节点和箭头"}],
            "document_checks": [], "issues": [],
        }
        (self.root / "qa-observations.json").write_text(json.dumps(payload, ensure_ascii=False))
        result = subprocess.run([sys.executable, str(ROOT / "scripts/prepare_audit_views.py"),
                                 "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.root / "15-quality-scorecard.json").exists())
        self.assertFalse((self.root / "09-final-peer-review.json").exists())

    def test_runtime_matrix_contains_only_four_bottom_checkers(self):
        matrix = json.loads((ROOT / "references/mode-checker-matrix.json").read_text())
        self.assertEqual(set(matrix["modes"]["FULL_BUILD"]), {"evidence", "figure", "formula", "delivery"})

    def test_eval_package_is_outside_runtime_adjudication(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import adjudicate_status
        self.assertNotIn("quality", adjudicate_status.REPORT_SPECS)


if __name__ == "__main__":
    unittest.main()
