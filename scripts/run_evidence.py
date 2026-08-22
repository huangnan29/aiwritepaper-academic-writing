#!/usr/bin/env python3
"""在项目根目录内安全执行证据命令，并生成可复核的执行记录。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# 证据命令必须快速结束；较大的任务应拆成多个可审计步骤。
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_TIMEOUT_SECONDS = 60.0
MAX_LOG_BYTES = 1024 * 1024
PROCESS_GRACE_SECONDS = 0.5
SECRET_ARGUMENT_RE = re.compile(
    r"(?i)(?:^|[-_])(?:api[-_]?key|token|secret|password)\s*[:=]|\b(?:sk|rk)-[A-Za-z0-9._-]{8,}"
)


class EvidenceCommandError(ValueError):
    """表示命令参数、项目路径或输出路径不符合安全约束。"""


def _utc_now() -> str:
    """返回带时区的 UTC 时间，便于跨机器比较。"""

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _resolve_root(raw_root: str | os.PathLike[str] | None) -> Path:
    """解析并检查项目根目录。"""

    candidate = (
        Path(raw_root).expanduser().resolve()
        if raw_root is not None
        else Path(__file__).resolve().parents[1]
    )
    if not candidate.is_dir():
        raise EvidenceCommandError(f"项目根目录不存在或不是目录：{candidate}")
    return candidate


def resolve_inside_root(root: Path, raw_path: str | os.PathLike[str], field: str) -> Path:
    """解析项目内路径；拒绝绝对越界路径、目录本身和穿越符号链接的路径。"""

    if not isinstance(raw_path, (str, os.PathLike)):
        raise EvidenceCommandError(f"{field} 必须是路径字符串")
    text = os.fspath(raw_path).strip()
    if not text:
        raise EvidenceCommandError(f"{field} 不能为空")
    path = Path(text).expanduser()
    resolved = (path if path.is_absolute() else root / path).resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as error:
        raise EvidenceCommandError(f"{field} 不能越出项目根目录：{text}") from error
    if resolved == root_resolved:
        raise EvidenceCommandError(f"{field} 不能指向项目根目录本身：{text}")
    return resolved


def root_relative_path(root: Path, path: Path) -> str:
    """将项目内绝对路径转成稳定的 POSIX 相对路径。"""

    return path.resolve().relative_to(root.resolve()).as_posix()


def _validate_timeout(value: str) -> float:
    """解析短超时秒数。"""

    try:
        timeout = float(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError("超时必须是正数秒") from error
    if not 0 < timeout <= MAX_TIMEOUT_SECONDS:
        raise argparse.ArgumentTypeError(
            f"超时必须大于 0 且不超过 {MAX_TIMEOUT_SECONDS:g} 秒"
        )
    return timeout


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """先终止再强制清理整个进程组，避免子进程继续占用输出管道。"""

    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        try:
            process.wait(timeout=PROCESS_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
    else:
        # Windows 没有与 POSIX killpg 等价的安全接口；新进程组仍可由父进程终止。
        try:
            process.terminate()
        except OSError:
            pass
        try:
            process.wait(timeout=PROCESS_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass


def _drain_output(
    stream: Any,
    handle: Any,
    max_bytes: int,
    state: dict[str, Any],
) -> None:
    """持续排空合并后的 stdout/stderr，并把写入量限制在上限内。"""

    try:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            remaining = max_bytes - int(state["written"])
            if remaining > 0:
                data = chunk[:remaining]
                handle.write(data)
                state["written"] += len(data)
            if len(chunk) > remaining:
                state["truncated"] = True
    except (OSError, ValueError):
        # 子进程被终止时管道可能提前关闭；已有日志仍然是有效的部分记录。
        state["read_error"] = True


def _sha256_file(path: Path) -> str:
    """以分块方式计算日志 SHA-256。"""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """写入 UTF-8 JSON 执行记录。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def execute_evidence(
    *,
    root: Path,
    evidence_id: str,
    claim: str,
    output_log: str,
    record_output: str,
    timeout: float,
    command: list[str],
) -> tuple[dict[str, Any], int]:
    """执行命令并返回执行记录及 CLI 退出码。"""

    if not evidence_id.strip():
        raise EvidenceCommandError("id 不能为空")
    if not claim.strip():
        raise EvidenceCommandError("claim 不能为空")
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise EvidenceCommandError("-- 后必须提供非空命令参数")
    if any(SECRET_ARGUMENT_RE.search(item) for item in command):
        raise EvidenceCommandError("命令参数疑似包含凭证；请改用进程环境或安全凭证存储，不写入执行记录")
    if not 0 < timeout <= MAX_TIMEOUT_SECONDS:
        raise EvidenceCommandError(
            f"超时必须大于 0 且不超过 {MAX_TIMEOUT_SECONDS:g} 秒"
        )

    root = root.resolve()
    output_path = resolve_inside_root(root, output_log, "output-log")
    record_path = resolve_inside_root(root, record_output, "record-output")
    if output_path.suffix.casefold() not in {".log", ".txt"}:
        raise EvidenceCommandError("output-log 必须使用 .log 或 .txt 后缀")
    if record_path.suffix.casefold() != ".json":
        raise EvidenceCommandError("record-output 必须使用 .json 后缀")
    if output_path == record_path:
        raise EvidenceCommandError("output-log 与 record-output 不能是同一个文件")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.parent.mkdir(parents=True, exist_ok=True)

    started_at = _utc_now()
    run_id = str(uuid.uuid4())
    timed_out = False
    return_code: int | None = None
    spawn_error: str | None = None
    state: dict[str, Any] = {"written": 0, "truncated": False, "read_error": False}

    with output_path.open("wb") as output_handle:
        try:
            process = subprocess.Popen(
                command,
                cwd=str(root),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                start_new_session=(os.name == "posix"),
                **(
                    {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                    if os.name == "nt"
                    else {}
                ),
            )
        except (OSError, ValueError) as error:
            spawn_error = f"无法启动命令：{error}"
        else:
            assert process.stdout is not None
            reader = threading.Thread(
                target=_drain_output,
                args=(process.stdout, output_handle, MAX_LOG_BYTES, state),
                name="证据输出读取器",
                daemon=True,
            )
            reader.start()
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                _terminate_process_group(process)
                try:
                    return_code = process.wait(timeout=PROCESS_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    return_code = process.poll()
            reader.join(timeout=PROCESS_GRACE_SECONDS + 0.5)
            if reader.is_alive():
                try:
                    process.stdout.close()
                except OSError:
                    pass
                reader.join(timeout=PROCESS_GRACE_SECONDS)
            else:
                try:
                    process.stdout.close()
                except OSError:
                    pass
            if return_code is None:
                return_code = process.poll()

        if spawn_error:
            output_handle.write((spawn_error + "\n").encode("utf-8", errors="replace"))

    finished_at = _utc_now()
    digest = _sha256_file(output_path)
    record: dict[str, Any] = {
        "run_id": run_id,
        "id": evidence_id,
        "claim": claim,
        "started_at": started_at,
        "finished_at": finished_at,
        "command": list(command),
        "command_argv": list(command),
        "cwd": str(root),
        "return_code": return_code,
        "timed_out": timed_out,
        "output_log": root_relative_path(root, output_path),
        "sha256": digest,
        "output_truncated": bool(state["truncated"]),
        "output_bytes": int(output_path.stat().st_size),
    }
    if spawn_error:
        record["error"] = spawn_error
    _write_json(record_path, record)

    if timed_out:
        exit_code = 124
    elif return_code is None:
        exit_code = 1
    elif return_code < 0:
        exit_code = 128 + abs(return_code)
    else:
        exit_code = return_code
    return record, exit_code


def build_parser() -> argparse.ArgumentParser:
    """构造中文命令行解析器。"""

    parser = argparse.ArgumentParser(description="在项目内执行可审计的证据命令。")
    parser.add_argument("--root", required=True, help="项目根目录。")
    parser.add_argument("--id", required=True, dest="evidence_id", help="证据条目 ID。")
    parser.add_argument("--claim", required=True, help="证据条目的主张文本。")
    parser.add_argument("--output-log", required=True, help="项目内 stdout/stderr 日志路径。")
    parser.add_argument("--record-output", required=True, help="项目内执行记录 JSON 路径。")
    parser.add_argument(
        "--timeout",
        type=_validate_timeout,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"超时秒数，范围为 0 到 {MAX_TIMEOUT_SECONDS:g} 秒，默认 {DEFAULT_TIMEOUT_SECONDS:g}。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行入口；命令参数必须位于独立的 -- 之后。"""

    raw_args = list(sys.argv[1:] if argv is None else argv)
    if "--" not in raw_args:
        print("失败：命令参数必须放在 -- 之后。", file=sys.stderr)
        return 2
    separator = raw_args.index("--")
    option_args = raw_args[:separator]
    command = raw_args[separator + 1 :]
    parser = build_parser()
    try:
        args = parser.parse_args(option_args)
        root = _resolve_root(args.root)
        record, exit_code = execute_evidence(
            root=root,
            evidence_id=args.evidence_id,
            claim=args.claim,
            output_log=args.output_log,
            record_output=args.record_output,
            timeout=args.timeout,
            command=command,
        )
    except (EvidenceCommandError, OSError, ValueError) as error:
        print(f"失败：{error}", file=sys.stderr)
        return 2

    print(f"执行记录已写入：{root / args.record_output}")
    print(f"命令返回码：{record['return_code']}")
    print(f"是否超时：{'是' if record['timed_out'] else '否'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
