#!/usr/bin/env python3
"""只读校验compiled prompts、路由目标和版本号同步。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

from build_compiled import (
    COMMON_DIR,
    COMMON_FILES,
    COMPILED_DIR,
    SKILL_ROOT,
    direction_files,
    read_source,
    render_compiled,
)


def frontmatter_version(skill_text: str) -> Optional[str]:
    match = re.search(r'^\s*version:\s*["\']?([^"\'\s]+)', skill_text, re.MULTILINE)
    return match.group(1) if match else None


def main() -> int:
    errors: List[str] = []
    directions = direction_files()
    compiled = sorted(COMPILED_DIR.glob("*-full.md"))
    access_tags = ["OPEN_API", "OPEN_WEB", "LOGIN_REQUIRED", "INSTITUTION_REQUIRED", "MANUAL_ONLY"]
    source_prefixes = ["发现与筛选", "证据与全文", "开放路线", "不宜作核心引文", "信源核验门槛"]

    literature_common = read_source(COMMON_DIR / "literature-and-citation.md")
    output_contract = read_source(COMMON_DIR / "output-contract.md")
    expected_common_headings = {
        "capability-and-runtime.md": "# 公共规则一：",
        "integrity-and-evidence.md": "# 公共规则二：",
        "literature-and-citation.md": "# 公共规则三：",
        "output-contract.md": "# 公共规则四：",
        "academic-figures.md": "# 公共规则五：",
        "statistical-figures-and-trace.md": "# 公共规则六：",
        "academic-prose-quality.md": "# 公共规则七：",
        "autonomous-completion.md": "# 公共规则八：",
        "final-quality-gates.md": "# 公共规则九：",
    }
    for common_name, expected_heading in expected_common_headings.items():
        if not read_source(COMMON_DIR / common_name).startswith(expected_heading):
            errors.append(f"公共规则编号或标题错误: {common_name} -> {expected_heading}")
    for heading in ["发现层", "证据层", "核验层"]:
        if heading not in literature_common:
            errors.append(f"公共文献规则缺少信源层级: {heading}")
    for field in ["evidence_role", "access_mode", "publication_status"]:
        if field not in literature_common:
            errors.append(f"公共文献规则缺少证据矩阵字段: {field}")
    for tag in access_tags:
        if tag not in literature_common:
            errors.append(f"公共文献规则缺少访问标记: {tag}")
    for term in ["GENERATED_AT_LOCAL", "YYYYMMDD-HHMMSS", "安全论文题目", "final-paper.docx", "run-manifest.json"]:
        if term not in output_contract:
            errors.append(f"输出契约缺少最终文件命名规则: {term}")
    for term in ["document_profile", "THESIS", "FINAL_STATUS", "figure-verification.json"]:
        if term not in output_contract and term not in read_source(COMMON_DIR / "autonomous-completion.md"):
            errors.append(f"输出契约缺少当前闭环字段: {term}")

    if len(directions) != 19:
        errors.append(f"方向源文件应为19个，实际为{len(directions)}个")
    if len(compiled) != 19:
        errors.append(f"compiled prompts应为19个，实际为{len(compiled)}个")

    expected_names = {f"{path.stem}-full.md" for path in directions}
    actual_names = {path.name for path in compiled}
    if expected_names != actual_names:
        errors.append(f"compiled文件集合不一致: 缺少={sorted(expected_names-actual_names)} 多出={sorted(actual_names-expected_names)}")

    for direction in directions:
        direction_text = read_source(direction)
        if direction_text.count("## 文献信源") != 1:
            errors.append(f"文献信源章节不是恰好一次: {direction.name}")
        else:
            required_pos = direction_text.find("## 必需证据")
            literature_pos = direction_text.find("## 文献信源")
            figures_pos = direction_text.find("## 图表与表格")
            if not (required_pos < literature_pos < figures_pos):
                errors.append(f"文献信源章节位置错误: {direction.name}")
            literature_section = direction_text[literature_pos:figures_pos]
            for prefix in source_prefixes:
                if literature_section.count(f"- {prefix}：") != 1:
                    errors.append(f"文献信源条目不是恰好一次: {direction.name} -> {prefix}")
            for prefix in source_prefixes[:3]:
                line_match = re.search(rf"^- {re.escape(prefix)}：.*$", literature_section, re.MULTILINE)
                if line_match and not any(tag in line_match.group(0) for tag in access_tags):
                    errors.append(f"信源条目缺少访问标记: {direction.name} -> {prefix}")

        output = COMPILED_DIR / f"{direction.stem}-full.md"
        if not output.exists():
            continue
        output_text = output.read_text(encoding="utf-8")
        if output_text != render_compiled(direction):
            errors.append(f"内容不同步: {output.name}")
        for common_name in COMMON_FILES:
            marker = f"<!-- 公共来源：references/common/{common_name} -->"
            if output_text.count(marker) != 1:
                errors.append(f"公共规则标记不是恰好一次: {output.name} -> {common_name}")
            common_text = read_source(COMMON_DIR / common_name)
            if output_text.count(common_text) != 1:
                errors.append(f"公共规则正文不是恰好一次: {output.name} -> {common_name}")
        direction_marker = f"<!-- 方向来源：references/directions/{direction.name} -->"
        if output_text.count(direction_marker) != 1:
            errors.append(f"方向标记不是恰好一次: {output.name}")
        if output_text.count(direction_text) != 1:
            errors.append(f"方向正文不是恰好一次: {output.name}")

    routing = (SKILL_ROOT / "references" / "routing.md").read_text(encoding="utf-8")
    route_names = set(re.findall(r"references/compiled-prompts/([a-z0-9-]+-full\.md)", routing))
    if route_names != actual_names:
        errors.append(f"routing目标不一致: 缺少={sorted(actual_names-route_names)} 多出={sorted(route_names-actual_names)}")

    skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    readme = (SKILL_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (SKILL_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    version = frontmatter_version(skill_text)
    if not version:
        errors.append("SKILL.md缺少metadata.version")
    else:
        if f"version-{version}-" not in readme:
            errors.append(f"README版本徽章未同步到{version}")
        if f"当前版本：`{version}`" not in readme:
            errors.append(f"README维护段未同步到{version}")
        if f"## {version} -" not in changelog:
            errors.append(f"CHANGELOG未包含{version}版本记录")

    required_refs = [
        "references/topic-selection.md",
        "references/routing.md",
        "references/prompt-composition.md",
        "references/deliverables/proposal-report.md",
        "references/deliverables/defense-presentation.md",
        "references/integrations/codex.md",
        "references/integrations/grok.md",
        "references/integrations/gemini-antigravity.md",
        "references/integrations/claude-cursor.md",
        "references/integrations/kimi-workbuddy.md",
        "references/integrations/universal-terminal.md",
    ]
    for reference in required_refs:
        if reference not in skill_text:
            errors.append(f"SKILL.md未接通: {reference}")
    if "references/figure-skills/" in skill_text:
        errors.append("SKILL.md仍引用空的references/figure-skills目录")
    for script_name in [
        "compose_prompt.py", "build_compiled.py", "verify_compiled.py",
        "verify_figure_package.py", "verify_manuscript_delivery.py",
    ]:
        if not (SKILL_ROOT / "scripts" / script_name).is_file():
            errors.append(f"缺少脚本: scripts/{script_name}")
    if not (SKILL_ROOT / "scripts" / "render_svg_layout.mjs").is_file():
        errors.append("缺少脚本: scripts/render_svg_layout.mjs")

    installers = "\n".join(
        (SKILL_ROOT / name).read_text(encoding="utf-8") for name in ["install.sh", "install.ps1"]
    )
    for agent_name in ["zcode", "deepseek-tui"]:
        if installers.count(agent_name) < 2:
            errors.append(f"跨平台安装器未完整接通: {agent_name}")

    statistical_rules = read_source(COMMON_DIR / "statistical-figures-and-trace.md")
    academic_figure_rules = read_source(COMMON_DIR / "academic-figures.md")
    figure_rules = academic_figure_rules + "\n" + statistical_rules
    for required_term in [
        "figure_plan", "figure-manifest.json", "final_embed_file", "DATA_CODE",
        "IMAGE_GENERATION", "SVG_FALLBACK", "data_status", "caption_claim", "VLM",
        "generation_receipt", "NATIVE_TOOL_RESULT", "checked_file_sha256", "schema_version",
        "execution_receipt", "output_sha256", "SVG降级图的机械校验",
        "svg_layout_mode", "COMPILED", "figure-spec.json",
        "display_number", "imagegen_eligible", "route_exemption", "IMAGEGEN_BYPASSED",
        "exactness_class", "DOMAIN_EXACT", "data_origin", "MODEL_SYNTHETIC",
        "figures/<FIGURE_ID>-facts.md", "各类SVG的通用布局语法", "整数坐标网格",
        "共线重叠", "预留空白带", "字形安全", "预检与视觉闭环",
        "language_contract", "allowed_foreign_tokens", "DETERMINISTIC_OVERLAY",
        "text_render_strategy", "language_check", "非白名单英文长句",
    ]:
        if required_term not in figure_rules:
            errors.append(f"图表公共规则缺少关键契约: {required_term}")

    prose_rules = read_source(COMMON_DIR / "academic-prose-quality.md")
    for required_term in ["材料推动段落", "控制框架和清单", "句子与段落节奏", "全文只保留一份连续参考文献", "不能输出“AI率”"]:
        if required_term not in prose_rules:
            errors.append(f"学术正文质量规则缺少关键约束: {required_term}")

    schema_path = SKILL_ROOT / "references" / "schemas" / "figure-manifest.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if schema.get("properties", {}).get("schema_version", {}).get("const") != "1.5":
            errors.append("Figure Manifest Schema版本不是1.5")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"Figure Manifest Schema不可用: {exc}")

    capability_schema_path = SKILL_ROOT / "references" / "schemas" / "capability-report.schema.json"
    try:
        capability_schema = json.loads(capability_schema_path.read_text(encoding="utf-8"))
        if capability_schema.get("properties", {}).get("schema_version", {}).get("const") != "1.0":
            errors.append("Capability Report Schema版本不是1.0")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"Capability Report Schema不可用: {exc}")

    svg_schema_path = SKILL_ROOT / "references" / "schemas" / "svg-layout-spec.schema.json"
    try:
        svg_schema = json.loads(svg_schema_path.read_text(encoding="utf-8"))
        if svg_schema.get("properties", {}).get("version", {}).get("const") != "1.0":
            errors.append("SVG Layout Spec Schema版本不是1.0")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"SVG Layout Spec Schema不可用: {exc}")

    audit_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [SKILL_ROOT / "SKILL.md", SKILL_ROOT / "README.md", *COMMON_DIR.glob("*.md"), *directions]
    )
    if re.search(r"sci[- ]?hub", audit_text, re.IGNORECASE):
        errors.append("正式规则仍包含Sci-Hub表述")
    for required_term in ["IET Inspec", "Ei Compendex", "SinoMed", "CBM", "zbMATH Open"]:
        if required_term not in audit_text:
            errors.append(f"方向信源缺少规范名称: {required_term}")

    if errors:
        print("校验失败:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("校验通过: 19份compiled prompts与源文件、路由和版本号全部同步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
