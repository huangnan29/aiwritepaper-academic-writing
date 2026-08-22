"""交付验收器的 P0 回归测试。"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
import zipfile
import io
from contextlib import redirect_stdout
from pathlib import Path

from scripts.validate_delivery import FAIL, PASS, _path_exists, main, validate


SOURCE_FILES = (
    "00-capability-report.md",
    "01-research-contract.md",
    "02-search-log.md",
    "03-evidence-matrix.csv",
    "04-reference-audit.md",
    "references.bib",
    "05-outline.md",
    "06-argument-map.md",
    "07-paper-full.md",
    "08-claim-citation-audit.md",
    "09-peer-review.md",
    "10-revision-log.md",
    "11-format-validation.md",
    "tables/table-data-and-sources.md",
)


def _write_valid_docx(path: Path) -> None:
    """写入最小但结构有效的 DOCX ZIP。"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            '<document xmlns="urn:test"><body><p>正文内容</p></body></document>',
        )
        archive.writestr("word/media/figure.png", b"PNG")


def _write_valid_pdf(path: Path) -> None:
    """写入满足基础签名、页面对象和 EOF 约束的最小 PDF。"""

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] /Contents 4 0 R >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    path.write_bytes(output)
def _write_source(root: Path, *, body: str | None = None) -> int:
    """生成测试所需的论文源文件和一张图。"""

    for filename in SOURCE_FILES:
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("源文件\n", encoding="utf-8")
    chapter = root / "chapters/01-第一章.md"
    chapter.parent.mkdir(parents=True, exist_ok=True)
    chapter_text = (
        "# 测试论文题目\n\n## 摘要\n" + "这是摘要。" * 10
        + "\n\n# 第一章\n" + "这是分章正文。" * 40
        + "\n\n# 参考文献\n[1] 测试文献。\n\n# 致谢\n感谢测试支持。\n"
    )
    chapter.write_text(chapter_text, encoding="utf-8")
    full = body or chapter_text
    (root / "07-paper-full.md").write_text(full, encoding="utf-8")
    figures = root / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    (figures / "fig-1.svg").write_text("<svg/>", encoding="utf-8")
    (figures / "fig-1.png").write_bytes(b"PNG")
    (figures / "figure-manifest.json").write_text(
        json.dumps({"figures": [{"svg_file": "fig-1.svg", "png_file": "fig-1.png"}]}),
        encoding="utf-8",
    )
    return len("".join(chapter_text.split()).replace("#", ""))


