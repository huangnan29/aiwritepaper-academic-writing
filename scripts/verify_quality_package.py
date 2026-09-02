#!/usr/bin/env python3
"""验证方向评分、终稿隔离审稿、图文语义与页面级视觉回执。"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {"evidence": 25, "content": 20, "structure": 15, "figures": 15, "documents": 15, "integrity": 10}
RUBRICS = json.loads((ROOT / "references/quality/direction-rubrics.json").read_text(encoding="utf-8"))
VALID_DIRECTIONS = set(RUBRICS["directions"])
RESOLVED_IMPORTANT = {"RESOLVED", "FIXED", "CLOSED", "ADDRESSED"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
BOUNDARY_TERMS = ["不得", "不能", "未执行", "未验证", "主张层级", "能力缺口", "不报告"]
PROCESS_TERMS = ["门禁", "回执", "哈希", "脚本路径", "run-manifest", "DESIGN_ONLY", "OBSERVED_STUDY", "REVIEW_SYNTHESIS"]
PROMOTIONAL_TERMS = ["首次", "首创", "攻克", "彻底解决", "卓越", "领先优势", "精准预测", "完美达标", "重大突破"]


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


def document_capabilities(root: Path, manifest: Dict[str, Any]) -> Optional[Dict[str, int]]:
    """从最终DOCX解包统计真实结构，不能用审计文字替代。"""
    path = resolve(root, manifest.get("docx"))
    if path is None or not path.is_file():
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if "word/document.xml" not in names:
                return None
            roots = [ET.fromstring(archive.read(name)) for name in names if name.startswith("word/") and name.endswith(".xml")]
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main", "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"}
        return {"omml": sum(len(r.findall(".//m:oMath", ns)) for r in roots), "tables": sum(len(r.findall(".//w:tbl", ns)) for r in roots), "drawings": sum(len(r.findall(".//w:drawing", ns)) + len(r.findall(".//w:pict", ns)) for r in roots), "media": sum(name.startswith("word/media/") for name in names)}
    except (OSError, zipfile.BadZipFile, ET.ParseError):
        return None


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


def check_review(root: Path, manifest: Dict[str, Any], score: Dict[str, Any], errors: List[str], warnings: List[str]) -> Optional[Path]:
    value = score.get("reviewer_report", "09-final-peer-review.json")
    review_path = resolve(root, value)
    if review_path is None or not review_path.is_file() or review_path.stat().st_size == 0:
        errors.append("FINAL_PEER_REVIEW_MISSING")
        return None
    if score.get("reviewer_report_sha256") != sha256(review_path):
        errors.append("FINAL_PEER_REVIEW_HASH")
    review = load(review_path)
    if not isinstance(review, dict) or review.get("schema_version") not in {"1.0", "1.1"}:
        errors.append("FINAL_PEER_REVIEW_SCHEMA")
        return review_path
    if review.get("direction_id") != manifest.get("direction_id"):
        errors.append("FINAL_PEER_REVIEW_DIRECTION")
    mode = review.get("reviewer_mode")
    if review.get("status") not in {"PASS", "REVIEWED", "PARTIAL"}:
        errors.append("FINAL_PEER_REVIEW_NOT_PASS")
    if review.get("status") == "PARTIAL":
        warnings.append("REVIEW_PARTIAL")
    if mode == "SELF":
        warnings.append("SELF_REVIEW_NOT_INDEPENDENT")
    elif mode == "ISOLATED" and review.get("schema_version") == "1.1":
        source = review.get("reviewer_source")
        if not isinstance(source, dict) or not source.get("path") or not source.get("sha256"):
            warnings.append("ISOLATED_REVIEW_SOURCE_UNBOUND")
        else:
            source_path = resolve(root, source.get("path"))
            if source_path is None or not source_path.is_file() or source.get("sha256") != sha256(source_path):
                warnings.append("ISOLATED_REVIEW_SOURCE_STALE")
    elif mode != "ISOLATED":
        errors.append("FINAL_PEER_REVIEW_MODE_INVALID")
    alignment = review.get("alignment")
    alignment_fields = {
        "title_supported", "research_question_answered", "method_result_consistent",
        "abstract_conclusion_consistent",
    }
    if not isinstance(alignment, dict) or any(alignment.get(field) is not True for field in alignment_fields):
        errors.append("FINAL_PEER_REVIEW_ALIGNMENT_FAIL")
    issues = review.get("issues")
    if not isinstance(issues, dict) or issues.get("critical_open") != 0 or issues.get("important_open") != 0:
        errors.append("FINAL_PEER_REVIEW_ISSUES_OPEN")
    if review.get("schema_version") == "1.1":
        items = issues.get("items") if isinstance(issues, dict) else None
        if not isinstance(items, list):
            errors.append("FINAL_PEER_REVIEW_ISSUE_ITEMS_MISSING")
        else:
            for item in items:
                if not isinstance(item, dict):
                    errors.append("FINAL_PEER_REVIEW_ISSUE_INVALID")
                elif str(item.get("severity", item.get("level", ""))).upper() in {"CRITICAL", "IMPORTANT"} and str(item.get("status", "")).upper() not in RESOLVED_IMPORTANT:
                    errors.append("FINAL_PEER_REVIEW_ISSUES_OPEN")
    if review.get("schema_version") == "1.1" and review.get("scores") is None:
        if score.get("scores") is not None or score.get("total") is not None:
            errors.append("FINAL_PEER_REVIEW_SCORE_MISMATCH")
    elif review.get("scores") != score.get("scores") or float(review.get("total", -1)) != float(score.get("total", -2)):
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


def count_units(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text)) + len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", text))


def check_prose(markdown: Path, errors: List[str], warnings: List[str]) -> Dict[str, Any]:
    text = markdown.read_text(encoding="utf-8", errors="replace")
    reference = re.search(r"^#{1,6}\s*(?:参考文献|References)\s*$", text, re.MULTILINE | re.IGNORECASE)
    main = text[:reference.start()] if reference else text
    first_chapter = re.search(r"^#{1,3}\s*(?:第\s*1\s*章|1(?:\.0)?[.、]?\s+)", main, re.MULTILINE)
    body = main[first_chapter.start():] if first_chapter else main
    conclusion_matches = list(re.finditer(r"^#{1,3}\s*.*(?:结论|总结).*?$", body, re.MULTILINE))
    conclusion = body[conclusion_matches[-1].start():] if conclusion_matches else ""
    body_units = count_units(body)
    conclusion_units = count_units(conclusion)
    ratio = conclusion_units / max(body_units, 1)
    boundary_density = sum(body.count(term) for term in BOUNDARY_TERMS) / max(body_units, 1) * 10000
    process_density = sum(body.count(term) for term in PROCESS_TERMS) / max(body_units, 1) * 10000
    promotional_density = sum(body.count(term) for term in PROMOTIONAL_TERMS) / max(body_units, 1) * 10000
    sentences = [re.sub(r"\s+", "", item) for item in re.split(r"[。！？!?]", body)]
    counts: Dict[str, int] = {}
    for sentence in sentences:
        if len(sentence) >= 24:
            counts[sentence] = counts.get(sentence, 0) + 1
    duplicate_sentences = sum(value - 1 for value in counts.values() if value > 1)
    if ratio > 0.10:
        warnings.append("CONCLUSION_RATIO_EXCESSIVE")
    elif ratio > 0.07:
        warnings.append("CONCLUSION_RATIO_HIGH")
    if boundary_density > 80:
        warnings.append("BOUNDARY_LANGUAGE_EXCESSIVE")
    elif boundary_density > 55:
        warnings.append("BOUNDARY_LANGUAGE_HIGH")
    if process_density > 20:
        warnings.append("PROCESS_LANGUAGE_LEAKAGE")
    if promotional_density > 20:
        warnings.append("PROMOTIONAL_LANGUAGE_HIGH")
    if duplicate_sentences > 3:
        warnings.append("DUPLICATE_SENTENCES_HIGH")
    return {
        "body_units": body_units,
        "conclusion_units": conclusion_units,
        "conclusion_ratio": round(ratio, 4),
        "boundary_terms_per_10000": round(boundary_density, 2),
        "process_terms_per_10000": round(process_density, 2),
        "promotional_terms_per_10000": round(promotional_density, 2),
        "duplicate_sentences": duplicate_sentences,
    }


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
        if not (score.get("schema_version") == "1.1" and scores is None and score.get("total") is None):
            errors.append("SCORES_MISSING")
        scores = {}
    if score.get("scores") is not None:
        for key, maximum in WEIGHTS.items():
            value = scores.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > maximum:
                errors.append(f"SCORE_RANGE:{key}")
                continue
            calculated += float(value)
            if value < maximum * 0.8:
                warnings.append(f"DIMENSION_BELOW_80_PERCENT:{key}")
    numeric_score = score.get("total")
    if score.get("schema_version") == "1.1" and score.get("scores") is None and numeric_score is None:
        numeric_score = None
    elif (isinstance(score.get("total"), bool) or not isinstance(score.get("total"), (int, float))
          or not math.isfinite(score.get("total")) or abs(calculated - float(score.get("total"))) > 0.01):
        errors.append("SCORE_TOTAL_MISMATCH")
    if score.get("critical"):
        errors.append("CRITICAL_NOT_ZERO")
    important = score.get("important")
    if not isinstance(important, list):
        if not (score.get("schema_version") == "1.1" and score.get("scores") is None and score.get("total") is None):
            errors.append("IMPORTANT_SHAPE")
    else:
        for issue in important:
            if not isinstance(issue, dict) or str(issue.get("status", "")).upper() not in RESOLVED_IMPORTANT:
                errors.append("IMPORTANT_NOT_RESOLVED")

    review_path = check_review(root, manifest, score, errors, warnings)
    independent_verified = False
    if review_path and review_path.is_file():
        try:
            review_snapshot = load(review_path)
            independent_verified = False
            if review_snapshot.get("schema_version") == "1.1":
                source = review_snapshot.get("reviewer_source")
                source_path = resolve(root, source.get("path")) if isinstance(source, dict) else None
                independent_verified = bool(source_path and source_path.is_file() and source.get("sha256") == sha256(source_path))
        except (OSError, ValueError, json.JSONDecodeError):
            independent_verified = False
    prose_metrics = check_prose(root / "07-paper-full.md", errors, warnings)
    delivery_report = resolve(root, manifest.get("delivery_verification_report", "13-delivery-verification.json"))
    if delivery_report is None or not delivery_report.is_file():
        errors.append("DELIVERY_REPORT_MISSING")
    else:
        delivery_payload = load(delivery_report)
        for warning in delivery_payload.get("warnings", []) if isinstance(delivery_payload, dict) else []:
            if isinstance(warning, str) and warning.startswith("BODY_TARGET_UNDERSHOOT"):
                warnings.append("BODY_TARGET_UNDERSHOOT")

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
    capabilities = document_capabilities(root, manifest) if visual.get("schema_version") == "1.1" else None
    profile_value = manifest.get("document_profile", "")
    profile = str(profile_value.get("type", profile_value) if isinstance(profile_value, dict) else profile_value).upper()
    figure_empty = not bool(figure_manifest.get("figures"))
    na_allowed = {}
    if capabilities is not None and profile in {"JOURNAL", "REPORT"}:
        na_allowed.update({"cover": True, "toc": True})
    if capabilities is not None:
        na_allowed.update({"complex_formula": capabilities["omml"] == 0,
                           "complex_table": capabilities["tables"] == 0,
                           "representative_figure": capabilities["drawings"] == 0 and capabilities["media"] == 0 and figure_empty})
    seen = {item.get("checkpoint") for item in checks}
    if not required_checkpoints.issubset(seen):
        errors.append("DOCUMENT_VISUAL_COVERAGE")
    for item in checks:
        status = item.get("status")
        checkpoint = item.get("checkpoint")
        if status == "NOT_APPLICABLE":
            if not na_allowed.get(checkpoint, False) or not isinstance(item.get("reason"), str) or not item["reason"].strip():
                errors.append("DOCUMENT_VISUAL_NA_UNPROVEN")
            continue
        if status != "PASS" or not isinstance(item.get("page"), int) or item.get("page") < 1:
            errors.append("DOCUMENT_VISUAL_NOT_PASS")
        check_artifact(root, item, "DOCUMENT_VISUAL", errors, image_required=True)

    status = "QUALITY_FAIL" if errors else ("QUALITY_PARTIAL" if warnings or numeric_score is None or calculated < 90 else "QUALITY_OK")
    inputs = [
        root / "run-manifest.json", root / "15-quality-scorecard.json", root / "claim-evidence-map.json",
        root / "figures/figure-semantic-audit.json", root / "16-document-visual-audit.json",
        root / "figures/figure-manifest.json",
    ]
    if review_path:
        inputs.append(review_path)
    if delivery_report and delivery_report.is_file():
        inputs.append(delivery_report)
    input_hashes = {str(path.relative_to(root)): sha256(path) for path in inputs if path.is_file()}
    script = Path(__file__).resolve()
    payload = {
        "schema_version": "1.1" if score.get("schema_version") == "1.1" else "1.0", "status": status,
        "total": calculated if numeric_score is not None else None,
        "errors": errors, "warnings": warnings,
        "metrics": {"prose": prose_metrics, "numeric_score": numeric_score,
                    "ninety_plus_verified": bool(numeric_score is not None and numeric_score >= 90
                                                 and not errors and not warnings and independent_verified
                                                 and (not review_path or load(review_path).get("reviewer_mode") == "ISOLATED")
                                                 and status == "QUALITY_OK")},
        "input_sha256": input_hashes,
        "verifier": {"name": script.name, "version": "2.1.0", "sha256": sha256(script)},
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
