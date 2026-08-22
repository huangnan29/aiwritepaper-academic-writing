#!/usr/bin/env python3
"""确定性整合论文分章，并在能力可用时导出 DOCX/PDF。

本脚本只依赖 Python 标准库。Markdown 是必需产物；DOCX/PDF 属于可选导出，
导出工具不存在或导出失败时必须如实报告，不能把计划文件当成已生成文件。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


# 稳定退出码：成功、实际失败、能力缺口（部分完成）。
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_PARTIAL = 2

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_PARTIAL = "PARTIAL"
CAPABILITY_GAP = "CAPABILITY_GAP"

# 这是终稿不允许出现的过程性占位。尤其不能用“详见分章”代替正文。
PLACEHOLDER_MARKERS = (
    "详见分章",
    "待补充",
    "待填写",
    "TODO",
    "FIXME",
    "TBD",
    "PLACEHOLDER",
)


class AssemblyError(RuntimeError):
    """表示章节读取或 Markdown 整合前提不满足。"""


def resolve_root(root_argument: str | os.PathLike[str] | None) -> Path:
    """解析项目根目录；不传参数时使用本脚本所在 Skill 根目录。"""

    if root_argument is None:
        return Path(__file__).resolve().parents[1]
    return Path(root_argument).expanduser().resolve()


def resolve_path(root: Path, path_argument: str | os.PathLike[str]) -> Path:
    """将输出路径解析到项目根目录内，拒绝越界覆盖其他文件。"""

    path = Path(path_argument).expanduser()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise AssemblyError(f"输出路径越出项目根目录，已拒绝：{resolved}") from error
    return resolved


def _normalise_glob(root: Path, chapters_glob: str | os.PathLike[str]) -> str:
    """把相对 glob 放到项目根目录下，保留绝对 glob 的含义。"""

    pattern = Path(chapters_glob).expanduser()
    if pattern.is_absolute() or ".." in pattern.parts:
        raise AssemblyError("章节 glob 必须是项目根目录内的相对路径，不能使用绝对路径或 ..")
    return str(root / pattern)


def _natural_name_key(path: Path) -> tuple[object, ...]:
    """对文件名中的数字执行自然排序，避免 chapter10 排在 chapter2 前。"""

    parts = re.split(r"(\d+)", path.name.casefold())
    return tuple(int(part) if part.isdigit() else part for part in parts) + (path.as_posix().casefold(),)


def find_chapter_files(
    root: Path,
    chapters_glob: str | os.PathLike[str] = "chapters/*.md",
    output_md: Path | None = None,
) -> list[Path]:
    """按文件名确定性查找章节，并排除输出文件本身。"""

    pattern = _normalise_glob(root, chapters_glob)
    candidates = [Path(item).resolve() for item in glob.glob(pattern, recursive=True)]
    output_resolved = output_md.resolve() if output_md is not None else None
    paths: list[Path] = []
    for path in candidates:
        try:
            path.relative_to(root.resolve())
        except ValueError:
            continue
        if (
            path.is_file()
            and path.suffix.casefold() == ".md"
            and not path.name.startswith(".")
            and (output_resolved is None or path != output_resolved)
        ):
            paths.append(path)
    # 文件名是首要排序键；同名文件再用完整路径稳定打破平局。
    return sorted(set(paths), key=_natural_name_key)


def _placeholder_markers(text: str) -> list[str]:
    """返回文本中出现的占位标记，比较时对英文标记不区分大小写。"""

    upper_text = text.upper()
    return [
        marker
        for marker in PLACEHOLDER_MARKERS
        if (marker.upper() in upper_text if marker.isascii() else marker in text)
    ]


def _read_chapter(path: Path) -> str:
    """读取单个章节，并拒绝编码错误或终稿占位。"""

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise AssemblyError(f"章节不是有效的 UTF-8 文本：{path}") from error
    except OSError as error:
        raise AssemblyError(f"无法读取章节 {path}：{error}") from error

    markers = _placeholder_markers(content)
    if markers:
        raise AssemblyError(
            f"章节 {path.name} 含有不允许进入终稿的占位内容：{', '.join(markers)}"
        )
    return content


def assemble_markdown(
    root: Path,
    chapters_glob: str | os.PathLike[str] = "chapters/*.md",
    output_md: str | os.PathLike[str] = "07-paper-full.md",
) -> tuple[Path, list[Path]]:
    """按文件名合并章节，写出非空的完整 Markdown。

    返回输出路径和实际采用的章节顺序，便于 CLI JSON 和上层调用审计。
    """

    root = root.resolve()
    output_path = resolve_path(root, output_md)
    chapter_paths = find_chapter_files(root, chapters_glob, output_path)
    if not chapter_paths:
        raise AssemblyError(f"没有找到章节文件：{chapters_glob}")

    sections: list[str] = []
    for path in chapter_paths:
        # 去掉各章末尾多余换行后再统一连接，确保重复运行结果一致。
        sections.append(_read_chapter(path).rstrip())

    assembled = "\n\n".join(sections).rstrip() + "\n"
    if not assembled.strip():
        raise AssemblyError("合并结果为空，拒绝生成完整 Markdown")
    if "详见分章" in assembled:
        # 防御性二次检查，避免未来修改读取规则时漏掉硬性占位约束。
        raise AssemblyError("合并结果仍含“详见分章”占位内容")

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(output_path.parent),
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(assembled)
            temporary_path = Path(handle.name)
        temporary_path.replace(output_path)
    except OSError as error:
        try:
            temporary_path.unlink(missing_ok=True)
        except (NameError, OSError):
            pass
        raise AssemblyError(f"无法写入完整 Markdown {output_path}：{error}") from error

    verify_nonempty(output_path, "完整 Markdown")
    return output_path, chapter_paths


def assemble_chapters(
    root: Path,
    chapters_glob: str | os.PathLike[str] = "chapters/*.md",
    output_md: str | os.PathLike[str] = "07-paper-full.md",
) -> tuple[Path, list[Path]]:
    """兼容性别名：按顺序整合章节。"""

    return assemble_markdown(root, chapters_glob, output_md)


def verify_nonempty(path: Path, label: str) -> None:
    """确认产物为普通文件且大小大于零。"""

    try:
        valid = path.is_file() and path.stat().st_size > 0
    except OSError as error:
        raise AssemblyError(f"无法验证{label} {path}：{error}") from error
    if not valid:
        raise AssemblyError(f"{label}不存在或为空：{path}")


def probe_tools() -> dict[str, str | None]:
    """一次性探测导出工具，返回工具名到可执行路径的映射。"""

    return {
        "pandoc": shutil.which("pandoc"),
        "xelatex": shutil.which("xelatex"),
        "lualatex": shutil.which("lualatex"),
        "libreoffice": shutil.which("libreoffice") or shutil.which("soffice"),
    }


def _run_command(
    command: list[str],
    root: Path,
    timeout: float = 120.0,
) -> tuple[int, str, str]:
    """运行导出命令并捕获输出，避免污染 JSON 标准输出。"""

    process: subprocess.Popen[str] | None = None
    try:
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=os.name != "nt",
            creationflags=(
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
                if os.name == "nt"
                else 0
            ),
        )
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if process is not None:
            try:
                if os.name == "nt":
                    process.kill()
                else:
                    os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                process.communicate(timeout=2)
            except (OSError, subprocess.SubprocessError):
                pass
        return 124, "", f"命令超过 {timeout:g} 秒，已停止等待"
    except OSError as error:
        return 127, "", str(error)
    return process.returncode, stdout or "", stderr or ""


def _safe_error_detail(stdout: str, stderr: str, returncode: int) -> str:
    """截断并脱敏外部工具错误，避免把 URL、令牌或大段正文写入报告。"""

    detail = (stderr.strip() or stdout.strip() or f"退出码 {returncode}")[:1200]
    detail = re.sub(r"https?://\S+", "[REDACTED_URL]", detail)
    detail = re.sub(
        r"(?i)\b(?:sk|rk|key|token|secret|password)[-_:=][A-Za-z0-9._-]+\b",
        "[REDACTED_SECRET]",
        detail,
    )
    return detail


def _result(status: str, path: Path | None = None, message: str = "") -> dict[str, Any]:
    """创建结构稳定的导出结果。"""

    item: dict[str, Any] = {"status": status}
    if path is not None:
        item["path"] = str(path)
    if message:
        item["message"] = message
    return item


def export_docx(
    root: Path,
    input_md: Path,
    output_docx: Path,
    tools: dict[str, str | None],
) -> dict[str, Any]:
    """优先调用 Pandoc 生成 DOCX，并验证真实产物。"""

    pandoc = tools.get("pandoc")
    if not pandoc:
        return _result(
            CAPABILITY_GAP,
            output_docx,
            "缺少 pandoc，无法生成 DOCX（CAPABILITY_GAP）",
        )

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_docx.unlink(missing_ok=True)
    except OSError as error:
        return _result(STATUS_FAIL, output_docx, f"无法清理旧 DOCX：{error}")
    command = [pandoc, str(input_md), "--from=markdown", "--to=docx", "-o", str(output_docx)]
    returncode, stdout, stderr = _run_command(command, root)
    if returncode != 0:
        detail = _safe_error_detail(stdout, stderr, returncode)
        return _result(STATUS_FAIL, output_docx, f"Pandoc 生成 DOCX 失败：{detail}")
    try:
        verify_nonempty(output_docx, "DOCX")
    except AssemblyError as error:
        return _result(STATUS_FAIL, output_docx, str(error))
    return _result(STATUS_PASS, output_docx, "DOCX 已由 pandoc 生成并通过非空验证")


def _libreoffice_pdf(
    root: Path,
    input_docx: Path,
    output_pdf: Path,
    office: str,
) -> dict[str, Any]:
    """使用 LibreOffice 将 DOCX 转成目标 PDF。"""

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    generated = output_pdf.parent / f"{input_docx.stem}.pdf"
    try:
        output_pdf.unlink(missing_ok=True)
        if generated != output_pdf:
            generated.unlink(missing_ok=True)
    except OSError as error:
        return _result(STATUS_FAIL, output_pdf, f"无法清理旧 PDF：{error}")
    try:
        profile_context = tempfile.TemporaryDirectory(
            prefix=".libreoffice-profile-",
            dir=str(output_pdf.parent),
        )
    except OSError as error:
        return _result(STATUS_FAIL, output_pdf, f"无法创建 LibreOffice 隔离配置：{error}")
    with profile_context as profile_directory:
        command = [
            office,
            "--headless",
            f"-env:UserInstallation={Path(profile_directory).as_uri()}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_pdf.parent),
            str(input_docx),
        ]
        started_ns = time.time_ns()
        returncode, stdout, stderr = _run_command(command, root)
    if returncode != 0:
        detail = _safe_error_detail(stdout, stderr, returncode)
        return _result(STATUS_FAIL, output_pdf, f"LibreOffice 转换 PDF 失败：{detail}")

    try:
        if not generated.is_file() or generated.stat().st_mtime_ns < started_ns:
            return _result(STATUS_FAIL, output_pdf, "LibreOffice 未生成本次运行的新 PDF")
        if generated != output_pdf and generated.is_file() and generated.stat().st_size > 0:
            # LibreOffice 以 DOCX 文件名生成 PDF；用户要求其他文件名时再移动。
            if output_pdf.exists():
                output_pdf.unlink()
            generated.replace(output_pdf)
        verify_nonempty(output_pdf, "PDF")
    except (AssemblyError, OSError) as error:
        return _result(STATUS_FAIL, output_pdf, f"PDF 转换后验证失败：{error}")
    return _result(STATUS_PASS, output_pdf, "PDF 已由 LibreOffice 转换并通过非空验证")


def export_pdf(
    root: Path,
    input_md: Path,
    output_pdf: Path,
    output_docx: Path | None,
    tools: dict[str, str | None],
) -> dict[str, Any]:
    """按 Pandoc+LaTeX、LibreOffice 两条路径生成 PDF。"""

    pandoc = tools.get("pandoc")
    latex_engine = tools.get("xelatex") or tools.get("lualatex")
    pandoc_failure: str | None = None
    if pandoc and latex_engine:
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        try:
            output_pdf.unlink(missing_ok=True)
        except OSError as error:
            return _result(STATUS_FAIL, output_pdf, f"无法清理旧 PDF：{error}")
        command = [
            pandoc,
            str(input_md),
            "--from=markdown",
            "--pdf-engine",
            latex_engine,
            "-o",
            str(output_pdf),
        ]
        returncode, stdout, stderr = _run_command(command, root)
        if returncode != 0:
            detail = _safe_error_detail(stdout, stderr, returncode)
            pandoc_failure = f"Pandoc PDF 生成失败：{detail}"
        else:
            try:
                verify_nonempty(output_pdf, "PDF")
            except AssemblyError as error:
                pandoc_failure = str(error)
            else:
                return _result(STATUS_PASS, output_pdf, f"PDF 已由 pandoc + {Path(latex_engine).name} 生成")

    office = tools.get("libreoffice")
    if office and output_docx is not None:
        try:
            verify_nonempty(output_docx, "用于转换 PDF 的 DOCX")
        except AssemblyError:
            # 没有可用 DOCX 时不能把 LibreOffice 的能力误报成 PDF 能力。
            return _result(
                CAPABILITY_GAP,
                output_pdf,
                "有 LibreOffice，但没有可转换的非空 DOCX（CAPABILITY_GAP）",
            )
        office_result = _libreoffice_pdf(root, output_docx, output_pdf, office)
        if office_result["status"] == STATUS_PASS and pandoc_failure:
            office_result["message"] = (
                "Pandoc/LaTeX 路径失败后，已改用 LibreOffice 从本次 DOCX 成功生成 PDF"
            )
        return office_result

    if pandoc_failure:
        return _result(STATUS_FAIL, output_pdf, pandoc_failure)

    missing: list[str] = []
    if not pandoc:
        missing.append("pandoc")
    if not latex_engine:
        missing.append("xelatex/lualatex")
    if not office:
        missing.append("libreoffice/soffice")
    return _result(
        CAPABILITY_GAP,
        output_pdf,
        "缺少 PDF 导出路径：" + "、".join(missing) + "（CAPABILITY_GAP）",
    )


def _path_for_report(path: Path | None) -> str | None:
    """将路径转成 JSON 可序列化字符串。"""

    return str(path) if path is not None else None


def assemble_and_export(
    root: Path | str,
    chapters_glob: str = "chapters/*.md",
    output_md: str = "07-paper-full.md",
    docx: str | None = "final-paper.docx",
    pdf: str | None = "final-paper.pdf",
    skip_docx: bool = False,
    skip_pdf: bool = False,
    mode: str = "full",
) -> dict[str, Any]:
    """执行整合和可选导出，返回稳定的审计报告字典。"""

    if mode not in {"full", "export", "source"}:
        raise ValueError(f"不支持的整合模式：{mode}")
    project_root = Path(root).expanduser().resolve()
    report: dict[str, Any] = {
        "status": STATUS_FAIL,
        "root": str(project_root),
        "mode": mode,
        "chapters_glob": chapters_glob,
        "outputs": {},
        "capabilities": {},
        "capability_gaps": [],
        "errors": [],
        "messages": [],
    }
    try:
        requested_markdown = resolve_path(project_root, output_md)
        if requested_markdown.suffix.casefold() not in {".md", ".markdown"}:
            raise AssemblyError("完整 Markdown 输出必须使用 .md 或 .markdown 后缀")
        if (
            mode != "export"
            and requested_markdown.exists()
            and requested_markdown.name != "07-paper-full.md"
        ):
            raise AssemblyError("非默认 Markdown 输出已存在，拒绝覆盖；请更换新文件名")
        if mode == "export" and requested_markdown.is_file():
            content = _read_chapter(requested_markdown)
            if not content.strip():
                raise AssemblyError("EXPORT_ONLY 的现有完整 Markdown 为空")
            markdown_path, chapter_paths = requested_markdown, []
        else:
            markdown_path, chapter_paths = assemble_markdown(
                project_root, chapters_glob=chapters_glob, output_md=output_md
            )
    except AssemblyError as error:
        report["errors"].append(str(error))
        return report

    report["output_md"] = str(markdown_path)
    report["chapters"] = [str(path) for path in chapter_paths]
    report["outputs"]["markdown"] = _result(STATUS_PASS, markdown_path, "Markdown 已生成并通过非空验证")

    # 在所有导出动作前统一探测工具，结果也写入 JSON 以便复核能力边界。
    tools = probe_tools()
    report["capabilities"] = tools
    docx_path = resolve_path(project_root, docx) if docx else None
    pdf_path = resolve_path(project_root, pdf) if pdf else None
    if docx_path is not None and docx_path.suffix.casefold() != ".docx":
        report["errors"].append("DOCX 输出必须使用 .docx 后缀")
        return report
    if pdf_path is not None and pdf_path.suffix.casefold() != ".pdf":
        report["errors"].append("PDF 输出必须使用 .pdf 后缀")
        return report
    output_paths = [path for path in (markdown_path, docx_path, pdf_path) if path is not None]
    if len(set(output_paths)) != len(output_paths):
        report["errors"].append("Markdown、DOCX、PDF 输出路径必须彼此不同")
        return report
    if any(path in set(chapter_paths) for path in (docx_path, pdf_path) if path is not None):
        report["errors"].append("DOCX/PDF 输出路径不能覆盖分章源文件")
        return report

    if skip_docx:
        docx_result = _result("SKIPPED", docx_path, "按参数跳过 DOCX 导出")
    elif docx_path is None:
        docx_result = _result("SKIPPED", None, "未指定 DOCX 输出路径")
    else:
        docx_result = export_docx(project_root, markdown_path, docx_path, tools)
    report["outputs"]["docx"] = docx_result
    if docx_result["status"] == CAPABILITY_GAP:
        report["capability_gaps"].append(docx_result.get("message", "DOCX 能力缺口"))
    elif docx_result["status"] == STATUS_FAIL:
        report["errors"].append(docx_result.get("message", "DOCX 导出失败"))

    if skip_pdf:
        pdf_result = _result("SKIPPED", pdf_path, "按参数跳过 PDF 导出")
    elif pdf_path is None:
        pdf_result = _result("SKIPPED", None, "未指定 PDF 输出路径")
    else:
        pdf_result = export_pdf(
            project_root,
            markdown_path,
            pdf_path,
            # 跳过 DOCX 生成时仍可使用调用方已提供的现有 DOCX；若本次生成失败，
            # 则不采信可能残留的旧文件，避免把旧产物误报为本次成功。
            docx_path
            if docx_result["status"] == STATUS_PASS or skip_docx
            else None,
            tools,
        )
    report["outputs"]["pdf"] = pdf_result
    if pdf_result["status"] == CAPABILITY_GAP:
        report["capability_gaps"].append(pdf_result.get("message", "PDF 能力缺口"))
    elif pdf_result["status"] == STATUS_FAIL:
        report["errors"].append(pdf_result.get("message", "PDF 导出失败"))

    if mode in {"full", "export"}:
        skipped = [
            label.upper()
            for label, result in (("docx", docx_result), ("pdf", pdf_result))
            if result.get("status") == "SKIPPED"
        ]
        if skipped:
            report["capability_gaps"].append(
                f"{mode} 模式不允许把跳过 {'、'.join(skipped)} 视为完整成功"
            )

    if report["errors"]:
        report["status"] = STATUS_FAIL
    elif report["capability_gaps"]:
        report["status"] = STATUS_PARTIAL
    else:
        report["status"] = STATUS_PASS
    return report


def build_parser() -> argparse.ArgumentParser:
    """构造中文命令行参数。"""

    parser = argparse.ArgumentParser(description="按文件名整合论文分章并导出 DOCX/PDF。")
    parser.add_argument("--root", help="项目根目录，默认使用脚本所属 Skill 根目录。")
    parser.add_argument(
        "--chapters-glob",
        default="chapters/*.md",
        help="章节 glob，默认 chapters/*.md。",
    )
    parser.add_argument(
        "--output-md",
        default="07-paper-full.md",
        help="完整 Markdown 输出路径，默认 07-paper-full.md。",
    )
    parser.add_argument(
        "--docx",
        nargs="?",
        const="final-paper.docx",
        default="final-paper.docx",
        help="DOCX 输出路径，默认 final-paper.docx。",
    )
    parser.add_argument(
        "--pdf",
        nargs="?",
        const="final-paper.pdf",
        default="final-paper.pdf",
        help="PDF 输出路径，默认 final-paper.pdf。",
    )
    parser.add_argument("--skip-docx", action="store_true", help="跳过 DOCX 导出。")
    parser.add_argument("--skip-pdf", action="store_true", help="跳过 PDF 导出。")
    parser.add_argument(
        "--mode",
        choices=("full", "export", "source", "FULL_BUILD", "EXPORT_ONLY"),
        default="full",
        help="运行模式；FULL_BUILD/full 和 EXPORT_ONLY/export 要求 DOCX/PDF，source 可只整合 Markdown。",
    )
    parser.add_argument("--json", action="store_true", help="以机器可读 JSON 输出报告。")
    return parser


def _exit_code(report: dict[str, Any]) -> int:
    """根据最终状态转换为稳定退出码。"""

    status = report.get("status")
    if status == STATUS_PASS:
        return EXIT_PASS
    if status == STATUS_PARTIAL:
        return EXIT_PARTIAL
    return EXIT_FAIL


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""

    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    mode_aliases = {"FULL_BUILD": "full", "EXPORT_ONLY": "export"}
    mode = mode_aliases.get(args.mode, args.mode)
    report = assemble_and_export(
        root=root,
        chapters_glob=args.chapters_glob,
        output_md=args.output_md,
        docx=args.docx,
        pdf=args.pdf,
        skip_docx=args.skip_docx,
        skip_pdf=args.skip_pdf,
        mode=mode,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(f"状态：{report['status']}")
        if report.get("output_md"):
            print(f"已生成：{report['output_md']}")
        for message in report.get("capability_gaps", []):
            print(f"能力缺口：{message}")
        for message in report.get("errors", []):
            print(f"失败：{message}", file=sys.stderr)
    return _exit_code(report)


if __name__ == "__main__":
    raise SystemExit(main())
