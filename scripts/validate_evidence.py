#!/usr/bin/env python3
"""校验证据清单，防止把模拟或计划内容写成真实系统结果。

清单文件默认是项目根目录下的 ``evidence-manifest.json``，顶层使用
``{"entries": [...]}``。为便于脚本调用，也兼容顶层直接使用条目数组。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


# 稳定退出码：0 表示清单通过，1 表示清单无效；参数解析仍由 argparse 使用 2。
EXIT_PASS = 0
EXIT_FAIL = 1

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

EVIDENCE_LEVELS = (
    "OBSERVED_REAL_SYSTEM",
    "SIMULATED",
    "SYNTHETIC_DATA",
    "HARDCODED_EXAMPLE",
    "VERIFIED_EXTERNAL",
    "PLANNED",
)

REQUIRED_FIELDS = (
    "id",
    "claim",
    "evidence_level",
    "sources",
    "command",
    "outputs",
    "sha256",
    "limitations",
)

# 模拟、合成和硬编码条目不能用这些词把内容包装为真实运行结果。
REAL_ASSERTION_PATTERNS = (
    re.compile(r"真实(?:系统|生产环境|生产|用户|数据|结果|运行|环境)"),
    re.compile(r"实际(?:系统|生产环境|生产|用户|数据|结果|运行|测量|环境)"),
    re.compile(r"线上(?:真实|实际|生产)"),
    re.compile(r"(?:已|已经)(?:部署|上线|验证|运行|实测)"),
    re.compile(r"(?:实测|观测到|观察到|测得|实验证明|生产数据)"),
    re.compile(
        r"\b(?:real|production|live|observed)\s+(?:system|result|data|user|environment)\b",
        re.IGNORECASE,
    ),
)

# 说明“并非真实结果”的否定语境必须允许，避免把合规免责声明判成违规。
REAL_NEGATION_PATTERNS = (
    re.compile(
        r"(?:不|非|未|无|并非|不是|不能|不可|不代表|不等于|仅为|仅用于|仅作).{0,12}"
        r"(?:真实系统|真实结果|真实数据|生产环境|实际结果|线上结果)"
    ),
)

NON_APPLICABLE_HASHES = {"N/A", "NA", "NOT_APPLICABLE", "不适用", "未计算"}
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


class EvidenceValidationReport:
    """收集全部校验问题，避免修复时只能看到第一个错误。"""

    def __init__(self, manifest: Path) -> None:
        self.manifest = manifest
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.entry_count = 0

    @property
    def status(self) -> str:
        """返回稳定的 PASS/FAIL 状态。"""

        return STATUS_FAIL if self.errors else STATUS_PASS

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def as_dict(self) -> dict[str, Any]:
        """转成 CLI JSON 使用的稳定结构。"""

        return {
            "status": self.status,
            "manifest": str(self.manifest),
            "entry_count": self.entry_count,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def resolve_root(root_argument: str | os.PathLike[str] | None) -> Path:
    """解析项目根目录；不传时使用本脚本所属 Skill 根目录。"""

    if root_argument is None:
        return Path(__file__).resolve().parents[1]
    return Path(root_argument).expanduser().resolve()


def resolve_manifest(root: Path, manifest_argument: str | os.PathLike[str] | None) -> Path:
    """解析清单路径，默认使用项目根目录下的 evidence-manifest.json。"""

    if manifest_argument is None:
        resolved = (root / "evidence-manifest.json").resolve()
    else:
        manifest = Path(manifest_argument).expanduser()
        resolved = manifest.resolve() if manifest.is_absolute() else (root / manifest).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"证据清单路径越出项目根目录：{resolved}") from error
    return resolved


def _as_sequence(value: Any, field: str, report: EvidenceValidationReport, index: int) -> list[Any]:
    """将常见的单值写法统一成列表；缺失或类型错误由调用者继续处理。"""

    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    if value is None:
        return []
    report.add_error(f"条目 {index} 的 {field} 必须是列表或非空字符串")
    return []


def _is_nonempty_string(value: Any) -> bool:
    """判断值是否是去空白后非空的字符串。"""

    return isinstance(value, str) and bool(value.strip())


def _output_path(root: Path, value: Any) -> tuple[str | None, Path | None]:
    """解析 outputs 中的路径写法，兼容 ``{"path": ...}``。"""

    if isinstance(value, str) and value.strip():
        raw = value.strip()
    elif isinstance(value, dict):
        raw_value = value.get("path", value.get("file"))
        if not isinstance(raw_value, str) or not raw_value.strip():
            return None, None
        raw = raw_value.strip()
    else:
        return None, None
    path = Path(raw).expanduser()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return raw, None
    return raw, resolved


def sha256_file(path: Path) -> str:
    """以分块方式计算文件 SHA-256。"""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalise_hashes(value: Any, report: EvidenceValidationReport, index: int) -> dict[str, str]:
    """把 sha256 字段统一成路径到摘要的映射。"""

    if isinstance(value, dict):
        result: dict[str, str] = {}
        for key, digest in value.items():
            if not isinstance(key, str):
                report.add_error(f"条目 {index} 的 sha256 键必须是字符串")
                continue
            if not isinstance(digest, str):
                report.add_error(f"条目 {index} 的 sha256[{key}] 必须是字符串")
                continue
            result[key] = digest.strip()
        return result
    if isinstance(value, str):
        digest = value.strip()
        return {"__single__": digest} if digest else {}
    if isinstance(value, list):
        result = {}
        for item in value:
            if isinstance(item, dict):
                key = item.get("path", item.get("file"))
                digest = item.get("sha256", item.get("hash"))
                if isinstance(key, str) and isinstance(digest, str):
                    result[key] = digest.strip()
                else:
                    report.add_error(f"条目 {index} 的 sha256 列表项必须含 path 和 sha256")
            elif isinstance(item, str):
                # 无路径的单项摘要只在单输出时有意义。
                result.setdefault("__single__", item.strip())
            else:
                report.add_error(f"条目 {index} 的 sha256 列表项格式无效")
        return result
    if value is None:
        return {}
    report.add_error(f"条目 {index} 的 sha256 必须是对象、字符串或列表")
    return {}


def _match_digest(
    raw_output: str,
    output_path: Path,
    hashes: dict[str, str],
) -> str | None:
    """从摘要映射中按相对路径、绝对路径或文件名匹配摘要。"""

    candidates = (raw_output, output_path.as_posix(), output_path.name)
    for candidate in candidates:
        if candidate in hashes:
            return hashes[candidate]
    if len(hashes) == 1 and "__single__" in hashes:
        return hashes["__single__"]
    return None


def _validate_hash_format(
    hashes: dict[str, str],
    report: EvidenceValidationReport,
    index: int,
    strict: bool,
) -> None:
    """校验摘要格式；非观察类允许显式写不适用。"""

    for key, digest in hashes.items():
        if not digest:
            if strict:
                report.add_error(f"条目 {index} 的 sha256[{key}] 不能为空")
            continue
        if not strict and digest.upper() in NON_APPLICABLE_HASHES:
            continue
        if not SHA256_PATTERN.fullmatch(digest):
            report.add_error(f"条目 {index} 的 sha256[{key}] 不是有效的 SHA-256 摘要")


def _command_argv(value: Any, report: EvidenceValidationReport, index: int, field: str) -> list[str]:
    """把清单或执行记录中的命令统一解析成参数数组。"""

    if isinstance(value, list):
        if not value or any(not isinstance(item, str) or not item for item in value):
            report.add_error(f"条目 {index} 的 {field} 必须是非空字符串参数列表")
            return []
        return list(value)
    if isinstance(value, str):
        if not value.strip():
            return []
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError as error:
            report.add_error(f"条目 {index} 的 {field} 无法解析：{error}")
            return []
        if not parsed:
            report.add_error(f"条目 {index} 的 {field} 不能为空")
        return parsed
    report.add_error(f"条目 {index} 的 {field} 必须是命令字符串或参数列表")
    return []


def _record_path(root: Path, value: Any) -> tuple[str | None, Path | None]:
    """解析执行记录路径，并复用项目内路径边界检查。"""

    return _output_path(root, value)


def _load_execution_record(
    root: Path,
    entry: dict[str, Any],
    index: int,
    report: EvidenceValidationReport,
) -> dict[str, Any] | None:
    """读取并检查观察证据对应的执行记录 JSON。"""

    raw_record, record_path = _record_path(root, entry.get("execution_record"))
    if raw_record is None or record_path is None:
        report.add_error(
            f"条目 {index}（{entry.get('id', '?')}）必须提供项目内 execution_record 路径"
        )
        return None
    if not record_path.is_file():
        report.add_error(
            f"条目 {index}（{entry.get('id', '?')}）的 execution_record 不存在：{raw_record}"
        )
        return None
    try:
        data = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        report.add_error(
            f"条目 {index}（{entry.get('id', '?')}）的 execution_record 无法读取：{error}"
        )
        return None
    if not isinstance(data, dict):
        report.add_error(
            f"条目 {index}（{entry.get('id', '?')}）的 execution_record 必须是 JSON 对象"
        )
        return None
    data["_record_path_internal"] = str(record_path)
    return data


def _validate_execution_record(
    root: Path,
    entry: dict[str, Any],
    index: int,
    hashes: dict[str, str],
    parsed_outputs: list[tuple[str, Path]],
    record: dict[str, Any] | None,
    report: EvidenceValidationReport,
) -> None:
    """核对执行记录与清单命令、输出路径、摘要及成功状态。"""

    if record is None:
        return
    entry_id = entry.get("id", "?")
    if record.get("id") != entry_id:
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record.id 与 manifest 不一致")
    if record.get("claim") != entry.get("claim"):
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record.claim 与 manifest 不一致")
    required_strings = ("run_id", "started_at", "finished_at", "cwd", "output_log")
    for field in required_strings:
        if not isinstance(record.get(field), str) or not record[field].strip():
            report.add_error(f"条目 {index}（{entry_id}）的 execution_record 缺少有效 {field}")
    started: datetime | None = None
    finished: datetime | None = None
    try:
        started = datetime.fromisoformat(str(record.get("started_at", "")).replace("Z", "+00:00"))
        finished = datetime.fromisoformat(str(record.get("finished_at", "")).replace("Z", "+00:00"))
        if finished < started:
            report.add_error(f"条目 {index}（{entry_id}）的 execution_record 时间顺序无效")
    except ValueError:
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record 时间格式无效")

    manifest_command = _command_argv(entry.get("command"), report, index, "command")
    record_command_value = record.get("command_argv", record.get("command"))
    record_command = _command_argv(record_command_value, report, index, "execution_record.command")
    if manifest_command and record_command and manifest_command != record_command:
        report.add_error(
            f"条目 {index}（{entry_id}）的 execution_record 命令与 manifest command 不一致"
        )
    if "command_argv" in record and "command" in record:
        command_alias = _command_argv(record.get("command"), report, index, "execution_record.command")
        if record_command and command_alias and record_command != command_alias:
            report.add_error(
                f"条目 {index}（{entry_id}）的 execution_record 命令别名不一致"
            )

    cwd_value = record.get("cwd")
    if isinstance(cwd_value, str) and cwd_value.strip():
        cwd_path = Path(cwd_value).expanduser()
        cwd_resolved = (cwd_path if cwd_path.is_absolute() else root / cwd_path).resolve()
        if cwd_resolved != root.resolve():
            report.add_error(
                f"条目 {index}（{entry_id}）的 execution_record.cwd 不在项目根目录或不是项目根目录"
            )

    output_raw = record.get("output_log")
    output_raw_text, output_path = _output_path(root, output_raw)
    if output_raw_text is None or output_path is None:
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record.output_log 越出项目根目录")
        return
    matching_output = next(
        ((raw, path) for raw, path in parsed_outputs if path == output_path), None
    )
    if matching_output is None:
        report.add_error(
            f"条目 {index}（{entry_id}）的 execution_record.output_log 未列在 manifest outputs 中：{output_raw_text}"
        )
    try:
        log_exists = output_path.is_file() and output_path.stat().st_size > 0
    except OSError:
        log_exists = False
    if not log_exists:
        report.add_error(
            f"条目 {index}（{entry_id}）的 execution_record 日志不存在或为空：{output_raw_text}"
        )

    return_code = record.get("return_code")
    if isinstance(return_code, bool) or not isinstance(return_code, int):
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record.return_code 无效")
    elif return_code != 0:
        report.add_error(
            f"条目 {index}（{entry_id}）的 execution_record.return_code 不是 0：{return_code}"
        )
    if record.get("timed_out") is not False:
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record 表明命令超时")

    record_digest = record.get("sha256")
    if isinstance(record_digest, dict):
        record_digest = _match_digest(output_raw_text, output_path, record_digest)
    if not isinstance(record_digest, str) or not SHA256_PATTERN.fullmatch(record_digest.strip()):
        report.add_error(f"条目 {index}（{entry_id}）的 execution_record.sha256 无效")
        return
    record_digest = record_digest.strip().lower()
    manifest_digest = _match_digest(output_raw_text, output_path, hashes)
    if manifest_digest is None or not SHA256_PATTERN.fullmatch(manifest_digest):
        report.add_error(
            f"条目 {index}（{entry_id}）的 manifest 未为 execution_record 日志提供有效 sha256"
        )
    elif record_digest != manifest_digest.lower():
        report.add_error(
            f"条目 {index}（{entry_id}）的 execution_record.sha256 与 manifest 不一致"
        )
    if log_exists:
        try:
            actual_digest = sha256_file(output_path)
        except OSError as error:
            report.add_error(f"条目 {index}（{entry_id}）无法读取 execution_record 日志哈希：{error}")
        else:
            if actual_digest != record_digest:
                report.add_error(
                    f"条目 {index}（{entry_id}）的 execution_record.sha256 与日志内容不匹配"
                )
        if started is not None and finished is not None:
            try:
                log_time = datetime.fromtimestamp(
                    output_path.stat().st_mtime,
                    tz=started.tzinfo,
                )
            except OSError:
                report.add_error(f"条目 {index}（{entry_id}）无法读取执行日志时间")
            else:
                tolerance = timedelta(seconds=2)
                if log_time < started - tolerance or log_time > finished + tolerance:
                    report.add_error(
                        f"条目 {index}（{entry_id}）的执行日志时间不在 execution_record 运行窗口内"
                    )
    record_path_value = record.get("_record_path_internal")
    if started is not None and finished is not None and isinstance(record_path_value, str):
        try:
            record_time = datetime.fromtimestamp(
                Path(record_path_value).stat().st_mtime,
                tz=finished.tzinfo,
            )
        except OSError:
            report.add_error(f"条目 {index}（{entry_id}）无法读取 execution_record 文件时间")
        else:
            tolerance = timedelta(seconds=2)
            if record_time < finished - tolerance:
                report.add_error(
                    f"条目 {index}（{entry_id}）的 execution_record 文件早于声明的完成时间"
                )


def _contains_real_assertion(claim: str) -> bool:
    """判断主张是否把模拟/示例结果写成真实系统结果。"""

    if not any(pattern.search(claim) for pattern in REAL_ASSERTION_PATTERNS):
        return False
    if any(pattern.search(claim) for pattern in REAL_NEGATION_PATTERNS):
        return False
    return True


def _text_output_real_assertion(root: Path, output: Any) -> tuple[str | None, bool]:
    """对项目内小型文本输出执行真实性用语扫描。"""

    raw, path = _output_path(root, output)
    if raw is None or path is None or not path.is_file():
        return raw, False
    if path.suffix.casefold() not in {".txt", ".log", ".json", ".csv", ".md"}:
        return raw, False
    try:
        if path.stat().st_size > 1024 * 1024:
            return raw, False
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return raw, False
    return raw, _contains_real_assertion(content)


def _numeric_tokens(text: str) -> set[str]:
    """提取可用于跨文件关联的定量标记，忽略单个普通数字。"""

    tokens = set(re.findall(r"(?<!\d)\d+(?:\.\d+)?%?(?!\d)", text))
    return {token for token in tokens if "." in token or "%" in token or len(token.rstrip("%")) >= 2}


def _scan_documents_for_simulated_leak(
    root: Path,
    entries: list[Any],
    report: EvidenceValidationReport,
) -> None:
    """阻止模拟或硬编码数值在论文中被改写成真实实测结果。"""

    non_real_tokens: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("evidence_level") not in {
            "SIMULATED",
            "SYNTHETIC_DATA",
            "HARDCODED_EXAMPLE",
        }:
            continue
        claim = entry.get("claim")
        if isinstance(claim, str):
            non_real_tokens.update(_numeric_tokens(claim))
        for output in _as_sequence(entry.get("outputs"), "outputs", report, 0):
            _raw, path = _output_path(root, output)
            if path is None or not path.is_file() or path.suffix.casefold() not in {
                ".txt", ".log", ".json", ".csv", ".md"
            }:
                continue
            try:
                if path.stat().st_size <= 1024 * 1024:
                    non_real_tokens.update(
                        _numeric_tokens(path.read_text(encoding="utf-8", errors="replace"))
                    )
            except OSError:
                continue
    if not non_real_tokens:
        return

    documents: list[Path] = []
    for relative in ("07-paper-full.md", "12-final-qa-report.md"):
        path = root / relative
        if path.is_file():
            documents.append(path)
    chapter_dir = root / "chapters"
    if chapter_dir.is_dir():
        documents.extend(sorted(chapter_dir.rglob("*.md")))

    for document in documents:
        try:
            lines = document.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if not _contains_real_assertion(line):
                continue
            matched = [
                token
                for token in non_real_tokens
                if re.search(rf"(?<!\d){re.escape(token)}(?!\d)", line)
            ]
            if matched:
                report.add_error(
                    f"{document.relative_to(root)} 第 {line_number} 行把模拟/合成/硬编码数值写成真实实测：{', '.join(sorted(matched))}"
                )


def _validate_observed_entry(
    root: Path,
    entry: dict[str, Any],
    index: int,
    hashes: dict[str, str],
    report: EvidenceValidationReport,
) -> None:
    """严格校验真实系统观察证据的执行记录、命令、原始输出和哈希。"""

    command = entry.get("command")
    command_is_valid = (
        _is_nonempty_string(command)
        or (
            isinstance(command, list)
            and bool(command)
            and all(isinstance(item, str) and bool(item) for item in command)
        )
    )
    if not command_is_valid:
        report.add_error(f"条目 {index}（{entry.get('id', '?')}）缺少真实运行命令")

    outputs = _as_sequence(entry.get("outputs"), "outputs", report, index)
    parsed_outputs: list[tuple[str, Path]] = []
    for output in outputs:
        raw_path, path = _output_path(root, output)
        if raw_path is None or path is None:
            report.add_error(f"条目 {index}（{entry.get('id', '?')}）的 outputs 含无效原始输出路径")
            continue
        parsed_outputs.append((raw_path, path))
        try:
            exists = path.is_file() and path.stat().st_size > 0
        except OSError:
            exists = False
        if not exists:
            report.add_error(
                f"条目 {index}（{entry.get('id', '?')}）的原始输出不存在或为空：{raw_path}"
            )

    if not parsed_outputs:
        report.add_error(f"条目 {index}（{entry.get('id', '?')}）必须提供至少一个原始输出")
    if not hashes:
        report.add_error(f"条目 {index}（{entry.get('id', '?')}）缺少原始输出 SHA-256")
    _validate_hash_format(hashes, report, index, strict=True)

    for raw_path, path in parsed_outputs:
        try:
            usable = path.is_file() and path.stat().st_size > 0
        except OSError:
            usable = False
        if not usable:
            continue
        expected = _match_digest(raw_path, path, hashes)
        if expected is None:
            report.add_error(
                f"条目 {index}（{entry.get('id', '?')}）未为原始输出提供对应 sha256：{raw_path}"
            )
            continue
        if not SHA256_PATTERN.fullmatch(expected):
            continue
        try:
            actual = sha256_file(path)
        except OSError as error:
            report.add_error(f"条目 {index}（{entry.get('id', '?')}）无法读取原始输出哈希：{error}")
            continue
        if actual.lower() != expected.lower():
            report.add_error(
                f"条目 {index}（{entry.get('id', '?')}）的 sha256 与原始输出不匹配：{raw_path}"
            )

    execution_record = _load_execution_record(root, entry, index, report)
    _validate_execution_record(
        root,
        entry,
        index,
        hashes,
        parsed_outputs,
        execution_record,
        report,
    )


def _validate_entry(root: Path, entry: Any, index: int, report: EvidenceValidationReport) -> None:
    """校验单条证据记录的结构、证据级别与真实性边界。"""

    if not isinstance(entry, dict):
        report.add_error(f"条目 {index} 必须是 JSON 对象")
        return

    missing = [field for field in REQUIRED_FIELDS if field not in entry]
    if missing:
        report.add_error(f"条目 {index} 缺少必需字段：{', '.join(missing)}")
        # 仍继续检查已存在字段，便于一次性反馈更多问题。

    entry_id = entry.get("id")
    if not _is_nonempty_string(entry_id):
        report.add_error(f"条目 {index} 的 id 必须是非空字符串")
    claim = entry.get("claim")
    if not _is_nonempty_string(claim):
        report.add_error(f"条目 {index} 的 claim 必须是非空字符串")
    level = entry.get("evidence_level")
    if level not in EVIDENCE_LEVELS:
        report.add_error(
            f"条目 {index} 的 evidence_level 无效：{level!r}；允许值为 {'、'.join(EVIDENCE_LEVELS)}"
        )

    # 所有字段都要有明确结构；非观察类允许为空，但不能伪造为字符串对象。
    sources = _as_sequence(entry.get("sources"), "sources", report, index)
    if any(not _is_nonempty_string(item) for item in sources):
        report.add_error(f"条目 {index} 的 sources 必须只含非空字符串")
    command = entry.get("command")
    if command is not None and not isinstance(command, (str, list)):
        report.add_error(f"条目 {index} 的 command 必须是命令字符串或参数列表")
    outputs = _as_sequence(entry.get("outputs"), "outputs", report, index)
    if any(_output_path(root, item)[0] is None for item in outputs):
        report.add_error(f"条目 {index} 的 outputs 必须只含文件路径")
    limitations = _as_sequence(entry.get("limitations"), "limitations", report, index)
    if any(not _is_nonempty_string(item) for item in limitations):
        report.add_error(f"条目 {index} 的 limitations 必须只含非空字符串")
    hashes = _normalise_hashes(entry.get("sha256"), report, index)

    if level in {"SIMULATED", "SYNTHETIC_DATA", "HARDCODED_EXAMPLE"}:
        if isinstance(claim, str) and _contains_real_assertion(claim):
            report.add_error(
                f"条目 {index}（{entry_id or '?'}）的 {level} 主张疑似声称真实系统结果"
            )
        _validate_hash_format(hashes, report, index, strict=False)
        if not limitations:
            report.add_error(
                f"条目 {index}（{entry_id or '?'}）的 {level} 必须说明不能代表真实系统的限制"
            )
        for output in outputs:
            raw_output, has_real_assertion = _text_output_real_assertion(root, output)
            if has_real_assertion:
                report.add_error(
                    f"条目 {index}（{entry_id or '?'}）的 {level} 输出疑似声称真实系统结果：{raw_output}"
                )
    elif level == "OBSERVED_REAL_SYSTEM":
        _validate_observed_entry(root, entry, index, hashes, report)
    elif level == "VERIFIED_EXTERNAL":
        if not sources:
            report.add_error(
                f"条目 {index}（{entry_id or '?'}）的 VERIFIED_EXTERNAL 必须提供可核验来源"
            )
        _validate_hash_format(hashes, report, index, strict=False)
    else:
        # 外部核验或计划记录不在本地强制执行命令，但如填写摘要仍验证格式。
        _validate_hash_format(hashes, report, index, strict=False)


def load_manifest(manifest_path: Path) -> Any:
    """读取 JSON 清单并返回原始对象。"""

    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise ValueError(f"证据清单不是有效的 UTF-8 文本：{manifest_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"证据清单 JSON 格式错误：{error}") from error
    except OSError as error:
        raise ValueError(f"无法读取证据清单 {manifest_path}：{error}") from error


def validate_manifest(root: Path, manifest_path: Path | None = None) -> EvidenceValidationReport:
    """校验 evidence-manifest.json 并返回报告对象。"""

    root = root.resolve()
    path = manifest_path.resolve() if manifest_path is not None else resolve_manifest(root, None)
    report = EvidenceValidationReport(path)
    try:
        path.relative_to(root)
    except ValueError:
        report.add_error(f"证据清单路径越出项目根目录：{path}")
        return report
    if not path.is_file():
        report.add_error(f"缺少证据清单：{path}")
        return report

    try:
        data = load_manifest(path)
    except ValueError as error:
        report.add_error(str(error))
        return report

    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict) and isinstance(data.get("entries"), list):
        entries = data["entries"]
    else:
        report.add_error("证据清单顶层必须是条目数组或含 entries 数组的对象")
        return report

    report.entry_count = len(entries)
    if not entries:
        report.add_error("证据清单 entries 不能为空")

    ids: set[str] = set()
    for index, entry in enumerate(entries, start=1):
        if isinstance(entry, dict) and isinstance(entry.get("id"), str):
            entry_id = entry["id"].strip()
            if entry_id in ids:
                report.add_error(f"条目 {index} 的 id 重复：{entry_id}")
            elif entry_id:
                ids.add(entry_id)
        _validate_entry(root, entry, index, report)
    _scan_documents_for_simulated_leak(root, entries, report)
    return report


def validate_evidence(root: Path | str, manifest: str | Path | None = None) -> dict[str, Any]:
    """兼容性函数：直接返回证据校验 JSON 字典。"""

    project_root = Path(root).expanduser().resolve()
    manifest_path = resolve_manifest(project_root, str(manifest) if manifest is not None else None)
    return validate_manifest(project_root, manifest_path).as_dict()


def build_parser() -> argparse.ArgumentParser:
    """构造中文命令行参数。"""

    parser = argparse.ArgumentParser(description="校验 evidence-manifest.json 的证据边界和哈希。")
    parser.add_argument("--root", help="项目根目录，默认使用脚本所属 Skill 根目录。")
    parser.add_argument(
        "--manifest",
        help="证据清单路径，默认项目根目录下的 evidence-manifest.json。",
    )
    parser.add_argument("--json", action="store_true", help="以机器可读 JSON 输出报告。")
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行入口，保证 JSON 模式不混入人类提示。"""

    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    try:
        manifest = resolve_manifest(root, args.manifest)
    except ValueError as error:
        if args.json:
            print(json.dumps({"status": STATUS_FAIL, "errors": [str(error)]}, ensure_ascii=False))
        else:
            print(f"失败：{error}", file=sys.stderr)
        return EXIT_FAIL
    report = validate_manifest(root, manifest)
    payload = report.as_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(f"状态：{payload['status']}")
        print(f"清单：{payload['manifest']}")
        for error in payload["errors"]:
            print(f"失败：{error}", file=sys.stderr)
        for warning in payload["warnings"]:
            print(f"警告：{warning}")
    return EXIT_PASS if report.status == STATUS_PASS else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
