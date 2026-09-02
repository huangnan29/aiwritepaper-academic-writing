#!/usr/bin/env python3
"""论文任务的准备/检查入口；只处理确定性准备，不生成论文或判断研究方法。"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from compose_prompt import compose, read_utf8, task_parts
from resolve_default_length import resolve as resolve_length
from select_execution_profile import select_profile, PROFILE_FILES, SELECTOR_VERSION

SKILL_ROOT = Path(__file__).resolve().parents[1]
CAPABILITIES = ("image_generation", "visual_inspection", "docx_export", "pdf_export")
CALLERS = {"CURRENT_AGENT", "PARENT_AGENT", "CLIENT", "MCP_OR_PLUGIN"}


def encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}必须明确提供，工具不能代模型判断")
    return value.strip()


def positive(value: Any, field: str, zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if zero else 1):
        raise ValueError(f"{field}必须是{'非负' if zero else '正'}整数")
    return value


def resolve_features(request: dict, catalog: dict, direction: str) -> tuple[list[str], str]:
    """方向默认优先；模型只需声明增删覆盖。保留旧features精确列表兼容。"""
    allowed = set(catalog["features"])
    legacy = request.get("features")
    if legacy is not None:
        if not isinstance(legacy, list) or any(not isinstance(item, str) or item not in allowed for item in legacy):
            raise ValueError("features必须是已知模块列表")
        if len(legacy) != len(set(legacy)):
            raise ValueError("features不能重复")
        return legacy, "LEGACY_EXPLICIT"
    defaults = catalog.get("direction_defaults", {}).get(direction)
    if not isinstance(defaults, list) or any(item not in allowed for item in defaults):
        raise ValueError(f"方向缺少合法DEFAULT_FEATURES: {direction}")
    override = request.get("feature_overrides", {})
    if override is None:
        override = {}
    if not isinstance(override, dict):
        raise ValueError("feature_overrides必须是对象")
    add = override.get("add", [])
    remove = override.get("remove", [])
    if any(not isinstance(items, list) for items in (add, remove)):
        raise ValueError("feature_overrides.add/remove必须是列表")
    if any(item not in allowed for item in [*add, *remove]):
        raise ValueError("feature_overrides含未知模块")
    if set(add) & set(remove):
        raise ValueError("同一模块不能同时增加和移除")
    selected = [item for item in defaults if item not in remove]
    selected.extend(item for item in add if item not in selected)
    return selected, "DIRECTION_DEFAULT_WITH_OVERRIDE"


def capability_report(request: dict, adapter: str) -> dict:
    """规范四项三态能力；工具只记录，不把未知推断成不可用。"""
    recorded = datetime.now().astimezone().isoformat(timespec="seconds")
    observed = request.get("observed_at")
    if observed is not None:
        if not isinstance(observed, str):
            raise ValueError("observed_at必须是带时区的时间字符串")
        try:
            stamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("缺少时区")
        except ValueError as exc:
            raise ValueError("observed_at需带时区的真实观察时间") from exc
    source = request.get("capabilities")
    if not isinstance(source, dict):
        source = {name: None for name in CAPABILITIES}
    details = request.get("capability_details", {})
    if not isinstance(details, dict):
        raise ValueError("capability_details必须是对象")
    result = {"schema_version": "2.1", "agent_adapter": adapter, "recorded_at": recorded,
              "observed_at": observed}
    for name in CAPABILITIES:
        item = source.get(name)
        if isinstance(item, dict):  # 兼容2.0请求
            available = item.get("available")
            if available not in {True, False, None}:
                raise ValueError(f"capabilities.{name}.available必须为true、false或null")
            tools = item.get("tools", [])
            callers = item.get("callers", [])
            if not isinstance(tools, list) or not isinstance(callers, list):
                raise ValueError(f"{name}.tools/callers必须是列表")
            detail = {
                "tool": tools[0] if tools else None,
                "caller": callers[0] if callers else None,
                "evidence": item.get("evidence"),
            }
        else:
            available = item
            if available not in {True, False, None}:
                raise ValueError(f"capabilities.{name}必须为true、false或null")
            raw_detail = details.get(name, {})
            if raw_detail is None:
                raw_detail = {}
            if not isinstance(raw_detail, dict):
                raise ValueError(f"capability_details.{name}必须是对象")
            detail = {key: raw_detail.get(key) for key in ("tool", "caller", "evidence")}
        if detail.get("caller") is not None and detail["caller"] not in CALLERS:
            raise ValueError(f"{name}.caller含未知调用层")
        result[name] = {"available": available, **detail}
    return result


def prepare(root: Path, request_file: Path, preview: bool = False) -> dict:
    """先计算并验证全部输入，再新建准备结果；不覆盖已有运行或用户文件。"""
    root = root.expanduser().resolve()
    source = request_file.expanduser().resolve()
    request_bytes = read_utf8(source)
    request = json.loads(request_bytes)
    if not isinstance(request, dict) or request.get("schema_version") != "1.0":
        raise ValueError("paper-request.json必须为schema_version=1.0对象")
    if request.get("example_only"):
        raise ValueError("这是示例模板，须替换为实际任务和能力观察")
    catalog = json.loads(read_utf8(SKILL_ROOT / "references/prompt-modules.json"))
    mode = request.get("run_mode", "FULL_BUILD")
    if mode in {"AUTO_COMPLETE", "AUTO_BENCHMARK"}:
        mode = "FULL_BUILD"
    if mode not in catalog["modes"]:
        raise ValueError("续跑/修改稿不能重新prepare；使用原续跑或修改稿入口")
    direction = nonempty(request.get("direction_id"), "direction_id")
    valid = {p.stem for p in (SKILL_ROOT / "references/directions").glob("*.md")}
    if direction not in valid:
        raise ValueError("direction_id必须由模型选择一个已有方向")
    adapter = nonempty(request.get("agent_adapter"), "agent_adapter")
    adapters = {p.stem for p in (SKILL_ROOT / "references/integrations").glob("*.md")}
    if adapter not in adapters:
        raise ValueError("agent_adapter不是已有适配器，请按实际工具选择")
    title = nonempty(request.get("paper_title"), "paper_title")
    model = nonempty(request.get("model_label"), "model_label（未知可写UNKNOWN）")
    capability = capability_report(request, adapter)
    requested = request.get("execution_profile")
    if requested is not None and requested not in {"FULL_AUTONOMY", "GUIDED", "WEAK_MODEL"}:
        raise ValueError("execution_profile无效")
    prior_files = request.get("prior_adjudications", [])
    if not isinstance(prior_files, list) or any(not isinstance(x, str) for x in prior_files):
        raise ValueError("prior_adjudications只能列用户授权的报告路径")
    priors = []
    for item in prior_files:
        path = Path(item).expanduser()
        path = path.resolve() if path.is_absolute() else (root / path).resolve()
        payload = json.loads(read_utf8(path))
        if not isinstance(payload, dict):
            raise ValueError("历史裁决不是对象")
        priors.append((path, payload))
    if mode != "FULL_BUILD" and requested not in {None, "FULL_AUTONOMY"}:
        raise ValueError("局部模式不附加整篇阶段卡")
    profile, selection_source, reasons, matched = select_profile(capability, model, requested, priors if mode == "FULL_BUILD" else [])

    document = request.get("document_profile", "THESIS")
    level = request.get("paper_level", "UNSPECIFIED")
    language = request.get("language", "zh-CN")
    if document not in {"THESIS", "JOURNAL", "REPORT", "CUSTOM"} or level not in {"UNSPECIFIED", "UNDERGRADUATE", "MASTER", "DOCTORAL"}:
        raise ValueError("文档类型或论文层次无效")
    nonempty(language, "language")
    explicit = request.get("target_length")
    if explicit is not None:
        positive(explicit, "target_length")
    lengths = resolve_length(document, level, language.lower(), explicit)
    for key, dest in [("min_length", "minimum"), ("max_length", "maximum")]:
        if key in request:
            lengths[dest] = positive(request[key], key)
    if not lengths["minimum"] <= lengths["target"] <= lengths["maximum"]:
        raise ValueError("篇幅上下限必须包含目标")
    title_policy = request.get("title_policy")
    if title_policy is None:
        title_policy = "SAFE_DOWNGRADE" if request.get("auto_complete_without_pause") is True else "ASK"
    if title_policy not in {"STRICT", "ASK", "SAFE_DOWNGRADE"}:
        raise ValueError("title_policy必须为STRICT、ASK或SAFE_DOWNGRADE")
    params = {"RUN_MODE": mode, "OUTPUT_DIR": str(root), "MODEL_LABEL": model, "RUN_LABEL": request.get("run_label", root.name), "DIRECTION_ID": direction,
              "PAPER_TITLE": title, "DOCUMENT_PROFILE": document, "PAPER_LEVEL": level, "LANGUAGE": language,
              "EXECUTION_PROFILE": profile, "TITLE_POLICY": title_policy,
              "TARGET_LENGTH": lengths["target"], "MIN_LENGTH": lengths["minimum"], "MAX_LENGTH": lengths["maximum"]}
    for key in ["min_references", "target_figures", "target_tables"]:
        if key in request:
            params[key.upper()] = positive(request[key], key, zero=True)
    for key in ["paper_type", "citation_style", "research_question", "research_method", "materials"]:
        if key in request:
            params[key.upper()] = request[key]
    constraints = request.get("constraints", "")
    if not isinstance(constraints, str):
        raise ValueError("constraints需保留用户约束的文本")
    params_bytes = ("# 本次运行契约\n\n```yaml\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in params.items()) + "\n```\n\n## 用户材料与限制\n\n" + constraints + "\n").encode("utf-8")
    features, feature_source = resolve_features(request, catalog, direction)
    task = {"schema_version": "1.0", "run_mode": mode, "direction_id": direction,
            "features": features, "feature_source": feature_source}
    variant = "compact" if profile == "WEAK_MODEL" else "full"
    folder = "compact-prompts" if variant == "compact" else "compiled-prompts"
    compiled_path = SKILL_ROOT / "references" / folder / f"{direction}-{variant}.md"
    chosen, modules = task_parts(read_utf8(compiled_path), task, params_bytes)
    adapter_path = SKILL_ROOT / "references/integrations" / f"{adapter}.md"
    parts = [params_bytes, chosen, read_utf8(adapter_path)]
    source_paths = [compiled_path, adapter_path]
    addon = {"PROPOSAL_ONLY": "proposal-report.md", "DEFENSE_ONLY": "defense-presentation.md"}.get(mode)
    if addon:
        path = SKILL_ROOT / "references/deliverables" / addon
        parts.append(read_utf8(path)); source_paths.append(path)
    checkpoints = None
    if profile != "FULL_AUTONOMY":
        template = SKILL_ROOT / "references/profiles/execution-checkpoints-template.json"
        rules = SKILL_ROOT / "references/profiles/staged-assistance.md"
        parts.extend([read_utf8(template), read_utf8(rules)]); source_paths.extend([template, rules])
        checkpoints = json.loads(read_utf8(template)); checkpoints["execution_profile"] = profile
    prompt = compose(parts)
    skill_text = read_utf8(SKILL_ROOT / "SKILL.md").decode()
    version = re.search(r'version:\s*"([^\"]+)"', skill_text).group(1)
    profile_report = {"schema_version": "1.0", "selected_profile": profile, "selection_source": selection_source,
                      "model_label": model, "agent_adapter": adapter, "compiled_variant": variant, "profile_rules": PROFILE_FILES[profile], "reason_codes": reasons,
                      "matched_prior_adjudications": matched, "capability_report": "00-capability-report.json",
                      "capability_report_sha256": sha(encoded(capability)), "selector": {"name": "select_execution_profile.py", "version": SELECTOR_VERSION, "sha256": sha(read_utf8(SKILL_ROOT / "scripts/select_execution_profile.py")), "generated_at": datetime.now().astimezone().isoformat()}}
    manifest = {"run_mode": mode, "model_label": model, "skill_version": version, "direction_id": direction, "agent_adapter": adapter,
                "execution_profile": profile, "profile_selection_report": "00-profile-selection.json", "paper_title": title,
                "paper_level": level, "document_profile": document, "manuscript_language": language,
                "abstract_contract": "BILINGUAL" if language.startswith("zh") and document in {"THESIS", "JOURNAL"} and mode not in {"PROPOSAL_ONLY", "DEFENSE_ONLY"} else "PRIMARY_ONLY",
                "target_length": lengths["target"], "min_length": lengths["minimum"], "max_length": lengths["maximum"],
                "reexport_documents": mode == "FIGURES_ONLY" and "documents" in task["features"],
                "title_policy": title_policy, "requested_title": title, "final_title": title,
                "active_prompt": "final-execution-prompt.md", "active_prompt_composition": "00-prompt-composition.json",
                "prompt_revision": 1,
                "preparation_status": "PREPARED_NOT_EXECUTED", "state_contract": "DERIVED_ONLY",
                "citation_mode": request.get("citation_mode", "NUMERIC")}
    if manifest["citation_mode"] not in {"NUMERIC", "AUTHOR_YEAR"}:
        raise ValueError("citation_mode无效")
    for key in ["min_references", "target_figures", "target_tables", "citation_mode", "research_claim_level"]:
        if key in request:
            manifest[key] = request[key]
    if "research_claim_level" in manifest and manifest["research_claim_level"] not in {"OBSERVED_STUDY", "DESIGN_ONLY", "PROTOCOL_ONLY", "REVIEW_SYNTHESIS"}:
        raise ValueError("research_claim_level无效")
    if checkpoints is not None:
        manifest["execution_checkpoints"] = "00-execution-checkpoints.json"
    outputs = {"run-params.md": params_bytes, "00-capability-report.json": encoded(capability), "00-profile-selection.json": encoded(profile_report),
               "task-selection.json": encoded(task), "final-execution-prompt.md": prompt, "run-manifest.json": encoded(manifest)}
    if checkpoints is not None:
        outputs["00-execution-checkpoints.json"] = encoded(checkpoints)
    hashes = {str(root / name): sha(data) for name, data in outputs.items() if name != "final-execution-prompt.md"}
    hashes.update({str(path): sha(read_utf8(path)) for path in source_paths})
    hashes[str(source)] = sha(request_bytes)
    report = {"status": "OK", "output": str(root / "final-execution-prompt.md"), "bytes": len(prompt), "sha256": sha(prompt),
              "inputs": list(hashes), "input_sha256": hashes, "execution_profile": profile, "task_selection": task, "selected_modules": modules,
              "scope_note": "仅完成准备；未检索、未写正文、未生图、未导出、未验证质量。"}
    outputs["00-prompt-composition.json"] = encoded(report)
    for name in outputs:
        path = root / name
        if path.exists() or path.is_symlink():
            raise ValueError(f"准备结果已存在，拒绝覆盖：{name}；继续已有任务请使用resume")
        if path.resolve() == source:
            raise ValueError("输出不能覆盖paper-request.json")
    result = {"status": "PREVIEW" if preview else "PREPARED_NOT_EXECUTED", "run_mode": mode, "execution_profile": profile,
              "prompt": str(root / "final-execution-prompt.md"), "prompt_bytes": len(prompt), "selected_modules": modules,
              "target_length": lengths["target"], "next_action": "完整读取唯一提示词，进行当前任务；不要重复创建兼容元数据文件。"}
    if preview:
        return result
    root.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for name, data in outputs.items():
            path = root / name
            with path.open("xb") as handle:
                handle.write(data); handle.flush(); os.fsync(handle.fileno())
            created.append(path)
    except OSError as exc:
        raise ValueError(f"准备写入中断，未覆盖旧文件；已新建{[p.name for p in created]}，请检查后恢复：{exc}") from exc
    return result


def _json_object(path: Path) -> dict:
    value = json.loads(read_utf8(path))
    if not isinstance(value, dict):
        raise ValueError(f"JSON根对象必须是对象: {path.name}")
    return value


def _feature_has_artifacts(root: Path, feature: str, manifest: dict) -> bool:
    checks = {
        "figures": [root / "figures/figure-manifest.json"],
        "statistics": [root / "data/data-provenance.json", root / "figures/statistical-figures.json"],
        "svg": list((root / "figures").glob("*.svg")) if (root / "figures").is_dir() else [],
        "formulas": [root / "equations/formula-audit.md", root / "equations/formula-verification.json"],
        "documents": [root / str(manifest.get("docx", "__missing__")), root / str(manifest.get("pdf", "__missing__"))],
    }
    return any(path.is_file() and path.stat().st_size > 0 for path in checks[feature])


def amend(root: Path, amendment_file: Path, preview: bool = False) -> dict:
    """只追加模块或执行获准的安全题目降级；保留全部旧提示词和摘要。"""
    root = root.expanduser().resolve()
    source = amendment_file.expanduser().resolve()
    amendment = _json_object(source)
    if amendment.get("schema_version") != "1.0":
        raise ValueError("prompt-amendment.json必须为schema_version=1.0")
    reason = nonempty(amendment.get("reason"), "reason")
    manifest = _json_object(root / "run-manifest.json")
    task_name = manifest.get("active_task_selection", "task-selection.json")
    task = _json_object(root / task_name)
    current_prompt_name = manifest.get("active_prompt", "final-execution-prompt.md")
    current_prompt = root / current_prompt_name
    if not current_prompt.is_file():
        raise ValueError("活动执行提示词缺失，不能amend")
    catalog = _json_object(SKILL_ROOT / "references/prompt-modules.json")
    allowed = set(catalog["features"])
    add = amendment.get("add_features", [])
    remove = amendment.get("remove_features", [])
    if not isinstance(add, list) or not isinstance(remove, list):
        raise ValueError("add_features/remove_features必须是列表")
    if any(item not in allowed for item in [*add, *remove]):
        raise ValueError("amend含未知模块")
    if set(add) & set(remove):
        raise ValueError("同一模块不能同时增加和移除")
    before = list(task.get("features", []))
    if any(item not in allowed for item in before):
        raise ValueError("现有task-selection含未知模块")
    for feature in remove:
        if _feature_has_artifacts(root, feature, manifest):
            raise ValueError(f"{feature}已有产物，不能通过amend移除")
    after = [item for item in before if item not in remove]
    after.extend(item for item in add if item not in after)

    title_change = amendment.get("title_change")
    final_title = manifest.get("final_title", manifest.get("paper_title"))
    title_record = None
    if title_change is not None:
        if not isinstance(title_change, dict):
            raise ValueError("title_change必须是对象")
        policy = manifest.get("title_policy", "ASK")
        if policy == "STRICT":
            raise ValueError("TITLE_POLICY=STRICT，禁止改题")
        if policy == "ASK" and title_change.get("user_authorized") is not True:
            raise ValueError("TITLE_POLICY=ASK时必须记录用户明确授权")
        rule_id = title_change.get("rule_id")
        if rule_id not in {"EFFECT_TO_ASSOCIATION", "IMPLEMENTATION_TO_DESIGN", "EMPIRICAL_TO_REVIEW"}:
            raise ValueError("题目降级只能使用预定义规则")
        final_title = nonempty(title_change.get("final_title"), "title_change.final_title")
        title_record = {
            "requested_title": manifest.get("requested_title", manifest.get("paper_title")),
            "previous_title": manifest.get("final_title", manifest.get("paper_title")),
            "final_title": final_title,
            "rule_id": rule_id,
            "evidence_gap": nonempty(title_change.get("evidence_gap"), "title_change.evidence_gap"),
            "user_authorized": title_change.get("user_authorized") is True,
        }
    if after == before and title_record is None:
        raise ValueError("amend没有产生任何变化")

    revision = int(manifest.get("prompt_revision", 1)) + 1
    suffix = f"v{revision}"
    params_name = f"run-params.{suffix}.md"
    task_output_name = f"task-selection.{suffix}.json"
    prompt_name = f"final-execution-prompt.{suffix}.md"
    report_name = f"00-prompt-composition.{suffix}.json"
    record_name = f"prompt-amendment.{suffix}.json"
    for name in (params_name, task_output_name, prompt_name, report_name, record_name):
        if (root / name).exists():
            raise ValueError(f"amend目标已存在，拒绝覆盖: {name}")

    original_params = read_utf8(root / manifest.get("active_run_params", "run-params.md"))
    amendment_block = {
        "PROMPT_REVISION": revision,
        "FEATURES_BEFORE": before,
        "FEATURES_AFTER": after,
        "AMEND_REASON": reason,
        "FINAL_TITLE": final_title,
    }
    params_bytes = original_params.rstrip(b"\r\n") + (
        "\n\n## 提示词修订记录\n\n```yaml\n" +
        "\n".join(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in amendment_block.items()) +
        "\n```\n"
    ).encode("utf-8")
    new_task = {**task, "features": after, "feature_source": "AMENDMENT", "prompt_revision": revision}
    profile = manifest.get("execution_profile", "FULL_AUTONOMY")
    variant = "compact" if profile == "WEAK_MODEL" else "full"
    direction = manifest.get("direction_id")
    compiled = SKILL_ROOT / "references" / ("compact-prompts" if variant == "compact" else "compiled-prompts") / f"{direction}-{variant}.md"
    chosen, modules = task_parts(read_utf8(compiled), new_task, params_bytes)
    adapter = SKILL_ROOT / "references/integrations" / f"{manifest.get('agent_adapter')}.md"
    parts = [params_bytes, chosen, read_utf8(adapter)]
    sources = [compiled, adapter]
    addon = {"PROPOSAL_ONLY": "proposal-report.md", "DEFENSE_ONLY": "defense-presentation.md"}.get(manifest.get("run_mode"))
    if addon:
        path = SKILL_ROOT / "references/deliverables" / addon
        parts.append(read_utf8(path)); sources.append(path)
    if profile != "FULL_AUTONOMY":
        template = SKILL_ROOT / "references/profiles/execution-checkpoints-template.json"
        rules = SKILL_ROOT / "references/profiles/staged-assistance.md"
        parts.extend([read_utf8(template), read_utf8(rules)]); sources.extend([template, rules])
    prompt = compose(parts)
    invalidated = []
    if (root / "07-paper-full.md").is_file():
        invalidated = ["FIGURES", "DOCUMENTS", "VALIDATION"] if set(add + remove) & {"figures", "statistics", "svg", "formulas", "documents"} else ["VALIDATION"]
    amendment_record = {
        "schema_version": "1.0", "revision": revision, "reason": reason,
        "features_before": before, "features_after": after, "title_change": title_record,
        "previous_prompt": current_prompt_name, "previous_prompt_sha256": sha(read_utf8(current_prompt)),
        "active_prompt": prompt_name, "active_prompt_sha256": sha(prompt),
        "invalidated_stages": invalidated, "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    report = {
        "status": "OK", "output": str(root / prompt_name), "bytes": len(prompt), "sha256": sha(prompt),
        "inputs": [str(path) for path in [root / params_name, compiled, adapter, source]],
        "selected_modules": modules, "prompt_revision": revision,
        "previous_prompt_sha256": amendment_record["previous_prompt_sha256"],
        "scope_note": "只修订活动提示词；旧提示词与旧摘要保留，失效阶段必须重检。",
    }
    next_manifest = {**manifest, "active_prompt": prompt_name, "active_prompt_composition": report_name,
                     "active_run_params": params_name,
                     "active_task_selection": task_output_name, "prompt_revision": revision,
                     "final_title": final_title, "validation_invalidated": invalidated,
                     "preparation_status": "AMENDED_NOT_EXECUTED"}
    outputs = {
        params_name: params_bytes, task_output_name: encoded(new_task), prompt_name: prompt,
        report_name: encoded(report), record_name: encoded(amendment_record),
    }
    result = {"status": "PREVIEW" if preview else "AMENDED_NOT_EXECUTED", "prompt": str(root / prompt_name),
              "prompt_bytes": len(prompt), "revision": revision, "selected_modules": modules,
              "invalidated_stages": invalidated}
    if preview:
        return result
    for name, data in outputs.items():
        with (root / name).open("xb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    temporary = root / ".run-manifest.next.json"
    temporary.write_bytes(encoded(next_manifest))
    os.replace(temporary, root / "run-manifest.json")
    return result


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "check":
        from check_paper import main as check_main
        return check_main(argv[1:])
    if argv and argv[0] == "resume":
        return subprocess.run([sys.executable, str(SKILL_ROOT / "scripts/prepare_resume.py"), *argv[1:]]).returncode
    parser = argparse.ArgumentParser(description="AIWritePaper：一次准备、一次检查；研究写作仍由模型决定")
    parser.add_argument("action", choices=["prepare"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--request", type=Path)
    parser.add_argument("--amend", action="store_true")
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args(argv)
    try:
        default_name = "prompt-amendment.json" if args.amend else "paper-request.json"
        request_arg = args.request or Path(default_name)
        request = request_arg if request_arg.is_absolute() else args.root / request_arg
        result = amend(args.root, request, args.preview) if args.amend else prepare(args.root, request, args.preview)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "PREPARATION_BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
