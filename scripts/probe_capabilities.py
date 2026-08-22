#!/usr/bin/env python3
"""对论文生产运行环境执行保守、可审计的能力探测。

本模块只使用 Python 标准库。它不会把语言模型、客户端内置工具或同一
供应商的其他产品当作本地能力；尤其是图片生成能力必须通过显式参数声明。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence
from urllib.parse import urlsplit


CAPABILITY_NAMES = (
    "FILESYSTEM",
    "CODE_EXEC",
    "FRONTEND_RENDERER",
    "SVG_RENDERER",
    "IMAGE_GENERATOR",
    "DOCX_ENGINE",
    "PDF_ENGINE",
    "DOC_INSPECTOR",
)

STATUSES = ("AVAILABLE", "PARTIAL", "CAPABILITY_GAP", "UNVERIFIED")

# 退出码保持稳定，便于自动化调用方只依赖数字而不解析人类输出。
EXIT_OK = 0
EXIT_CAPABILITY_GAP = 1
EXIT_RUNTIME_ERROR = 3

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PDF_SIGNATURE = b"%PDF-"
_PROBE_MARKER = "CAPABILITY_PROBE_OK"
_INSPECT_MARKER = "CAPABILITY_INSPECT_OK"
_MAX_COMMAND_TIMEOUT = 10.0


@dataclass(frozen=True)
class ProbeResult:
    """单项能力的状态、证据和限制。"""

    status: str
    evidence: list[str]
    limitations: list[str]

    def as_dict(self) -> dict[str, object]:
        """转换为机器可读的普通字典。"""

        return {
            "status": self.status,
            "evidence": list(self.evidence),
            "limitations": list(self.limitations),
        }


def _result(status: str, evidence: Iterable[str], limitations: Iterable[str]) -> ProbeResult:
    """构造结果并在内部保证状态值合法。"""

    if status not in STATUSES:
        raise ValueError(f"未知能力状态：{status}")
    return ProbeResult(status, list(evidence), list(limitations))


def resolve_root(root_argument: str | None) -> Path:
    """解析探测根目录；未传参数时使用脚本所属 Skill 根目录。"""

    if root_argument is None:
        return Path(__file__).resolve().parents[1]
    return Path(root_argument).expanduser().resolve(strict=False)


def _safe_environment(temp_root: Path | None = None) -> dict[str, str]:
    """为外部探测命令准备最小环境，绝不把环境内容写入报告。"""

    # 不改写 HOME/USERPROFILE。浏览器和 Office 使用各自的显式配置目录参数隔离。
    environment = {"PATH": os.environ.get("PATH", "")}
    if temp_root is not None:
        environment["TMPDIR"] = str(temp_root)
        environment["TMP"] = str(temp_root)
        environment["TEMP"] = str(temp_root)
    return environment


def _run_external_capture(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float = 12.0,
    temp_root: Path | None = None,
) -> tuple[bool, str, str]:
    """运行白名单中的外部命令，并在超时时清理整个进程组。"""

    # 即使调用方传入更大的值，也将单个外部命令限制在短时间内。
    effective_timeout = max(0.1, min(float(timeout), _MAX_COMMAND_TIMEOUT))
    process: subprocess.Popen[str] | None = None
    try:
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=_safe_environment(temp_root),
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
        stdout, _stderr = process.communicate(timeout=effective_timeout)
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
                process.communicate(timeout=2.0)
            except (OSError, subprocess.SubprocessError):
                try:
                    process.kill()
                except OSError:
                    pass
        return False, "", "命令超时"
    except (OSError, subprocess.SubprocessError):
        # 不回传 stderr，避免命令行、环境变量或工具自身日志中的敏感信息进入报告。
        return False, "", "命令未能完成"
    if process.returncode != 0:
        return False, "", "命令返回非零状态"
    return True, stdout, "命令执行成功"


def _run_external(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: float = 12.0,
    temp_root: Path | None = None,
) -> tuple[bool, str]:
    """运行白名单中的外部命令，只返回成功标记和固定的失败原因。"""

    ok, _stdout, reason = _run_external_capture(
        command,
        cwd=cwd,
        timeout=timeout,
        temp_root=temp_root,
    )
    return ok, reason


def _first_executable(names: Sequence[str]) -> tuple[str, str] | None:
    """从固定的工具名中找出第一个可执行文件。"""

    for name in names:
        path = shutil.which(name)
        if path:
            return name, path
    return None


def _valid_png(path: Path) -> bool:
    """检查文件是否至少具有非空 PNG 文件头。"""

    try:
        return path.is_file() and path.stat().st_size > len(_PNG_SIGNATURE) and path.read_bytes()[:8] == _PNG_SIGNATURE
    except OSError:
        return False


def _valid_pdf(path: Path) -> bool:
    """检查文件是否至少具有非空 PDF 文件头和结束标记。"""

    try:
        if not path.is_file() or path.stat().st_size < 100:
            return False
        content = path.read_bytes()
    except OSError:
        return False
    return content.startswith(_PDF_SIGNATURE) and b"%%EOF" in content[-1024:]


def _write_minimal_svg(path: Path) -> None:
    """写入固定 SVG，用于验证渲染器确实能产生位图。"""

    path.write_text(
        """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"160\" height=\"80\">
  <rect width=\"160\" height=\"80\" fill=\"#ffffff\"/>
  <circle cx=\"40\" cy=\"40\" r=\"20\" fill=\"#3366cc\"/>
  <text x=\"72\" y=\"46\" font-size=\"14\">probe</text>
