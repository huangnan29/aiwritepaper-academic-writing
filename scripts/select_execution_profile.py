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
PROFILE_FILES = {
    "FULL_AUTONOMY": "references/profiles/full-autonomy.md",
    "GUIDED": "references/profiles/guided.md",
    "WEAK_MODEL": "references/profiles/weak-model.md",
}


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


def select_profile(
    capability: Dict[str, Any], model_label: str, requested: Optional[str],
    priors: List[tuple[Path, Dict[str, Any]]],
) -> tuple[str, str, List[str], List[Dict[str, Any]]]:
    reasons: List[str] = []
    matched_priors: List[Dict[str, Any]] = []
    if requested:
        reasons.append("USER_OVERRIDE")
        return requested, "USER_OVERRIDE", reasons, matched_priors

    prior_fail = False
    prior_partial = False
    for path, payload in priors:
        identity = payload.get("run_identity")
        if not isinstance(identity, dict) or identity.get("model_label") != model_label:
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
        if final_status == "FAIL":
            prior_fail = True
        elif final_status == "PARTIAL" or delivery_status == "PARTIAL":
            prior_partial = True
    if prior_fail:
        reasons.append("SAME_MODEL_PRIOR_FAIL")
        return "WEAK_MODEL", "PRIOR_ADJUDICATION", reasons, matched_priors
    if prior_partial:
        reasons.append("SAME_MODEL_PRIOR_PARTIAL")
        return "GUIDED", "PRIOR_ADJUDICATION", reasons, matched_priors

    missing_delivery_tools: List[str] = []
    for field in ["docx_export", "pdf_export"]:
        value = capability.get(field)
        if not isinstance(value, dict) or value.get("available") is not True:
            missing_delivery_tools.append(field)
    if missing_delivery_tools:
        reasons.extend(f"CAPABILITY_GAP_{field.upper()}" for field in missing_delivery_tools)
        return "GUIDED", "CAPABILITY_GAP", reasons, matched_priors

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
            "name": script.name, "version": "1.6.0", "sha256": sha256(script),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    atomic_write(args.output.expanduser().resolve(), rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
