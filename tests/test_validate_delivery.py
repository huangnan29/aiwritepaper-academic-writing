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


MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000000020001e221bc330000000049454e44ae426082"
)


def _opt_out_image_generation_policy() -> dict[str, object]:
    """返回明确声明用户退出 image-gen 的测试策略。"""

    return {
        "client_tool_exposed": True,
        "required": False,
        "eligible_figure_ids": [],
        "attempted": False,
        "tool_or_model": None,
        "generated_artifacts": [],
        "generated_by_figure": {},
        "not_used_reason": "测试用户明确退出 image-gen，仅验证确定性图表交付。",
        "explicit_user_opt_out": True,
        "venue_prohibits_ai_images": False,
    }


def _required_image_generation_policy(
    eligible: list[str],
    artifacts: list[str],
    generated_by_figure: dict[str, str],
) -> dict[str, object]:
    """返回需要逐图覆盖的 image-gen 测试策略。"""

    return {
        "client_tool_exposed": True,
        "required": True,
        "eligible_figure_ids": eligible,
        "attempted": True,
        "tool_or_model": "Codex built-in imagegen/image_gen",
        "generated_artifacts": artifacts,
        "generated_by_figure": generated_by_figure,
        "prompt_by_figure": {
            figure_id: f"figures/{figure_id}.md" for figure_id in eligible
        },
        "not_used_reason": None,
        "explicit_user_opt_out": False,
        "venue_prohibits_ai_images": False,
    }


