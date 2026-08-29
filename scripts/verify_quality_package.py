#!/usr/bin/env python3
"""验证方向评分、终稿隔离审稿、图文语义与页面级视觉回执。"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {"evidence": 25, "content": 20, "structure": 15, "figures": 15, "documents": 15, "integrity": 10}
RUBRICS = json.loads((ROOT / "references/quality/direction-rubrics.json").read_text(encoding="utf-8"))
VALID_DIRECTIONS = set(RUBRICS["directions"])
RESOLVED_IMPORTANT = {"RESOLVED", "FIXED", "CLOSED", "ADDRESSED"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, (dict, list)):
        raise ValueError(str(path))
    return payload


def resolve(root: Path, value: Any) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def is_image(path: Path) -> bool:
    if path.suffix.lower() not in IMAGE_SUFFIXES:
        return False
    head = path.read_bytes()[:16]
    return (
        head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith(b"\xff\xd8\xff")
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")
    )


def check_artifact(root: Path, item: Dict[str, Any], prefix: str, errors: List[str], image_required: bool) -> None:
    for field in ["checked_file", "visual_receipt"]:
        path = resolve(root, item.get(field))
        if path is None:
            errors.append(f"{prefix}_{field.upper()}_PATH")
            continue
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"{prefix}_{field.upper()}_MISSING")
            continue
        if item.get(field + "_sha256") != sha256(path):
            errors.append(f"{prefix}_{field.upper()}_HASH")
        if field == "checked_file" and image_required and not is_image(path):
            errors.append(f"{prefix}_CHECKED_FILE_NOT_PAGE_IMAGE")


def check_review(root: Path, manifest: Dict[str, Any], score: Dict[str, Any], errors: List[str]) -> Optional[Path]:
    value = score.get("reviewer_report", "09-final-peer-review.json")
    review_path = resolve(root, value)
    if review_path is None or not review_path.is_file() or review_path.stat().st_size == 0:
        errors.append("FINAL_PEER_REVIEW_MISSING")
        return None
    if score.get("reviewer_report_sha256") != sha256(review_path):
        errors.append("FINAL_PEER_REVIEW_HASH")
    review = load(review_path)
    if not isinstance(review, dict) or review.get("schema_version") != "1.0":
        errors.append("FINAL_PEER_REVIEW_SCHEMA")
        return review_path
    if review.get("direction_id") != manifest.get("direction_id"):
        errors.append("FINAL_PEER_REVIEW_DIRECTION")
    if review.get("status") != "PASS" or review.get("reviewer_mode") != "ISOLATED":
        errors.append("FINAL_PEER_REVIEW_NOT_PASS")
    issues = review.get("issues")
    if not isinstance(issues, dict) or issues.get("critical_open") != 0 or issues.get("important_open") != 0:
        errors.append("FINAL_PEER_REVIEW_ISSUES_OPEN")
    if review.get("scores") != score.get("scores") or float(review.get("total", -1)) != float(score.get("total", -2)):
        errors.append("FINAL_PEER_REVIEW_SCORE_MISMATCH")
    reviewed = review.get("reviewed_artifacts")
    required = ["07-paper-full.md", "figures/figure-manifest.json", "16-document-visual-audit.json"]
    for field in ["docx", "pdf"]:
        if isinstance(manifest.get(field), str):
            required.append(manifest[field])
        else:
            errors.append(f"FINAL_PEER_REVIEW_MANIFEST_{field.upper()}_MISSING")
    if not isinstance(reviewed, dict):
        errors.append("FINAL_PEER_REVIEW_ARTIFACTS_MISSING")
        return review_path
    for relative in required:
        path = resolve(root, relative)
        if path is None or not path.is_file() or reviewed.get(relative) != sha256(path):
            errors.append(f"FINAL_PEER_REVIEW_ARTIFACT_STALE:{relative}")
    return review_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--report", type=Path, default=Path("17-quality-verification.json"))
    args = parser.parse_args()
    root = args.root.resolve()
    errors: List[str] = []
    warnings: List[str] = []

    try:
        manifest = load(root / "run-manifest.json")
        score = load(root / "15-quality-scorecard.json")
        claims = load(root / "claim-evidence-map.json")
        semantic = load(root / "figures/figure-semantic-audit.json")
        visual = load(root / "16-document-visual-audit.json")
        figure_manifest = load(root / "figures/figure-manifest.json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc))
        return 1
    if not all(isinstance(item, dict) for item in [manifest, score, claims, semantic, visual, figure_manifest]):
        errors.append("QUALITY_INPUT_SHAPE")

    direction = manifest.get("direction_id")
    if direction not in VALID_DIRECTIONS:
        errors.append("DIRECTION_ID_INVALID")
    if score.get("direction_id") != direction:
        errors.append("DIRECTION_RUBRIC_MISMATCH")
    scores = score.get("scores")
    calculated = 0.0
    if not isinstance(scores, dict):
        errors.append("SCORES_MISSING")
        scores = {}
    for key, maximum in WEIGHTS.items():
        value = scores.get(key)
        if not isinstance(value, (int, float)) or value < 0 or value > maximum:
            errors.append(f"SCORE_RANGE:{key}")
            continue
        calculated += float(value)
        if value < maximum * 0.8:
            warnings.append(f"DIMENSION_BELOW_80_PERCENT:{key}")
    if abs(calculated - float(score.get("total", -1))) > 0.01:
        errors.append("SCORE_TOTAL_MISMATCH")
    if score.get("critical"):
        errors.append("CRITICAL_NOT_ZERO")
    important = score.get("important")
    if not isinstance(important, list):
        errors.append("IMPORTANT_SHAPE")
    else:
        for issue in important:
            if not isinstance(issue, dict) or str(issue.get("status", "")).upper() not in RESOLVED_IMPORTANT:
                errors.append("IMPORTANT_NOT_RESOLVED")

    review_path = check_review(root, manifest, score, errors)

    claim_rows = claims.get("claims", [])
    if not claim_rows or any(
        not item.get("location")
        or (item.get("importance") in {"CORE", "CONCLUSION"} and not item.get("evidence_ids"))
        for item in claim_rows
    ):
        errors.append("CLAIM_EVIDENCE_COVERAGE")

    figures = figure_manifest.get("figures", [])
    expected = {item.get("figure_id") for item in figures}
    audits = semantic.get("figures", [])
    actual = {item.get("figure_id") for item in audits}
    if expected != actual or any(item.get("status") != "PASS" or not item.get("blind_summary") for item in audits):
        errors.append("FIGURE_SEMANTIC_NOT_PASS")
    for item in audits:
        check_artifact(root, item, "FIGURE_SEMANTIC", errors, image_required=True)

    required_checkpoints = {
        "cover", "primary_abstract", "toc", "complex_table", "complex_formula",
        "representative_figure", "references", "last_page",
    }
    checks = visual.get("checks", [])
    if not required_checkpoints.issubset({item.get("checkpoint") for item in checks}):
        errors.append("DOCUMENT_VISUAL_COVERAGE")
    for item in checks:
        if item.get("status") != "PASS" or not isinstance(item.get("page"), int) or item.get("page") < 1:
            errors.append("DOCUMENT_VISUAL_NOT_PASS")
        check_artifact(root, item, "DOCUMENT_VISUAL", errors, image_required=True)

    status = "QUALITY_FAIL" if errors else ("QUALITY_PARTIAL" if warnings or calculated < 90 else "QUALITY_OK")
    inputs = [
        root / "run-manifest.json", root / "15-quality-scorecard.json", root / "claim-evidence-map.json",
        root / "figures/figure-semantic-audit.json", root / "16-document-visual-audit.json",
        root / "figures/figure-manifest.json",
    ]
    if review_path:
        inputs.append(review_path)
    input_hashes = {str(path.relative_to(root)): sha256(path) for path in inputs if path.is_file()}
    script = Path(__file__).resolve()
    payload = {
        "schema_version": "1.0", "status": status, "total": calculated,
        "errors": errors, "warnings": warnings, "input_sha256": input_hashes,
        "verifier": {"name": script.name, "version": "1.9.2", "sha256": sha256(script)},
    }
    output = args.report if args.report.is_absolute() else root / args.report
    try:
        output.resolve().relative_to(root)
    except ValueError:
        print("报告路径必须位于输出目录内")
        return 1
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if status == "QUALITY_FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
