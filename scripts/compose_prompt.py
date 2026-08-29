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
    parser.add_argument("--compiled", required=True, type=Path, help="唯一 *-full.md或*-compact.md")
    parser.add_argument("--addon", action="append", default=[], type=Path, help="可重复的附加交付规则")
    parser.add_argument("--profile-selection", type=Path, default=None, help="00-profile-selection.json")
    parser.add_argument("--profile-rules", type=Path, default=None, help="GUIDED或WEAK_MODEL规则")
    parser.add_argument("--output", required=True, type=Path, help="最终输出文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = "FULL_AUTONOMY"
    selection_path: Optional[Path] = None
    selection_hash: Optional[str] = None
    if args.profile_selection is not None:
        selection_path = args.profile_selection.expanduser().resolve()
        selection = json.loads(read_utf8(selection_path).decode("utf-8"))
        if not isinstance(selection, dict) or selection.get("schema_version") != "1.0":
            raise ValueError("Profile Selection必须为schema_version=1.0对象")
        profile = str(selection.get("selected_profile") or "")
        if profile not in {"FULL_AUTONOMY", "GUIDED", "WEAK_MODEL"}:
            raise ValueError(f"selected_profile无效: {profile}")
        selection_hash = hashlib.sha256(selection_path.read_bytes()).hexdigest()

    if profile == "WEAK_MODEL":
        if not args.compiled.name.endswith("-compact.md"):
            raise ValueError("WEAK_MODEL必须使用*-compact.md")
        expected_profile_file = "weak-model.md"
    else:
        if not args.compiled.name.endswith("-full.md"):
            raise ValueError(f"{profile}必须使用*-full.md")
        expected_profile_file = "guided.md" if profile == "GUIDED" else None

    if expected_profile_file is None:
        if args.profile_rules is not None:
            raise ValueError("FULL_AUTONOMY不附加Profile任务卡，以保护强模型原执行路径")
        if any(path.name == "execution-checkpoints-template.json" for path in args.addon):
            raise ValueError("FULL_AUTONOMY不附加阶段模板")
    else:
        if args.profile_rules is None or args.profile_rules.name != expected_profile_file:
            raise ValueError(f"{profile}必须附加references/profiles/{expected_profile_file}")
        if not any(path.name == "execution-checkpoints-template.json" for path in args.addon):
            raise ValueError(f"{profile}必须把execution-checkpoints-template.json合入最终提示词")

    inputs = [args.params, args.compiled, *args.addon]
    if args.profile_rules is not None:
        inputs.append(args.profile_rules)
    resolved_inputs = [path.expanduser().resolve() for path in inputs]
    output = args.output.expanduser().resolve()

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
        "execution_profile": profile,
        "profile_selection": str(selection_path) if selection_path else None,
        "profile_selection_sha256": selection_hash,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
