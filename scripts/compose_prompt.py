#!/usr/bin/env python3
"""按固定顺序合成单一最终执行提示词，不参与任何论文决策。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import List, Optional


def read_utf8(path: Path) -> bytes:
    """读取非空UTF-8文件，同时保留原始字节。"""
    data = path.read_bytes()
    if not data.strip():
        raise ValueError(f"输入文件为空: {path}")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"输入文件不是有效UTF-8: {path}") from exc
    return data


def compose(parts: List[bytes]) -> bytes:
    """仅规范文件边界换行，正文原始字节保持不变。"""
    return b"\n\n".join(part.rstrip(b"\r\n") for part in parts) + b"\n"


def atomic_write(output: Path, data: bytes) -> None:
    """在目标目录内原子替换，避免留下半写入文件。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output.parent, prefix=f".{output.name}.", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="确定性合成 final-execution-prompt.md")
    parser.add_argument("--params", required=True, type=Path, help="本次 run-params.md")
    parser.add_argument("--compiled", required=True, type=Path, help="唯一 *-full.md")
    parser.add_argument("--addon", action="append", default=[], type=Path, help="可重复的附加交付规则")
    parser.add_argument("--output", required=True, type=Path, help="最终输出文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inputs = [args.params, args.compiled, *args.addon]
    resolved_inputs = [path.expanduser().resolve() for path in inputs]
    output = args.output.expanduser().resolve()

    if not args.compiled.name.endswith("-full.md"):
        raise ValueError(f"compiled文件名必须以 -full.md 结尾: {args.compiled}")
    if len(set(resolved_inputs)) != len(resolved_inputs):
        raise ValueError("输入文件存在重复")
    if output in resolved_inputs:
        raise ValueError("输出文件不能覆盖输入文件")

    payload = compose([read_utf8(path) for path in resolved_inputs])
    atomic_write(output, payload)

    report = {
        "status": "OK",
        "output": str(output),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "inputs": [str(path) for path in resolved_inputs],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
