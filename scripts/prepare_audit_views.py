#!/usr/bin/env python3
"""把人工或模型的具体观察投影为机械检查视图；不生成评分或审稿身份。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("路径必须是非空字符串")
    path = (root / value).resolve()
    path.relative_to(root)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"文件不存在或为空: {value}")
    return path


def bind_artifact(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    """只绑定已经存在的观察材料，不补写PASS、时间或语义结论。"""
    allowed = {
        "figure_id", "checkpoint", "page", "status", "reason", "blind_summary",
        "location", "evidence", "fix", "severity", "claim_id", "evidence_ids",
        "source_locator", "final_embed_file", "remaining_issues",
    }
    output = {key: value for key, value in item.items() if key in allowed}
    for field in ("checked_file", "visual_receipt"):
        if field not in item:
            continue
        path = safe_file(root, item[field])
        supplied = item.get(field + "_sha256")
        actual = digest(path)
        if supplied is not None and supplied != actual:
            raise ValueError(f"{field}_sha256与文件不一致: {item[field]}")
        output[field] = item[field]
        output[field + "_sha256"] = actual
    return output


def atomic_write(path: Path, value: Any) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def rows(value: Any, nested: str) -> list[dict[str, Any]]:
    result = value.get(nested) if isinstance(value, dict) else value
    if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
        raise ValueError(f"{nested}必须是对象列表")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="生成无评分的观察视图")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, default=Path("qa-observations.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    source = args.input if args.input.is_absolute() else root / args.input
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("schema_version") != "2.1":
            raise ValueError("qa-observations.json必须使用schema_version=2.1")
        manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
        authority = json.loads((root / "figures/figure-manifest.json").read_text(encoding="utf-8"))
        claims = rows(payload.get("claims", []), "claims")
        figures = rows(payload.get("figures", []), "figures")
        documents = rows(payload.get("document_checks", []), "checks")
        issues = rows(payload.get("issues", []), "items")

        authority_rows = authority.get("figures") if isinstance(authority, dict) else None
        if not isinstance(authority_rows, list):
            raise ValueError("权威figure-manifest.json缺少figures")
        authority_map = {
            item.get("figure_id"): item for item in authority_rows
            if isinstance(item, dict) and isinstance(item.get("figure_id"), str)
        }
        figure_view = []
        for item in figures:
            figure_id = item.get("figure_id")
            if figure_id not in authority_map:
                raise ValueError(f"figure_id不在权威清单中: {figure_id}")
            final_file = authority_map[figure_id].get("final_embed_file")
            if item.get("final_embed_file") != final_file:
                raise ValueError(f"final_embed_file与权威清单不一致: {figure_id}")
            safe_file(root, final_file)
            if not isinstance(item.get("status"), str) or not item.get("blind_summary"):
                raise ValueError(f"图片观察必须有status和blind_summary: {figure_id}")
            if "checked_file" not in item or "visual_receipt" not in item:
                raise ValueError(f"图片观察必须绑定实际文件和回执: {figure_id}")
            figure_view.append(bind_artifact(root, item))

        document_view = []
        for item in documents:
            if item.get("status") == "NOT_APPLICABLE":
                if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                    raise ValueError("NOT_APPLICABLE必须填写具体原因")
            else:
                if not isinstance(item.get("page"), int) or item["page"] < 1:
                    raise ValueError("页面观察必须填写正整数page")
                if "checked_file" not in item or "visual_receipt" not in item:
                    raise ValueError("页面观察必须绑定页面图和回执")
            document_view.append(bind_artifact(root, item))

        issue_view = []
        for item in issues:
            if str(item.get("severity", "")).upper() not in {"CRITICAL", "IMPORTANT", "ADVISORY"}:
                raise ValueError("问题severity必须为CRITICAL、IMPORTANT或ADVISORY")
            for field in ("location", "evidence", "fix", "status"):
                if not isinstance(item.get(field), str) or not item[field].strip():
                    raise ValueError(f"问题缺少{field}")
            issue_view.append(bind_artifact(root, item))

        outputs = {
            "claim-evidence-map.json": {"schema_version": "2.1", "claims": claims},
            "figures/figure-semantic-audit.json": {"schema_version": "2.1", "figures": figure_view},
            "16-document-visual-audit.json": {"schema_version": "2.1", "checks": document_view},
            "issue-register.json": {"schema_version": "2.1", "direction_id": manifest.get("direction_id"), "items": issue_view},
            "figures/figure-manifest.md": "# Figure Manifest\n\n" + "\n".join(
                f"- figure_id: {item['figure_id']}\n  final_embed_file: {item.get('final_embed_file')}"
                for item in authority_rows if isinstance(item, dict) and item.get("figure_id")
            ) + "\n",
        }
        capability = root / "00-capability-report.json"
        if capability.is_file():
            data = json.loads(capability.read_text(encoding="utf-8"))
            outputs["00-capability-report.md"] = "# 能力审计视图\n\n```json\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n```\n"
        source_resolved = source.resolve()
        for name, value in outputs.items():
            target = (root / name).resolve()
            target.relative_to(root)
            if target == source_resolved:
                raise ValueError("输出不能覆盖观察源文件")
            atomic_write(target, value)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "OBSERVATION_PROJECTION_BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "OBSERVATIONS_PROJECTED", "outputs": list(outputs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
