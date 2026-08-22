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


VALID_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120" width="240" height="120">
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
