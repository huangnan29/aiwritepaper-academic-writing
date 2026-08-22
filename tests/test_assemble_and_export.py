"""assemble_and_export 的 P0 单元测试。"""

from __future__ import annotations

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import assemble_and_export as assembler  # noqa: E402


class AssembleAndExportTests(unittest.TestCase):
    """覆盖确定性合并、占位拒绝和能力缺口降级。"""

    def _project(self) -> tempfile.TemporaryDirectory[str]:
        project = tempfile.TemporaryDirectory()
        (Path(project.name) / "chapters").mkdir()
        return project

    def test_按文件名排序合并章节(self) -> None:
        """章节顺序由文件名决定，而不是创建顺序。"""

        with self._project() as project:
            root = Path(project)
            (root / "chapters" / "10.md").write_text("第十章", encoding="utf-8")
            (root / "chapters" / "02.md").write_text("第二章", encoding="utf-8")
            (root / "chapters" / "01.md").write_text("第一章", encoding="utf-8")

            output, chapters = assembler.assemble_markdown(root)

            self.assertEqual([path.name for path in chapters], ["01.md", "02.md", "10.md"])
            self.assertEqual(output.read_text(encoding="utf-8"), "第一章\n\n第二章\n\n第十章\n")

    def test_自然排序避免chapter10提前(self) -> None:
        """未补零的章节编号仍应按数值顺序合并。"""

        with self._project() as project:
            root = Path(project)
            (root / "chapters" / "chapter10.md").write_text("第十章", encoding="utf-8")
            (root / "chapters" / "chapter2.md").write_text("第二章", encoding="utf-8")
            output, chapters = assembler.assemble_markdown(root)

            self.assertEqual([path.name for path in chapters], ["chapter2.md", "chapter10.md"])
            self.assertEqual(output.read_text(encoding="utf-8"), "第二章\n\n第十章\n")

    def test_拒绝输出到项目外(self) -> None:
        """模型传入错误绝对路径时不能覆盖项目外文件。"""

        with self._project() as project, tempfile.TemporaryDirectory() as outside:
            root = Path(project)
            (root / "chapters" / "01.md").write_text("正文", encoding="utf-8")
            with self.assertRaises(assembler.AssemblyError):
                assembler.assemble_markdown(root, output_md=Path(outside) / "paper.md")

    def test_忽略指向项目外的章节软链接(self) -> None:
        """chapters 下的软链接不能把项目外文件混入论文。"""

        with self._project() as project, tempfile.TemporaryDirectory() as outside:
            root = Path(project)
            outside_chapter = Path(outside) / "outside.md"
            outside_chapter.write_text("外部内容", encoding="utf-8")
            try:
                os.symlink(outside_chapter, root / "chapters/01.md")
            except OSError as error:
                self.skipTest(f"当前环境不支持软链接：{error}")
            with self.assertRaises(assembler.AssemblyError):
                assembler.assemble_markdown(root)

    def test_拒绝详见分章占位(self) -> None:
        """占位内容不能悄悄进入完整论文。"""

        with self._project() as project:
            root = Path(project)
            (root / "chapters" / "01.md").write_text("本章正文\n详见分章", encoding="utf-8")

            with self.assertRaises(assembler.AssemblyError):
                assembler.assemble_markdown(root)
            self.assertFalse((root / "07-paper-full.md").exists())

    def test_缺少导出工具明确降级(self) -> None:
        """Markdown 可用但导出工具缺失时必须是 PARTIAL/CAPABILITY_GAP。"""

        with self._project() as project:
            root = Path(project)
            (root / "chapters" / "01.md").write_text("正文", encoding="utf-8")
            with patch.object(
                assembler,
                "probe_tools",
                return_value={"pandoc": None, "xelatex": None, "lualatex": None, "libreoffice": None},
            ):
                report = assembler.assemble_and_export(root)

            self.assertEqual(report["status"], assembler.STATUS_PARTIAL)
            self.assertEqual(report["outputs"]["docx"]["status"], assembler.CAPABILITY_GAP)
            self.assertEqual(report["outputs"]["pdf"]["status"], assembler.CAPABILITY_GAP)
            self.assertTrue(Path(report["output_md"]).is_file())
            self.assertEqual(assembler._exit_code(report), assembler.EXIT_PARTIAL)

    def test_full模式跳过导出不能pass(self) -> None:
        """FULL_BUILD 不能用 skip 参数绕过 DOCX/PDF 交付。"""

        with self._project() as project:
            root = Path(project)
            (root / "chapters" / "01.md").write_text("正文", encoding="utf-8")
            report = assembler.assemble_and_export(
                root,
                skip_docx=True,
                skip_pdf=True,
                mode="full",
            )

        self.assertEqual(report["status"], assembler.STATUS_PARTIAL)
        self.assertTrue(any("不允许把跳过" in item for item in report["capability_gaps"]))

    def test_source模式允许只整合markdown(self) -> None:
        """source 模式可明确选择只构建 Markdown。"""

        with self._project() as project:
            root = Path(project)
            (root / "chapters" / "01.md").write_text("正文", encoding="utf-8")
            report = assembler.assemble_and_export(
                root,
                skip_docx=True,
                skip_pdf=True,
                mode="source",
            )

        self.assertEqual(report["status"], assembler.STATUS_PASS)

    def test_export模式可直接使用现有定稿(self) -> None:
        """EXPORT_ONLY 不应强制要求 chapters/ 仍存在。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "07-paper-full.md").write_text("# 定稿\n\n完整正文", encoding="utf-8")
            report = assembler.assemble_and_export(
                root,
                skip_docx=True,
                skip_pdf=True,
                mode="export",
            )

        self.assertEqual(report["outputs"]["markdown"]["status"], assembler.STATUS_PASS)
        self.assertEqual(report["status"], assembler.STATUS_PARTIAL)

    def test_libreoffice不得复用旧pdf(self) -> None:
        """命令返回0但没有新产物时不能把旧 PDF 报成成功。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docx = root / "paper.docx"
            output = root / "renamed.pdf"
            docx.write_bytes(b"docx")
            (root / "paper.pdf").write_bytes(b"old-pdf")
            with patch.object(assembler, "_run_command", return_value=(0, "", "")):
                result = assembler._libreoffice_pdf(root, docx, output, "/usr/bin/true")

        self.assertEqual(result["status"], assembler.STATUS_FAIL)
        self.assertIn("未生成本次运行的新 PDF", result["message"])

    def test_pandoc_pdf失败后回退_libreoffice(self) -> None:
        """LaTeX 路径失败时应继续尝试从本次 DOCX 转换 PDF。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            markdown = root / "07-paper-full.md"
            docx = root / "final-paper.docx"
            pdf = root / "final-paper.pdf"
            markdown.write_text("正文", encoding="utf-8")
            docx.write_bytes(b"docx")
            tools = {
                "pandoc": "/fake/pandoc",
                "xelatex": "/fake/xelatex",
                "lualatex": None,
                "libreoffice": "/fake/soffice",
            }
            with patch.object(
                assembler,
                "_run_command",
                return_value=(1, "", "LaTeX 公式失败"),
            ), patch.object(
                assembler,
                "_libreoffice_pdf",
                return_value={"status": assembler.STATUS_PASS, "path": str(pdf)},
            ):
                result = assembler.export_pdf(root, markdown, pdf, docx, tools)

        self.assertEqual(result["status"], assembler.STATUS_PASS)
        self.assertIn("LibreOffice", result["message"])


if __name__ == "__main__":
    unittest.main()
