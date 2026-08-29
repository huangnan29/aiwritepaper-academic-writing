#!/usr/bin/env python3
"""根据当前版本验收报告计算唯一权威状态，不生成或修改论文内容。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPORT_SPECS = {
    "evidence": {
        "manifest_field": "evidence_verification_report",
        "default": "04-evidence-verification.json",
        "script": "verify_evidence_integrity.py",
    },
    "figure": {
        "manifest_field": "figure_verification_report",
        "default": "figures/figure-verification.json",
        "script": "verify_figure_package.py",
    },
    "formula": {
        "manifest_field": "formula_verification_report",
        "default": "equations/formula-verification.json",
        "script": "verify_formula_rendering.py",
    },
    "delivery": {
        "manifest_field": "delivery_verification_report",
        "default": "13-delivery-verification.json",
        "script": "verify_manuscript_delivery.py",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_under_root(root: Path, value: Any) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


class StatusAdjudicator:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.conflicts: List[str] = []
        self.report_hashes: Dict[str, str] = {}
        self.reports: Dict[str, Dict[str, Any]] = {}

    def error(self, code: str, detail: str) -> None:
        self.errors.append(f"{code}: {detail}")

    def load_manifest(self, path: Path) -> Dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("RUN_MANIFEST_INVALID", str(exc))
            return {}
        if not isinstance(payload, dict):
            self.error("RUN_MANIFEST_SHAPE", "根对象必须为对象")
            return {}
        return payload

    def load_reports(self, manifest: Dict[str, Any]) -> None:
        for name, spec in REPORT_SPECS.items():
            value = manifest.get(spec["manifest_field"], spec["default"])
            path = resolve_under_root(self.root, value)
            if path is None or not path.is_file() or path.stat().st_size == 0:
                self.error("REPORT_MISSING", f"{name}: {value}")
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                self.error("REPORT_INVALID", f"{name}: {exc}")
                continue
            if not isinstance(payload, dict):
                self.error("REPORT_SHAPE", name)
                continue
            verifier = payload.get("verifier")
            expected_script = SKILL_ROOT / "scripts" / spec["script"]
            expected_hash = sha256(expected_script)
            if not isinstance(verifier, dict):
                self.error("REPORT_VERIFIER_MISSING", name)
            else:
                if verifier.get("name") != spec["script"]:
                    self.error("REPORT_VERIFIER_NAME", f"{name}: {verifier.get('name')}")
                if verifier.get("sha256") != expected_hash:
                    self.error("REPORT_VERIFIER_STALE", name)
            input_hashes = payload.get("input_sha256")
            if not isinstance(input_hashes, dict) or not input_hashes:
                self.error("REPORT_INPUT_HASHES_MISSING", name)
            else:
                for relative, declared_hash in input_hashes.items():
                    input_path = resolve_under_root(self.root, relative)
                    if input_path is None or not input_path.is_file() or input_path.stat().st_size == 0:
                        self.error("REPORT_INPUT_MISSING", f"{name}: {relative}")
                    elif not isinstance(declared_hash, str) or declared_hash.lower() != sha256(input_path):
                        self.error("REPORT_INPUT_STALE", f"{name}: {relative}")
            self.reports[name] = payload
            self.report_hashes[name] = sha256(path)

    def derive(self, manifest: Dict[str, Any]) -> Dict[str, str]:
        evidence = self.reports.get("evidence", {})
        figure = self.reports.get("figure", {})
        formula = self.reports.get("formula", {})
        delivery = self.reports.get("delivery", {})
        evidence_status = evidence.get("status")
        claim_level = manifest.get("research_claim_level")

        if self.errors or evidence_status == "EVIDENCE_FAIL":
            research_status = "FAIL"
        elif evidence_status == "EVIDENCE_PARTIAL":
            research_status = "PARTIAL"
        elif claim_level in {"DESIGN_ONLY", "PROTOCOL_ONLY"}:
            research_status = "PARTIAL"
        elif claim_level in {"OBSERVED_STUDY", "REVIEW_SYNTHESIS"}:
            research_status = "PASS"
        else:
            research_status = "FAIL"
            self.error("RESEARCH_CLAIM_LEVEL_INVALID", str(claim_level))

        figure_mechanical = figure.get("mechanical_status")
        figure_visual = figure.get("visual_status")
        formula_status = formula.get("status")
        delivery_status_raw = delivery.get("status")
        if (
            self.errors
            or figure_mechanical != "PASS"
            or formula_status != "FORMULA_OK"
            or delivery_status_raw != "DELIVERY_OK"
        ):
            delivery_status = "FAIL"
        elif figure_visual == "PARTIAL":
            delivery_status = "PARTIAL"
        elif figure_visual == "PASS":
            delivery_status = "PASS"
        else:
            delivery_status = "FAIL"
            self.error("FIGURE_VISUAL_STATUS_INVALID", str(figure_visual))

        if research_status == "FAIL" or delivery_status == "FAIL":
            final_status = "FAIL"
        elif research_status == "PASS" and delivery_status == "PASS":
            final_status = "PASS"
        else:
            final_status = "PARTIAL"

        derived = {
            "research_status": research_status,
            "delivery_status": delivery_status,
            "final_status": final_status,
        }
        for field, value in derived.items():
            declared = manifest.get(field)
            if declared != value:
                self.conflicts.append(f"{field}: 声明{declared}，权威值{value}")
        return derived


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="计算AIWritePaper唯一权威交付状态")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run-manifest", type=Path, default=Path("run-manifest.json"))
    parser.add_argument("--report", type=Path, default=Path("14-adjudicated-status.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    adjudicator = StatusAdjudicator(root)
    manifest_path = args.run_manifest if args.run_manifest.is_absolute() else root / args.run_manifest
    manifest = adjudicator.load_manifest(manifest_path)
    adjudicator.load_reports(manifest)
    authoritative = adjudicator.derive(manifest)
    script = Path(__file__).resolve()
    payload = {
        "schema_version": "1.0",
        "status": f"ADJUDICATED_{authoritative['final_status']}",
        "authoritative_status": authoritative,
        "declared_status": {
            "research_status": manifest.get("research_status"),
            "delivery_status": manifest.get("delivery_status"),
            "final_status": manifest.get("final_status"),
        },
        "conflicts": adjudicator.conflicts,
        "errors": adjudicator.errors,
        "warnings": adjudicator.warnings,
        "report_sha256": adjudicator.report_hashes,
        "verifier": {
            "name": script.name, "version": "1.4.0", "sha256": sha256(script),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "scope_note": "权威状态只裁决证据与交付门禁，不替代同行评审或学校审查",
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    report = args.report if args.report.is_absolute() else root / args.report
    try:
        report.resolve().relative_to(root)
    except ValueError:
        print("报告路径必须位于输出目录内", file=sys.stderr)
        return 1
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(rendered + "\n", encoding="utf-8")
    return 1 if authoritative["final_status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
