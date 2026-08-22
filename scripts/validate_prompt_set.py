#!/usr/bin/env python3
"""对论文提示词集合执行不改文件的静态一致性检查。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from compile_prompts import COMMON_MARKDOWN_ORDER


# 这些文件构成 Skill 包和提示词路由的最小交付面。
REQUIRED_FILES = (
    "SKILL.md",
    "CHANGELOG.md",
    "agents/openai.yaml",
    "references/routing.md",
    "references/topic-selection.md",
    "references/universal-reference-prompt.md",
    "references/evidence-manifest.md",
    "references/common/academic-figures.md",
    "references/common/executable-gates.md",
    "references/figure-skills/academic-figure-routing.md",
    "references/figure-skills/academic-svg-quality.md",
    "skills/academic-figure-router/SKILL.md",
    "skills/academic-svg-enhancer/SKILL.md",
    "skills/academic-svg-enhancer/scripts/audit_svg.py",
    "skills/academic-svg-enhancer/tests/test_audit_svg.py",
    "scripts/probe_capabilities.py",
    "scripts/run_evidence.py",
    "scripts/assemble_and_export.py",
    "scripts/validate_evidence.py",
    "scripts/validate_delivery.py",
    "tests/test_probe_capabilities.py",
    "tests/test_run_evidence.py",
    "tests/test_assemble_and_export.py",
    "tests/test_validate_evidence.py",
    "tests/test_validate_delivery.py",
)

# 只扫描容易明确判定为脚手架的词，避免把正常的否定规则误判为占位内容。
PLACEHOLDER_PATTERNS = (
    re.compile(r"\b(?:TODO|FIXME|TBD|PLACEHOLDER)\b", re.IGNORECASE),
    re.compile(r"待补充|待填写|待确定|占位符|占位内容|此处填写"),
    re.compile(r"\{\{[^{}\n]+\}\}"),
    re.compile(r"<\s*(?:YOUR|FILL|INSERT|TODO)[^>\n]*>", re.IGNORECASE),
    re.compile(r"\[[^\]\n]*(?:待填写|待补充|TODO|占位)[^\]\n]*\]", re.IGNORECASE),
    re.compile(r"(?<![\w])XXX(?![\w])"),
)

# 每个完整提示词必须拥有的关键章节标记，支持中英文标题。
REQUIRED_SECTION_GROUPS = {
    "真实性规则": ("真实性", "学术诚信", "不得编造", "禁止虚构", "integrity"),
    "文献与引用规则": ("文献", "参考文献", "引用", "literature", "citation"),
    "证据规则": ("证据", "证据矩阵", "研究材料", "数据要求", "evidence"),
    "可执行门禁": ("可执行生产门禁", "能力探测", "交付验收器", "executable gate"),
    "最终验收规则": ("最终验收", "质量门", "验收标准", "最终质量", "final acceptance", "quality gate"),
}

HEADING_PATTERN = re.compile(r"(?im)^\s*#{1,6}\s+(.+?)\s*$")
MANIFEST_MARKER = "公共来源（固定顺序）"


class ValidationReport:
    """收集静态检查错误，避免发现一个错误后提前结束。"""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)


def resolve_root(root_argument: str | None) -> Path:
    """解析项目根目录，默认使用当前脚本所在项目的根目录。"""

    if root_argument is None:
        return Path(__file__).resolve().parents[1]
    return Path(root_argument).expanduser().resolve()


def relative_path(root: Path, path: Path) -> str:
    """返回统一使用正斜线的项目相对路径。"""

    return path.relative_to(root).as_posix()


def read_utf8(path: Path, root: Path, report: ValidationReport) -> str | None:
    """读取文本文件，失败时将问题写入报告。"""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report.add(f"{relative_path(root, path)} 不是有效的 UTF-8 文本")
    except OSError as error:
        report.add(f"无法读取 {relative_path(root, path)}：{error}")
    return None


def check_required_files(root: Path, report: ValidationReport) -> None:
    """检查 Skill 包的必需文件和提示词目录。"""

    for filename in REQUIRED_FILES:
        path = root / filename
        if not path.is_file():
            report.add(f"缺少必需文件：{filename}")

    required_directories = (
        "references/common",
        "references/directions",
        "references/compiled-prompts",
        "references/figure-skills",
        "skills/academic-figure-router",
        "skills/academic-svg-enhancer",
        "tests",
    )
    for dirname in required_directories:
        if not (root / dirname).is_dir():
            report.add(f"缺少必需目录：{dirname}")

    common_dir = root / "references/common"
    for filename in COMMON_MARKDOWN_ORDER:
        if common_dir.is_dir() and not (common_dir / filename).is_file():
            report.add(f"缺少固定公共规则文件：{relative_path(root, common_dir / filename)}")


def markdown_files(directory: Path) -> list[Path]:
    """获取指定目录下的直接 Markdown 文件。"""

    if not directory.is_dir():
        return []
    return sorted(
        (
            path
            for path in directory.glob("*.md")
            if path.is_file() and not path.name.startswith(".")
        ),
        key=lambda path: path.name.casefold(),
    )


def check_direction_pairing(root: Path, report: ValidationReport) -> list[Path]:
    """检查方向源文件与完整编译文件是否一一对应。"""

    directions_dir = root / "references/directions"
    compiled_dir = root / "references/compiled-prompts"
    sources = markdown_files(directions_dir)
    compiled = markdown_files(compiled_dir)

    if not sources:
        report.add("references/directions 下没有方向源 Markdown 文件")
    if not compiled:
        report.add("references/compiled-prompts 下没有完整提示词文件")

    source_names = {path.name for path in sources}
    compiled_names = {path.name for path in compiled}
    expected_compiled_names = {f"{path.stem}-full.md" for path in sources}

    for filename in sorted(source_names - {name[:-8] + ".md" for name in compiled_names if name.endswith("-full.md")}):
        report.add(f"方向源没有对应完整提示词：references/directions/{filename}")

    for filename in sorted(compiled_names - expected_compiled_names):
        report.add(f"存在没有方向源的完整提示词：references/compiled-prompts/{filename}")

    return sources


def is_prohibition_line(line: str, match: re.Match[str]) -> bool:
    """判断命中词是否只是提示词中禁止占位内容的规则说明。"""

    prefix = line[: match.start()]
    return bool(re.search(r"不得|禁止|严禁|不应|不能|避免|清除|移除|检查|检测|不得保留", prefix))


def find_placeholder_lines(content: str) -> list[int]:
    """返回实际包含占位脚手架的行号。"""

    lines: list[int] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if any(
            match and not is_prohibition_line(line, match)
            for pattern in PLACEHOLDER_PATTERNS
            for match in [pattern.search(line)]
        ):
            lines.append(line_number)
    return lines


def check_no_placeholders(root: Path, report: ValidationReport) -> None:
    """检查公共、方向和完整提示词中是否残留脚手架占位内容。"""

    directories = (
        root / "references/common",
        root / "references/directions",
        root / "references/compiled-prompts",
    )
    for directory in directories:
        for path in markdown_files(directory):
            content = read_utf8(path, root, report)
            if content is None:
                continue
            line_numbers = find_placeholder_lines(content)
            if line_numbers:
                numbers = "、".join(str(number) for number in line_numbers)
                report.add(f"{relative_path(root, path)} 含占位脚手架，行号：{numbers}")


def heading_texts(content: str) -> list[str]:
    """提取 Markdown 标题文本，用于关键章节检查。"""

    return [match.group(1).strip().casefold() for match in HEADING_PATTERN.finditer(content)]


def contains_section(content: str, markers: tuple[str, ...]) -> bool:
    """判断标题中是否出现某组关键章节标记。"""

    headings = heading_texts(content)
    return any(marker.casefold() in heading for heading in headings for marker in markers)


def check_compiled_prompts(root: Path, report: ValidationReport) -> None:
    """检查每个完整提示词的来源头和关键规则章节。"""

    compiled_dir = root / "references/compiled-prompts"
    directions_dir = root / "references/directions"
    common_paths = [
        root / "references/common" / filename for filename in COMMON_MARKDOWN_ORDER
    ]
    for path in markdown_files(compiled_dir):
        content = read_utf8(path, root, report)
        if content is None:
            continue
        header = content[:4000]
        if not content.lstrip().startswith("<!--") or MANIFEST_MARKER not in header:
            report.add(f"{relative_path(root, path)} 缺少来源清单头")

        source_stem = path.name[: -len("-full.md")] if path.name.endswith("-full.md") else ""
        direction_path = directions_dir / f"{source_stem}.md"
        if source_stem and direction_path.is_file():
            expected_source = relative_path(root, direction_path)
            if expected_source not in header:
                report.add(f"{relative_path(root, path)} 来源清单未列出方向源：{expected_source}")

        for common_path in common_paths:
            expected_source = relative_path(root, common_path)
            if common_path.is_file() and expected_source not in header:
                report.add(f"{relative_path(root, path)} 来源清单未列出公共源：{expected_source}")

        missing_sections = [
            name
            for name, markers in REQUIRED_SECTION_GROUPS.items()
            if not contains_section(content, markers)
        ]
        if missing_sections:
            report.add(
                f"{relative_path(root, path)} 缺少关键章节：" + "、".join(missing_sections)
            )


def validate(root: Path) -> ValidationReport:
    """执行全部静态一致性检查并返回报告。"""

    report = ValidationReport()
    check_required_files(root, report)
    check_direction_pairing(root, report)
    check_no_placeholders(root, report)
    check_compiled_prompts(root, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""

    parser = argparse.ArgumentParser(description="检查论文提示词集合的静态一致性。")
    parser.add_argument(
        "--root",
        help="aiwritepaper-agentic-skill 项目根目录，默认使用当前脚本所属项目。",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """执行命令行静态检查入口。"""

    args = build_parser().parse_args(argv)
    root = resolve_root(args.root)
    if not root.is_dir():
        print(f"检查失败：项目根目录不存在：{root}", file=sys.stderr)
        return 1

    report = validate(root)
    if report.errors:
        print("静态检查结果：FAIL")
        for error in report.errors:
            print(f"- {error}")
        print(f"共发现 {len(report.errors)} 个问题。")
        return 1

    print("静态检查结果：PASS")
    print("必需文件、方向配对、来源清单、占位脚手架和关键章节检查均通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
