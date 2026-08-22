#!/usr/bin/env python3
"""按固定公共规则顺序编译论文方向提示词。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# 公共规则的顺序决定完整提示词中的规则优先级和阅读顺序。
COMMON_MARKDOWN_ORDER = (
    "capability-and-runtime.md",
    "integrity-and-evidence.md",
    "literature-and-citation.md",
    "output-contract.md",
    "academic-figures.md",
    "executable-gates.md",
    "final-quality-gates.md",
)


class PromptCompilationError(RuntimeError):
    """表示提示词目录不满足编译前提。"""


def resolve_root(root_argument: str | None) -> Path:
    """解析项目根目录，默认使用当前脚本所在项目的根目录。"""

    if root_argument is None:
        return Path(__file__).resolve().parents[1]
    return Path(root_argument).expanduser().resolve()


def read_markdown(path: Path) -> str:
    """以 UTF-8 读取 Markdown，并将读取错误转换为可读异常。"""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise PromptCompilationError(f"文件不是有效的 UTF-8 文本：{path}") from error
    except OSError as error:
        raise PromptCompilationError(f"无法读取文件：{path}：{error}") from error


def require_directories(root: Path) -> tuple[Path, Path, Path]:
    """确认公共规则、方向规则和编译输出目录存在。"""

    references = root / "references"
    common_dir = references / "common"
    directions_dir = references / "directions"
    compiled_dir = references / "compiled-prompts"
    missing = [
        str(path.relative_to(root))
        for path in (common_dir, directions_dir, compiled_dir)
        if not path.is_dir()
    ]
    if missing:
        raise PromptCompilationError("缺少必需目录：" + "、".join(missing))
    return common_dir, directions_dir, compiled_dir


def load_common_sources(common_dir: Path, root: Path) -> list[tuple[Path, str]]:
    """按照固定顺序加载公共 Markdown。"""

    sources: list[tuple[Path, str]] = []
    missing: list[str] = []
    for filename in COMMON_MARKDOWN_ORDER:
        path = common_dir / filename
        if not path.is_file():
            missing.append(str(path.relative_to(root)))
            continue
        sources.append((path, read_markdown(path)))
    if missing:
        raise PromptCompilationError("缺少必需公共规则文件：" + "、".join(missing))
    return sources


def load_direction_sources(directions_dir: Path) -> list[tuple[Path, str]]:
    """按文件名排序加载所有方向 Markdown。"""

    paths = sorted(
        (
            path
            for path in directions_dir.glob("*.md")
            if path.is_file() and not path.name.startswith(".")
        ),
        key=lambda path: path.name.casefold(),
    )
    if not paths:
        raise PromptCompilationError("references/directions 下没有方向 Markdown 文件")
    return [(path, read_markdown(path)) for path in paths]


def source_manifest(root: Path, common_sources: list[tuple[Path, str]], direction: Path) -> str:
    """生成写入完整提示词开头的来源清单。"""

    lines = [
        "<!--",
        "本文件由 scripts/compile_prompts.py 自动生成，请勿直接编辑。",
        "公共来源（固定顺序）：",
    ]
    lines.extend(
        f"- {path.relative_to(root).as_posix()}" for path, _content in common_sources
    )
    lines.extend(
        [
            "方向来源：",
            f"- {direction.relative_to(root).as_posix()}",
            "来源清单结束。",
            "-->",
        ]
    )
    return "\n".join(lines)


def compile_direction(
    root: Path,
    compiled_dir: Path,
    common_sources: list[tuple[Path, str]],
    direction: tuple[Path, str],
) -> Path:
    """将公共规则和一个方向规则合并为独立完整提示词。"""

    direction_path, direction_content = direction
    output_path = compiled_dir / f"{direction_path.stem}-full.md"
    sections = [
        source_manifest(root, common_sources, direction_path),
        f"# {direction_path.stem} 完整论文生成提示词",
        "## 合并说明",
        "本文件由公共规则与当前方向规则合并生成，执行时应整体读取。",
    ]
    for path, content in common_sources:
        sections.extend(
            [
                f"<!-- 公共来源：{path.relative_to(root).as_posix()} -->",
                content.rstrip(),
            ]
        )
    sections.extend(
        [
            f"<!-- 方向来源：{direction_path.relative_to(root).as_posix()} -->",
            direction_content.rstrip(),
        ]
    )
    output_path.write_text("\n\n".join(sections).rstrip() + "\n", encoding="utf-8")
    return output_path


def compile_prompts(root: Path) -> list[Path]:
    """编译全部方向提示词并返回输出路径。"""

    common_dir, directions_dir, compiled_dir = require_directories(root)
    common_sources = load_common_sources(common_dir, root)
    direction_sources = load_direction_sources(directions_dir)
    return [
        compile_direction(root, compiled_dir, common_sources, direction)
        for direction in direction_sources
    ]


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="将公共论文规则与各论文方向规则合并为完整提示词。"
    )
    parser.add_argument(
        "--root",
        help="aiwritepaper-agentic-skill 项目根目录，默认使用当前脚本所属项目。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """执行命令行编译入口。"""

    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    try:
        outputs = compile_prompts(root)
    except PromptCompilationError as error:
        print(f"编译失败：{error}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"编译失败：无法写入输出文件：{error}", file=sys.stderr)
        return 1

    for output in outputs:
        print(f"已生成：{output.relative_to(root).as_posix()}")
    print(f"编译完成：共生成 {len(outputs)} 个完整提示词。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
