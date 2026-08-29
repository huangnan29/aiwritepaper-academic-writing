#!/usr/bin/env python3
"""机械检查Markdown公式语法及DOCX/PDF公式渲染，不判断公式学术含义。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
RAW_TEX_COMMAND = re.compile(
    r"\\(?:frac|dfrac|tfrac|sqrt|text|mathrm|mathbf|mathit|mathbb|partial|nabla|cdot|times|"
    r"approx|Omega|omega|mu|alpha|beta|gamma|delta|theta|lambda|sigma|pi|sum|prod|int|lim|log|exp|"
    r"sin|cos|tan|le|ge|in|notin|rightarrow|leftarrow|overline|hat|bar|vec|left|right|begin|end)\b"
)
RAW_DELIMITER = re.compile(r"\$\$|\\\[|\\\]|\\\(|\\\)")
RAW_SINGLE_DOLLAR_PAIR = re.compile(r"(?<!\\)\$(?!\$)[^$\n]{1,500}(?<!\\)\$")
MATH_HINT = re.compile(
    r"\$\$(?:.|\n)*?\$\$|\\\[(?:.|\n)*?\\\]|\\\((?:.|\n)*?\\\)|(?<!\\)\$(?!\$)[^$\n]+?(?<!\\)\$",
    re.MULTILINE,
)


@dataclass
class Formula:
    delimiter: str
    content: str
    line: int
    display: bool


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verifier_identity() -> Dict[str, str]:
    script = Path(__file__).resolve()
    return {
        "name": script.name, "version": "1.9.0", "sha256": sha256(script),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def strip_code_fences(text: str) -> str:
    return re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.DOTALL)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def brace_error(content: str) -> Optional[str]:
    depth = 0
    escaped = False
    for char in content:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return "出现多余右花括号"
    if depth:
        return f"花括号未闭合，差值={depth}"
    return None


def extract_formulas(text: str) -> Tuple[List[Formula], List[str]]:
    """按出现顺序解析四类公式分隔符，并报告未闭合分隔符。"""
    source = strip_code_fences(text)
    formulas: List[Formula] = []
    errors: List[str] = []
    index = 0
    length = len(source)
    while index < length:
        if source.startswith("$$", index):
            end = source.find("$$", index + 2)
            if end < 0:
                errors.append(f"SOURCE_DELIMITER_UNBALANCED: 第{line_number(source, index)}行缺少结束$$")
                break
            formulas.append(Formula("$$", source[index + 2:end], line_number(source, index), True))
            index = end + 2
            continue
        if source.startswith(r"\[", index):
            end = source.find(r"\]", index + 2)
            if end < 0:
                errors.append(rf"SOURCE_DELIMITER_UNBALANCED: 第{line_number(source, index)}行缺少结束\]")
                break
            formulas.append(Formula(r"\[", source[index + 2:end], line_number(source, index), True))
            index = end + 2
            continue
        if source.startswith(r"\(", index):
            end = source.find(r"\)", index + 2)
            if end < 0:
                errors.append(rf"SOURCE_DELIMITER_UNBALANCED: 第{line_number(source, index)}行缺少结束\)")
                break
            formulas.append(Formula(r"\(", source[index + 2:end], line_number(source, index), False))
            index = end + 2
            continue
        if source[index] == "$" and (index == 0 or source[index - 1] != "\\"):
            end = index + 1
            while True:
                end = source.find("$", end)
                if end < 0:
                    errors.append(f"SOURCE_DELIMITER_UNBALANCED: 第{line_number(source, index)}行缺少结束$")
                    index = length
                    break
                if source[end - 1] != "\\" and not source.startswith("$$", end):
                    content = source[index + 1:end]
                    if "\n" in content:
                        errors.append(f"SOURCE_INLINE_MULTILINE: 第{line_number(source, index)}行的行内公式跨行")
                    formulas.append(Formula("$", content, line_number(source, index), False))
                    index = end + 1
                    break
                end += 1
            continue
        index += 1

    for formula in formulas:
        if not formula.content.strip():
            errors.append(f"SOURCE_FORMULA_EMPTY: 第{formula.line}行")
        mismatch = brace_error(formula.content)
        if mismatch:
            errors.append(f"SOURCE_BRACE_UNBALANCED: 第{formula.line}行{mismatch}")
        control_names = {
            "\t": "TAB", "\x00": "NUL", "\x08": "BACKSPACE", "\x0b": "VERTICAL_TAB",
            "\x0c": "FORM_FEED", "\x1b": "ESC",
        }
        controls = sorted({
            control_names.get(char, f"U+{ord(char):04X}")
            for char in formula.content
            if ord(char) < 32 and char != "\n"
        })
        if controls:
            errors.append(
                f"SOURCE_CONTROL_CHARACTER: 第{formula.line}行公式含{','.join(controls)}，可能由反斜杠转义损坏"
            )
        begin_envs = re.findall(r"\\begin\{([^}]+)\}", formula.content)
        end_envs = re.findall(r"\\end\{([^}]+)\}", formula.content)
        if begin_envs != end_envs:
            errors.append(f"SOURCE_ENVIRONMENT_UNBALANCED: 第{formula.line}行 begin={begin_envs} end={end_envs}")
    return formulas, errors


def raw_tex_hits(text: str) -> List[str]:
    hits = RAW_DELIMITER.findall(text) + RAW_TEX_COMMAND.findall(text)
    if RAW_SINGLE_DOLLAR_PAIR.search(text):
        hits.append("$")
    return sorted(set(hits))


def docx_metrics(path: Path) -> Tuple[Dict[str, Any], List[str]]:
    errors: List[str] = []
    metrics: Dict[str, Any] = {"omml_count": 0, "raw_tex_hits": [], "visible_text_length": 0}
    if not path.is_file() or path.stat().st_size == 0:
        return metrics, [f"DOCX_MISSING: {path}"]
    if not zipfile.is_zipfile(path):
        return metrics, [f"DOCX_INVALID: {path}"]
    try:
        with zipfile.ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                return metrics, [f"DOCX_DOCUMENT_XML_MISSING: {path}"]
            root = ET.fromstring(archive.read("word/document.xml"))
    except (OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        return metrics, [f"DOCX_PARSE_FAILED: {exc}"]
    visible = "\n".join(node.text or "" for node in root.findall(f".//{{{WORD_NS}}}t"))
    metrics["visible_text_length"] = len(visible)
    metrics["omml_count"] = len(root.findall(f".//{{{MATH_NS}}}oMath"))
    metrics["raw_tex_hits"] = raw_tex_hits(visible)
    if metrics["raw_tex_hits"]:
        errors.append("DOCX_RAW_LATEX: " + ", ".join(metrics["raw_tex_hits"]))
    return metrics, errors


def extract_pdf_text(path: Path) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """优先使用pypdf，降级使用本地pdftotext；都不可用时返回能力缺口。"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages), "pypdf", len(reader.pages)
    except ImportError:
        pass
    except Exception as exc:
        return None, f"pypdf-error:{exc}", None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "paper.txt"
            completed = subprocess.run(
                ["pdftotext", "-layout", str(path), str(output)],
                check=False, capture_output=True, text=True, timeout=120,
            )
            if completed.returncode != 0:
                return None, f"pdftotext-error:{completed.stderr.strip()}", None
            return output.read_text(encoding="utf-8", errors="replace"), "pdftotext", None
    except FileNotFoundError:
        return None, "CAPABILITY_GAP: 缺少pypdf和pdftotext", None
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"pdftotext-error:{exc}", None


