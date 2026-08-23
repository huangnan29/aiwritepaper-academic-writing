#!/usr/bin/env python3
"""只读校验compiled prompts、路由目标和版本号同步。"""

from __future__ import annotations

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
    expected_common_headings = {
        "capability-and-runtime.md": "# 公共规则一：",
        "integrity-and-evidence.md": "# 公共规则二：",
        "literature-and-citation.md": "# 公共规则三：",
        "output-contract.md": "# 公共规则四：",
        "academic-figures.md": "# 公共规则五：",
        "statistical-figures-and-trace.md": "# 公共规则六：",
        "autonomous-completion.md": "# 公共规则七：",
        "final-quality-gates.md": "# 公共规则八：",
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
    ]
    for reference in required_refs:
        if reference not in skill_text:
            errors.append(f"SKILL.md未接通: {reference}")
    if "references/figure-skills/" in skill_text:
        errors.append("SKILL.md仍引用空的references/figure-skills目录")
    for script_name in ["compose_prompt.py", "build_compiled.py", "verify_compiled.py", "verify_figure_package.py"]:
        if not (SKILL_ROOT / "scripts" / script_name).is_file():
            errors.append(f"缺少脚本: scripts/{script_name}")

    statistical_rules = read_source(COMMON_DIR / "statistical-figures-and-trace.md")
    for required_term in [
        "figure_plan", "figure-manifest.json", "final_embed_file", "DATA_CODE",
        "IMAGE_GENERATION", "SVG_FALLBACK", "data_status", "caption_claim", "VLM",
    ]:
        if required_term not in statistical_rules:
            errors.append(f"统计图公共规则缺少关键契约: {required_term}")

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
