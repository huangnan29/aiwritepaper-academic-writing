#!/usr/bin/env python3
"""冻结独立评审输入；不评分、不调用审稿模型、不修改论文目录。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    path.relative_to(root)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"评审输入不存在或为空: {value}")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="生成冻结的独立评审包")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output.resolve()
    try:
        output.relative_to(root)
    except ValueError:
        pass
    else:
        raise SystemExit("独立评审包必须写到论文目录之外")
    if output.exists():
        raise SystemExit("输出已存在，拒绝覆盖")
    manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
    files = ["07-paper-full.md", "03-evidence-matrix.csv", "figures/figure-manifest.json", "12-final-qa-report.md", "14-adjudicated-status.json"]
    for field in ("docx", "pdf"):
        value = manifest.get(field)
        if not isinstance(value, str):
            raise SystemExit(f"Manifest缺少{field}")
        files.append(value)
    frozen = {}
    for value in files:
        path = within(root, value)
        frozen[value] = {"sha256": digest(path), "bytes": path.stat().st_size}
    payload = {
        "schema_version": "1.0", "direction_id": manifest.get("direction_id"),
        "review_id": hashlib.sha256((str(root) + datetime.now().isoformat()).encode()).hexdigest()[:16],
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_root": str(root), "artifacts": frozen,
        "writer_declared_scores": None,
        "scope_note": "冻结包不含作者自评分；评审者须独立读取实际文件。",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "FROZEN", "output": str(output), "artifacts": len(frozen)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
