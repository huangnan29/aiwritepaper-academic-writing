#!/usr/bin/env python3
"""从公共规则与方向源文件重建19份完整版和19份紧凑版提示词。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile
from typing import List, Optional


SKILL_ROOT = Path(__file__).resolve().parents[1]
COMMON_DIR = SKILL_ROOT / "references" / "common"
DIRECTIONS_DIR = SKILL_ROOT / "references" / "directions"
COMPILED_DIR = SKILL_ROOT / "references" / "compiled-prompts"
COMPACT_DIR = SKILL_ROOT / "references" / "compact-prompts"
WEAK_CORE = COMMON_DIR / "weak-model-core.md"

COMMON_FILES = [
    "capability-and-runtime.md",
    "integrity-and-evidence.md",
    "literature-and-citation.md",
    "output-contract.md",
    "academic-figures.md",
    "statistical-figures-and-trace.md",
    "academic-prose-quality.md",
    "autonomous-completion.md",
    "final-quality-gates.md",
    "mathematical-formulas.md",
]


def read_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"源文件为空: {path}")
    return text.rstrip("\r\n")


def render_compiled(direction: Path) -> str:
    prompt_id = direction.stem
    common_list = "\n".join(f"- references/common/{name}" for name in COMMON_FILES)
    header = (
        "<!--\n"
        "本文件已由Skill维护流程预先合成为单一完整提示词；运行时请完整读取，不要继续加载其他规则。\n"
        "公共来源（固定顺序）：\n"
        f"{common_list}\n"
        "方向来源：\n"
        f"- references/directions/{direction.name}\n"
        "来源清单结束。\n"
        "-->\n\n"
        f"# {prompt_id} 完整论文生成提示词\n\n"
        "## 合并说明\n\n"
        "本文件由公共规则与当前方向规则合并生成，执行时应整体读取。\n\n"
    )

    sections: List[str] = [header.rstrip("\r\n")]
    for name in COMMON_FILES:
        source = COMMON_DIR / name
        sections.append(f"<!-- 公共来源：references/common/{name} -->\n\n{read_source(source)}")
    sections.append(
        f"<!-- 方向来源：references/directions/{direction.name} -->\n\n{read_source(direction)}"
    )
    return "\n\n".join(sections) + "\n"


def render_compact(direction: Path) -> str:
    """由一个紧凑公共核心与同一方向源生成弱模型提示词。"""
    prompt_id = direction.stem
    header = (
        "<!--\n"
        "本文件由弱模型紧凑公共核心与当前方向源确定性合成。\n"
        "运行时只读取本文件，不加载完整版提示词或其他公共规则。\n"
        "公共来源：references/common/weak-model-core.md\n"
        f"方向来源：references/directions/{direction.name}\n"
        "-->\n\n"
        f"# {prompt_id} 弱模型紧凑论文生成提示词\n"
    )
    return (
        header.rstrip("\r\n")
        + "\n\n<!-- 紧凑公共来源：references/common/weak-model-core.md -->\n\n"
        + read_source(WEAK_CORE)
        + f"\n\n<!-- 方向来源：references/directions/{direction.name} -->\n\n"
        + read_source(direction)
        + "\n"
    )


def direction_files() -> List[Path]:
    return sorted(DIRECTIONS_DIR.glob("*.md"))


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", delete=False
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重建全部 compiled prompts")
    parser.add_argument("--check", action="store_true", help="只报告差异，不写文件")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    directions = direction_files()
    if len(directions) != 19:
        raise ValueError(f"方向源文件应为19个，实际为{len(directions)}个")

    changed: List[str] = []
    for direction in directions:
        outputs = [
            (COMPILED_DIR / f"{direction.stem}-full.md", render_compiled(direction)),
            (COMPACT_DIR / f"{direction.stem}-compact.md", render_compact(direction)),
        ]
        for output, expected in outputs:
            current = output.read_text(encoding="utf-8") if output.exists() else None
            if current != expected:
                changed.append(str(output.relative_to(SKILL_ROOT)))
                if not args.check:
                    atomic_write(output, expected)

    if args.check and changed:
        print("不同步的compiled prompts:")
        for name in changed:
            print(f"- {name}")
        return 1

    action = "需要重建" if args.check else "已重建"
    print(f"{action}: {len(changed)}；方向总数: {len(directions)}；每方向full+compact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
