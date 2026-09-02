#!/usr/bin/env python3
"""根据用户覆盖、同模型历史裁决与实际工具能力选择执行Profile。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional


PROFILES = {"FULL_AUTONOMY", "GUIDED", "WEAK_MODEL"}
SELECTOR_VERSION = "2.1.0-dev"
PROFILE_FILES = {
    "FULL_AUTONOMY": "references/profiles/full-autonomy.md",
    "GUIDED": "references/profiles/guided.md",
    "WEAK_MODEL": "references/profiles/weak-model.md",
}

# 只有能指向产出执行本身的明确错误，才允许把历史结果解释为模型执行失败。
# 研究材料不足、设计/协议模式和外部能力缺口不属于此集合。
EXECUTION_FAILURE_MARKERS = (
    "EXECUTION_FAILED", "EXECUTION_ERROR", "BODY_MISSING", "BODY_INCOMPLETE",
    "BODY_EMPTY", "BODY_ABSENT", "BODY_LENGTH_LOW", "MISSING_BODY",
    "FILE_MISSING", "OUTPUT_MISSING", "OUTPUT_FILE_MISSING", "STRUCTURE_INVALID",
    "STRUCTURE_BROKEN", "DRAFT_MISSING", "CONTENT_MISSING",
)
NON_EXECUTION_MARKERS = (
    "CAPABILITY", "QUOTA", "RATE_LIMIT", "MATERIAL", "EVIDENCE", "DESIGN_ONLY",
    "PROTOCOL_ONLY", "EXTERNAL", "TOOL_GAP", "NOT_APPLICABLE",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON根对象必须为对象: {path}")
    return payload


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="选择AIWritePaper执行Profile")
    parser.add_argument("--capability-report", required=True, type=Path)
    parser.add_argument("--model-label", required=True)
    parser.add_argument("--requested-profile", choices=sorted(PROFILES), default=None)
    parser.add_argument("--prior-adjudication", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def _client_identity(payload: Dict[str, Any]) -> Optional[str]:
    """读取历史记录中的客户端身份，兼容旧报告的字段名。"""
    for key in ("agent_adapter", "client_label", "client", "client_identity"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _same_execution_identity(
    identity: Dict[str, Any], model_label: str, client_label: Optional[str]
) -> bool:
    if identity.get("model_label") != model_label:
        return False
    # 当前能力报告有客户端身份时，历史报告必须有同一身份；避免只凭模型名串用结果。
    if client_label is None:
        return True
    return _client_identity(identity) == client_label


def _issue_values(payload: Dict[str, Any]) -> List[str]:
    """提取结构化问题码，并兼容报告原有的 errors/error 字段。"""
    values: List[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, str):
            values.append(value.upper())
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            # 同一问题的类别和原因保持在一起，避免把“因工具缺失而缺文件”拆成执行失败。
            fields = [value[key] for key in ("code", "reason_code", "reason", "type", "category") if isinstance(value.get(key), str)]
            if fields:
                values.append(" ".join(fields).upper())

    for key in ("execution_issues", "reason_codes", "errors", "error"):
        collect(payload.get(key))
    reports = payload.get("reports")
    if isinstance(reports, dict):
        for report in reports.values():
            if isinstance(report, dict):
                for key in ("execution_issues", "errors", "error"):
                    collect(report.get(key))
    status = payload.get("authoritative_status")
    if isinstance(status, dict):
        for key in ("execution_issues", "errors", "error"):
            collect(status.get(key))
    return values


def _execution_failure_reasons(payload: Dict[str, Any]) -> List[str]:
    reasons: List[str] = []
    for value in _issue_values(payload):
        if any(marker in value for marker in NON_EXECUTION_MARKERS):
            continue
        if any(marker in value for marker in EXECUTION_FAILURE_MARKERS):
            reasons.append(value.split(":", 1)[0].strip())
    return list(dict.fromkeys(reasons))


def select_profile(
    capability: Dict[str, Any], model_label: str, requested: Optional[str],
    priors: List[tuple[Path, Dict[str, Any]]],
) -> tuple[str, str, List[str], List[Dict[str, Any]]]:
    reasons: List[str] = []
    matched_priors: List[Dict[str, Any]] = []
    if requested:
        reasons.append("USER_OVERRIDE")
        return requested, "USER_OVERRIDE", reasons, matched_priors

    prior_fail_reasons: List[str] = []
    prior_partial_reasons: List[str] = []
    client_label = _client_identity(capability)
    for path, payload in priors:
        identity = payload.get("run_identity")
        if not isinstance(identity, dict) or not _same_execution_identity(
            identity, model_label, client_label
        ):
            continue
        authoritative = payload.get("authoritative_status")
        if not isinstance(authoritative, dict):
            continue
        final_status = authoritative.get("final_status")
        delivery_status = authoritative.get("delivery_status")
        matched_priors.append({
            "path": str(path), "sha256": sha256(path),
            "final_status": final_status, "delivery_status": delivery_status,
        })
        execution_reasons = _execution_failure_reasons(payload)
        if final_status == "FAIL" and execution_reasons:
            prior_fail_reasons.extend(execution_reasons)
        elif (final_status == "PARTIAL" or delivery_status == "PARTIAL") and execution_reasons:
            prior_partial_reasons.extend(execution_reasons)
    if prior_fail_reasons:
        reasons.extend(["SAME_MODEL_PRIOR_FAIL", *prior_fail_reasons])
        return "WEAK_MODEL", "PRIOR_ADJUDICATION", reasons, matched_priors
    if prior_partial_reasons:
        reasons.extend(["SAME_MODEL_PRIOR_PARTIAL", *prior_partial_reasons])
        return "GUIDED", "PRIOR_ADJUDICATION", reasons, matched_priors

    missing_delivery_tools: List[str] = []
    for field in ["docx_export", "pdf_export"]:
        value = capability.get(field)
        if not isinstance(value, dict) or value.get("available") is not True:
            missing_delivery_tools.append(field)
    if missing_delivery_tools:
        reasons.extend(f"CAPABILITY_GAP_{field.upper()}" for field in missing_delivery_tools)
        reasons.append("CAPABILITY_GAP_LOCAL_HINT_ONLY")

    reasons.append("NO_WEAK_SIGNAL")
    return "FULL_AUTONOMY", "DEFAULT_STRONG_PRESERVING", reasons, matched_priors


def main() -> int:
    args = parse_args()
    capability_path = args.capability_report.expanduser().resolve()
    capability = load_json(capability_path)
    if capability.get("schema_version") != "1.0":
        raise ValueError("当前Profile选择器只接受Capability Report schema_version=1.0")
    prior_payloads: List[tuple[Path, Dict[str, Any]]] = []
    for prior in args.prior_adjudication:
        path = prior.expanduser().resolve()
        prior_payloads.append((path, load_json(path)))
    profile, source, reasons, matched = select_profile(
        capability, args.model_label, args.requested_profile, prior_payloads
    )
    script = Path(__file__).resolve()
    payload = {
        "schema_version": "1.0",
        "selected_profile": profile,
        "selection_source": source,
        "model_label": args.model_label,
        "agent_adapter": capability.get("agent_adapter"),
        "compiled_variant": "compact" if profile == "WEAK_MODEL" else "full",
        "profile_rules": PROFILE_FILES[profile],
        "reason_codes": reasons,
        "capability_report": str(capability_path),
        "capability_report_sha256": sha256(capability_path),
        "matched_prior_adjudications": matched,
        "selector": {
            "name": script.name, "version": SELECTOR_VERSION, "sha256": sha256(script),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    atomic_write(args.output.expanduser().resolve(), rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
