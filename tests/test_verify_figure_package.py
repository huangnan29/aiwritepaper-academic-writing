#!/usr/bin/env python3
"""verify_figure_package.py的隔离测试。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_figure_package.py"
SPEC = importlib.util.spec_from_file_location("verify_figure_package", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FigurePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "figures").mkdir()
        (self.root / "data").mkdir()
        (self.root / "data/results.csv").write_text("group,value\nA,1\nB,2\n", encoding="utf-8")
        (self.root / "figures/plot.py").write_text("print('plot from data/results.csv')\n", encoding="utf-8")
        (self.root / "figures/fig-1-final.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        (self.root / "07-paper-full.md").write_text(
            "正文先引用图1。\n\n![趋势图](figures/fig-1-final.png)\n", encoding="utf-8"
        )
        with zipfile.ZipFile(self.root / "final-paper.docx", "w") as archive:
            archive.write(self.root / "figures/fig-1-final.png", "word/media/image1.png")
        (self.root / "final-paper.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        script_hash = hashlib.sha256((self.root / "figures/plot.py").read_bytes()).hexdigest()
        self.manifest = {
            "schema_version": "1.0",
            "figures": [{
                "figure_id": "fig-1", "title": "趋势图", "figure_type": "STATISTICAL",
                "claim_bearing": True, "generation_route": "DATA_CODE", "data_status": "OBSERVED",
                "prompt_file": None, "generated_file": None, "fallback_file": None,
                "source_data": [{"dataset_id": "results-v1", "file": "data/results.csv"}],
                "transformation": {"script": "figures/plot.py", "sha256": script_hash},
                "caption_claim": "B组高于A组", "supported_manuscript_claims": [{"claim": "B组更高", "locator": "结果"}],
                "limitations": [], "canvas_contains_figure_number_or_caption": False,
                "final_embed_file": "figures/fig-1-final.png",
                "vlm_verification": {"status": "PASS", "iterations": 1, "remaining_issues": []},
            }],
        }
        self.write_manifest()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manifest(self) -> None:
        (self.root / "figures/figure-manifest.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8"
        )

    def verify(self) -> MODULE.FigureVerifier:
        verifier = MODULE.FigureVerifier(self.root)
        verifier.verify_manifest(self.root / "figures/figure-manifest.json")
        verifier.verify_markdown(self.root / "07-paper-full.md")
        verifier.verify_docx(self.root / "final-paper.docx")
        verifier.verify_pdf(self.root / "final-paper.pdf")
        return verifier

    def test_valid_package(self) -> None:
        self.assertEqual(self.verify().errors, [])

    def test_proposed_data_status_fails(self) -> None:
        self.manifest["figures"][0]["data_status"] = "PROPOSED"
        self.write_manifest()
        self.assertTrue(any("DATA_STATUS_INVALID" in item for item in self.verify().errors))

    def test_script_hash_mismatch_fails(self) -> None:
        self.manifest["figures"][0]["transformation"]["sha256"] = "0" * 64
        self.write_manifest()
        self.assertTrue(any("SCRIPT_HASH_MISMATCH" in item for item in self.verify().errors))

    def test_markdown_wrong_image_fails(self) -> None:
        (self.root / "figures/other.png").write_bytes(b"other")
        (self.root / "07-paper-full.md").write_text("![错误](figures/other.png)\n", encoding="utf-8")
        errors = self.verify().errors
        self.assertTrue(any("MARKDOWN_ROUTE" in item for item in errors))
        self.assertTrue(any("MARKDOWN_EXTRA_IMAGES" in item for item in errors))

    def test_randomness_requires_declaration(self) -> None:
        (self.root / "figures/plot.py").write_text("import numpy as np\nnp.random.seed(42)\n", encoding="utf-8")
        self.manifest["figures"][0]["transformation"]["sha256"] = hashlib.sha256(
            (self.root / "figures/plot.py").read_bytes()
        ).hexdigest()
        self.write_manifest()
        self.assertTrue(any("RANDOMNESS_UNDECLARED" in item for item in self.verify().errors))

    def test_image_generation_cannot_finish_as_svg(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/prompt.md").write_text("prompt", encoding="utf-8")
        (self.root / "figures/generated.png").write_bytes(b"generated")
        (self.root / "figures/fallback.svg").write_text("<svg/>", encoding="utf-8")
        figure.update({
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "prompt_file": "figures/prompt.md", "generated_file": "figures/generated.png",
            "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "none"}, "final_embed_file": "figures/fallback.svg",
        })
        self.write_manifest()
        errors = self.verify().errors
        self.assertTrue(any("FINAL_FORMAT" in item for item in errors))

    def test_valid_image_generation_embeds_generated_file(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/prompt.md").write_text("prompt", encoding="utf-8")
        figure.update({
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False,
            "prompt_file": "figures/prompt.md", "generated_file": "figures/fig-1-final.png",
            "source_data": [], "transformation": {"method": "none"},
        })
        self.write_manifest()
        self.assertEqual(self.verify().errors, [])

    def test_caption_inside_canvas_fails(self) -> None:
        self.manifest["figures"][0]["canvas_contains_figure_number_or_caption"] = True
        self.write_manifest()
        self.assertTrue(any("CAPTION_IN_CANVAS" in item for item in self.verify().errors))

    def test_docx_media_mismatch_fails(self) -> None:
        with zipfile.ZipFile(self.root / "final-paper.docx", "w") as archive:
            archive.writestr("word/media/image1.png", b"wrong-image")
        self.assertTrue(any("DOCX_MEDIA_MISMATCH" in item for item in self.verify().errors))

    def test_svg_fallback_requires_cjk_font(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/fallback.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><text>中文节点</text></svg>', encoding="utf-8"
        )
        figure.update({
            "generation_route": "SVG_FALLBACK", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False,
            "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "svg-render"}, "capability_gap": "IMAGE_GENERATOR unavailable",
        })
        self.write_manifest()
        self.assertTrue(any("SVG_CJK_FONT_MISSING" in item for item in self.verify().errors))


if __name__ == "__main__":
    unittest.main()
