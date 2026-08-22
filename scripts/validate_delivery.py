#!/usr/bin/env python3
"""对论文交付目录执行可重复的 P0 结构验收。

该脚本只依赖 Python 标准库。它不会采信论文自身的 PASS 声明，而是根据
实际落盘文件、文档结构、正文体量、图文件和时间戳重新计算状态。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
from xml.etree import ElementTree

try:
    from . import validate_evidence as evidence_validator
except ImportError:
    import validate_evidence as evidence_validator


PASS = "PASS"
PARTIAL = "PARTIAL"
FAIL = "FAIL"

MODE_ALIASES = {
    "full": "full",
    "source": "source",
    "figures": "figures",
    "FULL_BUILD": "full",
    "AUDIT_ONLY": "full",
    "FIGURES_ONLY": "figures",
}

# 稳定退出码：成功、可交付但有能力缺口、硬性验收失败。
EXIT_CODES = {PASS: 0, PARTIAL: 1, FAIL: 2}

SOURCE_REQUIRED_FILES = (
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
    "figures/figure-manifest.json",
)

FINAL_REQUIRED_FILES = (
    "final-paper.docx",
    "final-paper.pdf",
    "run-manifest.json",
    "12-final-qa-report.md",
)

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
HEADING_RE = re.compile(r"(?im)^\s*#{1,6}\s+(.+?)\s*$")
STATUS_RE = re.compile(r"(?<![A-Za-z])(PASS|PARTIAL|FAIL)(?![A-Za-z])", re.I)
PATH_SUFFIX_RE = re.compile(
    r"\.(?:md|markdown|csv|bib|json|yaml|yml|tex|docx|pdf|svg|png|html?|py|js|mjs|java|sql)$",
    re.I,
)

POINTER_PATTERNS = (
    re.compile(r"详见\s*(?:分章|章节(?:文件)?|对应分章|文件链接)", re.I),
    re.compile(r"正文(?:完整内容)?[^\n]{0,30}详见(?:对应)?分章", re.I),
    re.compile(r"file://[^\n]*(?:chapters?/|07-paper-full)", re.I),
    re.compile(r"\[[^\]]*(?:分章|章节文件|完整源码|工作区文件)[^\]]*\]\([^\n)]*(?:file://|chapters?/|\.md)", re.I),
)

REQUIRED_PAPER_SECTIONS = {
    "摘要": re.compile(r"(?im)^\s*#{1,6}\s*(?:(?:中文)?摘\s*要|abstract)\s*$"),
    "参考文献": re.compile(r"(?im)^\s*#{1,6}\s*(?:参考\s*文献|references)\s*$"),
    "致谢": re.compile(r"(?im)^\s*#{1,6}\s*(?:致\s*谢|acknowledg(?:e)?ments?)\s*$"),
}


def _iso_timestamp(timestamp: float | int | None) -> str | None:
    """将文件时间转换为稳定的 UTC ISO 文本。"""

    if timestamp is None:
        return None
    return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()


def _normalise_status(value: Any) -> str | None:
    """从中英文状态声明中提取规范状态。"""

    if not isinstance(value, str):
        return None
    match = STATUS_RE.search(value.upper())
    if match:
        return match.group(1).upper()
    if "通过" in value or "已完成" in value:
        return PASS
    if "部分" in value or "能力缺口" in value or "待人工" in value:
        return PARTIAL
    if "失败" in value or "不通过" in value:
        return FAIL
    return None


def _count_cjk(text: str) -> int:
    """统计 CJK 字符数量。"""

    return len(CJK_RE.findall(text))


def _read_text(path: Path) -> str:
    """尽量读取文本，坏编码也不让验收器崩溃。"""

    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return path.read_text(encoding="utf-8", errors="replace")


def _relative(root: Path, path: Path) -> str:
    """返回项目内的统一相对路径。"""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _is_nonempty_file(path: Path) -> bool:
    """判断文件存在且有内容。"""

    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


@dataclass
class Issue:
    """一条可审计的验收问题。"""

    code: str
    message: str
    severity: str = FAIL
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class Check:
    """一项检查及其结构化详情。"""

    name: str
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """收集验收结果，并根据问题严重级别计算最终状态。"""

    root: Path
    mode: str
    phase: str = "final"
    checks: list[Check] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    declarations: dict[str, str | None] = field(
        default_factory=lambda: {"manifest": None, "qa": None}
    )

    @property
    def status(self) -> str:
        """只依据脚本发现的问题计算状态。"""

        if any(issue.severity == FAIL for issue in self.issues):
            return FAIL
        if any(issue.severity == PARTIAL for issue in self.issues):
            return PARTIAL
        return PASS

    @property
    def exit_code(self) -> int:
        """返回稳定的命令行退出码。"""

        return EXIT_CODES[self.status]

    def add_check(
        self,
        name: str,
        status: str,
        message: str,
        **details: Any,
    ) -> None:
        """记录一项检查。"""

        self.checks.append(Check(name, status, message, details))

    def add_issue(
        self,
        code: str,
        message: str,
        severity: str = FAIL,
        **details: Any,
    ) -> None:
        """记录问题并避免完全重复的噪声。"""

        if severity not in {PARTIAL, FAIL}:
            raise ValueError(f"不支持的问题级别：{severity}")
        if any(issue.code == code and issue.message == message for issue in self.issues):
            return
        self.issues.append(Issue(code, message, severity, details))

    def as_dict(self) -> dict[str, Any]:
        """返回 JSON 可序列化的完整报告。"""

        return {
            "status": self.status,
            "mode": self.mode,
            "phase": self.phase,
            "root": str(self.root),
            "exit_code": self.exit_code,
            "checks": [check.as_dict() for check in self.checks],
            "issues": [issue.as_dict() for issue in self.issues],
            "metrics": self.metrics,
            "declarations": self.declarations,
        }


def resolve_root(root_argument: str | None) -> Path:
    """解析根目录；未传参数时使用当前工作目录。"""

    return Path(root_argument).expanduser().resolve() if root_argument else Path.cwd().resolve()


def _iter_strings(value: Any) -> Iterator[str]:
    """递归获取字典/列表中的字符串。"""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _iter_strings(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _iter_strings(child)


def _looks_like_path(value: str) -> bool:
    """判断字符串是否像交付文件路径或 glob。"""

    value = value.strip().strip("`'\"").strip()
    if not value or value.startswith(("http://", "https://", "file://")):
        return False
    if "/" not in value and not PATH_SUFFIX_RE.search(value):
        return False
    return bool(PATH_SUFFIX_RE.search(value) or "/" in value or "\\" in value)


def _clean_declared_path(value: str) -> str | None:
    """从 manifest 单项中清除数量说明和 Markdown 标记。"""

    value = value.strip().strip("`'\"").strip()
    if not value or value.startswith(("http://", "https://", "file://")):
        return None
    # 处理“figures/*.svg (13 each)”等人类说明，只保留路径部分。
    match = re.match(r"(?:\./)?([^\s,;()]+\.(?:md|markdown|csv|bib|json|yaml|yml|tex|docx|pdf|svg|png|html?|py|js|mjs|java|sql)(?:\*)?)", value, re.I)
    if match:
        return match.group(1)
    if _looks_like_path(value) and not re.search(r"[\u4e00-\u9fff]", value):
        return value.rstrip("。；,;")
    return None


def _declared_paths(manifest: Any) -> list[str]:
    """提取 manifest 中真正表示交付文件的声明。

    仅扫描明确的文件清单字段，避免把模型名称、工作目录和能力说明误当成
    文件。`files_not_generated`、`sha256_inventory_excludes` 等字段是例外。
    """

    list_keys = {
        "artifacts",
        "required_files",
        "deliverables",
        "outputs",
        "output_files",
        "source_files",
        "final_files",
        "file_list",
    }
    map_keys = {
        "files",
        "file_inventory",
        "inventory",
        "sha256",
        "hashes",
        "checksums",
        "file_sha256",
    }
    found: list[str] = []

    def visit(value: Any, key: str | None = None) -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                lower = str(child_key).casefold()
                if any(token in lower for token in ("not_generated", "not-generated", "missing", "empty", "excludes")):
                    continue
                if lower in list_keys:
                    for item in _iter_strings(child_value):
                        # 一个值可能是“a.svg, b.png (各一张)”。
                        for part in re.split(r"[,;]\s*", item):
                            cleaned = _clean_declared_path(part)
                            if cleaned:
                                found.append(cleaned)
                    continue
                if lower in map_keys:
                    if isinstance(child_value, dict):
                        for map_key, map_value in child_value.items():
                            cleaned_key = _clean_declared_path(str(map_key))
                            if cleaned_key:
                                found.append(cleaned_key)
                            for item in _iter_strings(map_value):
                                cleaned_value = _clean_declared_path(item)
                                if cleaned_value and "/" in cleaned_value:
                                    found.append(cleaned_value)
                    else:
                        for item in _iter_strings(child_value):
                            cleaned = _clean_declared_path(item)
                            if cleaned:
                                found.append(cleaned)
                    continue
                visit(child_value, lower)
        elif isinstance(value, (list, tuple)) and key in list_keys:
            for item in value:
                cleaned = _clean_declared_path(str(item)) if isinstance(item, str) else None
                if cleaned:
                    found.append(cleaned)

    visit(manifest)
    result: list[str] = []
    seen: set[str] = set()
    for item in found:
        normalized = item.replace("\\", "/")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _path_exists(root: Path, declared: str) -> bool:
    """判断相对路径或 glob 声明是否命中项目内文件。"""

    candidate = Path(declared).expanduser()
    has_glob = any(char in declared for char in "*?[]")
    if candidate.is_absolute():
        if has_glob:
            return False
        try:
            resolved = candidate.resolve()
            resolved.relative_to(root.resolve())
        except ValueError:
            return False
        return resolved.is_file() or resolved.is_dir()
    if ".." in candidate.parts:
        return False
    pattern = root / candidate
    if has_glob:
        for path in root.glob(declared):
            try:
                path.resolve().relative_to(root.resolve())
            except ValueError:
                continue
            if path.is_file() or path.is_dir():
                return True
        return False
    try:
        resolved = pattern.resolve()
        resolved.relative_to(root.resolve())
    except ValueError:
        return False
    return resolved.is_file() or resolved.is_dir()


def _json_file(path: Path) -> Any:
    """读取 JSON 文件，兼容 UTF-8 BOM。"""

    return json.loads(path.read_text(encoding="utf-8-sig"))


def _first_status_in_manifest(manifest: dict[str, Any]) -> str | None:
    """按优先级读取 manifest 顶层状态。"""

    for key in ("overall_status", "final_status", "status", "state"):
        if key in manifest:
            status = _normalise_status(manifest[key])
            if status:
                return status
    return None


def _extract_numeric(value: Any) -> list[float]:
    """从数字或带逗号/范围的文本提取数字。"""

    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [float(value)]
    if not isinstance(value, str):
        return []
    values: list[float] = []
    for match in re.findall(r"\d[\d,]*(?:\.\d+)?", value):
        try:
            values.append(float(match.replace(",", "")))
        except ValueError:
            continue
    return values


def _manifest_body_declarations(manifest: dict[str, Any]) -> list[tuple[str, float]]:
    """提取可能代表正文体量的 manifest 声明。"""

    declarations: list[tuple[str, float]] = []

    def visit(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                lower = str(key).casefold()
                if any(token in lower for token in ("target", "min", "max", "reference", "figure", "table", "page", "byte", "sha")):
                    # 目标值、参考文献、图表、页数、字节数不是正文 CJK 体量。
                    if isinstance(child, (dict, list)):
                        visit(child, child_path)
                    continue
                if any(token in lower for token in ("word_count", "body_chars", "cjk", "chinese_chars", "body_length", "正文字符", "正文长度")):
                    numbers = _extract_numeric(child)
                    if isinstance(child, str) and len(numbers) >= 2 and "-" in child:
                        numbers = [sum(numbers[:2]) / 2]
                    if numbers:
                        declarations.append((child_path, numbers[0]))
                visit(child, child_path)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(manifest)
    # 同一字段可能在递归路径中被二次发现，保留第一次。
    result: list[tuple[str, float]] = []
    seen: set[tuple[str, float]] = set()
    for item in declarations:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _qa_body_declarations(text: str) -> list[tuple[str, float]]:
    """从 QA 中提取明确的正文/中文体量声明。"""

    result: list[tuple[str, float]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        lower = line.casefold()
        if not any(token in lower for token in ("正文", "中文", "cjk", "汉字", "字数", "字符数")):
            continue
        if any(token in lower for token in ("目标区间", "目标字数", "target_length")):
            # 目标不是实际测量值；但行首通常仍有“实际：N”，下面只取冒号后的首项。
            pass
        numbers = _extract_numeric(line)
        if not numbers:
            continue
        # 优先取“中文 21,568”或“CJK: 21,568”，否则取该行的首个数。
        marked = re.search(r"(?:中文|汉字|cjk|正文(?:字符数|字数|体量)?)\s*[:：=]?\s*(\d[\d,]*)", line, re.I)
        number = float(marked.group(1).replace(",", "")) if marked else numbers[0]
        # 低于 1000 的段落/章节编号不是体量。
        if number >= 1000:
            result.append((f"QA第{line_number}行", number))
    return result


def _compare_body_declarations(
    report: ValidationReport,
    full_text: str,
    manifest: dict[str, Any] | None,
    qa_text: str | None,
) -> None:
    """检查实际 CJK 体量与外部声明是否存在明显矛盾。"""

    actual = _count_cjk(full_text)
    report.metrics["body_cjk_chars"] = actual
    report.metrics["paper_full_bytes"] = len(full_text.encode("utf-8"))
    declarations: list[tuple[str, float]] = []
    if manifest:
        declarations.extend(_manifest_body_declarations(manifest))
    if qa_text:
        declarations.extend(_qa_body_declarations(qa_text))
    report.metrics["body_declarations"] = [
        {"source": source, "value": value} for source, value in declarations
    ]
    if actual <= 0:
        report.add_issue("body-empty", "07-paper-full.md 没有实际 CJK 正文内容", FAIL)
        return
    for source, declared in declarations:
        if declared <= 0:
            continue
        difference = abs(actual - declared) / max(actual, declared)
        # 允许 CJK 与 Word 总字符统计存在少量差异，超过 30% 或 5,000 字视为矛盾。
        if difference > 0.30 and abs(actual - declared) > 5000:
            report.add_issue(
                "body-count-mismatch",
                f"正文 CJK 实测 {actual} 与 {source} 声明 {int(declared)} 明显矛盾",
                FAIL,
                actual=actual,
                declared=declared,
                source=source,
                relative_difference=round(difference, 4),
            )


def _chapter_files(root: Path) -> list[Path]:
    """返回分章 Markdown 文件。"""

    chapter_dir = root / "chapters"
    if not chapter_dir.is_dir():
        return []
    return sorted(
        [
            path
            for path in chapter_dir.rglob("*")
            if path.is_file() and path.suffix.casefold() in {".md", ".markdown"}
        ],
        key=lambda path: path.as_posix().casefold(),
    )


def _body_without_references(text: str) -> str:
    """粗略去掉参考文献之后的部分，避免参考文献量污染正文统计。"""

    match = re.search(r"(?im)^\s*#{1,6}\s*(?:参考文献|参考资料|references)\s*$", text)
    return text[: match.start()] if match else text


def _check_integrated_paper(report: ValidationReport, root: Path) -> str | None:
    """检查 07 是否包含真实整合内容，而非分章链接。"""

    path = root / "07-paper-full.md"
    if not _is_nonempty_file(path):
        return None
    text = _read_text(path)
    body_text = _body_without_references(text)
    chapter_paths = _chapter_files(root)
    chapter_texts = [_read_text(item) for item in chapter_paths]
    chapter_cjk = sum(_count_cjk(item) for item in chapter_texts)
    full_cjk = _count_cjk(body_text)
    report.metrics["chapter_count"] = len(chapter_paths)
    report.metrics["chapter_cjk_chars"] = chapter_cjk
    report.metrics["body_cjk_chars_without_references"] = full_cjk

    pointer_hits: list[str] = []
    for pattern in POINTER_PATTERNS:
        pointer_hits.extend(match.group(0) for match in pattern.finditer(text))
    report.metrics["integration_pointer_hits"] = pointer_hits[:20]

    unsafe_local_paths = re.findall(
        r"(?:file://[^\s)]+|(?<![\w])/(?:Users|home|tmp|private/tmp)/[^\s)]+|[A-Za-z]:\\[^\s)]+)",
        text,
    )
    remote_images = re.findall(r"!\[[^\]]*\]\(https?://[^)]+\)", text, re.I)
    report.metrics["unsafe_local_path_count"] = len(unsafe_local_paths)
    report.metrics["remote_image_count"] = len(remote_images)
    if unsafe_local_paths:
        report.add_issue(
            "paper-local-paths",
            "07-paper-full.md 含本机绝对路径或 file:// 链接，终稿不可移植",
            FAIL,
            paths=unsafe_local_paths[:20],
        )
    if remote_images:
        report.add_issue(
            "paper-remote-images",
            "07-paper-full.md 含远程图片，终稿必须改为项目内嵌资源",
            FAIL,
            images=remote_images[:20],
        )

    if not chapter_paths:
        report.add_issue("chapters-missing", "缺少 chapters/ 分章源文件", FAIL)
    elif not any(_is_nonempty_file(item) for item in chapter_paths):
        report.add_issue("chapters-empty", "chapters/ 下没有非空分章源文件", FAIL)

    if full_cjk <= 0:
        report.add_issue("paper-full-empty", "07-paper-full.md 没有整合后的正文", FAIL)

    if chapter_cjk >= 500 and full_cjk < chapter_cjk * 0.50:
        report.add_issue(
            "paper-not-integrated",
            "07-paper-full.md 的正文体量远低于分章总量，疑似仅保留分章说明或文件链接",
            FAIL,
            body_cjk_chars=full_cjk,
            chapter_cjk_chars=chapter_cjk,
        )

    explicit_pointer = any(
        "详见分章" in hit or "完整内容" in hit or "file://" in hit
        for hit in pointer_hits
    )
    if explicit_pointer and (chapter_cjk == 0 or full_cjk < max(500, chapter_cjk * 0.75)):
        report.add_issue(
            "paper-pointer-only",
            "07-paper-full.md 含“详见分章/文件链接”式占位，未证明全文整合",
            FAIL,
            hits=pointer_hits[:20],
        )

    missing_sections = [
        name for name, pattern in REQUIRED_PAPER_SECTIONS.items() if not pattern.search(text)
    ]
    report.metrics["missing_paper_sections"] = missing_sections
    if missing_sections:
        report.add_issue(
            "paper-sections-missing",
            "07-paper-full.md 缺少终稿必需章节：" + "、".join(missing_sections),
            FAIL,
            sections=missing_sections,
        )

    # 若章节有标题，至少核对标题在全文中出现，防止只拼接一段摘要。
    missing_headings: list[str] = []
    for chapter_text in chapter_texts:
        match = HEADING_RE.search(chapter_text)
        if not match:
            continue
        heading = re.sub(r"[`*_]", "", match.group(1)).strip()
        if heading and heading not in text:
            missing_headings.append(heading[:80])
    if missing_headings and len(missing_headings) == len([item for item in chapter_texts if HEADING_RE.search(item)]):
        report.add_issue(
            "chapter-headings-not-integrated",
            "07-paper-full.md 未出现分章标题，无法证明章节已整合",
            FAIL,
            missing_headings=missing_headings[:20],
        )
    return text


def _check_source_files(report: ValidationReport, root: Path) -> tuple[str | None, dict[str, Any] | None]:
    """检查论文源文件、分章目录和图表清单。"""

    missing: list[str] = []
    empty: list[str] = []
    for filename in SOURCE_REQUIRED_FILES:
        path = root / filename
        if not path.is_file():
            missing.append(filename)
        elif path.stat().st_size <= 0:
            empty.append(filename)
    if missing:
        report.add_issue("source-missing", "缺少必需论文源文件：" + "、".join(missing), FAIL, files=missing)
    if empty:
        report.add_issue("source-empty", "论文源文件为空：" + "、".join(empty), FAIL, files=empty)

    chapter_paths = _chapter_files(root)
    if not chapter_paths:
        report.add_issue("chapters-missing", "缺少非空的 chapters/ 分章源文件", FAIL)

    figure_manifest: dict[str, Any] | list[Any] | None = None
    figure_path = root / "figures/figure-manifest.json"
    if figure_path.is_file() and figure_path.stat().st_size > 0:
        try:
            figure_manifest = _json_file(figure_path)
        except (OSError, ValueError, TypeError) as error:
            report.add_issue("figure-manifest-invalid", f"图表清单 JSON 无法解析：{error}", FAIL)

    full_text = _check_integrated_paper(report, root)
    if full_text is None and (root / "07-paper-full.md").is_file():
        full_text = _read_text(root / "07-paper-full.md")
    return full_text, figure_manifest if isinstance(figure_manifest, (dict, list)) else None


def _check_manifest(report: ValidationReport, root: Path, required: bool = True) -> dict[str, Any] | None:
    """解析运行清单并核对其中声明的文件。"""

    path = root / "run-manifest.json"
    if not path.is_file():
        if required:
            report.add_issue("manifest-missing", "缺少必需文件：run-manifest.json", FAIL)
        return None
    try:
        manifest = _json_file(path)
    except (OSError, ValueError, TypeError) as error:
        report.add_issue("manifest-invalid", f"run-manifest.json 无法解析：{error}", FAIL)
        return None
    if not isinstance(manifest, dict):
        report.add_issue("manifest-shape", "run-manifest.json 顶层必须是 JSON 对象", FAIL)
        return None
    report.declarations["manifest"] = _first_status_in_manifest(manifest)
    declared_mode = manifest.get("run_mode")
    report.metrics["manifest_run_mode"] = declared_mode
    if report.mode == "full":
        if declared_mode != "FULL_BUILD":
            report.add_issue(
                "manifest-run-mode",
                "full 验收要求 run-manifest.json 明确记录 run_mode=FULL_BUILD",
                FAIL,
                declared=declared_mode,
            )

    declared = _declared_paths(manifest)
    missing = [item for item in declared if not _path_exists(root, item)]
    report.metrics["manifest_declared_files"] = declared
    report.metrics["manifest_missing_files"] = missing
    if missing:
        report.add_issue(
            "manifest-files-missing",
            "manifest 声明的文件未真实存在：" + "、".join(missing),
            FAIL,
            files=missing,
        )
    return manifest


def _check_docx(report: ValidationReport, root: Path) -> dict[str, Any]:
    """用 ZIP/XML 结构检查 DOCX，不依赖 python-docx。"""

    path = root / "final-paper.docx"
    result: dict[str, Any] = {"path": "final-paper.docx", "exists": path.is_file()}
    if not path.is_file():
        report.add_issue("docx-missing", "缺少最终文档：final-paper.docx", FAIL)
        report.add_check("docx", FAIL, "final-paper.docx 不存在", **result)
        return result
    try:
        result["bytes"] = path.stat().st_size
    except OSError:
        result["bytes"] = 0
    if result["bytes"] <= 0:
        report.add_issue("docx-empty", "final-paper.docx 为空", FAIL)
        report.add_check("docx", FAIL, "DOCX 为空", **result)
        return result
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            names = set(archive.namelist())
            result["zip_entries"] = len(names)
            if bad_member:
                raise ValueError(f"ZIP 成员损坏：{bad_member}")
            required_names = {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}
            missing = sorted(required_names - names)
            if missing:
                raise ValueError("缺少 DOCX 结构成员：" + "、".join(missing))
            root_xml = ElementTree.fromstring(archive.read("[Content_Types].xml"))
            rels_xml = ElementTree.fromstring(archive.read("_rels/.rels"))
            document_xml = ElementTree.fromstring(archive.read("word/document.xml"))
            if root_xml.tag.rsplit("}", 1)[-1] != "Types":
                raise ValueError("[Content_Types].xml 根元素不是 Types")
            overrides = [
                element.attrib.get("PartName")
                for element in root_xml.iter()
                if element.tag.rsplit("}", 1)[-1] == "Override"
            ]
            if "/word/document.xml" not in overrides:
                raise ValueError("[Content_Types].xml 未声明 /word/document.xml")
            if rels_xml.tag.rsplit("}", 1)[-1] != "Relationships":
                raise ValueError("_rels/.rels 根元素不是 Relationships")
            targets = [
                element.attrib.get("Target")
                for element in rels_xml.iter()
                if element.tag.rsplit("}", 1)[-1] == "Relationship"
            ]
            if "word/document.xml" not in targets:
                raise ValueError("_rels/.rels 未关联 word/document.xml")
            if document_xml.tag.rsplit("}", 1)[-1] != "document":
                raise ValueError("word/document.xml 根元素不是 document")
            text = "".join(document_xml.itertext()).strip()
            if not text:
                raise ValueError("word/document.xml 没有正文文本")
            result["text_chars"] = len(text)
            result["images"] = len([name for name in names if name.startswith("word/media/")])
            result["tables"] = sum(1 for element in document_xml.iter() if element.tag.rsplit("}", 1)[-1] == "tbl")
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError, ValueError) as error:
        result["error"] = str(error)
        report.add_issue("docx-invalid", f"final-paper.docx ZIP/XML 校验失败：{error}", FAIL)
        report.add_check("docx", FAIL, "DOCX 结构校验失败", **result)
        return result
    report.add_check("docx", PASS, "DOCX ZIP/XML 结构校验通过", **result)
    return result


def _pdf_page_count(path: Path) -> tuple[int | None, str]:
    """优先用 pdfinfo 真实解析页数；无工具时才做轻量对象计数。"""

    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        try:
            completed = subprocess.run(
                [pdfinfo, str(path)],
                check=False,
                capture_output=True,
                text=True,
                timeout=8,
            )
            match = re.search(r"(?im)^Pages:\s*(\d+)\s*$", completed.stdout)
            if match:
                return int(match.group(1)), "pdfinfo"
            return None, "pdfinfo-failed"
        except (OSError, subprocess.SubprocessError):
            return None, "pdfinfo-failed"
    try:
        data = path.read_bytes()
    except OSError:
        return None, "fallback-failed"
    matches = re.findall(rb"/Type\s*/Page(?:\s|/|>)", data)
    return (len(matches) or None), "fallback"


def _check_pdf(report: ValidationReport, root: Path) -> dict[str, Any]:
    """检查 PDF 非空和签名，并尽可能记录页数。"""

    path = root / "final-paper.pdf"
    result: dict[str, Any] = {"path": "final-paper.pdf", "exists": path.is_file()}
    if not path.is_file():
        report.add_issue("pdf-missing", "缺少最终文档：final-paper.pdf", FAIL)
        report.add_check("pdf", FAIL, "final-paper.pdf 不存在", **result)
        return result
    try:
        data = path.read_bytes()
        result["bytes"] = len(data)
        signature = data[:5]
    except OSError as error:
        result["error"] = str(error)
        report.add_issue("pdf-read-error", f"无法读取 final-paper.pdf：{error}", FAIL)
        report.add_check("pdf", FAIL, "PDF 无法读取", **result)
        return result
    result["signature"] = signature.decode("ascii", errors="replace")
    if result["bytes"] < 100:
        report.add_issue("pdf-too-small", "final-paper.pdf 过小，不能证明是完整 PDF", FAIL)
    elif signature != b"%PDF-":
        report.add_issue("pdf-signature", "final-paper.pdf 缺少 %PDF- 文件签名", FAIL)
    elif b"%%EOF" not in data[-2048:]:
        report.add_issue("pdf-eof-missing", "final-paper.pdf 缺少结束标记 %%EOF", FAIL)
    if result["bytes"] >= 100 and signature == b"%PDF-":
        result["pages"], result["page_check_method"] = _pdf_page_count(path)
        if not result["pages"] or result["pages"] <= 0:
            report.add_issue("pdf-pages-missing", "无法确认 final-paper.pdf 含有至少一页", FAIL)
        elif result["page_check_method"] == "fallback":
            report.add_issue(
                "pdf-parser-gap",
                "未找到 pdfinfo，仅完成轻量页对象检查，不能替代真实 PDF 解析",
                PARTIAL,
            )
    pdf_issues = [issue for issue in report.issues if issue.code.startswith("pdf-")]
    if any(issue.severity == FAIL for issue in pdf_issues):
        report.add_check("pdf", FAIL, "PDF 基础校验失败", **result)
    elif pdf_issues:
        report.add_check("pdf", PARTIAL, "PDF 基础结构通过，但缺少完整解析工具", **result)
    else:
        report.add_check("pdf", PASS, "PDF 签名和非空校验通过", **result)
    report.metrics["pdf_pages"] = result.get("pages")
    return result


def _figure_count_from_manifest(value: Any) -> int | None:
    """取得图表清单中的图数。"""

    if isinstance(value, list):
        return len(value)
    if not isinstance(value, dict):
        return None
    for key in ("figures", "items", "entries", "assets"):
        child = value.get(key)
        if isinstance(child, list):
            return len(child)
    for key in ("figures_count", "figure_count", "count", "total"):
        numbers = _extract_numeric(value.get(key))
        if numbers:
            return int(numbers[0])
    return None


def _figure_manifest_files(value: Any) -> list[str]:
    """提取图表清单中声明的本地文件名。"""

    keys = {"filename", "file", "svg_file", "png_file", "html_file", "source_file"}
    found: list[str] = []

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if str(key).casefold() in keys and isinstance(child, str) and child.strip():
                    found.append(child.strip())
                else:
                    visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    return list(dict.fromkeys(found))


def _manifest_declared_count(manifest: dict[str, Any] | None) -> int | None:
    """读取运行清单中的图数声明。"""

    if not manifest:
        return None
    candidates: list[tuple[str, Any]] = []

    def visit(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                lower = str(key).casefold()
                child_path = f"{path}.{key}" if path else str(key)
                if "figure" in lower and any(token in lower for token in ("count", "total", "number")):
                    candidates.append((child_path, child))
                visit(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(manifest)
    for path, value in candidates:
        numbers = _extract_numeric(value)
        if numbers:
            return int(numbers[0])
    return None


def _qa_figure_count(text: str | None) -> int | None:
    """从 QA 中读取带数量语义的图数。"""

    if not text:
        return None
    patterns = (
        re.compile(r"(?:图表|图片|图|figures?|figure)\s*(?:数量|总数|数|count)?\s*[:：=]\s*(\d+)", re.I),
        re.compile(r"(?:图表|图片|图)\s*\|\s*(\d+)\b", re.I),
        re.compile(r"(?:共|包含|含有)\s*(\d+)\s*(?:张图|幅图|个图|figures?)", re.I),
        re.compile(r"\b(\d+)\s*张[^\n|]{0,30}(?:SVG|图)", re.I),
    )
    for line in text.splitlines():
        if "figures/" in line.casefold() or "figure-manifest" in line.casefold():
            continue
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return int(match.group(1))
    return None


def _check_figures(
    report: ValidationReport,
    root: Path,
    run_manifest: dict[str, Any] | None = None,
    qa_text: str | None = None,
) -> dict[str, Any]:
    """统计 SVG/PNG 并核对图表清单。"""

    figure_dir = root / "figures"
    result: dict[str, Any] = {"directory": "figures", "exists": figure_dir.is_dir()}
    if not figure_dir.is_dir():
        report.add_issue("figures-missing", "缺少 figures/ 图表目录", FAIL)
        report.add_check("figures", FAIL, "figures/ 不存在", **result)
        return result
    svg_paths = sorted(path for path in figure_dir.rglob("*") if path.is_file() and path.suffix.casefold() == ".svg")
    png_paths = sorted(path for path in figure_dir.rglob("*") if path.is_file() and path.suffix.casefold() == ".png")
    result.update({"svg_count": len(svg_paths), "png_count": len(png_paths)})
    report.metrics["svg_count"] = len(svg_paths)
    report.metrics["png_count"] = len(png_paths)
    if not svg_paths and not png_paths:
        report.add_issue("figures-empty", "figures/ 下没有 SVG 或 PNG 图文件", FAIL)

    figure_manifest_path = figure_dir / "figure-manifest.json"
    figure_manifest: Any | None = None
    if not figure_manifest_path.is_file():
        report.add_issue("figure-manifest-missing", "缺少 figures/figure-manifest.json", FAIL)
    else:
        try:
            figure_manifest = _json_file(figure_manifest_path)
        except (OSError, ValueError, TypeError) as error:
            report.add_issue("figure-manifest-invalid", f"图表清单 JSON 无法解析：{error}", FAIL)
    expected = _figure_count_from_manifest(figure_manifest)
    declared_files = _figure_manifest_files(figure_manifest)
    missing_declared_files: list[str] = []
    for declared_file in declared_files:
        candidate = Path(declared_file)
        if candidate.parts and candidate.parts[0].casefold() == "figures":
            candidate = Path(*candidate.parts[1:])
        if candidate.is_absolute() or ".." in candidate.parts:
            missing_declared_files.append(declared_file)
            continue
        resolved = (figure_dir / candidate).resolve()
        try:
            resolved.relative_to(figure_dir.resolve())
        except ValueError:
            missing_declared_files.append(declared_file)
            continue
        if not resolved.is_file():
            missing_declared_files.append(declared_file)
    result["declared_files"] = declared_files
    result["missing_declared_files"] = missing_declared_files
    if missing_declared_files:
        report.add_issue(
            "figure-manifest-files-missing",
            "图表清单声明的文件不存在或越出 figures/：" + "、".join(missing_declared_files),
            FAIL,
            files=missing_declared_files,
        )
    run_declared = _manifest_declared_count(run_manifest)
    qa_declared = _qa_figure_count(qa_text)
    result.update({"figure_manifest_count": expected, "manifest_count": run_declared, "qa_count": qa_declared})
    report.metrics["figure_manifest_count"] = expected
    if expected is not None and len(svg_paths) != expected:
        report.add_issue(
            "svg-count-mismatch",
            f"SVG 实际数量 {len(svg_paths)} 与图表清单声明 {expected} 不一致",
            FAIL,
            actual=len(svg_paths),
            declared=expected,
        )
    if expected is not None and len(png_paths) != expected:
        report.add_issue(
            "png-count-mismatch",
            f"PNG 实际数量 {len(png_paths)} 与图表清单声明 {expected} 不一致",
            PARTIAL,
            actual=len(png_paths),
            declared=expected,
        )
    if run_declared is not None and len(svg_paths) != run_declared:
        report.add_issue(
            "manifest-figure-count-mismatch",
            f"SVG 实际数量 {len(svg_paths)} 与 run-manifest 图数 {run_declared} 不一致",
            FAIL,
            actual=len(svg_paths),
            declared=run_declared,
        )
    if qa_declared is not None and len(svg_paths) != qa_declared:
        report.add_issue(
            "qa-figure-count-mismatch",
            f"SVG 实际数量 {len(svg_paths)} 与 QA 图数 {qa_declared} 不一致",
            FAIL,
            actual=len(svg_paths),
            declared=qa_declared,
        )
    if len(svg_paths) != len(png_paths):
        report.add_issue(
            "figure-format-gap",
            f"SVG/PNG 数量不一致：SVG {len(svg_paths)}、PNG {len(png_paths)}",
            PARTIAL,
            svg=len(svg_paths),
            png=len(png_paths),
        )
    if not any(issue.code.startswith("figures-") or issue.code.endswith("count-mismatch") or issue.code == "figure-manifest-missing" for issue in report.issues):
        report.add_check("figures", PASS, "SVG/PNG 数量和图表清单校验通过", **result)
    else:
        check_status = FAIL if any(issue.severity == FAIL and (issue.code.startswith("figures-") or "figure" in issue.code) for issue in report.issues) else PARTIAL
        report.add_check("figures", check_status, "图表数量或清单存在问题", **result)
    return result


def _check_docx_figure_embedding(
    report: ValidationReport,
    docx_result: dict[str, Any],
    figure_result: dict[str, Any],
) -> None:
    """核对最终 DOCX 是否实际嵌入计划图，而非只在磁盘生成图片。"""

    expected = figure_result.get("figure_manifest_count")
    embedded = docx_result.get("images")
    if not docx_result.get("exists") or not isinstance(embedded, int):
        return
    if isinstance(expected, int) and expected > 0:
        if not isinstance(embedded, int) or embedded < expected:
            report.add_issue(
                "docx-figures-missing",
                f"DOCX 实际嵌入图片 {embedded or 0} 张，少于图表清单 {expected} 张",
                FAIL,
                embedded=embedded or 0,
                expected=expected,
            )


def _parse_qa_status(text: str) -> str | None:
    """提取 QA 的最终状态，而不是正文中偶然出现的 PASS。"""

    patterns = (
        r"(?:最终状态|最终交付状态|综合质量验收判定|验收结论|总体状态)[^\n]{0,80}",
        r"(?:final\s+status|overall\s+status)[^\n]{0,80}",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            status = _normalise_status(match.group(0))
            if status:
                return status
    return None


def _check_qa(report: ValidationReport, root: Path) -> str | None:
    """检查 QA 文件存在、可读、未留有 Critical/Important 未关闭项。"""

    path = root / "12-final-qa-report.md"
    if not _is_nonempty_file(path):
        report.add_issue("qa-missing", "缺少必需文件：12-final-qa-report.md", FAIL)
        return None
    text = _read_text(path)
    report.declarations["qa"] = _parse_qa_status(text)
    report.metrics["qa_mtime"] = _iso_timestamp(path.stat().st_mtime)
    critical_open = _open_issue_count(text, "critical")
    important_open = _open_issue_count(text, "important")
    report.metrics["qa_critical_open"] = critical_open
    report.metrics["qa_important_open"] = important_open
    if critical_open > 0:
        report.add_issue("qa-critical-open", f"QA 声明仍有 {critical_open} 个 Critical 问题未关闭", FAIL)
    if important_open > 0:
        report.add_issue("qa-important-open", f"QA 声明仍有 {important_open} 个 Important 问题未关闭", FAIL)
    return text


def _open_issue_count(text: str, label: str) -> int:
    """解析 QA 中 Critical/Important 的未关闭数量。"""

    count = 0
    pattern = re.compile(
        rf"(?:{label}|{label.capitalize()})(?:\s*问题|_issues?|\s*issues?|\s*open|\s*未关闭)?\s*[:：=]?\s*(\d+)",
        re.I,
    )
    for match in pattern.finditer(text):
        value = int(match.group(1))
        if value > count:
            count = value
    # 兼容“Critical/Important 未解决问题均为 0”式写法，不产生误报。
    if count == 0:
        return 0
    return count


def _check_qa_timestamp(report: ValidationReport, root: Path) -> None:
    """确保 QA 文件晚于章节、图和最终文档。"""

    qa_path = root / "12-final-qa-report.md"
    if not _is_nonempty_file(qa_path):
        return
    try:
        qa_ns = qa_path.stat().st_mtime_ns
    except OSError:
        return
    candidates: list[Path] = []
    candidates.extend(_chapter_files(root))
    candidates.extend(
        path
        for path in (root / "figures").rglob("*")
        if path.is_file() and path.suffix.casefold() in {".svg", ".png", ".html", ".json"}
    ) if (root / "figures").is_dir() else None
    candidates.extend(root / filename for filename in ("07-paper-full.md", "final-paper.docx", "final-paper.pdf"))
    candidates.extend(
        root / filename
        for filename in SOURCE_REQUIRED_FILES
        if filename != "07-paper-full.md"
    )
    candidates.extend(root / filename for filename in ("evidence-manifest.json", "run-manifest.json"))
    candidates = list(dict.fromkeys(candidates))
    stale: list[str] = []
    newest_path: Path | None = None
    newest_ns = -1
    for path in candidates:
        if not path.is_file():
            continue
        try:
            item_ns = path.stat().st_mtime_ns
        except OSError:
            continue
        if item_ns > newest_ns:
            newest_ns, newest_path = item_ns, path
        if qa_ns <= item_ns:
            stale.append(_relative(root, path))
    report.metrics["qa_mtime"] = _iso_timestamp(qa_ns / 1_000_000_000)
    report.metrics["latest_artifact"] = _relative(root, newest_path) if newest_path else None
    report.metrics["latest_artifact_mtime"] = _iso_timestamp(newest_ns / 1_000_000_000) if newest_ns >= 0 else None
    if stale:
        report.add_issue(
            "qa-time-order",
            "QA 时间必须晚于章节、图和最终文档；发现较晚产物：" + "、".join(stale),
            FAIL,
            stale_files=stale,
        )


def _check_evidence_manifest(report: ValidationReport, root: Path) -> None:
    """运行证据清单校验，并将失败并入最终状态。"""

    manifest = root / "evidence-manifest.json"
    evidence_report = evidence_validator.validate_manifest(root, manifest)
    report.metrics["evidence_manifest_entries"] = evidence_report.entry_count
    report.metrics["evidence_validation_status"] = evidence_report.status
    if evidence_report.status == evidence_validator.STATUS_FAIL:
        for error in evidence_report.errors:
            report.add_issue("evidence-invalid", error, FAIL)
        report.add_check(
            "evidence",
            FAIL,
            "evidence-manifest.json 未通过证据边界与哈希校验",
            manifest=str(manifest),
        )
    else:
        report.add_check(
            "evidence",
            PASS,
            "evidence-manifest.json 校验通过",
            manifest=str(manifest),
        )


def _add_declaration_conflicts(report: ValidationReport) -> None:
    """终验收要求 manifest 与 QA 声明严格等于脚本计算状态。"""

    if report.phase != "final" or report.mode != "full":
        return
    computed = report.status
    for name, status in report.declarations.items():
        if status != computed:
            report.add_issue(
                "declared-status-conflict",
                f"{name} 声明 {status or '缺失'}，但终验收计算状态为 {computed}",
                FAIL,
                declared=status,
                computed=computed,
                source=name,
            )


def validate(
    root: Path | str,
    mode: str = "full",
    phase: str = "final",
) -> ValidationReport:
    """执行指定模式的交付验收。"""

    if mode not in MODE_ALIASES:
        raise ValueError(f"不支持的验收模式：{mode}")
    if phase not in {"preqa", "final"}:
        raise ValueError(f"不支持的验收阶段：{phase}")
    mode = MODE_ALIASES[mode]
    resolved_root = Path(root).expanduser().resolve()
    report = ValidationReport(resolved_root, mode, phase)
    if not resolved_root.is_dir():
        report.add_issue("root-missing", f"项目根目录不存在：{resolved_root}", FAIL)
        return report

    run_manifest: dict[str, Any] | None = None
    qa_text: str | None = None
    if mode in {"full", "source"}:
        full_text, _ = _check_source_files(report, resolved_root)
        if full_text is None and (resolved_root / "07-paper-full.md").is_file():
            full_text = _read_text(resolved_root / "07-paper-full.md")
        if mode == "full":
            run_manifest = _check_manifest(report, resolved_root, required=True)
            if phase == "final":
                qa_text = _check_qa(report, resolved_root)
            _check_evidence_manifest(report, resolved_root)
            docx_result = _check_docx(report, resolved_root)
            _check_pdf(report, resolved_root)
            if full_text is not None:
                _compare_body_declarations(report, _body_without_references(full_text), run_manifest, qa_text)
            figure_result = _check_figures(report, resolved_root, run_manifest, qa_text)
            _check_docx_figure_embedding(report, docx_result, figure_result)
            if phase == "final":
                _check_qa_timestamp(report, resolved_root)
        elif (resolved_root / "run-manifest.json").is_file():
            # source 模式不要求运行清单，但存在时仍核对它的声明。
            run_manifest = _check_manifest(report, resolved_root, required=False)
    else:
        _check_figures(report, resolved_root)

    _add_declaration_conflicts(report)
    return report


def validate_delivery(
    root: Path | str,
    mode: str = "full",
    phase: str = "final",
) -> ValidationReport:
    """兼容调用方的语义化函数名。"""

    return validate(root, mode, phase)


def _human_report(report: ValidationReport) -> str:
    """生成中文可读报告。"""

    lines = [
        f"交付验收结果：{report.status}",
        f"模式：{report.mode}",
        f"阶段：{report.phase}",
        f"根目录：{report.root}",
        f"退出码：{report.exit_code}",
    ]
    for check in report.checks:
        lines.append(f"[{check.status}] {check.name}：{check.message}")
    if report.issues:
        lines.append("问题：")
        for issue in report.issues:
            lines.append(f"- [{issue.severity}] {issue.message}")
    else:
        lines.append("问题：无")
    if report.metrics:
        lines.append("关键指标：")
        for key, value in report.metrics.items():
            if key in {"manifest_declared_files", "body_declarations", "integration_pointer_hits"}:
                continue
            lines.append(f"- {key}：{value}")
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="论文交付 P0 验收器")
    parser.add_argument("--root", help="论文交付目录，默认使用当前目录")
    parser.add_argument(
        "--mode",
        default="full",
        choices=("full", "source", "figures", "FULL_BUILD", "AUDIT_ONLY", "FIGURES_ONLY"),
        help="验收范围：full/source/figures，或 Skill 模式 FULL_BUILD/AUDIT_ONLY/FIGURES_ONLY",
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    parser.add_argument(
        "--phase",
        choices=("preqa", "final"),
        default="final",
        help="preqa 在生成 QA 前计算状态；final 在写入 QA/manifest 状态后执行终验收",
    )
    parser.add_argument("--output", help="将同样的报告写入指定文件")
    return parser


def _write_output(path_argument: str, content: str, root: Path) -> None:
    """只在论文项目根目录内写入验收报告。"""

    path = Path(path_argument).expanduser()
    path = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"验收报告输出路径越出项目根目录：{path}") from error
    if path.exists() and path.is_dir():
        path = path / ("delivery-validation.json" if content.lstrip().startswith("{") else "delivery-validation.txt")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""

    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    try:
        report = validate(root, args.mode, args.phase)
        content = (
            json.dumps(report.as_dict(), ensure_ascii=False, indent=2) + "\n"
            if args.json
            else _human_report(report)
        )
        if args.output:
            _write_output(args.output, content, root)
        print(content, end="")
        return report.exit_code
    except (OSError, ValueError, TypeError) as error:
        # 保持失败行为稳定，不把内部 traceback 泄露给调用方。
        if args.json:
            payload = {"status": FAIL, "mode": args.mode, "phase": args.phase, "root": str(root), "exit_code": EXIT_CODES[FAIL], "error": str(error)}
            content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        else:
            content = f"交付验收结果：FAIL\n错误：{error}\n"
        try:
            if args.output:
                _write_output(args.output, content, root)
        except OSError:
            pass
        print(content, end="", file=sys.stderr if args.json else sys.stdout)
        return EXIT_CODES[FAIL]


if __name__ == "__main__":
    raise SystemExit(main())
