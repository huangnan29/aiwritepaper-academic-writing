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

    if len(directions) != 19:
        errors.append(f"方向源文件应为19个，实际为{len(directions)}个")
    if len(compiled) != 19:
        errors.append(f"compiled prompts应为19个，实际为{len(compiled)}个")

    expected_names = {f"{path.stem}-full.md" for path in directions}
    actual_names = {path.name for path in compiled}
    if expected_names != actual_names:
        errors.append(f"compiled文件集合不一致: 缺少={sorted(expected_names-actual_names)} 多出={sorted(actual_names-expected_names)}")

    for direction in directions:
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
        if output_text.count(read_source(direction)) != 1:
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
    for script_name in ["compose_prompt.py", "build_compiled.py", "verify_compiled.py"]:
        if not (SKILL_ROOT / "scripts" / script_name).is_file():
            errors.append(f"缺少脚本: scripts/{script_name}")

    if errors:
        print("校验失败:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("校验通过: 19份compiled prompts与源文件、路由和版本号全部同步")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
