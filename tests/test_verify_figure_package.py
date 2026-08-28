#!/usr/bin/env python3
"""verify_figure_package.py的隔离测试。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
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
        (self.root / "00-capability-report.json").write_text(json.dumps({
            "schema_version": "1.0", "agent_adapter": "codex",
            "observed_at": "2026-08-24T09:00:00-07:00",
            "image_generation": {
                "available": True, "callers": ["CURRENT_AGENT"],
                "tools": ["imagegen"], "evidence": "测试工具清单",
            },
            "visual_inspection": {"available": True, "callers": ["CURRENT_AGENT"], "tools": ["view_image"], "evidence": "测试"},
            "docx_export": {"available": True, "callers": ["CURRENT_AGENT"], "tools": ["python-docx"], "evidence": "测试"},
            "pdf_export": {"available": True, "callers": ["CURRENT_AGENT"], "tools": ["pypdf"], "evidence": "测试"},
        }, ensure_ascii=False), encoding="utf-8")
        (self.root / "data/results.csv").write_text("group,value\nA,1\nB,2\n", encoding="utf-8")
        (self.root / "figures/plot.py").write_text("print('plot from data/results.csv')\n", encoding="utf-8")
        (self.root / "figures/fig-1-final.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        (self.root / "figures/vlm-receipt.txt").write_text("视觉工具检查结果：通过", encoding="utf-8")
        (self.root / "figures/data-execution.log").write_text(
            "uv run python figures/plot.py --input data/results.csv --output figures/fig-1-final.png",
            encoding="utf-8",
        )
        (self.root / "07-paper-full.md").write_text(
            "正文先引用图1。\n\n![趋势图](figures/fig-1-final.png)\n", encoding="utf-8"
        )
        (self.root / "figures/figure-manifest.md").write_text(
            "| figure_id | final_embed_file |\n|---|---|\n| fig-1 | figures/fig-1-final.png |\n",
            encoding="utf-8",
        )
        document_xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>第一章 绪论</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1 背景</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>1.1.1 问题</w:t></w:r></w:p>
<w:p><w:r><w:instrText>TOC \\o "1-3"</w:instrText></w:r></w:p>
<w:p><w:r><w:t>图1 趋势图</w:t></w:r></w:p>
</w:body></w:document>'''
        with zipfile.ZipFile(self.root / "final-paper.docx", "w") as archive:
            archive.write(self.root / "figures/fig-1-final.png", "word/media/image1.png")
            archive.writestr("word/document.xml", document_xml)
        try:
            from pypdf import PdfWriter
            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            with (self.root / "final-paper.pdf").open("wb") as handle:
                writer.write(handle)
        except ImportError:
            (self.root / "final-paper.pdf").write_bytes(b"%PDF-1.4\n%%EOF")
        (self.root / "run-manifest.json").write_text(json.dumps({
            "docx": "final-paper.docx", "pdf": "final-paper.pdf",
        }), encoding="utf-8")
        script_hash = hashlib.sha256((self.root / "figures/plot.py").read_bytes()).hexdigest()
        final_hash = hashlib.sha256((self.root / "figures/fig-1-final.png").read_bytes()).hexdigest()
        vlm_receipt_hash = hashlib.sha256((self.root / "figures/vlm-receipt.txt").read_bytes()).hexdigest()
        source_hash = hashlib.sha256((self.root / "data/results.csv").read_bytes()).hexdigest()
        execution_hash = hashlib.sha256((self.root / "figures/data-execution.log").read_bytes()).hexdigest()
        self.manifest = {
            "schema_version": "1.5",
            "figures": [{
                "figure_id": "fig-1", "display_number": "1", "title": "趋势图", "figure_type": "STATISTICAL",
                "exactness_class": "DATA_GRAPH", "imagegen_eligible": False, "route_exemption": None,
                "claim_bearing": True, "generation_route": "DATA_CODE", "data_status": "OBSERVED",
                "prompt_file": None, "generated_file": None, "fallback_file": None,
                "source_data": [{"dataset_id": "results-v1", "file": "data/results.csv", "sha256": source_hash, "origin": "USER_PROVIDED", "acquisition_receipt": None}],
                "transformation": {
                    "script": "figures/plot.py", "sha256": script_hash,
                    "execution_receipt": {
                        "command": "uv run python figures/plot.py --input data/results.csv --output figures/fig-1-final.png",
                        "receipt_file": "figures/data-execution.log", "receipt_sha256": execution_hash,
                        "script_sha256": script_hash,
                        "inputs": [{"file": "data/results.csv", "sha256": source_hash}],
                        "output_sha256": final_hash,
                    },
                },
                "caption_claim": "B组高于A组", "supported_manuscript_claims": [{"claim": "B组更高", "locator": "结果"}],
                "limitations": [], "canvas_contains_figure_number_or_caption": False,
                "generation_receipt": None,
                "svg_layout_mode": None, "svg_layout": None,
                "language_contract": {
                    "manuscript_language": "zh-CN", "label_language": "zh-CN",
                    "exact_labels": ["实验组", "对照组"],
                    "allowed_foreign_tokens": ["95% CI"],
                },
                "text_render_strategy": "DOMAIN_VECTOR_TEXT", "text_overlay": None,
                "final_embed_file": "figures/fig-1-final.png",
                "vlm_verification": {
                    "status": "PASS", "iterations": 1, "remaining_issues": [],
                    "evidence_level": "VISUAL_TOOL_RESULT", "tool": "view_image",
                    "checked_at": "2026-08-23T09:05:00-07:00",
                    "checked_file_sha256": final_hash, "receipt_file": "figures/vlm-receipt.txt",
                    "receipt_sha256": vlm_receipt_hash,
                    "language_check": {
                        "status": "PASS", "target_language": "zh-CN",
                        "observed_language": "zh-CN+technical-tokens",
                        "unintended_foreign_text": [], "allowed_foreign_tokens_verified": True,
                        "exact_labels_verified": True,
                    },
                },
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
        verifier.verify_capability_report(self.root / "00-capability-report.json")
        verifier.verify_manifest(self.root / "figures/figure-manifest.json")
        verifier.verify_manifest_summary(self.root / "figures/figure-manifest.md")
        verifier.verify_markdown(self.root / "07-paper-full.md")
        verifier.verify_docx(self.root / "final-paper.docx")
        verifier.verify_pdf(self.root / "final-paper.pdf")
        return verifier

    def test_valid_package(self) -> None:
        self.assertEqual(self.verify().errors, [])

    def test_cli_reads_document_paths_from_run_manifest(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "STRUCTURE_OK")

    def test_proposed_data_status_fails(self) -> None:
        self.manifest["figures"][0]["data_status"] = "PROPOSED"
        self.write_manifest()
        self.assertTrue(any("DATA_STATUS_INVALID" in item for item in self.verify().errors))

    def test_script_hash_mismatch_fails(self) -> None:
        self.manifest["figures"][0]["transformation"]["sha256"] = "0" * 64
        self.write_manifest()
        self.assertTrue(any("SCRIPT_HASH_MISMATCH" in item for item in self.verify().errors))

    def test_data_execution_input_mismatch_fails(self) -> None:
        self.manifest["figures"][0]["transformation"]["execution_receipt"]["inputs"][0]["sha256"] = "0" * 64
        self.write_manifest()
        self.assertTrue(any("DATA_EXECUTION_INPUT_MISMATCH" in item for item in self.verify().errors))

    def test_source_data_hash_mismatch_fails(self) -> None:
        self.manifest["figures"][0]["source_data"][0]["sha256"] = "0" * 64
        self.write_manifest()
        self.assertTrue(any("SOURCE_DATA_HASH_MISMATCH" in item for item in self.verify().errors))

    def test_model_synthetic_data_cannot_support_result(self) -> None:
        self.manifest["figures"][0]["source_data"][0]["origin"] = "MODEL_SYNTHETIC"
        self.write_manifest()
        self.assertTrue(any("MODEL_SYNTHETIC_RESULT_FORBIDDEN" in item for item in self.verify().errors))

    def test_markdown_wrong_image_fails(self) -> None:
        (self.root / "figures/other.png").write_bytes(b"other")
        (self.root / "07-paper-full.md").write_text("![错误](figures/other.png)\n", encoding="utf-8")
        errors = self.verify().errors
        self.assertTrue(any("MARKDOWN_ROUTE" in item for item in errors))
        self.assertTrue(any("MARKDOWN_EXTRA_IMAGES" in item for item in errors))

    def test_manifest_summary_wrong_route_fails(self) -> None:
        (self.root / "figures/figure-manifest.md").write_text(
            "| figure_id | final_embed_file |\n|---|---|\n| fig-1 | figures/old.svg |\n", encoding="utf-8"
        )
        self.assertTrue(any("MANIFEST_SUMMARY_ROUTE" in item for item in self.verify().errors))

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
            "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True, "route_exemption": None,
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "prompt_file": "figures/prompt.md", "generated_file": "figures/generated.png",
            "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "none"}, "final_embed_file": "figures/fallback.svg",
        })
        self.write_manifest()
        errors = self.verify().errors
        self.assertTrue(any("FINAL_FORMAT" in item for item in errors))

    def test_imagegen_available_blocks_structural_svg(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/fallback.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><style>text{font-family:"PingFang SC"}</style></svg>',
            encoding="utf-8",
        )
        figure.update({
            "figure_type": "PROCESS", "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True,
            "route_exemption": "IMAGE_TOOL_UNAVAILABLE", "generation_route": "SVG_FALLBACK",
            "data_status": "NOT_APPLICABLE", "claim_bearing": False,
            "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "svg-render"}, "capability_gap": "子执行器未暴露工具",
            "svg_layout_mode": "NATIVE", "svg_layout": None,
        })
        self.write_manifest()
        errors = self.verify().errors
        self.assertTrue(any("IMAGEGEN_BYPASSED" in item for item in errors))
        self.assertTrue(any("FALSE_IMAGE_TOOL_GAP" in item for item in errors))

    def test_valid_image_generation_embeds_generated_file(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/prompt.md").write_text("逐字标签：实验组、对照组", encoding="utf-8")
        (self.root / "figures/tool-receipt.json").write_text(
            '{"source":"native tool result","call_id":"call-123"}', encoding="utf-8"
        )
        prompt_hash = hashlib.sha256((self.root / "figures/prompt.md").read_bytes()).hexdigest()
        generated_hash = hashlib.sha256((self.root / "figures/fig-1-final.png").read_bytes()).hexdigest()
        receipt_hash = hashlib.sha256((self.root / "figures/tool-receipt.json").read_bytes()).hexdigest()
        figure.update({
            "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True, "route_exemption": None,
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False,
            "prompt_file": "figures/prompt.md", "generated_file": "figures/fig-1-final.png",
            "source_data": [], "transformation": {"method": "none"},
            "text_render_strategy": "DIRECT_IMAGE_TEXT", "text_overlay": None,
            "generation_receipt": {
                "evidence_level": "NATIVE_TOOL_RESULT", "tool": "imagegen", "provider": "OpenAI",
                "model": "gpt-image", "invoked_at": "2026-08-23T09:00:00-07:00",
                "call_id": "call-123", "receipt_file": "figures/tool-receipt.json",
                "receipt_sha256": receipt_hash, "prompt_sha256": prompt_hash,
                "generated_sha256": generated_hash,
            },
        })
        self.write_manifest()
        self.assertEqual(self.verify().errors, [])

    def test_domain_exact_cannot_use_image_generation(self) -> None:
        figure = self.manifest["figures"][0]
        figure.update({
            "title": "精确传感器接线电路", "figure_type": "DOMAIN",
            "exactness_class": "DOMAIN_EXACT", "imagegen_eligible": True,
            "generation_route": "IMAGE_GENERATION", "route_exemption": None,
            "claim_bearing": False, "data_status": "NOT_APPLICABLE",
            "source_data": [], "transformation": {},
        })
        self.write_manifest()
        self.assertTrue(any("DOMAIN_EXACT_IMAGEGEN_FORBIDDEN" in item for item in self.verify().errors))

    def test_skipped_visual_check_marks_partial(self) -> None:
        self.manifest["figures"][0]["vlm_verification"] = {
            "status": "SKIPPED", "remaining_issues": [], "reason": "无视觉工具",
            "language_check": {
                "status": "SKIPPED", "reason": "无视觉工具", "target_language": "zh-CN",
                "observed_language": "unknown", "unintended_foreign_text": [],
                "allowed_foreign_tokens_verified": True, "exact_labels_verified": True,
            },
        }
        self.write_manifest()
        verifier = self.verify()
        self.assertEqual(verifier.errors, [])
        self.assertEqual(verifier.visual_status, "PARTIAL")

    def test_chinese_manuscript_rejects_english_figure_language(self) -> None:
        contract = self.manifest["figures"][0]["language_contract"]
        contract["label_language"] = "en-US"
        language_check = self.manifest["figures"][0]["vlm_verification"]["language_check"]
        language_check["target_language"] = "en-US"
        language_check["observed_language"] = "en-US"
        self.write_manifest()
        self.assertTrue(any("FIGURE_LANGUAGE_MISMATCH" in item for item in self.verify().errors))

    def test_language_check_rejects_unintended_english(self) -> None:
        language_check = self.manifest["figures"][0]["vlm_verification"]["language_check"]
        language_check["unintended_foreign_text"] = ["Power supply"]
        self.write_manifest()
        self.assertTrue(any("LANGUAGE_CHECK_FOREIGN_TEXT" in item for item in self.verify().errors))

    def test_text_strategy_requires_exact_labels(self) -> None:
        self.manifest["figures"][0]["language_contract"]["exact_labels"] = []
        self.write_manifest()
        self.assertTrue(any("EXACT_LABELS_MISSING" in item for item in self.verify().errors))

    def test_image_prompt_requires_exact_labels(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/prompt.md").write_text("English labels only", encoding="utf-8")
        figure.update({
            "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True,
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False, "prompt_file": "figures/prompt.md",
            "generated_file": "figures/fig-1-final.png", "source_data": [],
            "transformation": {"method": "none"}, "generation_receipt": None,
            "text_render_strategy": "DIRECT_IMAGE_TEXT", "text_overlay": None,
        })
        self.write_manifest()
        self.assertTrue(any("PROMPT_EXACT_LABEL_MISSING" in item for item in self.verify().errors))

    def test_valid_deterministic_text_overlay(self) -> None:
        figure = self.manifest["figures"][0]
        prompt = self.root / "figures/prompt.md"
        prompt.write_text("生成无文字底图；逐字标签：实验组、对照组", encoding="utf-8")
        generated = self.root / "figures/generated-base.png"
        generated.write_bytes(b"generated-base")
        tool_receipt = self.root / "figures/tool-receipt.json"
        tool_receipt.write_text('{"source":"native","call_id":"call-overlay"}', encoding="utf-8")
        overlay_source = self.root / "figures/labels.svg"
        overlay_source.write_text('<svg><text>实验组</text><text>对照组</text></svg>', encoding="utf-8")
        overlay_receipt = self.root / "figures/overlay.log"
        overlay_receipt.write_text("render labels.svg over generated-base.png", encoding="utf-8")
        figure.update({
            "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True,
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False, "prompt_file": "figures/prompt.md",
            "generated_file": "figures/generated-base.png", "source_data": [],
            "transformation": {"method": "generated_bitmap_plus_svg_text_overlay"},
            "text_render_strategy": "DETERMINISTIC_OVERLAY",
            "generation_receipt": {
                "evidence_level": "NATIVE_TOOL_RESULT", "tool": "imagegen", "provider": "OpenAI",
                "model": "gpt-image", "invoked_at": "2026-08-23T09:00:00-07:00",
                "call_id": "call-overlay", "receipt_file": "figures/tool-receipt.json",
                "receipt_sha256": hashlib.sha256(tool_receipt.read_bytes()).hexdigest(),
                "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                "generated_sha256": hashlib.sha256(generated.read_bytes()).hexdigest(),
            },
            "text_overlay": {
                "source_file": "figures/labels.svg",
                "source_sha256": hashlib.sha256(overlay_source.read_bytes()).hexdigest(),
                "receipt_file": "figures/overlay.log",
                "receipt_sha256": hashlib.sha256(overlay_receipt.read_bytes()).hexdigest(),
                "base_generated_sha256": hashlib.sha256(generated.read_bytes()).hexdigest(),
                "final_sha256": hashlib.sha256((self.root / "figures/fig-1-final.png").read_bytes()).hexdigest(),
                "method": "SVG labels composited over generated bitmap",
            },
        })
        self.write_manifest()
        self.assertEqual(self.verify().errors, [])

    def test_image_generation_without_receipt_fails(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/prompt.md").write_text("prompt", encoding="utf-8")
        figure.update({
            "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True, "route_exemption": None,
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False, "prompt_file": "figures/prompt.md",
            "generated_file": "figures/fig-1-final.png", "source_data": [],
            "transformation": {"method": "none"}, "generation_receipt": None,
        })
        self.write_manifest()
        self.assertTrue(any("GENERATION_RECEIPT_MISSING" in item for item in self.verify().errors))

    def test_declared_only_generation_receipt_fails(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/prompt.md").write_text("prompt", encoding="utf-8")
        (self.root / "figures/tool-receipt.txt").write_text("模型自述", encoding="utf-8")
        figure.update({
            "exactness_class": "SEMANTIC_STRUCTURE", "imagegen_eligible": True, "route_exemption": None,
            "generation_route": "IMAGE_GENERATION", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False, "prompt_file": "figures/prompt.md",
            "generated_file": "figures/fig-1-final.png", "source_data": [],
            "transformation": {"method": "none"},
            "generation_receipt": {
                "evidence_level": "DECLARED_ONLY", "tool": "Imagine", "provider": "Grok",
                "model": "NOT_EXPOSED", "invoked_at": "2026-08-23T09:00:00-07:00",
                "call_id": "NOT_EXPOSED", "receipt_file": "figures/tool-receipt.txt",
                "receipt_sha256": hashlib.sha256((self.root / "figures/tool-receipt.txt").read_bytes()).hexdigest(),
                "prompt_sha256": hashlib.sha256((self.root / "figures/prompt.md").read_bytes()).hexdigest(),
                "generated_sha256": hashlib.sha256((self.root / "figures/fig-1-final.png").read_bytes()).hexdigest(),
            },
        })
        self.write_manifest()
        self.assertTrue(any("GENERATION_RECEIPT_UNVERIFIED" in item for item in self.verify().errors))

    def test_caption_inside_canvas_fails(self) -> None:
        self.manifest["figures"][0]["canvas_contains_figure_number_or_caption"] = True
        self.write_manifest()
        self.assertTrue(any("CAPTION_IN_CANVAS" in item for item in self.verify().errors))

    def test_declared_only_vlm_pass_fails(self) -> None:
        self.manifest["figures"][0]["vlm_verification"]["evidence_level"] = "DECLARED_ONLY"
        self.write_manifest()
        self.assertTrue(any("VLM_RECEIPT_UNVERIFIED" in item for item in self.verify().errors))

    def test_vlm_checked_wrong_file_fails(self) -> None:
        self.manifest["figures"][0]["vlm_verification"]["checked_file_sha256"] = "0" * 64
        self.write_manifest()
        self.assertTrue(any("VLM_CHECKED_FILE_MISMATCH" in item for item in self.verify().errors))

    def test_docx_media_mismatch_fails(self) -> None:
        with zipfile.ZipFile(self.root / "final-paper.docx", "w") as archive:
            archive.writestr("word/media/image1.png", b"wrong-image")
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body/></w:document>',
            )
        self.assertTrue(any("DOCX_MEDIA_MISMATCH" in item for item in self.verify().errors))

    def test_docx_missing_toc_fails(self) -> None:
        with zipfile.ZipFile(self.root / "final-paper.docx", "w") as archive:
            archive.write(self.root / "figures/fig-1-final.png", "word/media/image1.png")
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>第一章</w:t></w:r></w:p>'
                '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>图1 趋势图</w:t></w:r></w:p>'
                '</w:body></w:document>',
            )
        self.assertTrue(any("DOCX_TOC_FIELD_MISSING" in item for item in self.verify().errors))

    def test_docx_duplicate_figure_caption_fails(self) -> None:
        with zipfile.ZipFile(self.root / "final-paper.docx", "w") as archive:
            archive.write(self.root / "figures/fig-1-final.png", "word/media/image1.png")
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>第一章</w:t></w:r></w:p>'
                '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1</w:t></w:r></w:p>'
                '<w:p><w:r><w:instrText>TOC \\o "1-3"</w:instrText></w:r></w:p>'
                '<w:p><w:r><w:t>图1 趋势图</w:t></w:r></w:p><w:p><w:r><w:t>图1 趋势图</w:t></w:r></w:p>'
                '</w:body></w:document>',
            )
        self.assertTrue(any("DOCX_FIGURE_CAPTION_DUPLICATE" in item for item in self.verify().errors))

    def test_svg_fallback_requires_cjk_font(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/fallback.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><text>中文节点</text></svg>', encoding="utf-8"
        )
        figure.update({
            "exactness_class": "DOMAIN_EXACT", "imagegen_eligible": False, "route_exemption": "DOMAIN_EXACTNESS",
            "generation_route": "SVG_FALLBACK", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False,
            "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "svg-render"}, "capability_gap": "IMAGE_GENERATOR unavailable",
            "svg_layout_mode": "NATIVE", "svg_layout": None,
        })
        self.write_manifest()
        self.assertTrue(any("SVG_CJK_FONT_MISSING" in item for item in self.verify().errors))

    def test_svg_crossing_lines_fail(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/fallback.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><line x1="0" y1="0" x2="100" y2="100"/>'
            '<line x1="0" y1="100" x2="100" y2="0"/></svg>', encoding="utf-8"
        )
        figure.update({
            "exactness_class": "DOMAIN_EXACT", "imagegen_eligible": False, "route_exemption": "DOMAIN_EXACTNESS",
            "generation_route": "SVG_FALLBACK", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False, "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "svg-render"}, "capability_gap": "IMAGE_GENERATOR unavailable",
            "svg_layout_mode": "NATIVE", "svg_layout": None,
        })
        self.write_manifest()
        self.assertTrue(any("SVG_LINE_CROSSING" in item for item in self.verify().errors))

    def test_svg_collinear_overlap_fails(self) -> None:
        figure = self.manifest["figures"][0]
        (self.root / "figures/fallback.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<line x1="20" y1="40" x2="160" y2="40"/>'
            '<polyline points="80,40 200,40 200,100"/>'
            '</svg>', encoding="utf-8"
        )
        figure.update({
            "exactness_class": "DOMAIN_EXACT", "imagegen_eligible": False,
            "route_exemption": "DOMAIN_EXACTNESS", "generation_route": "SVG_FALLBACK",
            "data_status": "NOT_APPLICABLE", "claim_bearing": False,
            "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "svg-render"},
            "capability_gap": "IMAGE_GENERATOR unavailable",
            "svg_layout_mode": "NATIVE", "svg_layout": None,
        })
        self.write_manifest()
        self.assertTrue(any("SVG_LINE_COLLINEAR_OVERLAP" in item for item in self.verify().errors))

    def test_svg_preflight_cli(self) -> None:
        svg = self.root / "figures/preflight.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<style>text{font-family:"PingFang SC",sans-serif}</style>'
            '<rect x="10" y="10" width="100" height="50"/>'
            '<text x="20" y="35">中文节点</text>'
            '</svg>', encoding="utf-8"
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(self.root), "--preflight-svg", "figures/preflight.svg"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "SVG_PREFLIGHT_OK")

    def make_compiled_svg_figure(self) -> None:
        figure = self.manifest["figures"][0]
        fallback = self.root / "figures/fallback.svg"
        fallback.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"><style>text{font-family:"PingFang SC",sans-serif}</style>'
            '<rect x="10" y="10" width="120" height="60"/><text x="20" y="40">中文节点</text></svg>',
            encoding="utf-8",
        )
        spec = self.root / "figures/fig-1-spec.json"
        spec.write_text(
            '{"version":"1.0","figure_id":"fig-1","template":"process","direction":"LR",'
            '"nodes":[{"id":"n1","label":"中文节点"}],"edges":[]}', encoding="utf-8"
        )
        report = self.root / "figures/fig-1-layout-report.json"
        report.write_text(json.dumps({
            "status": "PASS",
            "input_sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(fallback.read_bytes()).hexdigest(),
        }), encoding="utf-8")
        renderer = SCRIPT.with_name("render_svg_layout.mjs")
        figure.update({
            "exactness_class": "DOMAIN_EXACT", "imagegen_eligible": False, "route_exemption": "DOMAIN_EXACTNESS",
            "generation_route": "SVG_FALLBACK", "data_status": "NOT_APPLICABLE",
            "claim_bearing": False, "fallback_file": "figures/fallback.svg", "source_data": [],
            "transformation": {"method": "svg-layout-compiled"},
            "capability_gap": "IMAGE_GENERATOR unavailable",
            "svg_layout_mode": "COMPILED",
            "svg_layout": {
                "spec_file": "figures/fig-1-spec.json",
                "spec_sha256": hashlib.sha256(spec.read_bytes()).hexdigest(),
                "report_file": "figures/fig-1-layout-report.json",
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
                "renderer": "aiwritepaper-academic-writing@1.2.0/render_svg_layout.mjs",
                "renderer_sha256": hashlib.sha256(renderer.read_bytes()).hexdigest(),
            },
        })
        self.write_manifest()

    def test_valid_compiled_svg_layout(self) -> None:
        self.make_compiled_svg_figure()
        self.assertEqual(self.verify().errors, [])

    def test_compiled_svg_wrong_output_hash_fails(self) -> None:
        self.make_compiled_svg_figure()
        report = self.root / "figures/fig-1-layout-report.json"
        payload = json.loads(report.read_text(encoding="utf-8"))
        payload["output_sha256"] = "0" * 64
        report.write_text(json.dumps(payload), encoding="utf-8")
        figure = self.manifest["figures"][0]
        figure["svg_layout"]["report_sha256"] = hashlib.sha256(report.read_bytes()).hexdigest()
        self.write_manifest()
        self.assertTrue(any("SVG_LAYOUT_OUTPUT_MISMATCH" in item for item in self.verify().errors))


if __name__ == "__main__":
    unittest.main()
