#!/usr/bin/env python3
"""按固定顺序合成单一最终执行提示词，不参与任何论文决策。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import tempfile
from typing import List, Optional


SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATTERN = re.compile(r"<!-- task-module:([a-z0-9-]+) -->\n(.*?)\n<!-- /task-module -->", re.DOTALL)


def task_parts(compiled: bytes, selection: dict, params: bytes) -> tuple[bytes, list[str]]:
    """只按模型显式选择抽取完整模块，不推断论文方法或改写模块原文。"""
    catalog = json.loads(read_utf8(SKILL_ROOT / "references/prompt-modules.json"))
    if not isinstance(selection, dict) or selection.get("schema_version") != "1.0":
        raise ValueError("任务选择必须为schema_version=1.0对象")
    mode = selection.get("run_mode")
    if mode not in catalog["modes"]:
        raise ValueError("不支持的合成模式；RESUME不得重建，REVISE_ONLY请用compose_revision.py")
    features = selection.get("features")
    if not isinstance(features, list) or any(not isinstance(x, str) or x not in catalog["features"] for x in features):
        raise ValueError("features必须显式列出支持的模块名称")
    if len(set(features)) != len(features):
        raise ValueError("features不能重复")
    if mode == "EXPORT_ONLY" and set(features) - {"documents", "formulas"}:
        raise ValueError("EXPORT_ONLY不得合入生图、统计或SVG生产模块")
    if mode == "FULL_BUILD":
        count = re.search(r"(?mi)^\s*TARGET_FIGURES\s*:\s*[\"']?(\d+)", params.decode("utf-8"))
        if count and int(count.group(1)) > 0 and not set(features) & {"figures", "statistics", "svg"}:
            raise ValueError("契约要求图片却未选择配图模块")
    for field, wanted in [("RUN_MODE", mode), ("DIRECTION_ID", selection.get("direction_id"))]:
        match = re.search(rf"(?m)^\s*{field}\s*:\s*[\"']?([^\s\"'`]+)", params.decode("utf-8"))
        value = match.group(1) if match else None
        if field == "RUN_MODE" and value in {"AUTO_COMPLETE", "AUTO_BENCHMARK"}:
            value = "FULL_BUILD"
        if match and value != wanted:
            raise ValueError(f"任务选择与run-params.md的{field}冲突")
    source = compiled.decode("utf-8")
    blocks = MODULE_PATTERN.findall(source)
    if not blocks or len(blocks) != len({name for name, _ in blocks}):
        raise ValueError("所选提示词缺少唯一模块边界，请用当前版本维护构建更新")
    selected = set(catalog["always"] + catalog["modes"][mode])
    for feature in features:
        selected.update(catalog["features"][feature])
    missing = selected - {name for name, _ in blocks}
    if missing:
        raise ValueError(f"提示词缺少模块：{sorted(missing)}")
    chosen = [(name, body) for name, body in blocks if name in selected]
    boundaries = {
        "FULL_BUILD": "完成当前契约的研究与论文交付。",
        "FIGURES_ONLY": "只优化用户授权的图片，不改正文主张；只有features包含documents且用户要求时才重导文档。",
        "EXPORT_ONLY": "只将已有定稿导出，不开展检索、改写正文或重新生图。",
        "AUDIT_ONLY": "只读检查；不覆盖原文、旧报告或图像，检查输出放独立审计目录。",
        "PROPOSAL_ONLY": "只交付开题报告，以计划性时态表达，不提前生成论文结果。",
        "DEFENSE_ONLY": "只重组已有证据为答辩材料，不新增研究结果。",
    }
    header = f"# 当前任务执行边界：{mode}\n\n{boundaries[mode]}\n\n以下模块在合成前已确定；执行只读取这一份MD。\n"
    return compose([header.encode("utf-8"), *[body.encode("utf-8") for _, body in chosen]]), [name for name, _ in chosen]


def read_utf8(path: Path) -> bytes:
    """读取非空UTF-8文件，同时保留原始字节。"""
    data = path.read_bytes()
    if not data.strip():
        raise ValueError(f"输入文件为空: {path}")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"输入文件不是有效UTF-8: {path}") from exc
    return data


def compose(parts: List[bytes]) -> bytes:
    """仅规范文件边界换行，正文原始字节保持不变。"""
    return b"\n\n".join(part.rstrip(b"\r\n") for part in parts) + b"\n"


def atomic_write(output: Path, data: bytes) -> None:
    """在目标目录内原子替换，避免留下半写入文件。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=output.parent, prefix=f".{output.name}.", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, output)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="确定性合成 final-execution-prompt.md")
    parser.add_argument("--params", required=True, type=Path, help="本次 run-params.md")
    parser.add_argument("--compiled", required=True, type=Path, help="唯一 *-full.md或*-compact.md")
    parser.add_argument("--addon", action="append", default=[], type=Path, help="可重复的附加交付规则")
    parser.add_argument("--profile-selection", type=Path, default=None, help="00-profile-selection.json")
    parser.add_argument("--profile-rules", type=Path, default=None, help="GUIDED或WEAK_MODEL规则")
    parser.add_argument("--task-selection", type=Path, default=None, help="模型选择的模式、方向、功能模块，不推断研究内容")
    parser.add_argument("--output", required=True, type=Path, help="最终输出文件")
    parser.add_argument("--report", type=Path, default=None, help="保存00-prompt-composition.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = "FULL_AUTONOMY"
    selection_path: Optional[Path] = None
    selection_hash: Optional[str] = None
    if args.profile_selection is not None:
        selection_path = args.profile_selection.expanduser().resolve()
        selection = json.loads(read_utf8(selection_path).decode("utf-8"))
        if not isinstance(selection, dict) or selection.get("schema_version") != "1.0":
            raise ValueError("Profile Selection必须为schema_version=1.0对象")
        profile = str(selection.get("selected_profile") or "")
        if profile not in {"FULL_AUTONOMY", "GUIDED", "WEAK_MODEL"}:
            raise ValueError(f"selected_profile无效: {profile}")
        selection_hash = hashlib.sha256(selection_path.read_bytes()).hexdigest()

    if profile == "WEAK_MODEL":
        if not args.compiled.name.endswith("-compact.md"):
            raise ValueError("WEAK_MODEL必须使用*-compact.md")
        expected_profile_file = "staged-assistance.md"
    else:
        if not args.compiled.name.endswith("-full.md"):
            raise ValueError(f"{profile}必须使用*-full.md")
        expected_profile_file = "staged-assistance.md" if profile == "GUIDED" else None

    if expected_profile_file is None:
        if args.profile_rules is not None:
            raise ValueError("FULL_AUTONOMY不附加Profile任务卡，以保护强模型原执行路径")
        if any(path.name == "execution-checkpoints-template.json" for path in args.addon):
            raise ValueError("FULL_AUTONOMY不附加阶段模板")
    else:
        if args.profile_rules is None or args.profile_rules.name != expected_profile_file:
            raise ValueError(f"{profile}必须附加references/profiles/{expected_profile_file}")
        if not any(path.name == "execution-checkpoints-template.json" for path in args.addon):
            raise ValueError(f"{profile}必须把execution-checkpoints-template.json合入最终提示词")

    automatic_addons = []
    task_selection = None
    if args.task_selection:
        task_selection = json.loads(read_utf8(args.task_selection))
        if not isinstance(task_selection, dict):
            raise ValueError("任务选择必须为JSON对象")
        direction = task_selection.get("direction_id")
        if not isinstance(direction, str) or not re.fullmatch(r"[a-z0-9-]+", direction):
            raise ValueError("direction_id无效")
        if args.compiled.name not in {f"{direction}-full.md", f"{direction}-compact.md"}:
            raise ValueError("任务选择与所选方向文件不一致")
        if task_selection.get("run_mode") != "FULL_BUILD" and profile != "FULL_AUTONOMY":
            raise ValueError("局部任务不加载完整论文阶段卡；保留局部模式与当前工具辅助")
        allowed_addons = {p.resolve() for p in (SKILL_ROOT / "references/integrations").glob("*.md")}
        allowed_addons.add((SKILL_ROOT / "references/profiles/execution-checkpoints-template.json").resolve())
        delivery_name = {"PROPOSAL_ONLY": "proposal-report.md", "DEFENSE_ONLY": "defense-presentation.md"}.get(task_selection.get("run_mode"))
        if delivery_name:
            allowed_addons.add((SKILL_ROOT / "references/deliverables" / delivery_name).resolve())
        if any(path.expanduser().resolve() not in allowed_addons for path in args.addon):
            raise ValueError("任务合成只接受当前适配器及适用交付附件；额外用户约束写入run-params.md")
        adapters = [p for p in args.addon if p.expanduser().resolve().parent == (SKILL_ROOT / "references/integrations").resolve()]
        if len(adapters) != 1:
            raise ValueError("任务合成必须且只能选择一个实际Agent适配器")
        delivery = {"PROPOSAL_ONLY": "proposal-report.md", "DEFENSE_ONLY": "defense-presentation.md"}.get(task_selection.get("run_mode"))
        if delivery and not any(path.name == delivery for path in args.addon):
            automatic_addons.append(SKILL_ROOT / "references/deliverables" / delivery)

    inputs = [args.params, args.compiled, *args.addon, *automatic_addons]
    if args.profile_rules is not None:
        inputs.append(args.profile_rules)
    resolved_inputs = [path.expanduser().resolve() for path in inputs]
    output = args.output.expanduser().resolve()

    if len(set(resolved_inputs)) != len(resolved_inputs):
        raise ValueError("输入文件存在重复")
    if output in resolved_inputs:
        raise ValueError("输出文件不能覆盖输入文件")

    if args.report is not None:
        report_path = args.report.expanduser().resolve()
        if report_path == output or report_path in resolved_inputs:
            raise ValueError("合成报告不能覆盖输入或最终提示词")
    if args.task_selection and (output == args.task_selection.resolve() or (args.report and report_path == args.task_selection.resolve())):
        raise ValueError("输出不能覆盖任务选择")
    if selection_path and (output == selection_path or (args.report and report_path == selection_path)):
        raise ValueError("输出不能覆盖Profile选择")
    parts = [read_utf8(path) for path in resolved_inputs]
    selected_modules = None
    if task_selection is not None:
        parts[1], selected_modules = task_parts(parts[1], task_selection, parts[0])
    payload = compose(parts)
    atomic_write(output, payload)

    report = {
        "status": "OK",
        "output": str(output),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "inputs": [str(path) for path in resolved_inputs],
        "execution_profile": profile,
        "profile_selection": str(selection_path) if selection_path else None,
        "profile_selection_sha256": selection_hash,
        "task_selection": task_selection,
        "selected_modules": selected_modules,
        "input_sha256": {str(path): hashlib.sha256(read_utf8(path)).hexdigest() for path in resolved_inputs},
    }
    if args.task_selection:
        report["input_sha256"][str(args.task_selection.resolve())] = hashlib.sha256(read_utf8(args.task_selection)).hexdigest()
        report["module_catalog_sha256"] = hashlib.sha256(read_utf8(SKILL_ROOT / "references/prompt-modules.json")).hexdigest()
        report["scope_note"] = "模块选择不是能力认证；实际图片路线及调用仍由figure检查器核验。"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.report is not None:
        report_path = args.report.expanduser().resolve()
        if report_path == output or report_path in resolved_inputs:
            raise ValueError("合成报告不能覆盖输入或最终提示词")
        atomic_write(report_path, (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