def _write_figure_manifest(
    root: Path,
    figures: list[dict[str, object]],
    policy: dict[str, object] | None = None,
) -> None:
    """写入图表清单测试夹具。"""

    payload: dict[str, object] = {"figures": figures}
    if policy is not None:
        payload["image_generation_policy"] = policy
    (root / "figures/figure-manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
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
    (figures / "fig-1.png").write_bytes(MINIMAL_PNG)
    (figures / "figure-manifest.json").write_text(
        json.dumps(
            {
                "figures": [{"svg_file": "fig-1.svg", "png_file": "fig-1.png"}],
                "image_generation_policy": _opt_out_image_generation_policy(),
            }
        ),
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

    def test_source_mode_does_not_require_image_generation_policy(self) -> None:
        """source 模式不因缺少 image_generation_policy 而失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_source(root)
            figure_manifest_path = root / "figures/figure-manifest.json"
            figure_manifest = json.loads(figure_manifest_path.read_text(encoding="utf-8"))
            figure_manifest.pop("image_generation_policy", None)
            figure_manifest_path.write_text(
                json.dumps(figure_manifest, ensure_ascii=False), encoding="utf-8"
            )
            report = validate(root, "source")

        self.assertEqual(report.status, PASS)
        self.assertNotIn("image-generation-policy-missing", {issue.code for issue in report.issues})

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

    def test_figures_mode_checks_raster_and_optional_svg_counts(self) -> None:
        """figures 模式以最终 raster 数量验收，SVG 仅作为可选源文件。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            (figures / "figure-manifest.json").write_text(
                json.dumps(
                    {
                        "figures": [{"svg_file": "one.svg", "png_file": "one.png"}],
                        "image_generation_policy": _opt_out_image_generation_policy(),
                    }
                ),
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
            (figures / "actual.png").write_bytes(MINIMAL_PNG)
            (figures / "figure-manifest.json").write_text(
                json.dumps(
                    {"figures": [{"svg_file": "wrong.svg", "png_file": "wrong.png"}]}
                ),
                encoding="utf-8",
            )
            report = validate(root, "FIGURES_ONLY")

        self.assertEqual(report.status, FAIL)
        self.assertIn("figure-manifest-files-missing", {issue.code for issue in report.issues})

    def test_image_generation_policy_missing_fails(self) -> None:
        """FULL_BUILD/FIGURES_ONLY 缺少图片生成策略时必须失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg", "png_file": "one.png"}],
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, FAIL)
        self.assertIn("image-generation-policy-missing", {issue.code for issue in report.issues})
        self.assertTrue(report.metrics["image_generation_policy_present"] is False)
        self.assertTrue(any(check.name == "image_generation_policy" for check in report.checks))

    def test_all_svg_without_image_generation_fails(self) -> None:
        """有图片工具且 eligible 图未生成位图时必须失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            policy = _required_image_generation_policy(["fig-1"], [], {})
            policy["attempted"] = False
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg"}],
                policy,
            )
            report = validate(root, "FIGURES_ONLY")

        self.assertEqual(report.status, FAIL)
        codes = {issue.code for issue in report.issues}
        self.assertIn("image-generation-not-attempted", codes)
        self.assertIn("image-generation-artifacts-missing", codes)

    def test_real_png_image_generation_passes(self) -> None:
        """真实非空 PNG 可覆盖 eligible 图并通过 image-gen 门禁。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            (figures / "fig-1.md").write_text("生成 fig-1 的详细提示词。", encoding="utf-8")
            policy = _required_image_generation_policy(
                ["fig-1"],
                ["figures/one.png"],
                {"fig-1": "figures/one.png"},
            )
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, PASS)
        self.assertEqual(report.metrics["image_generation_covered_count"], 1)
        self.assertEqual(report.metrics["image_generation_valid_artifact_count"], 1)

    def test_raster_only_delivery_without_svg_passes(self) -> None:
        """没有 SVG 修正源时，真实最终 PNG 仍可作为主交付通过。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            (figures / "fig-1.md").write_text("生成 fig-1 的详细提示词。", encoding="utf-8")
            policy = _required_image_generation_policy(
                ["fig-1"],
                ["figures/one.png"],
                {"fig-1": "figures/one.png"},
            )
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, PASS)
        self.assertEqual(report.metrics["svg_count"], 0)
        self.assertEqual(report.metrics["raster_count"], 1)

    def test_pseudo_png_signature_fails(self) -> None:
        """仅有 PNG 扩展名或少量字节不能冒充真实 PNG。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.png").write_bytes(b"PNG")
            (figures / "fig-1.md").write_text("生成 fig-1 的详细提示词。", encoding="utf-8")
            policy = _required_image_generation_policy(
                ["fig-1"],
                ["figures/one.png"],
                {"fig-1": "figures/one.png"},
            )
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, FAIL)
        self.assertIn(
            "image-generation-artifact-signature-invalid",
            {issue.code for issue in report.issues},
        )

    def test_eligible_figure_without_prompt_fails(self) -> None:
        """eligible 图缺少逐图 prompt_file 映射时必须失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            policy = _required_image_generation_policy(
                ["fig-1"],
                ["figures/one.png"],
                {"fig-1": "figures/one.png"},
            )
            policy["prompt_by_figure"] = {}
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, FAIL)
        self.assertIn("image-generation-prompt-missing", {issue.code for issue in report.issues})

    def test_svg_artifact_is_rejected(self) -> None:
        """SVG 不能作为 image-gen 位图产物，即使路径存在也必须失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            policy = _required_image_generation_policy(
                ["fig-1"],
                ["figures/one.svg"],
                {"fig-1": "figures/one.svg"},
            )
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, FAIL)
        self.assertIn("image-generation-artifact-format-invalid", {issue.code for issue in report.issues})

    def test_image_generation_artifact_path_traversal_fails(self) -> None:
        """image-gen 产物越出 figures/ 时必须失败。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            (root / "outside.png").write_bytes(MINIMAL_PNG)
            policy = _required_image_generation_policy(
                ["fig-1"],
                ["../outside.png"],
                {"fig-1": "../outside.png"},
            )
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, FAIL)
        self.assertIn("image-generation-artifact-outside", {issue.code for issue in report.issues})

    def test_explicit_image_generation_opt_out_passes(self) -> None:
        """用户明确退出 image-gen 时，确定性 SVG/PNG 交付可以通过。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg", "png_file": "one.png"}],
                _opt_out_image_generation_policy(),
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, PASS)

    def test_each_eligible_figure_requires_its_own_image_artifact(self) -> None:
        """多个 eligible 图号不能由一个 image-gen 产物冒充全部覆盖。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            for figure_id in ("fig-1", "fig-2"):
                (figures / f"{figure_id}.svg").write_text("<svg/>", encoding="utf-8")
                (figures / f"{figure_id}.png").write_bytes(MINIMAL_PNG)
            policy = _required_image_generation_policy(
                ["fig-1", "fig-2"],
                ["figures/fig-1.png"],
                {"fig-1": "figures/fig-1.png"},
            )
            _write_figure_manifest(
                root,
                [
                    {"figure_id": "fig-1", "svg_file": "fig-1.svg", "png_file": "fig-1.png"},
                    {"figure_id": "fig-2", "svg_file": "fig-2.svg", "png_file": "fig-2.png"},
                ],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, FAIL)
        self.assertIn("image-generation-eligible-uncovered", {issue.code for issue in report.issues})
        self.assertEqual(report.metrics["image_generation_missing_figure_ids"], ["fig-2"])

    def test_each_eligible_figure_with_prompt_and_raster_passes(self) -> None:
        """多个 eligible 图号各自有独立位图和 prompt 时通过。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            for figure_id in ("fig-1", "fig-2"):
                (figures / f"{figure_id}.png").write_bytes(MINIMAL_PNG)
                (figures / f"{figure_id}.md").write_text(
                    f"生成 {figure_id} 的详细提示词。", encoding="utf-8"
                )
            policy = _required_image_generation_policy(
                ["fig-1", "fig-2"],
                ["figures/fig-1.png", "figures/fig-2.png"],
                {
                    "fig-1": "figures/fig-1.png",
                    "fig-2": "figures/fig-2.png",
                },
            )
            _write_figure_manifest(
                root,
                [
                    {"figure_id": "fig-1", "png_file": "fig-1.png"},
                    {"figure_id": "fig-2", "png_file": "fig-2.png"},
                ],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, PASS)
        self.assertEqual(report.metrics["image_generation_covered_count"], 2)
        self.assertEqual(report.metrics["image_generation_valid_prompt_count"], 2)

    def test_deterministic_only_reason_allows_empty_eligible_set(self) -> None:
        """只有数据、原始科研或领域图时可用明确理由放弃 image-gen。"""

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            figures = root / "figures"
            figures.mkdir()
            (figures / "one.svg").write_text("<svg/>", encoding="utf-8")
            (figures / "one.png").write_bytes(MINIMAL_PNG)
            policy = {
                "client_tool_exposed": True,
                "required": False,
                "eligible_figure_ids": [],
                "attempted": False,
                "tool_or_model": None,
                "generated_artifacts": [],
                "generated_by_figure": {},
                "deterministic_only_reason": "本项目只有统计数据图、原始科研图像和公式等领域图。",
                "not_used_reason": "全部图形均需保持确定性或原始来源。",
                "explicit_user_opt_out": False,
                "venue_prohibits_ai_images": False,
            }
            _write_figure_manifest(
                root,
                [{"figure_id": "fig-1", "svg_file": "one.svg", "png_file": "one.png"}],
                policy,
            )
            report = validate(root, "figures")

        self.assertEqual(report.status, PASS)

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
