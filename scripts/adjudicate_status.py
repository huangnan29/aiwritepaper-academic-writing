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
        self.mode_matrix = json.loads(
            (SKILL_ROOT / "references" / "mode-checker-matrix.json").read_text(encoding="utf-8")
        )

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
        run_mode = manifest.get("run_mode", "FULL_BUILD")
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
            skipped = payload.get("status") in {"SKIPPED_NOT_APPLICABLE", "SKIPPED_UNCHANGED"}
            expected_name = "write_skipped_report.py" if skipped else spec["script"]
            expected_script = SKILL_ROOT / "scripts" / expected_name
            expected_hash = sha256(expected_script)
            if not isinstance(verifier, dict):
                self.error("REPORT_VERIFIER_MISSING", name)
            else:
                if verifier.get("name") != expected_name:
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
            if skipped:
                allowed = self.mode_matrix.get("modes", {}).get(run_mode, {}).get(name, [])
                if payload.get("status") not in allowed:
                    self.error("REPORT_SKIP_NOT_ALLOWED", f"{run_mode}.{name}: {payload.get('status')}")
                if payload.get("mode") != run_mode or payload.get("category") != name:
                    self.error("REPORT_SKIP_IDENTITY", name)
                if payload.get("status") == "SKIPPED_UNCHANGED":
                    inherited = payload.get("inherited")
                    if not isinstance(inherited, dict) or inherited.get("status") in {
                        "SKIPPED_NOT_APPLICABLE", "SKIPPED_UNCHANGED"
                    }:
                        self.error("REPORT_SKIP_UPSTREAM_INVALID", name)
            self.reports[name] = payload
            self.report_hashes[name] = sha256(path)

    def validate_execution_checkpoints(self, manifest: Dict[str, Any]) -> None:
        profile = manifest.get("execution_profile")
        if profile == "FULL_AUTONOMY":
            return
        if profile not in {"GUIDED", "WEAK_MODEL"}:
            self.error("EXECUTION_PROFILE_INVALID", str(profile))
            return
        value = manifest.get("execution_checkpoints", "00-execution-checkpoints.json")
        path = resolve_under_root(self.root, value)
        if path is None or not path.is_file() or path.stat().st_size == 0:
            self.error("EXECUTION_CHECKPOINTS_MISSING", str(value))
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            self.error("EXECUTION_CHECKPOINTS_INVALID", str(exc))
            return
        if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
            self.error("EXECUTION_CHECKPOINTS_SCHEMA", "当前仅接受schema_version=1.0")
            return
        if payload.get("execution_profile") != profile:
            self.error("EXECUTION_CHECKPOINTS_PROFILE_MISMATCH", str(payload.get("execution_profile")))
        stages = payload.get("stages")
        required = ["EVIDENCE", "OUTLINE", "DRAFT", "FIGURES", "DOCUMENTS", "VALIDATION"]
        if not isinstance(stages, dict):
            self.error("EXECUTION_CHECKPOINTS_STAGES", "stages必须为对象")
            return
        for stage_name in required:
            stage = stages.get(stage_name)
            if not isinstance(stage, dict):
                self.error("EXECUTION_CHECKPOINT_STAGE_MISSING", stage_name)
                continue
            status = stage.get("status")
            if status not in {"PASS", "PARTIAL"}:
                self.error("EXECUTION_CHECKPOINT_STAGE_OPEN", f"{stage_name}: {status}")
            outputs = stage.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                self.error("EXECUTION_CHECKPOINT_OUTPUTS_MISSING", stage_name)
                continue
            for item in outputs:
                if not isinstance(item, dict):
                    self.error("EXECUTION_CHECKPOINT_OUTPUT_INVALID", stage_name)
                    continue
                output_path = resolve_under_root(self.root, item.get("file"))
                if output_path is None or not output_path.is_file() or output_path.stat().st_size == 0:
                    self.error("EXECUTION_CHECKPOINT_FILE_MISSING", f"{stage_name}: {item.get('file')}")
                elif item.get("sha256") != sha256(output_path):
                    self.error("EXECUTION_CHECKPOINT_HASH_MISMATCH", f"{stage_name}: {item.get('file')}")

    def validate_revision_impact(self, manifest: Dict[str, Any]) -> None:
        if manifest.get("run_mode") != "REVISE_ONLY": return
        path = resolve_under_root(self.root, manifest.get("revision_impact", "revision-impact.json"))
        if path is None or not path.is_file(): self.error("REVISION_IMPACT_MISSING", "revision-impact.json"); return
        try: payload=json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc: self.error("REVISION_IMPACT_INVALID", str(exc)); return
        if payload.get("schema_version")!="1.0" or payload.get("run_mode")!="REVISE_ONLY": self.error("REVISION_IMPACT_SCHEMA", str(path))
        if not payload.get("items"): self.error("REVISION_ITEMS_MISSING", str(path))
        for item in payload.get("frozen_files",[]):
            p=resolve_under_root(self.root,item.get("file")) if isinstance(item,dict) else None
            if p is None or not p.is_file(): self.error("REVISION_FROZEN_FILE_MISSING", str(item))
            elif item.get("sha256")!=sha256(p): self.error("REVISION_FROZEN_FILE_CHANGED", str(item.get("file")))

    def derive(self, manifest: Dict[str, Any]) -> Dict[str, str]:
        def effective(name: str) -> Dict[str, Any]:
            payload = self.reports.get(name, {})
            if payload.get("status") == "SKIPPED_UNCHANGED":
                inherited = payload.get("inherited")
                return inherited if isinstance(inherited, dict) else {}
            if payload.get("status") == "SKIPPED_NOT_APPLICABLE":
                if name == "evidence": return {"status": "EVIDENCE_OK"}
                if name == "figure": return {"mechanical_status": "PASS", "visual_status": "PASS"}
                if name == "formula": return {"status": "FORMULA_OK"}
                if name == "delivery": return {"status": "DELIVERY_OK"}
            return payload

        evidence = effective("evidence")
        figure = effective("figure")
        formula = effective("formula")
        delivery = effective("delivery")
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
            if manifest.get("state_contract") == "DERIVED_ONLY":
                continue
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
    adjudicator.validate_execution_checkpoints(manifest)
    adjudicator.validate_revision_impact(manifest)
    adjudicator.load_reports(manifest)
    authoritative = adjudicator.derive(manifest)
    script = Path(__file__).resolve()
    payload = {
        "schema_version": "1.0",
        "status": f"ADJUDICATED_{authoritative['final_status']}",
        "run_identity": {
            "model_label": manifest.get("model_label"),
            "skill_version": manifest.get("skill_version"),
            "execution_profile": manifest.get("execution_profile"),
            "run_mode": manifest.get("run_mode", "FULL_BUILD"),
        },
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
            "name": script.name, "version": "2.1.0-rc.2", "sha256": sha256(script),
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