def pdf_metrics(path: Path) -> Tuple[Dict[str, Any], List[str]]:
    metrics: Dict[str, Any] = {"extractor": None, "pages": None, "raw_tex_hits": [], "visible_text_length": 0}
    if not path.is_file() or path.stat().st_size == 0:
        return metrics, [f"PDF_MISSING: {path}"]
    if path.stat().st_size < 8 or path.read_bytes()[:5] != b"%PDF-":
        return metrics, [f"PDF_INVALID: {path}"]
    text, extractor, pages = extract_pdf_text(path)
    metrics["extractor"] = extractor
    metrics["pages"] = pages
    if text is None:
        return metrics, [f"PDF_TEXT_CHECK_UNAVAILABLE: {extractor}"]
    metrics["visible_text_length"] = len(text)
    metrics["raw_tex_hits"] = raw_tex_hits(text)
    errors: List[str] = []
    if metrics["raw_tex_hits"]:
        errors.append("PDF_RAW_LATEX: " + ", ".join(metrics["raw_tex_hits"]))
    return metrics, errors


def resolve_under_root(root: Path, value: Any, field: str) -> Tuple[Optional[Path], Optional[str]]:
    if not isinstance(value, str) or not value.strip():
        return None, f"MANIFEST_PATH_MISSING: {field}"
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None, f"MANIFEST_PATH_ESCAPE: {field}={value}"
    if not path.is_file() or path.stat().st_size == 0:
        return None, f"FINAL_FILE_MISSING: {field}={value}"
    return path, None