def _write_full_artifacts(root: Path, *, declared_body: int | None = None) -> None:
    """补齐最小通过样例的最终文档、manifest 和 QA。"""

    body = (root / "07-paper-full.md").read_text(encoding="utf-8")
    actual_cjk = sum(1 for char in body if "\u4e00" <= char <= "\u9fff")
    _write_valid_docx(root / "final-paper.docx")
    _write_valid_pdf(root / "final-paper.pdf")
    (root / "evidence-manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "id": "PLAN-01",
                        "claim": "本测试夹具只验证交付结构",
                        "evidence_level": "PLANNED",
                        "sources": ["测试夹具"],
                        "command": "",
                        "outputs": [],
                        "sha256": "N/A",
                        "limitations": ["不代表真实研究结果"],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    artifacts = list(SOURCE_FILES) + [
        "chapters/01-第一章.md",
        "figures/figure-manifest.json",
        "figures/fig-1.svg",
        "figures/fig-1.png",
        "final-paper.docx",
        "final-paper.pdf",
        "run-manifest.json",
        "12-final-qa-report.md",
    ]
    manifest = {
        "status": "PASS",
        "run_mode": "FULL_BUILD",
        "body_cjk_chars": declared_body if declared_body is not None else actual_cjk,
        "figures_count": 1,
        "artifacts": artifacts,
    }
    (root / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    (root / "12-final-qa-report.md").write_text(
        "# 最终 QA 报告\n\n最终状态：PASS\n正文 CJK 字符数：%d\n图数量：1\nCritical问题：0；Important问题：0\n"
        % (declared_body if declared_body is not None else actual_cjk),
        encoding="utf-8",
    )
    # 明确构造“QA 晚于产物”的时间顺序，不依赖文件系统的写入速度。
    base = 1_800_000_000
    for path in root.rglob("*"):
        if path.is_file() and path.name != "12-final-qa-report.md":
            os.utime(path, (base, base))
    os.utime(root / "12-final-qa-report.md", (base + 100, base + 100))


class ValidateDeliveryTests(unittest.TestCase):
    """覆盖假 PASS、最小通过和两个子模式。"""

    def test_gemini_like_false_pass_is_fail(self) -> None:
        """声明 PASS 但缺最终文档且整合稿只有分章链接时必须 FAIL。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(
                root,
                body=(
                    "# 第一章\n\n正文完整内容已完成，详见分章文件。\n"
                    "[第一章](file:///tmp/chapters/01-第一章.md)\n"
                ),
            )
            (root / "run-manifest.json").write_text(
                json.dumps(
                    {
                        "overall_status": "PASS",
                        "word_count_total": 30000,
                        "figures_count": 1,
                        "artifacts": [
                            "07-paper-full.md",
                            "chapters/01-第一章.md",
                            "figures/figure-manifest.json",
                            "figures/fig-1.svg",
                            "figures/fig-1.png",
                            "run-manifest.json",
                            "12-final-qa-report.md",
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (root / "12-final-qa-report.md").write_text(
                "# QA\n最终状态：PASS\n正文字符数：30000\n图数量：1\nCritical问题：0；Important问题：0\n",
                encoding="utf-8",
            )
            report = validate(root, "full")
            self.assertEqual(report.status, FAIL)
            codes = {issue.code for issue in report.issues}
            self.assertIn("docx-missing", codes)
            self.assertIn("pdf-missing", codes)
            self.assertIn("paper-pointer-only", codes)
            self.assertIn("paper-local-paths", codes)
            self.assertIn("declared-status-conflict", codes)

    def test_manifest不得用父目录路径证明交付(self) -> None:
        """项目外文件即使存在，也不能满足 manifest 声明。"""

        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "paper"
            root.mkdir()
            (parent / "outside.pdf").write_bytes(b"external")

            self.assertFalse(_path_exists(root, "../outside.pdf"))

    def test_minimal_full_delivery_passes(self) -> None:
        """最小真实文件集合在结构和时间顺序正确时通过。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(root)
            _write_full_artifacts(root)
            report = validate(root, "full")
            self.assertEqual(report.status, PASS)
            self.assertEqual(report.exit_code, 0)
            self.assertEqual(report.metrics["svg_count"], 1)
            self.assertEqual(report.metrics["png_count"], 1)
            self.assertEqual(report.metrics["pdf_pages"], 1)

    def test_source_mode_does_not_require_final_documents(self) -> None:
        """source 模式只验收论文源文件，不把缺最终文档误报为失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(root)
            report = validate(root, "source")
            self.assertEqual(report.status, PASS)
            self.assertNotIn("docx-missing", {issue.code for issue in report.issues})

    def test_skill模式别名可执行(self) -> None:
        """AUDIT_ONLY 应映射为完整只读验收。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(root)
            _write_full_artifacts(root)
            report = validate(root, "AUDIT_ONLY")

        self.assertEqual(report.status, PASS)
        self.assertEqual(report.mode, "full")

    def test_preqa阶段不要求qa文件(self) -> None:
        """预验收先计算状态，之后才由代理写 QA 和最终状态。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(root)
            _write_full_artifacts(root)
            (root / "12-final-qa-report.md").unlink()
            manifest_path = root / "run-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["status"] = "PENDING"
            manifest["artifacts"] = [
                item for item in manifest["artifacts"] if item != "12-final-qa-report.md"
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            report = validate(root, "FULL_BUILD", "preqa")

        self.assertEqual(report.status, PASS)
        self.assertEqual(report.phase, "preqa")

    def test_figures_mode_checks_svg_and_png_counts(self) -> None:
        """figures 模式可独立验收图表清单和 SVG/PNG 数量。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(b"PNG")
            (figures / "figure-manifest.json").write_text(
                json.dumps({"figures": [{"svg_file": "one.svg", "png_file": "one.png"}]}),
                encoding="utf-8",
            )
            report = validate(root, "figures")
            self.assertEqual(report.status, PASS)
            self.assertEqual(report.metrics["svg_count"], 1)
            self.assertEqual(report.metrics["png_count"], 1)

    def test_图表清单不能只对数量而文件名错误(self) -> None:
        """数量相等但清单指向不存在文件时必须失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "actual.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "actual.png").write_bytes(b"PNG")
            (figures / "figure-manifest.json").write_text(
                json.dumps(
                    {"figures": [{"svg_file": "wrong.svg", "png_file": "wrong.png"}]}
                ),
                encoding="utf-8",
            )
            report = validate(root, "FIGURES_ONLY")

        self.assertEqual(report.status, FAIL)
        self.assertIn("figure-manifest-files-missing", {issue.code for issue in report.issues})

    def test_json_cli_and_output_file(self) -> None:
        """CLI 的 JSON 与 --output 应输出可解析的同一报告。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(root)
            output = root / "report.json"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    ["--root", str(root), "--mode", "source", "--json", "--output", str(output)]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], PASS)
            self.assertEqual(payload["mode"], "source")
            self.assertEqual(json.loads(stdout.getvalue()), payload)


if __name__ == "__main__":
    unittest.main()