</svg>
""",
        encoding="utf-8",
    )


def _write_minimal_html(path: Path) -> None:
    """写入固定 HTML，用于验证浏览器渲染器。"""

    path.write_text(
        """<!doctype html>
<html><head><meta charset=\"utf-8\"><style>body{margin:0}div{width:160px;height:80px;background:#3366cc}</style></head>
<body><div></div></body></html>
""",
        encoding="utf-8",
    )


def _write_minimal_docx(path: Path, marker: str = _PROBE_MARKER) -> None:
    """写入不依赖第三方库的最小 OOXML 文档。"""

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    package_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{marker}</w:t></w:r></w:p><w:sectPr/></w:body>
</w:document>
"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", package_rels)
        archive.writestr("word/document.xml", document)


def _write_minimal_pdf(path: Path, marker: str = _INSPECT_MARKER) -> None:
    """写入固定单页 PDF，供文档检查器提取文本。"""

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 240 120] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(('BT /F1 12 Tf 12 60 Td (' + marker + ') Tj ET').encode('ascii'))} >>\nstream\nBT /F1 12 Tf 12 60 Td ({marker}) Tj ET\nendstream".encode("ascii"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(output)


def _probe_filesystem(root: Path) -> ProbeResult:
    """实际验证根目录的存在、读取、写入和临时清理能力。"""

    if not root.exists():
        return _result("CAPABILITY_GAP", ["探测根目录不存在"], ["无法在指定根目录执行文件读写探测"])
    if not root.is_dir():
        return _result("CAPABILITY_GAP", ["探测根目录不是目录"], ["需要一个可访问的项目目录"])
    if not os.access(root, os.R_OK | os.X_OK):
        return _result("CAPABILITY_GAP", ["探测根目录不可读取或不可进入"], ["无法安全读取项目文件"])

    try:
        with tempfile.TemporaryDirectory(prefix=".capability-probe-", dir=str(root)) as directory:
            probe_path = Path(directory) / "filesystem-check.txt"
            probe_path.write_text(_PROBE_MARKER, encoding="utf-8")
            if probe_path.read_text(encoding="utf-8") != _PROBE_MARKER:
                return _result("PARTIAL", ["文件可创建但读回内容不一致"], ["未通过完整读写一致性检查"])
    except OSError:
        return _result("PARTIAL", ["根目录可读取，但临时文件读写探测失败"], ["当前根目录可能没有写权限；未留下探测文件"])

    return _result(
        "AVAILABLE",
        ["根目录存在且已通过临时文件创建、写入、读回和清理探测"],
        ["结果只代表本次运行和指定根目录的权限，不代表其他挂载点"]
    )


def _probe_code_exec(root: Path) -> ProbeResult:
    """通过受控 Python 子进程验证代码执行能力。"""

    executable = Path(sys.executable)
    if not executable.is_file():
        return _result("CAPABILITY_GAP", ["当前 Python 解释器路径不可执行"], ["无法启动受控代码探测子进程"])
    cwd = root if root.is_dir() else None
    ok, stdout, reason = _run_external_capture(
        [str(executable), "-B", "-c", "import sys; sys.stdout.write('CAPABILITY_PROBE_OK')"],
        cwd=cwd,
        timeout=8.0,
    )
    if not ok:
        return _result("PARTIAL", ["已找到 Python 解释器，但受控子进程探测失败"], [reason, "未记录子进程原始输出"])
    if stdout != _PROBE_MARKER:
        return _result("PARTIAL", ["Python 子进程返回值或固定校验标记不符合预期"], ["未记录子进程原始输出"])
    return _result("AVAILABLE", ["Python 标准库子进程已返回固定校验标记"], ["只验证了 Python 代码执行，不代表其他语言运行时"])


def _render_with_browser(name: str, executable: str, html: Path, output: Path, workdir: Path) -> tuple[bool, str]:
    """调用已发现的浏览器或浏览器 CLI 生成 PNG。"""

    url = html.as_uri()
    if name == "playwright":
        command = [executable, "screenshot", "--device=Desktop Chrome", url, str(output)]
    elif name == "firefox":
        command = [executable, "--headless", "--screenshot", str(output), url]
    else:
        profile = workdir / "browser-profile"
        command = [
            executable,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            "--no-first-run",
            "--disable-extensions",
            f"--user-data-dir={profile}",
            f"--screenshot={output}",
            "--window-size=640,480",
            url,
        ]
    return _run_external(command, cwd=workdir, timeout=25.0, temp_root=workdir)


def _probe_frontend_renderer(root: Path) -> ProbeResult:
    """实际渲染固定 HTML 并检查 PNG 结果。"""

    candidates = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "firefox", "playwright")
    found = [(name, path) for name in candidates if (path := shutil.which(name))]
    if not found:
        return _result("CAPABILITY_GAP", ["未发现可调用的本地浏览器渲染器"], ["未把前端源码能力或客户端预览能力视为渲染器"])

    try:
        with tempfile.TemporaryDirectory(prefix=".frontend-probe-") as directory:
            workdir = Path(directory)
            html = workdir / "probe.html"
            output = workdir / "probe.png"
            _write_minimal_html(html)
            failures: list[str] = []
            for name, executable in found:
                try:
                    output.unlink(missing_ok=True)
                except OSError:
                    pass
                ok, reason = _render_with_browser(name, executable, html, output, workdir)
                if ok and _valid_png(output):
                    return _result(
                        "AVAILABLE",
                        [f"已由本地 {name} 渲染固定 HTML 并生成有效 PNG"],
                        ["只验证了静态页面截图，不代表 JavaScript、网络资源或字体均可用"],
                    )
                failures.append(f"{name} 探测未产出有效图像：{reason}")
    except OSError:
        return _result("PARTIAL", ["已发现浏览器渲染器，但无法准备临时页面"], ["未留下探测文件"])
    return _result("PARTIAL", ["已发现浏览器或截图 CLI，但实际渲染探测失败"], ["未记录外部命令原始输出；可能缺少无头浏览器运行时"])


def _render_with_svg_tool(name: str, executable: str, source: Path, output: Path, workdir: Path) -> tuple[bool, str]:
    """按工具类型调用 SVG 到 PNG 的转换命令。"""

    if name == "rsvg-convert":
        command = [executable, "-o", str(output), str(source)]
    elif name == "inkscape":
        command = [executable, str(source), "--export-type=png", f"--export-filename={output}"]
    elif name == "cairosvg":
        command = [executable, str(source), "-o", str(output)]
    else:
        command = [executable, str(source), str(output)]
    return _run_external(command, cwd=workdir, timeout=20.0, temp_root=workdir)


def _probe_svg_renderer(root: Path) -> ProbeResult:
    """实际转换固定 SVG 并检查 PNG 结果。"""

    candidates = ("rsvg-convert", "inkscape", "cairosvg", "magick", "convert")
    found = [(name, path) for name in candidates if (path := shutil.which(name))]
    if not found:
        return _result("CAPABILITY_GAP", ["未发现可调用的 SVG 转换器"], ["编写 SVG 源码不等同于实际渲染"])

    try:
        with tempfile.TemporaryDirectory(prefix=".svg-probe-") as directory:
            workdir = Path(directory)
            source = workdir / "probe.svg"
            output = workdir / "probe.png"
            _write_minimal_svg(source)
            for name, executable in found:
                ok, reason = _render_with_svg_tool(name, executable, source, output, workdir)
                if ok and _valid_png(output):
                    return _result(
                        "AVAILABLE",
                        [f"已由本地 {name} 将固定 SVG 转换为有效 PNG"],
                        ["只验证了 SVG 到 PNG 的基本路径，不代表复杂字体、滤镜或外部资源均可用"],
                    )
                # 同一个输出路径供下一个工具复用，失败工具的文件不会被报告引用。
                try:
                    output.unlink(missing_ok=True)
                except OSError:
                    pass
    except OSError:
        return _result("PARTIAL", ["已发现 SVG 转换器，但无法准备临时素材"], ["未留下探测文件"])
    return _result("PARTIAL", ["已发现 SVG 转换器，但实际转换探测失败"], ["未记录外部命令原始输出"])


def _safe_declared_name(value: str) -> str:
    """清理显式图片工具声明，避免把路径、令牌或 URL 查询串写入报告。"""

    text = value.strip()
    if not text:
        return "已声明的图片工具"
    parsed = urlsplit(text)
    if parsed.scheme and parsed.netloc:
        text = parsed.netloc
    elif "/" in text or "\\" in text:
        text = Path(text.replace("\\", "/")).name
    text = re.sub(
        r"(?i)\b(?:sk|rk|key|token|secret|password)[-_:=][a-z0-9._-]+\b",
        "[REDACTED_SECRET]",
        text,
    )
    text = re.sub(r"[^\w.:@+\-/\[\]]+", " ", text, flags=re.UNICODE).strip()
    return text[:80] or "已声明的图片工具"


def _valid_image_artifact(path: Path) -> bool:
    """验证常见图片产物的文件头，避免用任意空壳文件证明图片能力。"""

    try:
        if not path.is_file() or path.stat().st_size < 12:
            return False
        header = path.read_bytes()[:16]
    except OSError:
        return False
    return (
        header.startswith(_PNG_SIGNATURE)
        or header.startswith(b"\xff\xd8\xff")
        or (header.startswith(b"RIFF") and header[8:12] == b"WEBP")
    )


def _probe_image_generator(
    declaration: str | None,
    artifact: Path | None = None,
) -> ProbeResult:
    """图片生成器必须同时有显式声明和本次运行的有效图片产物。"""

    if declaration is None or not declaration.strip():
        return _result(
            "UNVERIFIED",
            ["未通过显式 CLI 参数声明专用图片生成工具或模型"],
            ["不能从 shell 中发现结果推断客户端内置图片工具；本次未调用图片生成器"],
        )
    name = _safe_declared_name(declaration)
    if artifact is None:
        return _result(
            "UNVERIFIED",
            [f"已登记图片工具或模型：{name}，但未提供本次运行产物"],
            ["声明不等于实际调用；需要 --image-generator-artifact 指向有效 PNG、JPEG 或 WebP"],
        )
    if not _valid_image_artifact(artifact):
        return _result(
            "UNVERIFIED",
            [f"已登记图片工具或模型：{name}，但图片产物未通过文件头验证"],
            ["产物不存在、为空或不是可识别的 PNG、JPEG、WebP；不得标记 AVAILABLE"],
        )
    return _result(
        "PARTIAL",
        [f"已登记图片工具或模型并验证图片文件：{name}；{_safe_declared_name(artifact.name)}"],
        ["文件存在不能单独证明由本次工具调用生成；需要证据执行记录后才能作为已调用能力"],
    )


def _office_command() -> tuple[str, str] | None:
    """查找可将 OOXML 文档导出的 Office 命令。"""

    return _first_executable(("soffice", "libreoffice"))


def _run_soffice_pdf(executable: str, docx: Path, output_directory: Path, workdir: Path) -> tuple[bool, str]:
    """用隔离用户配置调用 LibreOffice/soffice 导出 PDF。"""

    profile = workdir / "office-profile"
    command = [
        executable,
        "--headless",
        f"-env:UserInstallation=file://{profile}",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_directory),
        str(docx),
    ]
    return _run_external(command, cwd=workdir, timeout=35.0, temp_root=workdir)


def _probe_docx_engine(root: Path) -> ProbeResult:
    """生成最小 DOCX，并让本地文档引擎实际处理它。"""

    office = _office_command()
    pandoc = shutil.which("pandoc")
    if office is None and not pandoc:
        return _result("CAPABILITY_GAP", ["未发现 soffice、libreoffice 或 pandoc"], ["无法实际生成或处理 DOCX"])

    failures: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix=".docx-probe-") as directory:
            workdir = Path(directory)
            docx = workdir / "probe.docx"
            _write_minimal_docx(docx)
            if office is not None:
                name, executable = office
                output_directory = workdir / "office-output"
                output_directory.mkdir()
                ok, reason = _run_soffice_pdf(executable, docx, output_directory, workdir)
                pdf = output_directory / "probe.pdf"
                if ok and _valid_pdf(pdf):
                    return _result(
                        "AVAILABLE",
                        [f"已由本地 {name} 读取最小 DOCX 并成功导出有效 PDF"],
                        ["只验证了基本文档处理路径，不代表复杂样式、目录或嵌入对象均可用"],
                    )
                failures.append(f"{name} 未成功处理 DOCX：{reason}")
            if pandoc:
                markdown = workdir / "probe.md"
                markdown.write_text(_PROBE_MARKER, encoding="utf-8")
                output = workdir / "pandoc.docx"
                ok, reason = _run_external(
                    [pandoc, "--from=markdown", "--to=docx", "--output", str(output), str(markdown)],
                    cwd=workdir,
                    timeout=25.0,
                    temp_root=workdir,
                )
                if ok and output.is_file() and zipfile.is_zipfile(output):
                    return _result(
                        "AVAILABLE",
                        ["已由本地 pandoc 将固定文本生成有效 DOCX 容器"],
                        ["未验证复杂版式、分页和 Word 专有字段"]
                    )
                failures.append(f"pandoc 未成功生成 DOCX：{reason}")
    except OSError:
        return _result("PARTIAL", ["已发现 DOCX 工具，但无法准备临时文档"], ["未留下探测文件"])
    return _result("PARTIAL", ["已发现 DOCX 工具，但实际处理探测失败"], ["未记录外部命令原始输出"])


def _run_weasyprint(executable: str, html: Path, output: Path, workdir: Path) -> tuple[bool, str]:
    """调用 weasyprint CLI 生成 PDF。"""

    return _run_external([executable, str(html), str(output)], cwd=workdir, timeout=30.0, temp_root=workdir)


def _run_wkhtmltopdf(executable: str, html: Path, output: Path, workdir: Path) -> tuple[bool, str]:
    """调用 wkhtmltopdf 生成 PDF。"""

    return _run_external([executable, "--quiet", str(html), str(output)], cwd=workdir, timeout=30.0, temp_root=workdir)


def _probe_pdf_engine(root: Path) -> ProbeResult:
    """实际生成 PDF 并检查基本文件完整性。"""

    office = _office_command()
    candidates = [
        ("weasyprint", shutil.which("weasyprint")),
        ("wkhtmltopdf", shutil.which("wkhtmltopdf")),
        ("typst", shutil.which("typst")),
        ("pandoc", shutil.which("pandoc")),
    ]
    found = [(name, path) for name, path in candidates if path]
    if office is None and not found:
        return _result("CAPABILITY_GAP", ["未发现可调用的 PDF 生成引擎"], ["未将 PDF 解析器误报为 PDF 生成器"])

    try:
        with tempfile.TemporaryDirectory(prefix=".pdf-probe-") as directory:
            workdir = Path(directory)
            html = workdir / "probe.html"
            _write_minimal_html(html)
            if office is not None:
                name, executable = office
                docx = workdir / "probe.docx"
                output_directory = workdir / "office-output"
                output_directory.mkdir()
                _write_minimal_docx(docx)
                ok, reason = _run_soffice_pdf(executable, docx, output_directory, workdir)
                pdf = output_directory / "probe.pdf"
                if ok and _valid_pdf(pdf):
                    return _result(
                        "AVAILABLE",
                        [f"已由本地 {name} 成功生成有效 PDF"],
                        ["只验证了固定最小文档的导出路径，不代表复杂论文排版均可用"],
                    )
                # 失败原因不写出外部命令的原始日志。
                _ = reason
            for name, executable in found:
                output = workdir / f"{name}.pdf"
                if name == "weasyprint":
                    ok, reason = _run_weasyprint(executable, html, output, workdir)
                elif name == "wkhtmltopdf":
                    ok, reason = _run_wkhtmltopdf(executable, html, output, workdir)
                elif name == "typst":
                    source = workdir / "probe.typ"
                    source.write_text("#set page(width: 160pt, height: 80pt)\nCapability probe", encoding="utf-8")
                    ok, reason = _run_external([executable, "compile", str(source), str(output)], cwd=workdir, timeout=30.0, temp_root=workdir)
                else:
                    markdown = workdir / "probe.md"
                    markdown.write_text("Capability probe", encoding="utf-8")
                    ok, reason = _run_external([executable, "--from=markdown", "--to=pdf", "--output", str(output), str(markdown)], cwd=workdir, timeout=30.0, temp_root=workdir)
                if ok and _valid_pdf(output):
                    return _result(
                        "AVAILABLE",
                        [f"已由本地 {name} 成功生成有效 PDF"],
                        ["只验证了固定最小输入的导出路径"]
                    )
                _ = reason
    except OSError:
        return _result("PARTIAL", ["已发现 PDF 引擎，但无法准备临时输入"], ["未留下探测文件"])
    return _result("PARTIAL", ["已发现 PDF 引擎，但实际生成探测失败"], ["未记录外部命令原始输出"])


def _probe_doc_inspector(root: Path) -> ProbeResult:
    """使用本地文本提取工具实际读取固定 PDF，并补充 OOXML 基本检查。"""

    pdftotext = shutil.which("pdftotext")
    mutool = shutil.which("mutool")
    pandoc = shutil.which("pandoc")
    docx2txt = shutil.which("docx2txt")
    if not any((pdftotext, mutool, pandoc, docx2txt)):
        return _result("CAPABILITY_GAP", ["未发现可调用的 PDF/DOCX 文本检查工具"], ["标准库仅能做容器级检查，未宣称具备完整文档解析能力"])

    try:
        with tempfile.TemporaryDirectory(prefix=".doc-inspector-probe-") as directory:
            workdir = Path(directory)
            pdf = workdir / "probe.pdf"
            _write_minimal_pdf(pdf)
            if pdftotext:
                text_output = workdir / "probe.txt"
                text_output.unlink(missing_ok=True)
                ok, reason = _run_external([pdftotext, str(pdf), str(text_output)], cwd=workdir, timeout=15.0, temp_root=workdir)
                try:
                    extracted = text_output.read_text(encoding="utf-8", errors="replace") if text_output.is_file() else ""
                except OSError:
                    extracted = ""
                if ok and _INSPECT_MARKER in extracted:
                    return _result(
                        "AVAILABLE",
                        ["已由本地 pdftotext 提取固定 PDF 中的校验文本"],
                        ["只验证文本提取，不等同于视觉版式审查、复杂 DOCX 语义解析或内容真实性核验"],
                    )
                _ = reason
            if mutool:
                mutool_output = workdir / "probe.txt"
                mutool_output.unlink(missing_ok=True)
                ok, reason = _run_external([mutool, "draw", "-F", "txt", "-o", str(mutool_output), str(pdf)], cwd=workdir, timeout=15.0, temp_root=workdir)
                try:
                    extracted = mutool_output.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    extracted = ""
                if ok and _INSPECT_MARKER in extracted:
                    return _result("AVAILABLE", ["已由本地 mutool 提取固定 PDF 中的校验文本"], ["只验证文本提取，不等同于视觉版式审查"])
                _ = reason
            if pandoc or docx2txt:
                docx = workdir / "probe.docx"
                _write_minimal_docx(docx)
                if pandoc:
                    ok, reason = _run_external([pandoc, "--from=docx", "--to=plain", "--output", str(workdir / "probe-docx.txt"), str(docx)], cwd=workdir, timeout=20.0, temp_root=workdir)
                    try:
                        extracted = (workdir / "probe-docx.txt").read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        extracted = ""
                    if ok and _PROBE_MARKER in extracted:
                        return _result("AVAILABLE", ["已由本地 pandoc 提取固定 DOCX 中的校验文本"], ["只验证基本文本解析，不等同于视觉版式审查"])
                    _ = reason
                if docx2txt:
                    extraction_dir = workdir / "docx-text"
                    extraction_dir.mkdir()
                    ok, reason = _run_external([docx2txt, str(docx), str(extraction_dir)], cwd=workdir, timeout=20.0, temp_root=workdir)
                    extracted_files = list(extraction_dir.glob("*"))
                    extracted = "".join(
                        file.read_text(encoding="utf-8", errors="replace")
                        for file in extracted_files
                        if file.is_file()
                    )
                    if ok and _PROBE_MARKER in extracted:
                        return _result("AVAILABLE", ["已由本地 docx2txt 提取固定 DOCX 中的校验文本"], ["只验证基本文本解析，不等同于视觉版式审查"])
                    _ = reason
    except OSError:
        return _result("PARTIAL", ["已发现文档检查工具，但无法准备临时文档"], ["未留下探测文件"])
    return _result("PARTIAL", ["已发现文档检查工具，但实际文本提取探测失败"], ["未记录外部命令原始输出"])


def _safe_probe(function: Callable[[], ProbeResult]) -> ProbeResult:
    """隔离单项探测异常，确保一项工具失败不污染其他结果。"""

    try:
        return function()
    except Exception:
        return _result("PARTIAL", ["探测过程发生未公开的运行时异常"], ["异常详情未写入报告，避免泄露环境或工具输出"])


def probe_capabilities(
    root: Path,
    image_generator: str | None = None,
    image_generator_artifact: Path | None = None,
) -> dict[str, object]:
    """执行全部 P0 能力探测并返回机器可读报告。"""

    safe_artifact = image_generator_artifact
    if safe_artifact is not None:
        try:
            safe_artifact.resolve().relative_to(root.resolve())
        except ValueError:
            safe_artifact = None
    results: dict[str, ProbeResult] = {}
    results["FILESYSTEM"] = _safe_probe(lambda: _probe_filesystem(root))
    results["CODE_EXEC"] = _safe_probe(lambda: _probe_code_exec(root))
    results["FRONTEND_RENDERER"] = _safe_probe(lambda: _probe_frontend_renderer(root))
    results["SVG_RENDERER"] = _safe_probe(lambda: _probe_svg_renderer(root))
    results["IMAGE_GENERATOR"] = _safe_probe(
        lambda: _probe_image_generator(image_generator, safe_artifact)
    )
    results["DOCX_ENGINE"] = _safe_probe(lambda: _probe_docx_engine(root))
    results["PDF_ENGINE"] = _safe_probe(lambda: _probe_pdf_engine(root))
    results["DOC_INSPECTOR"] = _safe_probe(lambda: _probe_doc_inspector(root))

    serialized = {name: results[name].as_dict() for name in CAPABILITY_NAMES}
    statuses = [results[name].status for name in CAPABILITY_NAMES]
    if all(status == "AVAILABLE" for status in statuses):
        overall = "AVAILABLE"
    elif "CAPABILITY_GAP" in statuses:
        overall = "CAPABILITY_GAP"
    elif "UNVERIFIED" in statuses:
        overall = "UNVERIFIED"
    else:
        overall = "PARTIAL"
    summary = {status: statuses.count(status) for status in STATUSES}
    return {
        "schema_version": "1.0",
        "root": str(root),
        "overall_status": overall,
        "capabilities": serialized,
        "summary": summary,
    }


def _exit_code(report: dict[str, object]) -> int:
    """将报告状态转换为稳定退出码。"""

    capabilities = report.get("capabilities", {})
    if not isinstance(capabilities, dict):
        return EXIT_RUNTIME_ERROR
    if set(capabilities) != set(CAPABILITY_NAMES):
        return EXIT_RUNTIME_ERROR
    statuses = [
        value.get("status")
        for value in capabilities.values()
        if isinstance(value, dict)
    ]
    return EXIT_OK if statuses and all(status == "AVAILABLE" for status in statuses) else EXIT_CAPABILITY_GAP


def _render_human(report: dict[str, object]) -> str:
    """生成不含敏感命令输出的人类可读中文摘要。"""

    capabilities = report.get("capabilities", {})
    lines = ["能力探测报告", f"总体状态：{report.get('overall_status', 'PARTIAL')}"]
    if isinstance(capabilities, dict):
        for name in CAPABILITY_NAMES:
            item = capabilities.get(name, {})
            status = item.get("status", "PARTIAL") if isinstance(item, dict) else "PARTIAL"
            lines.append(f"- {name}：{status}")
    lines.append(f"退出码建议：{_exit_code(report)}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """构造能力探测命令行参数。"""

    parser = argparse.ArgumentParser(description="探测论文生产所需的本地 P0 能力并输出 JSON 报告。")
    parser.add_argument("--root", help="项目根目录；默认使用当前脚本所属 Skill 根目录。")
    parser.add_argument("--json", action="store_true", help="将机器可读 JSON 输出到标准输出。")
    parser.add_argument("--output", help="将机器可读 JSON 报告写入指定文件；父目录必须已存在。")
    parser.add_argument(
        "--image-generator",
        "--image-generator-tool",
        "--declare-image-generator",
        dest="image_generator",
        metavar="NAME",
        help="显式登记图片生成工具或模型；不传时 IMAGE_GENERATOR 保持 UNVERIFIED。",
    )
    parser.add_argument(
        "--image-generator-artifact",
        help="本次图片工具调用生成的 PNG、JPEG 或 WebP；只有产物有效时才标记 AVAILABLE。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """执行命令行入口。"""

    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    image_artifact = None
    if args.image_generator_artifact:
        candidate = Path(args.image_generator_artifact).expanduser()
        image_artifact = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    report = probe_capabilities(root, args.image_generator, image_artifact)
    report["exit_code"] = _exit_code(report)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.output:
        if args.output == "-":
            # “-” 只表示不额外创建文件，标准输出仍按 --json 规则处理。
            pass
        else:
            try:
                output_path = Path(args.output).expanduser()
                output_path = output_path.resolve() if output_path.is_absolute() else (root / output_path).resolve()
                try:
                    output_path.relative_to(root.resolve())
                except ValueError:
                    print("能力探测失败：输出路径越出项目根目录。", file=sys.stderr)
                    return EXIT_RUNTIME_ERROR
                output_path.write_text(payload, encoding="utf-8")
            except OSError:
                print("能力探测失败：无法写入输出文件。", file=sys.stderr)
                return EXIT_RUNTIME_ERROR

    if args.json:
        sys.stdout.write(payload)
    else:
        sys.stdout.write(_render_human(report) + "\n")
        if args.output:
            sys.stdout.write(f"已写入机器可读报告：{Path(args.output).expanduser()}\n")
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
