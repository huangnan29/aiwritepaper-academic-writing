#!/usr/bin/env python3
"""audit_svg.py 的最小标准库单元测试。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_svg.py"
SPEC = importlib.util.spec_from_file_location("audit_svg", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:  # 测试环境损坏时提示
    raise RuntimeError(f"无法加载审计脚本：{SCRIPT_PATH}")
AUDIT = importlib.util.module_from_spec(SPEC)
# dataclasses 需要模块已经登记在 sys.modules 中，动态加载时显式补上。
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120" width="240" height="120" font-family="Noto Sans CJK SC, sans-serif">
  <title>研究流程图</title>
  <desc>展示研究步骤之间的顺序关系。</desc>
  <rect x="10" y="10" width="220" height="100" fill="#ffffff" stroke="#333333"/>
  <text x="120" y="65" text-anchor="middle" font-size="12px">研究步骤</text>
</svg>"""


class AuditSvgTests(unittest.TestCase):
    """覆盖通过、失败、JSON 输出和多个文件汇总。"""

    def write_svg(self, directory: Path, name: str, content: str) -> Path:
        """写入临时 SVG，测试结束后由 TemporaryDirectory 自动清理。"""

        path = directory / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_svg_passes(self) -> None:
        """完整的自包含 SVG 应通过所有默认静态门。"""

        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "valid.svg", VALID_SVG)
            result = AUDIT.audit_svg(path)

        self.assertTrue(result["ok"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["metrics"]["text_element_count"], 1)
        self.assertEqual(result["metrics"]["blank_text_element_count"], 0)

    def test_static_findings_are_reported(self) -> None:
        """远程资源、foreignObject、空白文字、小字号和大画布都应被报告。"""

        invalid = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20000 20000">
  <title>问题图</title>
  <desc>用于测试静态审计。</desc>
  <foreignObject width="100" height="40"/>
  <image href="https://example.com/figure.png" width="20" height="20"/>
  <text x="1" y="1" font-size="6px"></text>
  <rect style="fill:url(https://example.com/style.svg#fill)" width="10" height="10"/>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "invalid.svg", invalid)
            result = AUDIT.audit_svg(path)

        self.assertFalse(result["ok"])
        codes = {finding["code"] for finding in result["findings"]}
        self.assertTrue(
            {
                "CANVAS_TOO_LARGE",
                "CANVAS_AREA_TOO_LARGE",
                "FOREIGN_OBJECT_PRESENT",
                "REMOTE_URL_PRESENT",
                "IMAGE_REMOTE_LINK",
                "FONT_TOO_SMALL",
                "BLANK_TEXT_ELEMENT",
            }.issubset(codes)
        )
        self.assertEqual(result["metrics"]["external_image_link_count"], 1)

    def test_cjk_without_font_family_fails(self) -> None:
        """常用汉字、扩展 A 和兼容区文字缺少字体声明时必须失败。"""

        missing_font = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">
  <title>中文字体缺失</title>
  <desc>测试中文字体静态门。</desc>
  <text x="10" y="60" font-size="12px">汉\u3400\uf900</text>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "missing-font.svg", missing_font)
            result = AUDIT.audit_svg(path)

        self.assertFalse(result["ok"])
        self.assertIn(
            "CJK_FONT_FAMILY_MISSING",
            {finding["code"] for finding in result["findings"]},
        )
        self.assertEqual(result["metrics"]["cjk_character_count"], 3)
        self.assertEqual(result["metrics"]["font_family_names"], [])

    def test_latin_font_stack_fails_and_collects_all_declarations(self) -> None:
        """根属性、style 属性和 style 元素中的拉丁字体栈都应被收集并拒绝。"""

        latin_stack = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120"
    font-family="Arial, Helvetica, sans-serif">
  <title>拉丁字体栈</title>
  <desc>测试不安全的字体回退。</desc>
  <style>.label { font-family: \"Times New Roman\", Georgia, serif; }</style>
  <text class="label" style="font-family: Roboto, sans-serif" x="10" y="60">中文标签</text>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "latin-stack.svg", latin_stack)
            result = AUDIT.audit_svg(path)

        self.assertFalse(result["ok"])
        self.assertIn(
            "CJK_FONT_FALLBACK_UNSAFE",
            {finding["code"] for finding in result["findings"]},
        )
        self.assertEqual(result["metrics"]["font_family_declaration_count"], 3)
        self.assertEqual(
            set(result["metrics"]["font_family_names"]),
            {
                "Arial",
                "Helvetica",
                "sans-serif",
                "Times New Roman",
                "Georgia",
                "serif",
                "Roboto",
            },
        )

    def test_explicit_chinese_font_stack_passes(self) -> None:
        """style 元素 CSS 中声明明确中文字体候选时应通过字体静态门。"""

        safe_stack = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">
  <title>中文字体栈</title>
  <desc>测试明确中文字体候选。</desc>
  <style>text { font-family: \"Source Han Sans SC\", sans-serif; }</style>
  <text x="10" y="60" font-size="12px">中文标签</text>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "safe-stack.svg", safe_stack)
            result = AUDIT.audit_svg(path)

        self.assertTrue(result["ok"])
        self.assertTrue(result["metrics"]["has_chinese_font_candidate"])
        self.assertEqual(
            result["metrics"]["chinese_font_candidates"], ["Source Han Sans SC"]
        )

    def test_text_level_latin_override_beats_safe_root(self) -> None:
        """text 自身的拉丁字体声明不能被安全根字体栈掩盖。"""

        overridden = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120"
    font-family="Noto Sans CJK SC, sans-serif">
  <title>元素覆盖</title>
  <desc>测试 text 自身的字体覆盖。</desc>
  <text style="font-family: Arial, sans-serif" x="10" y="60">中文标签</text>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "text-override.svg", overridden)
            result = AUDIT.audit_svg(path)

        self.assertFalse(result["ok"])
        self.assertIn(
            "CJK_FONT_FALLBACK_UNSAFE",
            {finding["code"] for finding in result["findings"]},
        )
        self.assertTrue(result["metrics"]["has_chinese_font_candidate"])
        self.assertEqual(result["metrics"]["cjk_text_audits"][0]["status"], "unsafe")
        self.assertEqual(
            result["metrics"]["cjk_text_audits"][0]["font_family_source"]["source_kind"],
            "element_style",
        )

    def test_unused_safe_class_does_not_cover_unstyled_text(self) -> None:
        """未匹配的安全 class 不能为无字体声明的中文 text 提供字体来源。"""

        unused_class = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">
  <title>未使用安全类</title>
  <desc>测试 CSS 选择器必须实际匹配。</desc>
  <style>.safe { font-family: Noto Sans CJK SC, sans-serif; }</style>
  <text class="other" x="10" y="60">中文标签</text>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "unused-safe-class.svg", unused_class)
            result = AUDIT.audit_svg(path)

        self.assertFalse(result["ok"])
        self.assertIn(
            "CJK_FONT_FAMILY_MISSING",
            {finding["code"] for finding in result["findings"]},
        )
        self.assertTrue(result["metrics"]["has_chinese_font_candidate"])
        self.assertIsNone(result["metrics"]["cjk_text_audits"][0]["font_family_source"])

    def test_two_cjk_texts_are_audited_independently(self) -> None:
        """两个中文 text 一安全一不安全时必须报告不安全元素。"""

        mixed = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120">
  <title>混合字体</title>
  <desc>测试逐元素字体审计。</desc>
  <style>
    text.safe { font-family: PingFang SC, sans-serif; }
    text.bad { font-family: Arial, sans-serif; }
  </style>
  <text class="safe" x="10" y="40">安全标签</text>
  <text class="bad" x="10" y="80">不安全标签</text>
