#!/usr/bin/env python3
"""以统一格式登记原始文件、下载和命令执行，供证据检查器复核。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List
import urllib.request


VERSION = "1.9.2"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def resolve(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"路径越出输出目录: {value}") from exc
    return candidate


def relative(root: Path, path: Path) -> str:
    return str(path.resolve().relative_to(root))


def identity() -> Dict[str, str]:
    script = Path(__file__).resolve()
    return {"name": script.name, "version": VERSION, "sha256": sha256(script)}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def file_record(root: Path, path: Path, allow_empty: bool = False) -> Dict[str, Any]:
    if not path.is_file() or (path.stat().st_size == 0 and not allow_empty):
        raise ValueError(f"文件不存在或为空: {path}")
    return {
        "file": relative(root, path),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "mtime_ns": path.stat().st_mtime_ns,
    }


def register(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    source = resolve(root, args.source)
    receipt = resolve(root, args.receipt)
    if args.origin not in {"USER_PROVIDED", "AUTHOR_OBSERVED"}:
        raise ValueError("register只接受USER_PROVIDED或AUTHOR_OBSERVED")
    payload = {
        "schema_version": "1.0",
        "receipt_type": "REGISTER",
        "origin": args.origin,
        "registered_at": now(),
        "collection_method": args.collection_method,
        "collector": args.collector,
        "source": file_record(root, source),
        "producer": identity(),
    }
    write_json(receipt, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def download(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    output = resolve(root, args.output)
    receipt = resolve(root, args.receipt)
    if not args.url.lower().startswith(("http://", "https://")):
        raise ValueError("下载地址必须为HTTP(S)")
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(args.url, headers={"User-Agent": "AIWritePaper provenance capture/1.9.2"})
    with urllib.request.urlopen(request, timeout=args.timeout) as response:
        status = int(getattr(response, "status", 200))
        output.write_bytes(response.read())
        final_url = response.geturl()
        content_type = response.headers.get("Content-Type", "")
    if status < 200 or status >= 300:
        raise ValueError(f"下载HTTP状态异常: {status}")
    payload = {
        "schema_version": "1.0",
        "receipt_type": "DOWNLOAD",
        "retrieved_at": now(),
        "source_url": args.url,
        "final_url": final_url,
        "http_status": status,
        "content_type": content_type,
        "output": file_record(root, output),
        "producer": identity(),
    }
    write_json(receipt, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def records(root: Path, values: List[str]) -> List[Dict[str, Any]]:
    return [file_record(root, resolve(root, value)) for value in values]


def run_command(args: argparse.Namespace) -> int:
    root = args.root.expanduser().resolve()
    receipt = resolve(root, args.receipt)
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("run模式缺少--后的命令")
    input_records = records(root, args.input)
    stdout_path = receipt.with_suffix(receipt.suffix + ".stdout.log")
    stderr_path = receipt.with_suffix(receipt.suffix + ".stderr.log")
    started_at = now()
    completed = subprocess.run(command, cwd=root, capture_output=True, text=False, check=False)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(completed.stdout)
    stderr_path.write_bytes(completed.stderr)
    output_records = records(root, args.output)
    payload = {
        "schema_version": "1.0",
        "receipt_type": "EXECUTION",
        "started_at": started_at,
        "finished_at": now(),
        "engine": args.engine,
        "engine_class": args.engine_class,
        "command": command,
        "exit_code": completed.returncode,
        "inputs": input_records,
        "outputs": output_records,
        "stdout": file_record(root, stdout_path, allow_empty=True),
        "stderr": file_record(root, stderr_path, allow_empty=True),
        "randomness": json.loads(args.randomness) if args.randomness else None,
        "producer": identity(),
    }
    write_json(receipt, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return completed.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成可机械复核的数据来源与执行回执")
    sub = parser.add_subparsers(dest="mode", required=True)

    register_parser = sub.add_parser("register", help="登记用户提供或作者实际观察的原始文件")
    register_parser.add_argument("--root", type=Path, default=Path.cwd())
    register_parser.add_argument("--source", required=True)
    register_parser.add_argument("--origin", required=True)
    register_parser.add_argument("--collection-method", required=True)
    register_parser.add_argument("--collector", required=True)
    register_parser.add_argument("--receipt", required=True)
    register_parser.set_defaults(func=register)

    download_parser = sub.add_parser("download", help="下载并登记公开原始文件")
    download_parser.add_argument("--root", type=Path, default=Path.cwd())
    download_parser.add_argument("--url", required=True)
    download_parser.add_argument("--output", required=True)
    download_parser.add_argument("--receipt", required=True)
    download_parser.add_argument("--timeout", type=int, default=60)
    download_parser.set_defaults(func=download)

    run_parser = sub.add_parser("run", help="运行计算或领域引擎并捕获输入输出")
    run_parser.add_argument("--root", type=Path, default=Path.cwd())
    run_parser.add_argument("--engine", required=True)
    run_parser.add_argument(
        "--engine-class", required=True,
        choices=["CALCULATION", "SPICE", "FEA", "CFD", "GIS", "STATISTICAL_MODEL", "DOMAIN_SOLVER"],
    )
    run_parser.add_argument("--input", action="append", default=[])
    run_parser.add_argument("--output", action="append", default=[])
    run_parser.add_argument("--randomness", help="含purpose、seed和distribution的JSON对象")
    run_parser.add_argument("--receipt", required=True)
    run_parser.add_argument("command", nargs=argparse.REMAINDER)
    run_parser.set_defaults(func=run_command)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return int(args.func(args))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
