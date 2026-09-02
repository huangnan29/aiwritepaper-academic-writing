#!/usr/bin/env python3
"""验证同源编译、任务模块隔离、方向/Schema/版本和必要工具；不证明论文质量。"""
from __future__ import annotations
import json
import re
from pathlib import Path
from build_compiled import (
    SKILL_ROOT, COMMON_DIR, COMMON_FILES, COMPILED_DIR, COMPACT_DIR,
    compact_source, direction_files, full_source, render_compiled, render_compact,
)
from compose_prompt import MODULE_PATTERN, task_parts


def frontmatter_version(text):
    match = re.search(r'^\s*version:\s*["\']?([^"\'\s]+)', text, re.MULTILINE)
    return match.group(1) if match else None


def main():
    errors = []
    directions = direction_files()
    ids = {p.stem for p in directions}
    if len(ids) != 19:
        errors.append("方向必须仍有19个")
    for folder, suffix, renderer in [(COMPILED_DIR, "full", render_compiled), (COMPACT_DIR, "compact", render_compact)]:
        expected = {f"{p.stem}-{suffix}.md" for p in directions}
        if {p.name for p in folder.glob("*.md")} != expected:
            errors.append(f"{folder.name}文件集合不一致")
        for direction in directions:
            target = folder / f"{direction.stem}-{suffix}.md"
            if not target.is_file() or target.read_text(encoding="utf-8") != renderer(direction):
                errors.append(f"编译不同步：{target.name}")
            elif suffix == "full" and target.stat().st_size > 40000:
                errors.append(f"完整版超出40KB维护预算：{target.name}")
            elif suffix == "compact" and target.stat().st_size > 24000:
                errors.append(f"紧凑编译容器超出24KB维护预算：{target.name}")
    for direction in directions:
        text = render_compiled(direction)
        blocks = dict(MODULE_PATTERN.findall(text))
        for name in COMMON_FILES:
            source = full_source(COMMON_DIR / name)
            if text.count(source) != 1 or Path(name).stem not in blocks:
                errors.append(f"公共规则非单一来源：{direction.name}/{name}")
        if full_source(direction) not in blocks.get("direction", ""):
            errors.append(f"方向内容丢失：{direction.name}")
        if set(blocks) != {Path(n).stem for n in COMMON_FILES} | {"direction", "method"}:
            errors.append(f"模块边界不完整：{direction.name}")
        compact_blocks = dict(MODULE_PATTERN.findall(render_compact(direction)))
        for name in COMMON_FILES:
            if compact_source(COMMON_DIR / name) not in compact_blocks.get(Path(name).stem, ""):
                errors.append(f"公共CORE漂移：{direction.name}/{name}")
        if compact_source(direction) not in compact_blocks.get("direction", ""):
            errors.append(f"方向CORE漂移：{direction.name}")

    routing = (SKILL_ROOT / "references/routing.md").read_text(encoding="utf-8")
    routes = set(re.findall(r"references/compiled-prompts/([a-z0-9-]+)-full[.]md", routing))
    if routes != ids:
        errors.append("方向路由集合不一致")
    for name in ["direction-rubrics.json", "direction-method-gates.json"]:
        obj = json.loads((SKILL_ROOT / "references/quality" / name).read_text(encoding="utf-8"))
        if set(obj.get("directions", {})) != ids:
            errors.append(f"专业规则集合不一致：{name}")
    rubrics = json.loads((SKILL_ROOT / "references/quality/direction-rubrics.json").read_text())
    if sum(rubrics["weights"].values()) != 100:
        errors.append("独立评测权重不等于100")

    # 每个模式真实抽取一次；检查功能模块缺失和局部任务混入方向正文。
    catalog = json.loads((SKILL_ROOT / "references/prompt-modules.json").read_text())
    if set(catalog.get("direction_defaults", {})) != ids:
        errors.append("19方向DEFAULT_FEATURES集合不完整")
    for mode in catalog["modes"]:
        selection = {"schema_version": "1.0", "run_mode": mode, "direction_id": directions[0].stem, "features": []}
        try:
            body, chosen = task_parts(render_compiled(directions[0]).encode(), selection, f"RUN_MODE: {mode}".encode())
            if not body or not set(catalog["always"]).issubset(chosen):
                errors.append(f"模式基础约束缺失：{mode}")
            if mode in {"FIGURES_ONLY", "EXPORT_ONLY", "DEFENSE_ONLY"} and "direction" in chosen:
                errors.append(f"局部任务混入整篇方向结构：{mode}")
            if mode == "EXPORT_ONLY" and {"academic-figures", "literature-and-citation"} & set(chosen):
                errors.append("导出模式混入研究或生图")
        except ValueError as exc:
            errors.append(f"模式无法合成：{mode}/{exc}")
    # 使用保守参数与最长通用适配估算最终输入，保证弱模型路径不是伪compact。
    adapter_bytes = max(path.stat().st_size for path in (SKILL_ROOT / "references/integrations").glob("*.md"))
    staged_bytes = (SKILL_ROOT / "references/profiles/staged-assistance.md").stat().st_size
    checkpoint_bytes = (SKILL_ROOT / "references/profiles/execution-checkpoints-template.json").stat().st_size
    params_budget = 1500
    for direction in directions:
        selection = {"schema_version": "1.0", "run_mode": "FULL_BUILD", "direction_id": direction.stem,
                     "features": catalog["direction_defaults"][direction.stem]}
        compact_body, _ = task_parts(render_compact(direction).encode(), selection, f"RUN_MODE: FULL_BUILD\nDIRECTION_ID: {direction.stem}\n".encode())
        estimated = len(compact_body) + adapter_bytes + staged_bytes + checkpoint_bytes + params_budget
        if estimated > 15000:
            errors.append(f"弱模型最终输入预算超限：{direction.name}={estimated}B")
        full_body, _ = task_parts(render_compiled(direction).encode(), selection, f"RUN_MODE: FULL_BUILD\nDIRECTION_ID: {direction.stem}\n".encode())
        professional = len(full_source(direction).encode())
        method = len(dict(MODULE_PATTERN.findall(render_compiled(direction))).get("method", "").encode())
        if (professional + method) / max(len(full_body), 1) < 0.30:
            errors.append(f"方向专业内容占比不足30%：{direction.name}")

    skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = frontmatter_version(skill)
    if not version or f"当前版本：`{version}`" not in readme or f"## {version} -" not in changelog:
        errors.append("入口、README、CHANGELOG版本不一致")
    for relative in re.findall(r"[]][(](references/[^)#]+)(?:#[^)]*)?[)]", skill):
        if not (SKILL_ROOT / relative).is_file():
            errors.append(f"入口链接缺失：{relative}")
    for path in (SKILL_ROOT / "references/schemas").glob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            errors.append(f"Schema不可解析：{path.name}")
    matrix = json.loads((SKILL_ROOT / "references/mode-checker-matrix.json").read_text())
    if set(matrix["modes"]) != {"FULL_BUILD", "RESUME", "REVISE_ONLY", "FIGURES_ONLY", "EXPORT_ONLY", "AUDIT_ONLY", "PROPOSAL_ONLY", "DEFENSE_ONLY"}:
        errors.append("模式检查矩阵不完整")
    for script in ["paper.py", "check_paper.py", "compose_prompt.py", "select_execution_profile.py", "prepare_audit_views.py", "prepare_resume.py", "compose_revision.py", "resolve_default_length.py", "verify_evidence_integrity.py", "verify_figure_package.py", "verify_formula_rendering.py", "verify_manuscript_delivery.py", "capture_provenance.py", "adjudicate_status.py", "write_skipped_report.py", "render_svg_layout.mjs"]:
        if not (SKILL_ROOT / "scripts" / script).is_file():
            errors.append(f"必要工具缺失：{script}")
    # 保留方向信源层次和术语，避免剪枝误删学科检索指导。
    prefixes = ["发现与筛选", "证据与全文", "开放路线", "不宜作核心引文", "信源核验门槛"]
    for direction in directions:
        source = direction.read_text(encoding="utf-8")
        if any(source.count(f"- {prefix}：") != 1 for prefix in prefixes):
            errors.append(f"方向文献信源丢失：{direction.name}")
    reviewers = {p.stem for p in (SKILL_ROOT / "references/reviewers").glob("*.md")}
    if reviewers != ids:
        errors.append("审稿参考集合不完整")
    benchmark = json.loads((SKILL_ROOT / "references/benchmarks/strong-model-benchmark.json").read_text())
    if len(benchmark.get("tasks", [])) != 57:
        errors.append("维护期基准必须保留57项；数量不代表已经执行")
    if errors:
        print("校验失败：\n" + "\n".join(f"- {x}" for x in errors))
        return 1
    print("通过：19方向同源full/compact、15KB弱模型预算、30%专业占比、模式与版本完整；不代表真实论文质量达标。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