class FormulaVerifier:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.hashes: Dict[str, str] = {}

    def verify(self, markdown: Path, run_manifest: Path, audit: Path) -> None:
        if not markdown.is_file() or markdown.stat().st_size == 0:
            self.errors.append(f"MARKDOWN_MISSING: {markdown}")
            return
        source = markdown.read_text(encoding="utf-8", errors="replace")
        forbidden_controls = sorted({
            f"U+{ord(char):04X}" for char in strip_code_fences(source)
            if ord(char) < 32 and char not in {"\n", "\t"}
        })
        if forbidden_controls:
            self.errors.append(
                "SOURCE_CONTROL_CHARACTER: Markdown含异常控制字符" + ",".join(forbidden_controls)
            )
        formulas, source_errors = extract_formulas(source)
        self.errors.extend(source_errors)
        self.metrics["source"] = {
            "formula_count": len(formulas),
            "inline_count": sum(not item.display for item in formulas),
            "display_count": sum(item.display for item in formulas),
            "delimiters": {name: sum(item.delimiter == name for item in formulas) for name in ["$", "$$", r"\(", r"\["]},
        }
        self.hashes["markdown_sha256"] = sha256(markdown)
        if run_manifest.is_file():
            self.hashes["run_manifest_sha256"] = sha256(run_manifest)

        source_without_math = MATH_HINT.sub("", strip_code_fences(source))
        outside_hits = raw_tex_hits(source_without_math)
        if outside_hits:
            self.errors.append("SOURCE_RAW_LATEX_OUTSIDE_MATH: " + ", ".join(outside_hits))
        if any(item.delimiter in {r"\(", r"\["} for item in formulas):
            self.errors.append("SOURCE_DELIMITER_NOT_NORMALIZED: 最终Markdown必须统一使用$与$$")

        if not audit.is_file() or audit.stat().st_size == 0:
            self.errors.append(f"FORMULA_AUDIT_MISSING: {audit}")
        else:
            audit_text = audit.read_text(encoding="utf-8", errors="replace")
            self.hashes["audit_sha256"] = sha256(audit)
            if formulas and not all(term in audit_text for term in ["符号", "单位", "量纲", "视觉"]):
                self.errors.append("FORMULA_AUDIT_INCOMPLETE: 缺少符号、单位、量纲或视觉复核记录")

        try:
            manifest = json.loads(run_manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.errors.append(f"RUN_MANIFEST_INVALID: {exc}")
            return
        if not isinstance(manifest, dict):
            self.errors.append("RUN_MANIFEST_SHAPE: 根对象必须是对象")
            return
        docx, docx_error = resolve_under_root(self.root, manifest.get("docx"), "docx")
        pdf, pdf_error = resolve_under_root(self.root, manifest.get("pdf"), "pdf")
        if docx_error:
            self.errors.append(docx_error)
        if pdf_error:
            self.errors.append(pdf_error)
        if docx:
            self.hashes["docx_sha256"] = sha256(docx)
            declared = manifest.get("docx_sha256")
            if not isinstance(declared, str) or declared.lower() != self.hashes["docx_sha256"]:
                self.errors.append("DOCX_HASH_MISMATCH: run-manifest.json")
            docx_result, docx_errors = docx_metrics(docx)
            self.metrics["docx"] = docx_result
            self.errors.extend(docx_errors)
            if formulas and docx_result["omml_count"] < len(formulas):
                self.errors.append(
                    f"DOCX_OMML_COUNT_LOW: 源稿公式={len(formulas)}，Word公式对象={docx_result['omml_count']}"
                )
        if pdf:
            self.hashes["pdf_sha256"] = sha256(pdf)
            declared = manifest.get("pdf_sha256")
            if not isinstance(declared, str) or declared.lower() != self.hashes["pdf_sha256"]:
                self.errors.append("PDF_HASH_MISMATCH: run-manifest.json")
            pdf_result, pdf_errors = pdf_metrics(pdf)
            self.metrics["pdf"] = pdf_result
            for error in pdf_errors:
                if not formulas and error.startswith("PDF_TEXT_CHECK_UNAVAILABLE"):
                    self.warnings.append(error)
                else:
                    self.errors.append(error)


def rooted(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验Markdown、DOCX与PDF公式渲染")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--markdown", type=Path, default=Path("07-paper-full.md"))
    parser.add_argument("--run-manifest", type=Path, default=Path("run-manifest.json"))
    parser.add_argument("--audit", type=Path, default=Path("equations/formula-audit.md"))
    parser.add_argument("--report", type=Path, default=Path("equations/formula-verification.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    verifier = FormulaVerifier(root)
    markdown_path = rooted(root, args.markdown)
    manifest_path = rooted(root, args.run_manifest)
    audit_path = rooted(root, args.audit)
    verifier.verify(markdown_path, manifest_path, audit_path)
    input_sha256: Dict[str, str] = {}
    for path in [markdown_path, manifest_path, audit_path]:
        if path.is_file():
            try:
                input_sha256[str(path.resolve().relative_to(root))] = sha256(path)
            except ValueError:
                pass
    for field, manifest_field in [("docx", "docx"), ("pdf", "pdf")]:
        try:
            run_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            value = run_payload.get(manifest_field)
            candidate = resolve_under_root(root, value, manifest_field)[0] if value else None
            if candidate:
                input_sha256[str(candidate.relative_to(root))] = sha256(candidate)
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    payload = {
        "schema_version": "1.0",
        "status": "FORMULA_OK" if not verifier.errors else "FORMULA_FAIL",
        "errors": verifier.errors,
        "warnings": verifier.warnings,
        "hashes": verifier.hashes,
        "input_sha256": input_sha256,
        "metrics": verifier.metrics,
        "verifier": verifier_identity(),
        "scope_note": "机械通过不代表公式推导、符号含义或学术结论正确",
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    report = rooted(root, args.report)
    try:
        report.relative_to(root)
    except ValueError:
        print("报告路径必须位于输出目录内", file=sys.stderr)
        return 1
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not verifier.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
