#!/usr/bin/env python3
"""为模式矩阵生成可审计的SKIPPED报告。"""

from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

VALID_CATEGORIES = {"evidence", "figure", "formula", "delivery"}
VALID_SKIP = {"SKIPPED_NOT_APPLICABLE", "SKIPPED_UNCHANGED"}

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""): h.update(chunk)
    return h.hexdigest()

def main() -> int:
    p = argparse.ArgumentParser(description="生成模式化SKIPPED检查报告")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--category", choices=sorted(VALID_CATEGORIES), required=True)
    p.add_argument("--mode", required=True)
    p.add_argument("--skip-status", choices=sorted(VALID_SKIP), required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--upstream-report", type=Path)
    p.add_argument("--input", action="append", default=[], type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args(); root = a.root.resolve(); matrix_path = Path(__file__).resolve().parents[1]/"references/mode-checker-matrix.json"
    matrix = json.loads(matrix_path.read_text(encoding="utf-8")); allowed = matrix.get("modes",{}).get(a.mode,{}).get(a.category,[])
    if a.skip_status not in allowed: raise ValueError(f"{a.mode}.{a.category}不允许{a.skip_status}")
    inherited = None; inputs = list(a.input)
    if a.skip_status == "SKIPPED_UNCHANGED":
        if a.upstream_report is None: raise ValueError("SKIPPED_UNCHANGED必须提供上游报告")
        up = a.upstream_report if a.upstream_report.is_absolute() else root/a.upstream_report
        inherited = json.loads(up.read_text(encoding="utf-8")); inputs.append(up)
    hashes = {}
    for item in inputs:
        path = item if item.is_absolute() else root/item
        resolved = path.resolve(); resolved.relative_to(root)
        if not resolved.is_file() or resolved.stat().st_size == 0: raise ValueError(f"输入不存在: {item}")
        hashes[str(resolved.relative_to(root))] = sha256(resolved)
    script = Path(__file__).resolve()
    payload = {"schema_version":"1.0","status":a.skip_status,"category":a.category,"mode":a.mode,"reason":a.reason,"inherited":inherited,"input_sha256":hashes,"verifier":{"name":script.name,"version":"1.9.0","sha256":sha256(script),"generated_at":datetime.now().astimezone().isoformat(timespec="seconds")}}
    out = a.output if a.output.is_absolute() else root/a.output; out.resolve().relative_to(root); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps(payload,ensure_ascii=False,indent=2)); return 0

if __name__ == "__main__": sys.exit(main())
