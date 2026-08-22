#!/usr/bin/env python3
"""对学术 SVG 执行确定性的静态质量审计。

脚本只使用 Python 标准库，不进行浏览器渲染，也不会修改输入文件。它的
结论仅表示 XML、资源引用和基础版面指标通过静态检查，不能替代视觉验收。
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, cast


# 退出码保持稳定，便于在论文流水线中直接判断结果。
EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3

# 这些阈值对应学术论文单栏或双栏图的常见范围；超出时只说明需要复核。
DEFAULT_MIN_FONT_PT = 8.0
DEFAULT_MAX_CANVAS_SIDE = 10_000.0
DEFAULT_MAX_CANVAS_AREA = 50_000_000.0

_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_LENGTH_RE = re.compile(
    rf"^({_NUMBER})(px|pt|pc|in|cm|mm|q|em|rem|ex|%)?$", re.IGNORECASE
)
_REMOTE_URL_RE = re.compile(r"(?i)(?:https?://|//)[^\s\"'<>]+")
_FONT_DECLARATION_RE = re.compile(r"font-size\s*:\s*([^;}\n]+)", re.IGNORECASE)
_FONT_FAMILY_DECLARATION_RE = re.compile(
    r"(?<![\w-])font-family\s*:\s*([^;}]+)", re.IGNORECASE
)
_CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_HIDDEN_DISPLAY_RE = re.compile(r"(?:^|;)\s*display\s*:\s*none\b", re.IGNORECASE)
_HIDDEN_VISIBILITY_RE = re.compile(
    r"(?:^|;)\s*visibility\s*:\s*(?:hidden|collapse)\b", re.IGNORECASE
)

# 覆盖常用汉字、CJK 扩展 A、兼容表意文字，并顺带覆盖后续扩展区。
_CJK_RE = re.compile(
    r"[\u3005\u3007\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
    r"\U00020000-\U0002A6DF\U0002A700-\U0002B73F"
    r"\U0002B740-\U0002B81F\U0002B820-\U0002CEAF"
    r"\U0002CEB0-\U0002EBEF\U0002F800-\U0002FA1F"
    r"\U00030000-\U0003134F\U00031350-\U000323AF]"
)

# 这些是 CSS generic family；它们本身不能证明含有中文字形。
_GENERIC_FONT_FAMILIES = {
    "cursive",
    "fantasy",
    "fangsong",
    "math",
    "monospace",
    "sans-serif",
    "serif",
    "system-ui",
    "ui-monospace",
    "ui-rounded",
    "ui-sans-serif",
    "ui-serif",
}

# 常见但不能作为中文字体保证的拉丁字体；集合只用于报告原因，不检查本机安装状态。
_UNSAFE_LATIN_FONT_FAMILIES = {
    "arial",
    "arial narrow",
    "calibri",
    "cambria",
    "comic sans ms",
    "consolas",
    "courier",
    "courier new",
    "dejavu sans",
    "georgia",
    "helvetica",
    "inter",
    "liberation sans",
    "lato",
    "menlo",
    "open sans",
    "roboto",
    "segoe ui",
    "tahoma",
    "times",
    "times new roman",
    "trebuchet ms",
    "verdana",
}

# 明确指向中文/CJK 字形的候选。静态门只检查声明，不检查目标机器是否安装。
_CHINESE_FONT_CANDIDATES = {
    "alibaba pu hui ti",
    "arial unicode ms",
    "heiti",
    "heiti sc",
    "hiragino sans gb",
    "kaiti",
    "kaiti sc",
    "lxgw wenkai",
    "microsoft yahei",
    "microsoft yahei ui",
    "noto sans cjk",
    "noto sans cjk cn",
    "noto sans cjk hk",
    "noto sans cjk sc",
    "noto sans cjk tc",
    "noto serif cjk",
    "noto serif cjk cn",
    "noto serif cjk hk",
    "noto serif cjk sc",
    "noto serif cjk tc",
    "pingfang sc",
    "sarasa gothic sc",
    "simsun",
    "simhei",
    "songti",
    "songti sc",
    "source han sans",
    "source han sans cn",
    "source han sans sc",
    "source han serif",
    "source han serif cn",
    "source han serif sc",
    "stheiti",
    "stsong",
    "wenquanyi micro hei",
    "思源宋体",
    "思源黑体",
    "宋体",
    "黑体",
}

# CSS-wide keywords不是可用的字体名称，不能把它们算作已声明字体栈。
_CSS_WIDE_FONT_KEYWORDS = {"inherit", "initial", "revert", "revert-layer", "unset"}


@dataclass(frozen=True)
class Finding:
    """一条可机器读取的审计发现。"""

    code: str
    message: str
    severity: str = "error"
    details: dict[str, Any] = field(default_factory=dict)


def _local_name(tag: Any) -> str:
    """去掉 XML 命名空间，只保留元素本地名。"""

    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _iter_attributes(root: ET.Element) -> Iterable[tuple[int, ET.Element, str, str]]:
    """遍历属性并携带稳定的元素序号，避免依赖 XML 行号。"""

    for index, element in enumerate(root.iter(), start=1):
        for name, value in element.attrib.items():
            yield index, element, name, value


def _parse_length(value: str, *, default_unit: str = "px") -> float | None:
    """把常见 SVG 长度转换为近似像素值；无法判断的单位返回 None。"""

    text = value.strip().lower()
    match = _LENGTH_RE.fullmatch(text)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or default_unit).lower()
    factors = {
        "px": 1.0,
        "pt": 96.0 / 72.0,
        "pc": 16.0,
        "in": 96.0,
        "cm": 96.0 / 2.54,
        "mm": 96.0 / 25.4,
        "q": 96.0 / 101.6,
        # 字号没有继承上下文时采用保守的 12pt 基准。
        "em": 16.0,
        "rem": 16.0,
        "ex": 8.0,
        "%": 0.16,
    }
    if unit not in factors:
        return None
    result = number * factors[unit]
    return result if math.isfinite(result) else None


def _parse_view_box(value: str) -> tuple[float, float, float, float] | None:
    """解析 viewBox 的四个有限数值，并确保宽高为正数。"""

    parts = [part for part in re.split(r"[\s,]+", value.strip()) if part]
    if len(parts) != 4:
        return None
    try:
        numbers = tuple(float(part) for part in parts)
    except ValueError:
        return None
    if not all(math.isfinite(number) for number in numbers):
        return None
    if numbers[2] <= 0 or numbers[3] <= 0:
        return None
    return cast(tuple[float, float, float, float], numbers)


def _font_size_to_pt(raw: str) -> float | None:
    """把 font-size 转换为近似 pt，便于统一比较最小字号。"""

    value = _parse_length(raw, default_unit="px")
    if value is None:
        return None
    # _parse_length 的像素结果转换为排版点。
    return value * 72.0 / 96.0


def _text_value(element: ET.Element) -> str:
    """获取元素及其子节点中的全部文字。"""

    return "".join(element.itertext())


def _normalize_font_family(raw: str) -> str:
    """规范化字体名，去掉 CSS 字体名常见的引号和多余空白。"""

    value = _clean_font_family_name(raw)
    return value.casefold()


def _clean_font_family_name(raw: str) -> str:
    """清理字体名但保留原有大小写，便于在 JSON 中展示声明内容。"""

    value = re.sub(r"\s*!important\s*$", "", raw.strip(), flags=re.IGNORECASE)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return re.sub(r"\s+", " ", value).strip()


def _is_css_wide_font_value(raw: str) -> bool:
    """判断声明是否只是 CSS-wide 继承/重置关键字。"""

    value = re.sub(r"\s*!important\s*$", "", raw.strip(), flags=re.IGNORECASE)
    return _normalize_font_family(value) in _CSS_WIDE_FONT_KEYWORDS


def _split_font_family_list(raw: str) -> list[str]:
    """按逗号拆分 font-family，并保留引号中的逗号。"""

    families: list[str] = []
    buffer: list[str] = []
    quote: str | None = None
    for char in raw:
        if char in {"'", '"'}:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
            buffer.append(char)
            continue
        if char == "," and quote is None:
            family = _clean_font_family_name("".join(buffer))
            if family and _normalize_font_family(family) not in _CSS_WIDE_FONT_KEYWORDS:
                families.append(family)
            buffer = []
            continue
        buffer.append(char)
    family = _clean_font_family_name("".join(buffer))
    if family and _normalize_font_family(family) not in _CSS_WIDE_FONT_KEYWORDS:
        families.append(family)
    return families


def _font_family_declarations_from_css(css: str) -> list[str]:
    """提取 CSS 文本中的 font-family 声明值，忽略注释内容。"""

    clean_css = _CSS_COMMENT_RE.sub("", css)
    return [
        match.group(1).strip()
        for match in _FONT_FAMILY_DECLARATION_RE.finditer(clean_css)
    ]


def _collect_font_families(root: ET.Element) -> tuple[list[dict[str, Any]], list[str]]:
    """收集根/元素属性、style 属性和 style 元素 CSS 中的字体声明。"""

    declarations: list[dict[str, Any]] = []
    families: list[str] = []

    def add_declaration(
        element_index: int, source: str, raw_value: str
    ) -> None:
        value = raw_value.strip()
        parsed_families = _split_font_family_list(value)
        if not value:
            return
        declarations.append(
            {
                "element_index": element_index,
                "raw": value,
                "source": source,
                "families": parsed_families,
            }
        )
        for family in parsed_families:
            if family not in families:
                families.append(family)

    for index, element in enumerate(root.iter(), start=1):
        # SVG 属性是大小写敏感的，规范属性名为小写 font-family。
        attribute_value = element.attrib.get("font-family")
        if attribute_value is not None:
            add_declaration(index, "attribute", attribute_value)

        style_attribute = element.attrib.get("style", "")
        for value in _font_family_declarations_from_css(style_attribute):
            add_declaration(index, "style", value)

        if _local_name(element.tag).lower() == "style":
            for value in _font_family_declarations_from_css(_text_value(element)):
                add_declaration(index, "style_element", value)

    return declarations, families


def _parse_simple_selector(selector: str) -> dict[str, Any] | None:
    """解析有限的单元素 CSS 选择器，复杂选择器一律不参与匹配。"""

    value = selector.strip()
    if not value or any(char.isspace() or char in ">+~:*[]()" for char in value):
        return None

    tag: str | None = None
    element_id: str | None = None
    class_name: str | None = None
    position = 0
    tag_match = re.match(r"[A-Za-z_][A-Za-z0-9_-]*", value)
    if tag_match:
        tag = tag_match.group(0).casefold()
        position = tag_match.end()

    while position < len(value):
        marker = value[position]
        if marker not in {"#", "."}:
            return None
        name_match = re.match(r"[A-Za-z_][A-Za-z0-9_-]*", value[position + 1 :])
        if name_match is None:
            return None
        name = name_match.group(0)
        position += 1 + name_match.end()
        if marker == "#":
            if element_id is not None:
                return None
            element_id = name
        else:
            if class_name is not None:
                return None
            class_name = name

    if tag is None and element_id is None and class_name is None:
        return None
    return {
        "tag": tag,
        "id": element_id,
        "class": class_name,
        "specificity": [
            1 if element_id is not None else 0,
            1 if class_name is not None else 0,
            1 if tag is not None else 0,
        ],
    }


def _iter_top_level_css_blocks(css: str) -> Iterable[tuple[str, str]]:
    """只迭代顶层 CSS 块，避免把未解析的嵌套 at-rule 当作可用规则。"""

    depth = 0
    selector_start = 0
    opening_brace: int | None = None
    for index, char in enumerate(css):
        if char == "{" and depth == 0:
            opening_brace = index
            depth = 1
        elif char == "{" and depth > 0:
            depth += 1
        elif char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and opening_brace is not None:
                yield (
                    css[selector_start:opening_brace].strip(),
                    css[opening_brace + 1 : index],
                )
                selector_start = index + 1
                opening_brace = None


def _collect_css_font_rules(root: ET.Element) -> list[dict[str, Any]]:
    """从 style 元素中提取可匹配的简单 CSS 字体规则。"""

    rules: list[dict[str, Any]] = []
    rule_order = 0
    for element_index, element in enumerate(root.iter(), start=1):
        if _local_name(element.tag).lower() != "style":
            continue
        css = _CSS_COMMENT_RE.sub("", _text_value(element))
        for selector_group, body in _iter_top_level_css_blocks(css):
            if not selector_group or selector_group.startswith("@"):
                continue
            declarations = _font_family_declarations_from_css(body)
            if not declarations:
                continue
            raw_value = declarations[-1]
            for selector_text in selector_group.split(","):
                selector = _parse_simple_selector(selector_text)
                if selector is None:
                    # 复杂/不完整选择器不能被降级为全局规则。
                    continue
                rule_order += 1
                rules.append(
                    {
                        "element_index": element_index,
                        "source": "style_element_css",
                        "selector": selector_text.strip(),
                        "selector_parts": selector,
                        "raw": raw_value,
                        "families": _split_font_family_list(raw_value),
                        "specificity": selector["specificity"],
                        "rule_order": rule_order,
                    }
                )
    return rules


def _selector_matches(selector: dict[str, Any], element: ET.Element) -> bool:
    """判断简单选择器是否匹配指定 SVG 元素。"""

    tag = selector.get("tag")
    if tag is not None and _local_name(element.tag).casefold() != tag:
        return False
    element_id = selector.get("id")
    if element_id is not None and element.attrib.get("id") != element_id:
        return False
    class_name = selector.get("class")
    if class_name is not None:
        classes = set(element.attrib.get("class", "").split())
        if class_name not in classes:
            return False
    return True


def _effective_declaration(
    declarations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """取同一元素上最后一个可审计的字体声明。"""

    for declaration in reversed(declarations):
        if declaration["families"]:
            return declaration
        if not _is_css_wide_font_value(declaration["raw"]):
            return declaration
    return None


def _ancestor_chain(
    element: ET.Element, parent_map: dict[ET.Element, ET.Element]
) -> list[ET.Element]:
    """按当前元素到根元素的顺序返回祖先链。"""

    chain: list[ET.Element] = []
    current: ET.Element | None = element
    while current is not None:
        chain.append(current)
        current = parent_map.get(current)
    return chain


def _resolve_cjk_font_source(
    element: ET.Element,
    *,
    parent_map: dict[ET.Element, ET.Element],
    element_indexes: dict[ET.Element, int],
    declarations_by_element: dict[int, list[dict[str, Any]]],
    css_rules: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """为单个中文 text 解析自身、祖先或匹配 CSS 规则中的字体来源。"""

    chain = _ancestor_chain(element, parent_map)
    for depth, node in enumerate(chain):
        direct = [
            declaration
            for declaration in declarations_by_element.get(element_indexes[node], [])
            if declaration["source"] in {"attribute", "style"}
        ]
        resolved = _effective_declaration(direct)
        if resolved is not None:
            source = dict(resolved)
            source["source_kind"] = (
                "element_style"
                if resolved["source"] == "style" and depth == 0
                else "element_attribute"
                if resolved["source"] == "attribute" and depth == 0
                else "ancestor_style"
                if resolved["source"] == "style"
                else "ancestor_attribute"
            )
            source["element_distance"] = depth
            return source

    # 没有内联/属性声明时，再按当前元素到根的顺序应用可解析 CSS 规则。
    for depth, node in enumerate(chain):
        matched = [
            rule
            for rule in css_rules
            if _selector_matches(rule["selector_parts"], node)
        ]
        if not matched:
            continue
        resolved = max(
            matched,
            key=lambda rule: (tuple(rule["specificity"]), rule["rule_order"]),
        )
        source = dict(resolved)
        source["source_kind"] = "css_selector"
        source["element_distance"] = depth
        return source
    return None


def _audit_cjk_text_font(
    element_index: int,
    value: str,
    *,
    element: ET.Element,
    parent_map: dict[ET.Element, ET.Element],
    element_indexes: dict[ET.Element, int],
    declarations_by_element: dict[int, list[dict[str, Any]]],
    css_rules: list[dict[str, Any]],
) -> dict[str, Any]:
    """返回一个可见中文 text 的字体来源、候选和稳定状态。"""

    source = _resolve_cjk_font_source(
        element,
        parent_map=parent_map,
        element_indexes=element_indexes,
        declarations_by_element=declarations_by_element,
        css_rules=css_rules,
    )
    family_names = list(source["families"]) if source is not None else []
    chinese_candidates = [
        family
        for family in family_names
        if _normalize_font_family(family) in _CHINESE_FONT_CANDIDATES
    ]
    if source is None:
        status = "missing"
        finding_code = "CJK_FONT_FAMILY_MISSING"
    elif not chinese_candidates:
        status = "unsafe"
        finding_code = "CJK_FONT_FALLBACK_UNSAFE"
    else:
        status = "safe"
        finding_code = None
    return {
        "text_element_index": element_index,
        "text": value,
        "cjk_character_count": len(_CJK_RE.findall(value)),
        "status": status,
        "finding_code": finding_code,
        "font_family_names": family_names,
        "generic_font_families": [
            family
            for family in family_names
            if _normalize_font_family(family) in _GENERIC_FONT_FAMILIES
        ],
        "unsafe_latin_font_families": [
            family
            for family in family_names
            if _normalize_font_family(family) in _UNSAFE_LATIN_FONT_FAMILIES
        ],
        "chinese_font_candidates": chinese_candidates,
        "font_family_source": source,
    }


def _is_hidden_text_element(
    element: ET.Element, parent_map: dict[ET.Element, ET.Element]
) -> bool:
    """识别直接或祖先声明为 display:none/visibility:hidden 的 text。"""

    current: ET.Element | None = element
    while current is not None:
        if current.attrib.get("display", "").strip().casefold() == "none":
            return True
        if current.attrib.get("visibility", "").strip().casefold() in {
            "hidden",
            "collapse",
        }:
            return True
        style = current.attrib.get("style", "")
        if _HIDDEN_DISPLAY_RE.search(style) or _HIDDEN_VISIBILITY_RE.search(style):
            return True
        current = parent_map.get(current)
    return False


def _visible_text_value(
    element: ET.Element, parent_map: dict[ET.Element, ET.Element]
) -> str:
    """递归获取 text 中未被隐藏子节点遮蔽的文字。"""

    if _is_hidden_text_element(element, parent_map):
        return ""
    parts: list[str] = []
    if element.text:
        parts.append(element.text)
    for child in element:
        parts.append(_visible_text_value(child, parent_map))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)


def _add_finding(
    findings: list[Finding],
    code: str,
    message: str,
    *,
    severity: str = "error",
    details: dict[str, Any] | None = None,
) -> None:
    """统一追加发现，确保 JSON 字段结构稳定。"""

    findings.append(
        Finding(code=code, message=message, severity=severity, details=details or {})
    )


def _new_result(path: Path) -> dict[str, Any]:
    """创建单文件报告的固定骨架。"""

    return {
        "path": str(path),
        "ok": False,
        "findings": [],
        "metrics": {
            "xml_parsed": False,
            "root_element": None,
            "has_view_box": False,
            "title_count": 0,
            "desc_count": 0,
            "nonempty_title_count": 0,
            "nonempty_desc_count": 0,
            "foreign_object_count": 0,
            "remote_url_count": 0,
            "image_count": 0,
            "external_image_link_count": 0,
            "relative_image_link_count": 0,
            "text_element_count": 0,
            "nonempty_text_element_count": 0,
            "blank_text_element_count": 0,
            "text_character_count": 0,
            "whitespace_character_count": 0,
            "cjk_text_present": False,
            "cjk_character_count": 0,
            "cjk_text_element_count": 0,
            "cjk_text_audit_count": 0,
            "cjk_text_audits": [],
            "cjk_text_audit_passed": True,
            "font_family_declaration_count": 0,
            "font_family_declarations": [],
            "font_family_count": 0,
            "font_family_names": [],
            "chinese_font_candidate_count": 0,
            "chinese_font_candidates": [],
            "has_chinese_font_candidate": False,
            "font_size_count": 0,
            "minimum_font_size_pt": None,
            "view_box": None,
            "canvas_width": None,
            "canvas_height": None,
            "canvas_area": None,
        },
        "thresholds": {
            "minimum_font_size_pt": DEFAULT_MIN_FONT_PT,
            "maximum_canvas_side": DEFAULT_MAX_CANVAS_SIDE,
            "maximum_canvas_area": DEFAULT_MAX_CANVAS_AREA,
        },
    }


def audit_svg(
    path: str | Path,
    *,
    min_font_size_pt: float = DEFAULT_MIN_FONT_PT,
    max_canvas_side: float = DEFAULT_MAX_CANVAS_SIDE,
    max_canvas_area: float = DEFAULT_MAX_CANVAS_AREA,
) -> dict[str, Any]:
    """审计单个 SVG 文件并返回可 JSON 序列化的字典。"""

    svg_path = Path(path)
    result = _new_result(svg_path)
    result["thresholds"] = {
        "minimum_font_size_pt": min_font_size_pt,
        "maximum_canvas_side": max_canvas_side,
        "maximum_canvas_area": max_canvas_area,
    }
    findings: list[Finding] = []

    try:
        source = svg_path.read_bytes()
    except OSError as error:
        _add_finding(
            findings,
            "FILE_READ_ERROR",
            f"无法读取 SVG 文件：{error}",
            details={"exception": type(error).__name__},
        )
        result["findings"] = [asdict(item) for item in findings]
        return result

    try:
        root = ET.fromstring(source)
    except ET.ParseError as error:
        _add_finding(
            findings,
            "XML_PARSE_ERROR",
            f"XML 无法解析：{error}",
            details={"exception": type(error).__name__},
        )
        result["findings"] = [asdict(item) for item in findings]
        return result

    metrics = result["metrics"]
    metrics["xml_parsed"] = True
    metrics["root_element"] = _local_name(root.tag)
    if _local_name(root.tag) != "svg":
        _add_finding(
            findings,
            "ROOT_NOT_SVG",
            f"根元素必须是 svg，实际为 {_local_name(root.tag) or root.tag!r}。",
        )
        # 根元素错误时不再把其子树误判为论文图件，但仍保留基础统计。

    view_box_raw = root.attrib.get("viewBox")
    view_box = _parse_view_box(view_box_raw) if view_box_raw is not None else None
    if view_box is None:
        _add_finding(
            findings,
            "VIEWBOX_MISSING_OR_INVALID",
            "必须提供由四个有限数值组成且宽高为正的 viewBox。",
            details={"value": view_box_raw},
        )
    else:
        metrics["has_view_box"] = True
        metrics["view_box"] = list(view_box)
        metrics["canvas_width"] = view_box[2]
        metrics["canvas_height"] = view_box[3]
        metrics["canvas_area"] = view_box[2] * view_box[3]

        if view_box[2] > max_canvas_side or view_box[3] > max_canvas_side:
            _add_finding(
                findings,
                "CANVAS_TOO_LARGE",
                "viewBox 单边尺寸疑似过大，请检查是否用巨大画布制造空白。",
                details={
                    "width": view_box[2],
                    "height": view_box[3],
                    "maximum_side": max_canvas_side,
                },
            )
        if metrics["canvas_area"] > max_canvas_area:
            _add_finding(
                findings,
                "CANVAS_AREA_TOO_LARGE",
                "viewBox 面积疑似过大，请检查画布与实际图形的比例。",
                details={
                    "area": metrics["canvas_area"],
                    "maximum_area": max_canvas_area,
                },
            )

    # 根节点的 width/height 也纳入画布复核；百分比和 calc() 无法可靠静态换算。
    for dimension in ("width", "height"):
        raw_dimension = root.attrib.get(dimension)
        if raw_dimension is None:
            continue
        parsed_dimension = _parse_length(raw_dimension)
        if parsed_dimension is None:
            continue
        if parsed_dimension > max_canvas_side:
            _add_finding(
                findings,
                "DECLARED_CANVAS_TOO_LARGE",
                f"根元素 {dimension} 声明值疑似过大。",
                details={
                    "attribute": dimension,
                    "value": raw_dimension,
                    "maximum_side": max_canvas_side,
                },
            )

    title_elements = [element for element in root.iter() if _local_name(element.tag) == "title"]
    desc_elements = [element for element in root.iter() if _local_name(element.tag) == "desc"]
    title_count = len(title_elements)
    desc_count = len(desc_elements)
    metrics["title_count"] = title_count
    metrics["desc_count"] = desc_count
    metrics["nonempty_title_count"] = sum(
        1 for element in title_elements if _text_value(element).strip()
    )
    metrics["nonempty_desc_count"] = sum(
        1 for element in desc_elements if _text_value(element).strip()
    )
    if title_count == 0:
        _add_finding(findings, "TITLE_MISSING", "SVG 缺少可访问性 title。")
    elif metrics["nonempty_title_count"] == 0:
        _add_finding(findings, "TITLE_EMPTY", "SVG 的 title 为空，无法提供图形名称。")
    if desc_count == 0:
        _add_finding(findings, "DESC_MISSING", "SVG 缺少可访问性 desc。")
    elif metrics["nonempty_desc_count"] == 0:
        _add_finding(findings, "DESC_EMPTY", "SVG 的 desc 为空，无法提供图形说明。")

    foreign_objects = [
        element for element in root.iter() if _local_name(element.tag).lower() == "foreignobject"
    ]
    metrics["foreign_object_count"] = len(foreign_objects)
    if foreign_objects:
        _add_finding(
            findings,
            "FOREIGN_OBJECT_PRESENT",
            "SVG 包含 foreignObject，可能导致跨渲染器或论文排版不一致。",
            details={"count": len(foreign_objects)},
        )

    # 统计文本并找出空白 text 节点；title/desc 不计入图中可见文字统计。
    all_elements = list(root.iter())
    element_indexes = {
        element: index for index, element in enumerate(all_elements, start=1)
    }
    text_elements = [element for element in all_elements if _local_name(element.tag) == "text"]
    metrics["text_element_count"] = len(text_elements)
    parent_map = {
        child: parent
        for parent in all_elements
        for child in parent
    }
    nonempty_texts: list[str] = []
    visible_nonempty_texts: list[tuple[int, str]] = []
    blank_texts: list[int] = []
    for element in text_elements:
        index = element_indexes[element]
        value = _text_value(element)
        metrics["text_character_count"] += len(value)
        metrics["whitespace_character_count"] += sum(1 for char in value if char.isspace())
        if value.strip():
            nonempty_texts.append(value)
            visible_value = _visible_text_value(element, parent_map)
            if visible_value.strip():
                visible_nonempty_texts.append((index, visible_value))
        else:
            blank_texts.append(index)
    metrics["nonempty_text_element_count"] = len(nonempty_texts)
    metrics["blank_text_element_count"] = len(blank_texts)
    if not text_elements:
        _add_finding(
            findings,
            "TEXT_ELEMENTS_MISSING",
            "SVG 没有可见 text 元素，学术图中的标签可能缺失。",
        )
    if blank_texts:
        _add_finding(
            findings,
            "BLANK_TEXT_ELEMENT",
            "SVG 包含空白 text 元素，可能是未清理的占位节点。",
            details={"text_element_indexes": blank_texts},
        )

    # 中文字体门只针对可见 text，不把 title/desc 或隐藏占位文字当作图中标签。
    cjk_characters = [
        character
        for _element_index, value in visible_nonempty_texts
        for character in _CJK_RE.findall(value)
    ]
    metrics["cjk_character_count"] = len(cjk_characters)
    metrics["cjk_text_element_count"] = sum(
        1 for _element_index, value in visible_nonempty_texts if _CJK_RE.search(value)
    )
    metrics["cjk_text_present"] = bool(cjk_characters)

    # 检查属性、样式和文字中的远程 URL。XML 命名空间声明不会出现在 attrib 中，
    # 因而不会把标准 SVG 命名空间误报为远程资源。
    remote_urls: set[str] = set()
    for _index, _element, _name, value in _iter_attributes(root):
        remote_urls.update(_REMOTE_URL_RE.findall(value))
    for element in root.iter():
        remote_urls.update(_REMOTE_URL_RE.findall(_text_value(element)))
    metrics["remote_url_count"] = len(remote_urls)
    if remote_urls:
        _add_finding(
            findings,
            "REMOTE_URL_PRESENT",
            "SVG 包含远程 URL，不符合自包含论文图要求。",
            details={"urls": sorted(remote_urls)},
        )

    image_elements = [element for element in root.iter() if _local_name(element.tag) == "image"]
    metrics["image_count"] = len(image_elements)
    remote_images: list[dict[str, str]] = []
    relative_images: list[dict[str, str]] = []
    for index, element in enumerate(image_elements, start=1):
        href_values = [
            value
            for name, value in element.attrib.items()
            if _local_name(name).lower() == "href"
        ]
        for href in href_values:
            if href.strip().lower().startswith("data:") or href.strip().startswith("#"):
                continue
            link = {"image_index": str(index), "href": href}
            if _REMOTE_URL_RE.search(href):
                remote_images.append(link)
            else:
                # 相对路径属于可审计的本地资源，不等同于远程外链。
                relative_images.append(link)
    metrics["external_image_link_count"] = len(remote_images)
    metrics["relative_image_link_count"] = len(relative_images)
    if remote_images:
        _add_finding(
            findings,
            "IMAGE_REMOTE_LINK",
            "image 元素引用了远程图片外链，不符合自包含论文图要求。",
            details={"links": remote_images},
        )

    font_family_declarations, font_family_names = _collect_font_families(root)
    chinese_font_candidates = [
        family
        for family in font_family_names
        if _normalize_font_family(family) in _CHINESE_FONT_CANDIDATES
    ]
    metrics["font_family_declaration_count"] = len(font_family_declarations)
    metrics["font_family_declarations"] = font_family_declarations
    metrics["font_family_count"] = len(font_family_names)
    metrics["font_family_names"] = font_family_names
    metrics["chinese_font_candidate_count"] = len(chinese_font_candidates)
    metrics["chinese_font_candidates"] = chinese_font_candidates
    metrics["has_chinese_font_candidate"] = bool(chinese_font_candidates)

    declarations_by_element: dict[int, list[dict[str, Any]]] = {}
    for declaration in font_family_declarations:
        declarations_by_element.setdefault(declaration["element_index"], []).append(
            declaration
        )
    css_rules = _collect_css_font_rules(root)
    cjk_text_audits: list[dict[str, Any]] = []
    for element_index, value in visible_nonempty_texts:
        if not _CJK_RE.search(value):
            continue
        audit = _audit_cjk_text_font(
            element_index,
            value,
            element=all_elements[element_index - 1],
            parent_map=parent_map,
            element_indexes=element_indexes,
            declarations_by_element=declarations_by_element,
            css_rules=css_rules,
        )
        cjk_text_audits.append(audit)
        finding_code = audit["finding_code"]
        if finding_code is not None:
            message = (
                "可见中文 text 没有声明可审计的 font-family。"
                if finding_code == "CJK_FONT_FAMILY_MISSING"
                else "可见中文 text 的字体栈没有明确中文字体候选，无法保证中文字形。"
            )
            _add_finding(
                findings,
                finding_code,
                message,
                details=audit,
            )
    metrics["cjk_text_audit_count"] = len(cjk_text_audits)
    metrics["cjk_text_audits"] = cjk_text_audits
    metrics["cjk_text_audit_passed"] = all(
        audit["status"] == "safe" for audit in cjk_text_audits
    )

    # 同时检查属性中的 font-size、style 属性和 style 元素中的 CSS 声明。
    font_sizes: list[dict[str, Any]] = []
    for index, element in enumerate(root.iter(), start=1):
        direct_font_size = element.attrib.get("font-size")
        if direct_font_size is not None:
            font_sizes.append(
                {
                    "element_index": index,
                    "raw": direct_font_size,
                    "pt": _font_size_to_pt(direct_font_size),
                    "source": "attribute",
                }
            )
        style_attribute = element.attrib.get("style", "")
        declarations = list(_FONT_DECLARATION_RE.finditer(style_attribute))
        if _local_name(element.tag).lower() == "style":
            declarations.extend(_FONT_DECLARATION_RE.finditer(_text_value(element)))
        for declaration in declarations:
            raw_size = declaration.group(1).strip().split()[0]
            font_sizes.append(
                {
                    "element_index": index,
                    "raw": raw_size,
                    "pt": _font_size_to_pt(raw_size),
                    "source": "style",
                }
            )
    metrics["font_size_count"] = len(font_sizes)
    numeric_font_sizes = [item["pt"] for item in font_sizes if item["pt"] is not None]
    if numeric_font_sizes:
        metrics["minimum_font_size_pt"] = min(numeric_font_sizes)
    small_fonts = [
        item for item in font_sizes if item["pt"] is not None and item["pt"] < min_font_size_pt
    ]
    if small_fonts:
        _add_finding(
            findings,
            "FONT_TOO_SMALL",
            f"发现小于 {min_font_size_pt:g}pt 的字号，嵌入论文后可能不可读。",
            details={"fonts": small_fonts},
        )

    result["findings"] = [asdict(item) for item in findings]
    result["ok"] = not findings
    return result


def audit_paths(
    paths: Iterable[str | Path],
    *,
    min_font_size_pt: float = DEFAULT_MIN_FONT_PT,
    max_canvas_side: float = DEFAULT_MAX_CANVAS_SIDE,
    max_canvas_area: float = DEFAULT_MAX_CANVAS_AREA,
) -> dict[str, Any]:
    """审计多个 SVG 并返回统一汇总报告。"""

    files = [
        audit_svg(
            path,
            min_font_size_pt=min_font_size_pt,
            max_canvas_side=max_canvas_side,
            max_canvas_area=max_canvas_area,
        )
        for path in paths
    ]
    failed = sum(1 for item in files if not item["ok"])
    finding_count = sum(len(item["findings"]) for item in files)
    return {
        "version": 1,
        "files": files,
        "summary": {
            "file_count": len(files),
            "passed_count": len(files) - failed,
            "failed_count": failed,
            "finding_count": finding_count,
        },
        "exit_code": EXIT_FINDINGS if failed else EXIT_OK,
    }


def _build_parser() -> argparse.ArgumentParser:
    """构造命令行参数解析器。"""

    parser = argparse.ArgumentParser(
        description="对一个或多个学术 SVG 执行 XML、资源和基础可读性静态审计。"
    )
    parser.add_argument("svg_paths", nargs="+", metavar="SVG", help="待审计的 SVG 路径")
    parser.add_argument(
        "--json", action="store_true", help="以稳定的 JSON 对象输出审计结果"
    )
    parser.add_argument(
        "--min-font-size",
        type=float,
        default=DEFAULT_MIN_FONT_PT,
        metavar="PT",
        help=f"最小字号阈值，单位 pt，默认 {DEFAULT_MIN_FONT_PT:g}",
    )
    parser.add_argument(
        "--max-canvas-side",
        type=float,
        default=DEFAULT_MAX_CANVAS_SIDE,
        metavar="UNIT",
        help=f"画布单边最大值，默认 {DEFAULT_MAX_CANVAS_SIDE:g}",
    )
    parser.add_argument(
        "--max-canvas-area",
        type=float,
        default=DEFAULT_MAX_CANVAS_AREA,
        metavar="UNIT2",
        help=f"画布最大面积，默认 {DEFAULT_MAX_CANVAS_AREA:g}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行入口，返回稳定退出码。"""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.min_font_size <= 0 or args.max_canvas_side <= 0 or args.max_canvas_area <= 0:
        parser.error("字号和画布阈值必须为正数。")

    try:
        report = audit_paths(
            args.svg_paths,
            min_font_size_pt=args.min_font_size,
            max_canvas_side=args.max_canvas_side,
            max_canvas_area=args.max_canvas_area,
        )
    except Exception as error:
        print(f"内部错误：{type(error).__name__}: {error}", file=sys.stderr)
        return EXIT_INTERNAL

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in report["files"]:
            if item["ok"]:
                print(f"[通过] {item['path']}")
            else:
                print(f"[失败] {item['path']}")
                for finding in item["findings"]:
                    print(
                        f"  - [{finding['severity']}] {finding['code']}："
                        f"{finding['message']}"
                    )
        summary = report["summary"]
        print(
            "汇总："
            f"文件 {summary['file_count']}，通过 {summary['passed_count']}，"
            f"失败 {summary['failed_count']}，发现 {summary['finding_count']}。"
        )
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
