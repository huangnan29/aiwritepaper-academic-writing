#!/usr/bin/env python3
"""把人工填写的 qa-review.json 严格投影为质量审计文件，不替人工做语义判断。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import math
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("路径必须是非空字符串")
    path = (root / value).resolve()
    path.relative_to(root)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"文件不存在或为空: {value}")
    return path


def artifact(root: Path, item: dict[str, Any]) -> dict[str, Any]:
    """只绑定真实存在的文件；不生成status、时间或语义结论。"""
    out = {k: item[k] for k in ("figure_id", "checkpoint", "page", "status", "reason", "blind_summary", "location", "evidence", "fix") if k in item}
    for field in ("checked_file", "visual_receipt"):
        if field in item:
            path = safe(root, item[field])
            supplied = item.get(field + "_sha256")
            if supplied is not None and supplied != digest(path):
                raise ValueError(f"{field}_sha256与文件不一致: {item[field]}")
            out[field] = item[field]
            out[field + "_sha256"] = digest(path)
    return out


def write_atomic(path: Path, payload: str) -> None:
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, default=Path("qa-review.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    source = args.input if args.input.is_absolute() else root / args.input
    try:
        qa = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(qa, dict) or qa.get("schema_version") != "1.1":
            raise ValueError("qa-review.json 必须使用schema_version=1.1")
        manifest = json.loads((root / "run-manifest.json").read_text(encoding="utf-8"))
        authority = json.loads((root / "figures/figure-manifest.json").read_text(encoding="utf-8"))
        direction = qa.get("direction_id", manifest.get("direction_id"))
        if not isinstance(direction, str) or not direction:
            raise ValueError("缺少direction_id")

        claims = qa.get("claims")
        claim_rows = claims.get("claims") if isinstance(claims, dict) else claims
        if not isinstance(claim_rows, list):
            raise ValueError("claims 必须是列表或包含claims列表的对象")
        figures = qa.get("figures")
        figure_rows = figures.get("figures") if isinstance(figures, dict) else figures
        if not isinstance(figure_rows, list):
            raise ValueError("figures 必须是列表或包含figures列表的对象")
        docs = qa.get("document_checks")
        doc_rows = docs.get("checks") if isinstance(docs, dict) else docs
        if not isinstance(doc_rows, list):
            raise ValueError("document_checks 必须是列表或包含checks列表的对象")
        if any(not isinstance(x, dict) for x in claim_rows + figure_rows + doc_rows):
            raise ValueError("审计条目必须是对象")
        figure_view = [artifact(root, x) for x in figure_rows]
        document_view = [artifact(root, x) for x in doc_rows]
        authority_rows = authority.get("figures") if isinstance(authority, dict) else None
        if not isinstance(authority_rows, list):
            raise ValueError("权威figure-manifest.json缺少figures")
        authority_map = {x.get("figure_id"): x for x in authority_rows if isinstance(x, dict)}
        for item in figure_rows:
            if item.get("figure_id") not in authority_map:
                raise ValueError("figure_id不在权威figure-manifest.json中")
            authoritative_file = authority_map[item["figure_id"]].get("final_embed_file")
            if item.get("final_embed_file") != authoritative_file:
                raise ValueError("qa的final_embed_file与权威manifest不一致")
            safe(root, authoritative_file)
            if not isinstance(item.get("status"), str) or not item.get("blind_summary"):
                raise ValueError("figure必须人工填写status和blind_summary")
            if "checked_file" not in item or "visual_receipt" not in item:
                raise ValueError("figure必须绑定checked_file和visual_receipt")
        for item in doc_rows:
            if item.get("status") == "NOT_APPLICABLE":
                if not isinstance(item.get("reason"), str) or not item["reason"].strip():
                    raise ValueError("NOT_APPLICABLE必须填写reason")
                continue
            if not isinstance(item.get("status"), str) or not isinstance(item.get("page"), int) or item["page"] < 1:
                raise ValueError("document_check必须人工填写status和正整数page")
            if "checked_file" not in item or "visual_receipt" not in item:
                raise ValueError("document_check必须绑定checked_file和visual_receipt")

        review = qa.get("review")
        if not isinstance(review, dict):
            raise ValueError("缺少review对象")
        mode = review.get("reviewer_mode")
        if mode not in {"SELF", "ISOLATED"}:
            raise ValueError("reviewer_mode必须为SELF或ISOLATED")
        if not isinstance(review.get("status"), str) or not isinstance(review.get("issues"), dict) or not isinstance(review.get("alignment"), dict):
            raise ValueError("review必须填写status、issues、alignment")
        if any(review["alignment"].get(k) not in {True, False} for k in ("title_supported", "research_question_answered", "method_result_consistent", "abstract_conclusion_consistent")):
            raise ValueError("alignment字段必须显式填写布尔值")
        review_view = {k: review[k] for k in ("status", "reviewer_mode", "issues", "alignment", "scores", "total", "reviewed_artifacts", "reviewer_source") if k in review}
        # 对来源和被检查文件只接受真实绑定，绝不以字符串宣称独立。
        if isinstance(review_view.get("reviewer_source"), dict):
            src = review_view["reviewer_source"]
            if "path" in src:
                path = safe(root, src["path"])
                actual = digest(path)
                if src.get("sha256") is not None and src["sha256"] != actual:
                    raise ValueError("reviewer_source.sha256与文件不一致")
                review_view["reviewer_source"] = {"path": src["path"], "sha256": actual}
        reviewed = review_view.get("reviewed_artifacts", {})
        if reviewed is None:
            reviewed = {}
        if not isinstance(reviewed, dict):
            raise ValueError("reviewed_artifacts必须是对象")
        bound = dict(reviewed)
        for name, supplied_hash in list(bound.items()):
            if not isinstance(supplied_hash, str):
                raise ValueError("reviewed_artifacts hash必须是字符串")
            actual = digest(safe(root, name))
            if supplied_hash != actual:
                raise ValueError(f"reviewed_artifacts hash过期: {name}")
        for name in ("07-paper-full.md", "figures/figure-manifest.json", "16-document-visual-audit.json", manifest.get("docx"), manifest.get("pdf")):
            if isinstance(name, str) and (root / name).is_file():
                actual = digest(safe(root, name))
                if name in bound and bound[name] != actual:
                    raise ValueError(f"reviewed_artifacts hash过期: {name}")
                bound[name] = actual
        review_view["reviewed_artifacts"] = bound

        score = {"schema_version": "1.1", "direction_id": direction}
        if "scores" in review:
            if not isinstance(review["scores"], dict) or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in review["scores"].values()):
                raise ValueError("scores必须是有限数字且不能是布尔值")
            score["scores"] = review["scores"]
        if "total" in review:
            if isinstance(review["total"], bool) or not isinstance(review["total"], (int, float)) or not math.isfinite(review["total"]):
                raise ValueError("total必须是有限数字且不能是布尔值")
            score["total"] = review["total"]
        items = review["issues"].get("items")
        if not isinstance(items, list) or any(not isinstance(x, dict) for x in items):
            raise ValueError("review.issues.items必须是显式对象列表")
        if items or "scores" in review:
            critical = [x for x in items if isinstance(x, dict) and str(x.get("severity", x.get("level", ""))).upper() == "CRITICAL"]
            important = [x for x in items if isinstance(x, dict) and str(x.get("severity", x.get("level", ""))).upper() == "IMPORTANT"]
            score["critical"] = [x for x in critical if str(x.get("status", "")).upper() not in {"RESOLVED", "FIXED", "CLOSED", "ADDRESSED"}]
            score["important"] = important
            if review["issues"].get("critical_open") != sum(str(x.get("status", "")).upper() not in {"RESOLVED", "FIXED", "CLOSED", "ADDRESSED"} for x in critical):
                raise ValueError("critical_open与issues.items不一致")
            if review["issues"].get("important_open") != sum(str(x.get("status", "")).upper() not in {"RESOLVED", "FIXED", "CLOSED", "ADDRESSED"} for x in important):
                raise ValueError("important_open与issues.items不一致")
        score["reviewer_report"] = "09-final-peer-review.json"
        output_names = ["claim-evidence-map.json", "figures/figure-semantic-audit.json", "16-document-visual-audit.json", "09-final-peer-review.json", "15-quality-scorecard.json", "figures/figure-manifest.md"]
        if (root / "00-capability-report.json").is_file():
            output_names.append("00-capability-report.md")
        source_resolved = source.resolve()
        for name in output_names:
            target = (root / name).resolve()
            target.relative_to(root)
            if target == source_resolved:
                raise ValueError("输出不能覆盖qa-review.json")
        outputs = {
            "claim-evidence-map.json": {"schema_version": "1.1", "claims": claim_rows},
            "figures/figure-semantic-audit.json": {"schema_version": "1.1", "figures": figure_view},
            "16-document-visual-audit.json": {"schema_version": "1.1", "checks": document_view},
            "09-final-peer-review.json": {"schema_version": "1.1", "direction_id": direction, **review_view},
            "15-quality-scorecard.json": score,
        }
        # 派生visual已经在内存中完成，终稿绑定的是它的最终字节而非旧文件。
        visual_text = json.dumps(outputs["16-document-visual-audit.json"], ensure_ascii=False, indent=2) + "\n"
        visual_hash = hashlib.sha256(visual_text.encode()).hexdigest()
        if "16-document-visual-audit.json" in reviewed and reviewed["16-document-visual-audit.json"] != visual_hash:
            raise ValueError("新的页面检查与此前绑定的visual摘要不一致，必须实际重审")
        review_view["reviewed_artifacts"]["16-document-visual-audit.json"] = visual_hash
        outputs["09-final-peer-review.json"]["reviewed_artifacts"] = review_view["reviewed_artifacts"]
        review_text = json.dumps(outputs["09-final-peer-review.json"], ensure_ascii=False, indent=2) + "\n"
        outputs["15-quality-scorecard.json"]["reviewer_report_sha256"] = hashlib.sha256(review_text.encode()).hexdigest()
        capability_path = root / "00-capability-report.json"
        if capability_path.is_file():
            capability = json.loads(capability_path.read_text(encoding="utf-8"))
            outputs["00-capability-report.md"] = "# 能力审计视图\n\n```json\n" + json.dumps(capability, ensure_ascii=False, indent=2) + "\n```\n"
        outputs["figures/figure-manifest.md"] = "# Figure Manifest\n\n" + "\n".join(
            f"- figure_id: {x['figure_id']}\n  final_embed_file: {x['final_embed_file']}" for x in authority_rows
        ) + "\n"
        for name, value in outputs.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            text_value = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n"
            write_atomic(path, text_value)
    except (ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"校验失败，未生成任何输出: {exc}")
        return 1
    except OSError as exc:
        print(f"输出写入失败，可能已有部分输出: {exc}")
        return 1
    print(json.dumps({"status": "PREPARED", "outputs": list(outputs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