</svg>"""
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_svg(Path(temp), "mixed-texts.svg", mixed)
            result = AUDIT.audit_svg(path)

        self.assertFalse(result["ok"])
        self.assertEqual(result["metrics"]["cjk_text_audit_count"], 2)
        self.assertEqual(
            [audit["status"] for audit in result["metrics"]["cjk_text_audits"]],
            ["safe", "unsafe"],
        )
        self.assertEqual(
            [audit["font_family_source"]["selector"] for audit in result["metrics"]["cjk_text_audits"]],
            ["text.safe", "text.bad"],
        )
        self.assertEqual(
            sum(
                finding["code"] == "CJK_FONT_FALLBACK_UNSAFE"
                for finding in result["findings"]
            ),
            1,
        )

    def test_malformed_xml_and_missing_root_are_findings(self) -> None:
        """XML 解析失败和非 svg 根元素都必须稳定返回失败。"""

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            malformed = self.write_svg(directory, "malformed.svg", "<svg>")
            wrong_root = self.write_svg(directory, "wrong.svg", "<g viewBox='0 0 10 10'/>")
            malformed_result = AUDIT.audit_svg(malformed)
            wrong_result = AUDIT.audit_svg(wrong_root)

        self.assertFalse(malformed_result["ok"])
        self.assertEqual(malformed_result["findings"][0]["code"], "XML_PARSE_ERROR")
        self.assertFalse(wrong_result["ok"])
        self.assertIn(
            "ROOT_NOT_SVG",
            {finding["code"] for finding in wrong_result["findings"]},
        )

    def test_json_cli_and_multiple_paths(self) -> None:
        """--json 应只输出可解析 JSON，并支持多个输入路径。"""

        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            passed = self.write_svg(directory, "passed.svg", VALID_SVG)
            failed = self.write_svg(directory, "failed.svg", "<svg>")
            completed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--json", str(passed), str(failed)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(completed.returncode, AUDIT.EXIT_FINDINGS)
        self.assertEqual(completed.stderr, "")
        report = json.loads(completed.stdout)
        self.assertEqual(report["summary"]["file_count"], 2)
        self.assertEqual(report["summary"]["passed_count"], 1)
        self.assertEqual(report["summary"]["failed_count"], 1)
        self.assertEqual(report["exit_code"], AUDIT.EXIT_FINDINGS)

    def test_missing_file_has_stable_failure(self) -> None:
        """不存在的输入路径应形成文件读取发现，而不是抛出未处理异常。"""

        result = AUDIT.audit_svg(Path("/tmp/academic-svg-audit-missing.svg"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["findings"][0]["code"], "FILE_READ_ERROR")


if __name__ == "__main__":
    unittest.main()
