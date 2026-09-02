#!/usr/bin/env python3
"""机械校验正文计数、证据矩阵与最终DOCX/PDF交付，不参与学术内容决策。"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import hashlib
import json
import re
import statistics
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
VALID_REFERENCE_STATUSES = {"VERIFIED_FULLTEXT", "VERIFIED_METADATA", "UNVERIFIED", "REJECTED"}
DOCUMENT_PROFILES = {"THESIS", "JOURNAL", "REPORT", "CUSTOM"}
EVIDENCE_FIELD_GROUPS = {
    "title": {"title", "题名"},
    "authors": {"authors", "author", "作者"},
    "year": {"year", "年份"},
    "identifier": {"doi", "url", "DOI", "URL"},
    "verification_source": {"verification_source", "核验来源"},
    "supported_claim": {"supported_claim", "supported_claims", "supports_claim", "支持主张"},
    "chapter": {"chapter", "chapters", "章节"},
    "evidence_role": {"evidence_role"},
    "access_mode": {"access_mode"},
    "publication_status": {"publication_status"},
    "notes": {"notes", "备注"},
}
BOUNDARY_TERMS = ["本文", "不得", "不能", "没有", "推断", "方案性", "未实施", "未测", "不报告", "不编造"]
TIMESTAMPED_NAME = re.compile(r"^.+_\d{8}-\d{6}\.(docx|pdf)$", re.IGNORECASE)
CHAPTER_HEADING = re.compile(
    r"^#{1,6}\s*(?:第?\s*[一二三四五六七八九十百0-9]+\s*章|[一二三四五六七八九十百0-9]+\s*[.、]\s*\S+)",
    re.MULTILINE,
)
REFERENCE_HEADING = re.compile(r"^#{1,6}\s*(?:参考文献|References)\s*$", re.MULTILINE | re.IGNORECASE)


class DeliveryVerifier:
    def __init__(self, root: Path, minimum: int, maximum: int, target: int) -> None:
        self.root = root.resolve()
        self.minimum = minimum
        self.maximum = maximum
        self.target = target
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.require_bilingual_abstract = False

    def error(self, code: str, detail: str) -> None:
        self.errors.append(f"{code}: {detail}")

    def warning(self, code: str, detail: str) -> None:
        self.warnings.append(f"{code}: {detail}")

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def resolve_relative_file(self, value: Any, field: str) -> Optional[Path]:
        if not isinstance(value, str) or not value.strip():
            self.error("FINAL_PATH_MISSING", field)
            return None
        candidate = (self.root / value).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            self.error("FINAL_PATH_ESCAPE", f"{field}: {value}")
            return None
        if not candidate.is_file() or candidate.stat().st_size == 0:
            self.error("FINAL_FILE_MISSING", f"{field}: {value}")
            return None
        return candidate

    @staticmethod
    def manuscript_body(text: str) -> str:
        first = CHAPTER_HEADING.search(text)
        if not first:
            return ""
        reference = REFERENCE_HEADING.search(text, first.end())
        body = text[first.start():reference.start() if reference else len(text)]
        body = re.sub(r"```.*?```", "", body, flags=re.DOTALL)
        # Pandoc可能把复杂表格展开成TeX longtable/tabular，多行内容不属于正文计数。
        body = re.sub(
            r"\\begin\{(?:longtable|tabular|tabularx|table)\}.*?\\end\{(?:longtable|tabular|tabularx|table)\}",
            "",
            body,
            flags=re.DOTALL | re.IGNORECASE,
        )
        body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
        body = re.sub(r"<[^>]+>", "", body)
        lines = body.splitlines()
        table_lines: set[int] = set()
        # Pandoc多行表格允许空行分隔记录，列分隔横线之间也可能只有一个空格。
        # 必须同时见到外框、列分隔线和闭合外框，不能把普通分隔线后的正文吞掉。
        border = re.compile(r"^ {2,}-{10,}\s*$")
        columns = re.compile(r"^ {2,}(?:-{3,}\s+)+-{3,}\s*$")
        index = 0
        while index < len(lines):
            if not border.match(lines[index]):
                index += 1
                continue
            end = index + 1
            while end < len(lines) and not border.match(lines[end]) and not re.match(r"^#{1,6}\s", lines[end]):
                end += 1
            if end < len(lines) and border.match(lines[end]) and any(columns.match(row) for row in lines[index + 1:end]):
                table_lines.update(range(index, end + 1))
                index = end + 1
            else:
                index += 1
        # 识别Pandoc纯Markdown多行表格：两空格列分隔或管线列分隔，且有长横线分隔行。
        separator = re.compile(r"^\s{2,}(?:[-‐‑‒–—]{3,}\s{2,})+[-‐‑‒–—]{3,}\s*$")
        for index, line in enumerate(lines):
            if not (separator.match(line) or ("|" in line and re.search(r"[-‐‑‒–—]{3,}", line))):
                continue
            start = index
            while start > 0 and lines[start - 1].strip() and ("|" in lines[start - 1] or re.search(r"\s{2,}", lines[start - 1])):
                start -= 1
            end = index
            while end + 1 < len(lines) and lines[end + 1].strip() and ("|" in lines[end + 1] or re.search(r"\s{2,}", lines[end + 1])):
                end += 1
            table_lines.update(range(start, end + 1))
        kept: List[str] = []
        for index, line in enumerate(lines):
            stripped = line.strip()
            if index in table_lines:
                continue
            if stripped.startswith("|"):
                continue
            # 表格边界和Pandoc控制行不计入正文，但不改动原始Markdown文件。
            if re.match(r"^(?:\s*:::|\s*\\(?:toprule|midrule|bottomrule|endhead|endfirsthead|arraybackslash)\b)", stripped, re.IGNORECASE):
                continue
            if re.match(r"^(?:图|表)\s*[0-9]+(?:[-－—.][0-9]+)*\s+", stripped):
                continue
            cleaned = re.sub(r"\\[A-Za-z@]+\*?(?:\s*\[[^\]]*\])?", " ", line)
            kept.append(re.sub(r"^#{1,6}\s*", "", cleaned))
        return "\n".join(kept)

    def verify_body_length(self, markdown: Path) -> None:
        if not markdown.is_file():
            self.error("MARKDOWN_MISSING", str(markdown))
            return
        text = markdown.read_text(encoding="utf-8", errors="replace")
        body = self.manuscript_body(text)
        if not body:
            self.error("BODY_BOUNDARY_MISSING", "没有找到第一章正文")
            return
        han = len(re.findall(r"[\u3400-\u9fff]", body))
        english_words = len(re.findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", body))
        units = han + english_words
        self.metrics["body_length"] = {
            "target": self.target,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "han_characters": han,
            "english_words": english_words,
            "effective_units": units,
        }
        preferred_min = round(self.target * 0.95)
        preferred_max = round(self.target * 1.05)
        if units < preferred_min:
            self.warning("BODY_TARGET_UNDERSHOOT", f"实际{units}，建议目标区间{preferred_min}-{preferred_max}")
        boundary_count = sum(body.count(term) for term in BOUNDARY_TERMS)
        boundary_density = boundary_count / max(units, 1) * 10000
        self.metrics["prose_advisory"] = {
            "boundary_term_count": boundary_count,
            "per_10000_units": round(boundary_density, 2),
        }
        if boundary_density > 55:
            self.warning("PROSE_BOUNDARY_REPETITION", f"边界词密度{boundary_density:.1f}/万单位，仅作修订提示")
        if units < self.minimum:
            self.error("BODY_LENGTH_LOW", f"实际{units}，最低{self.minimum}")
        elif units > self.maximum:
            self.error("BODY_LENGTH_HIGH", f"实际{units}，最高{self.maximum}")

    def verify_abstracts(self, markdown: Path, contract: str) -> None:
        if not markdown.is_file():
            return
        text = markdown.read_text(encoding="utf-8", errors="replace")
        chinese = bool(re.search(r"^(?:#{1,6}\s*摘要\s*$|\*\*摘要[:：]?\*\*)", text, re.MULTILINE))
        english = bool(re.search(r"^#{1,6}\s*Abstract\s*$", text, re.MULTILINE | re.IGNORECASE))
        chinese_keywords = bool(re.search(r"(?:关键词|关键字)[:：]", text))
        english_keywords = bool(re.search(r"\bKeywords?\s*[:：]", text, re.IGNORECASE))
        self.metrics["abstracts"] = {"contract": contract, "chinese": chinese, "english": english, "chinese_keywords": chinese_keywords, "english_keywords": english_keywords}
        if contract == "BILINGUAL":
            self.require_bilingual_abstract = True
            for code, ok in [("CHINESE_ABSTRACT_MISSING", chinese), ("ENGLISH_ABSTRACT_MISSING", english), ("CHINESE_KEYWORDS_MISSING", chinese_keywords), ("ENGLISH_KEYWORDS_MISSING", english_keywords)]:
                if not ok: self.error(code, str(markdown))

    def verify_evidence_matrix(
        self, matrix: Path, markdown: Path, bibliography: Path,
        citation_mode: str = "NUMERIC",
    ) -> None:
        if not matrix.is_file():
            self.error("EVIDENCE_MATRIX_MISSING", str(matrix))
            return
        rows: List[Dict[str, Any]] = []
        try:
            with matrix.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, restkey="__extra__", restval="__missing__")
                if not reader.fieldnames or "source_id" not in reader.fieldnames or "status" not in reader.fieldnames:
                    self.error("EVIDENCE_MATRIX_HEADER", "缺少source_id或status")
                    return
                field_lookup: Dict[str, List[str]] = {}
                for group, aliases in EVIDENCE_FIELD_GROUPS.items():
                    matched = [field for field in reader.fieldnames if field in aliases or field.lower() in {a.lower() for a in aliases}]
                    field_lookup[group] = matched
                    if not matched:
                        self.error("EVIDENCE_MATRIX_REQUIRED_FIELD", group)
                for line_number, row in enumerate(reader, start=2):
                    rows.append(row)
                    if row.get("__extra__") or "__missing__" in row.values():
                        self.error("EVIDENCE_MATRIX_ROW", f"第{line_number}行列数不一致")
                    status = str(row.get("status") or "").strip()
                    if status not in VALID_REFERENCE_STATUSES:
                        self.error("EVIDENCE_STATUS_INVALID", f"第{line_number}行: {status}")
                    if status != "REJECTED":
                        for group in ["title", "authors", "year", "verification_source", "supported_claim", "chapter", "evidence_role", "access_mode", "publication_status", "notes"]:
                            fields = field_lookup.get(group) or []
                            if fields and not any(str(row.get(field) or "").strip() for field in fields):
                                self.error("EVIDENCE_FIELD_EMPTY", f"第{line_number}行: {group}")
                        id_fields = field_lookup.get("identifier") or []
                        if id_fields and not any(str(row.get(field) or "").strip() for field in id_fields):
                            self.error("EVIDENCE_IDENTIFIER_EMPTY", f"第{line_number}行")
        except (OSError, UnicodeError, csv.Error) as exc:
            self.error("EVIDENCE_MATRIX_INVALID", str(exc))
            return

        source_ids = [str(row.get("source_id") or "").strip() for row in rows]
        if any(not item for item in source_ids):
            self.error("EVIDENCE_SOURCE_ID_MISSING", "存在空source_id")
        if len(source_ids) != len(set(source_ids)):
            self.error("EVIDENCE_SOURCE_ID_DUPLICATE", "source_id不唯一")

        final_text = markdown.read_text(encoding="utf-8", errors="replace") if markdown.is_file() else ""
        reference_match = REFERENCE_HEADING.search(final_text)
        reference_section = final_text[reference_match.end():] if reference_match else ""
        numbered_references = len(re.findall(r"^\s*(?:[-*]\s*)?\[[0-9]+\]", reference_section, re.MULTILINE))
        accepted_rows = [
            row for row in rows
            if str(row.get("status") or "").strip() not in {"UNVERIFIED", "REJECTED"}
        ]
        if citation_mode == "AUTHOR_YEAR":
            compact_reference = re.sub(r"[\s*_`]+", "", reference_section).lower()
            matched_titles = 0
            for row in accepted_rows:
                title = re.sub(r"[\s*_`]+", "", str(row.get("title") or "")).lower()
                minimum_title_length = 4 if re.search(r"[\u3400-\u9fff]", title) else 8
                if len(title) >= minimum_title_length and title in compact_reference:
                    matched_titles += 1
            final_references = matched_titles
        else:
            final_references = numbered_references
        bib_entries = 0
        if bibliography.is_file():
            bib_entries = len(re.findall(r"^\s*@\w+\s*\{", bibliography.read_text(encoding="utf-8", errors="replace"), re.MULTILINE))
        else:
            self.error("BIBLIOGRAPHY_MISSING", str(bibliography))

        for row in rows:
            if str(row.get("status") or "").strip() != "UNVERIFIED":
                continue
            title = re.sub(r"\s+", "", str(row.get("title") or ""))
            if len(title) >= 8 and title.lower() in re.sub(r"\s+", "", reference_section).lower():
                self.error("UNVERIFIED_IN_FINAL_REFERENCES", str(row.get("source_id") or title[:20]))

        self.metrics["references"] = {
            "evidence_rows": len(rows),
            "final_references": final_references,
            "bib_entries": bib_entries,
            "citation_mode": citation_mode,
        }
        if final_references == 0:
            detail = "最终正文没有可匹配的作者—年份参考文献" if citation_mode == "AUTHOR_YEAR" else "最终正文没有编号参考文献"
            self.error("FINAL_REFERENCES_MISSING", detail)
        if bib_entries != final_references:
            self.error("BIB_FINAL_COUNT_MISMATCH", f"BibTeX={bib_entries}，最终参考文献={final_references}")
        if len(rows) < final_references:
            self.error("EVIDENCE_FINAL_COUNT_MISMATCH", f"证据矩阵={len(rows)}，最终参考文献={final_references}")

    def verify_docx(
        self, path: Path, declared_tables: Optional[int], markdown: Path,
        require_toc: bool, enforce_body_font: bool, minimum_body_font_pt: float,
    ) -> None:
        if not zipfile.is_zipfile(path):
            self.error("DOCX_INVALID", str(path))
            return
        with zipfile.ZipFile(path) as archive:
            if "word/document.xml" not in archive.namelist():
                self.error("DOCX_DOCUMENT_XML_MISSING", str(path))
                return
            try:
                root = ET.fromstring(archive.read("word/document.xml"))
            except ET.ParseError as exc:
                self.error("DOCX_DOCUMENT_XML_INVALID", str(exc))
                return
            styles_root = None
            if "word/styles.xml" in archive.namelist():
                try:
                    styles_root = ET.fromstring(archive.read("word/styles.xml"))
                except ET.ParseError:
                    self.warning("DOCX_STYLES_PARSE_FAILED", str(path))
            table_count = len(root.findall(".//w:tbl", WORD_NS))
            style_counts = {level: 0 for level in (1, 2, 3)}
            normal_size: Optional[float] = None
            style_indents: Dict[str, Dict[str, str]] = {}
            style_bases: Dict[str, str] = {}
            style_ids = set()
            if styles_root is not None:
                for style in styles_root.findall(".//w:style", WORD_NS):
                    style_id = style.get(f"{{{WORD_NS['w']}}}styleId", "")
                    style_key = style_id.lower()
                    if style_key:
                        style_ids.add(style_key)
                    indent_node = style.find("./w:pPr/w:ind", WORD_NS)
                    if indent_node is not None:
                        style_indents[style_key] = {
                            key.rsplit("}", 1)[-1]: value for key, value in indent_node.attrib.items()
                        }
                    based_on_node = style.find("./w:basedOn", WORD_NS)
                    if based_on_node is not None:
                        style_bases[style_key] = based_on_node.get(
                            f"{{{WORD_NS['w']}}}val", ""
                        ).lower()
                    if style_id.lower() == "normal":
                        size_node = style.find("./w:rPr/w:sz", WORD_NS)
                        if size_node is not None:
                            try:
                                normal_size = float(size_node.get(f"{{{WORD_NS['w']}}}val", "")) / 2
                            except ValueError:
                                pass

            def effective_indent(paragraph: ET.Element) -> Dict[str, str]:
                style_node = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
                style_key = (
                    style_node.get(f"{{{WORD_NS['w']}}}val", "").lower()
                    if style_node is not None else "normal"
                )
                if style_key not in style_ids:
                    style_key = "normal"
                chain: List[str] = []
                seen = set()
                while style_key and style_key not in seen:
                    seen.add(style_key)
                    chain.append(style_key)
                    style_key = style_bases.get(style_key, "")
                merged: Dict[str, str] = {}
                for key in reversed(chain):
                    merged.update(style_indents.get(key, {}))
                direct_indent = paragraph.find("./w:pPr/w:ind", WORD_NS)
                if direct_indent is not None:
                    merged.update({
                        key.rsplit("}", 1)[-1]: value
                        for key, value in direct_indent.attrib.items()
                    })
                return merged

            table_cell_paragraphs = 0
            indented_table_cell_paragraphs = 0
            table_indent_examples: List[str] = []
            for paragraph in root.findall(".//w:tc/w:p", WORD_NS):
                paragraph_text = "".join(
                    node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)
                ).strip()
                if not paragraph_text:
                    continue
                table_cell_paragraphs += 1
                indent = effective_indent(paragraph)
                bad_fields: List[str] = []
                for field in ["firstLine", "firstLineChars", "hanging", "hangingChars"]:
                    value = indent.get(field)
                    if value is None:
                        continue
                    try:
                        if int(value) != 0:
                            bad_fields.append(f"{field}={value}")
                    except ValueError:
                        bad_fields.append(f"{field}={value}")
                if bad_fields:
                    indented_table_cell_paragraphs += 1
                    if len(table_indent_examples) < 5:
                        table_indent_examples.append(
                            f"{paragraph_text[:24]} ({', '.join(bad_fields)})"
                        )
            if indented_table_cell_paragraphs:
                self.error(
                    "DOCX_TABLE_CELL_PARAGRAPH_INDENT",
                    f"{indented_table_cell_paragraphs}/{table_cell_paragraphs}；示例: "
                    + " | ".join(table_indent_examples),
                )

            # 逐个媒体段落检查Pandoc alt text与正式图题，避免把正文中的正常图号引用误报。
            paragraphs = root.findall(".//w:body/w:p", WORD_NS)
            paragraph_texts = [
                "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
                for paragraph in paragraphs
            ]
            captions: List[Tuple[int, str]] = []
            for index, paragraph in enumerate(paragraphs):
                style_node = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
                style = style_node.get(f"{{{WORD_NS['w']}}}val", "").lower() if style_node is not None else ""
                text = paragraph_texts[index]
                if text and (style in {"caption", "figurecaption", "tablecaption"} or re.match(r"^(?:图|表|figure|table)\s*[0-9一二三四五六七八九十]+(?:[.、:-]|\s)", text, re.IGNORECASE)):
                    captions.append((index, text))
            duplicate_caption_count = 0
            media_count = 0
            media_alt_texts: List[str] = []
            for index, paragraph in enumerate(paragraphs):
                drawings = paragraph.findall(".//wp:docPr", {"wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"})
                has_media = bool(drawings or paragraph.findall(".//w:pict", WORD_NS) or paragraph.findall(".//w:object", WORD_NS))
                if not has_media:
                    continue
                media_count += 1
                doc_alt_values = []
                for doc_pr in drawings:
                    for key in ("descr", "title"):
                        value = doc_pr.get(key, "").strip()
                        if value:
                            doc_alt_values.append(value)
                # docPr descr/title是元数据，不等同于Word中实际可见文字。
                alt_values = []
                alt_values.extend(value for value in [paragraph_texts[index]] if value)
                # 某些Pandoc链会把alt text落成媒体前后的独立可见段落。
                # 只纳入短、无句末标点的邻近文本，避免把正文中的“参见图1”当作题注。
                for neighbor in (index - 1, index + 1):
                    if 0 <= neighbor < len(paragraphs) and paragraph_texts[neighbor] and neighbor not in {pos for pos, _ in captions}:
                        candidate = paragraph_texts[neighbor]
                        if len(candidate) <= 120 and not re.search(r"[。！？.!?]$", candidate):
                            alt_values.append(candidate)
                media_alt_texts.extend(alt_values)
                # 正式题注通常紧邻媒体段落；最多看前后两段，且只在题注候选中比对。
                nearby = [text for pos, text in captions if 0 < abs(pos - index) <= 2]
                for alt in alt_values:
                    compact_alt = re.sub(r"\s+", "", alt).lower()
                    if not compact_alt:
                        continue
                    metadata_locates_visible_alt = any(
                        re.sub(r"\s+", "", metadata).lower() in compact_alt
                        or compact_alt in re.sub(r"\s+", "", metadata).lower()
                        for metadata in doc_alt_values
                    )
                    if metadata_locates_visible_alt and nearby:
                        duplicate_caption_count += 1
                        break
                    if any(compact_alt == re.sub(r"\s+", "", caption).lower() or compact_alt in re.sub(r"\s+", "", caption).lower() or re.sub(r"\s+", "", caption).lower() in compact_alt for caption in nearby):
                        duplicate_caption_count += 1
                        break
            if duplicate_caption_count:
                self.error("DOCX_DUPLICATE_MEDIA_CAPTION", f"{duplicate_caption_count}/{media_count}个媒体邻近段落的alt text与正式题注重复")
            weighted_body_sizes: List[float] = []
            for paragraph in root.findall(".//w:p", WORD_NS):
                style_node = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
                style = style_node.get(f"{{{WORD_NS['w']}}}val", "") if style_node is not None else ""
                for level in (1, 2, 3):
                    if style.lower() == f"heading{level}":
                        style_counts[level] += 1
                paragraph_text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
                if len(paragraph_text) < 20 or style.lower() in {"title", "subtitle", "caption", "toc1", "toc2", "toc3"} or style.lower().startswith("heading"):
                    continue
                for run in paragraph.findall("./w:r", WORD_NS):
                    run_text = "".join(node.text or "" for node in run.findall(".//w:t", WORD_NS))
                    if not run_text.strip():
                        continue
                    size_node = run.find("./w:rPr/w:sz", WORD_NS)
                    run_size = normal_size
                    if size_node is not None:
                        try:
                            run_size = float(size_node.get(f"{{{WORD_NS['w']}}}val", "")) / 2
                        except ValueError:
                            pass
                    if run_size is not None:
                        weighted_body_sizes.extend([run_size] * max(1, len(run_text)))
            field_text = " ".join(node.text or "" for node in root.findall(".//w:instrText", WORD_NS))
            field_text += " " + " ".join(
                node.get(f"{{{WORD_NS['w']}}}instr", "") for node in root.findall(".//w:fldSimple", WORD_NS)
            )
            if require_toc and not re.search(r"\bTOC\b", field_text, re.IGNORECASE):
                self.error("DOCX_TOC_FIELD_MISSING", str(path))
            if self.require_bilingual_abstract:
                visible_all = "\n".join(node.text or "" for node in root.findall(".//w:t", WORD_NS))
                for term in ["摘要", "Abstract", "关键词", "Keywords"]:
                    if not re.search(re.escape(term), visible_all, re.IGNORECASE):
                        self.error("DOCX_BILINGUAL_ABSTRACT_MISSING", term)
            if style_counts[1] == 0 or style_counts[2] == 0:
                self.error("DOCX_HEADING_HIERARCHY", str(style_counts))
            markdown_text = markdown.read_text(encoding="utf-8", errors="replace") if markdown.is_file() else ""
            if re.search(r"^###\s+", markdown_text, re.MULTILINE) and style_counts[3] == 0:
                self.error("DOCX_HEADING3_MISSING", "Markdown包含三级标题但Word没有Heading 3")
            if isinstance(declared_tables, int) and table_count < declared_tables:
                self.error("DOCX_TABLE_COUNT_LOW", f"Word={table_count}，Manifest={declared_tables}")
            body_font_pt = statistics.median(weighted_body_sizes) if weighted_body_sizes else normal_size
            if enforce_body_font:
                if body_font_pt is None:
                    self.error("DOCX_BODY_FONT_UNKNOWN", str(path))
                elif body_font_pt < minimum_body_font_pt:
                    self.error("DOCX_BODY_FONT_TOO_SMALL", f"中位字号{body_font_pt:g}pt，最低{minimum_body_font_pt:g}pt")
            self.metrics["docx"] = {
                "tables": table_count, "heading_counts": style_counts,
                "toc_field": "TOC" in field_text.upper(), "body_font_pt": body_font_pt,
                "table_cell_paragraphs": table_cell_paragraphs,
                "indented_table_cell_paragraphs": indented_table_cell_paragraphs,
                "media_count": media_count,
                "duplicate_media_captions": duplicate_caption_count,
            }

    def verify_pdf(self, path: Path, require_toc: bool, markdown: Optional[Path] = None) -> None:
        if path.stat().st_size < 8 or path.read_bytes()[:5] != b"%PDF-":
            self.error("PDF_INVALID", str(path))
            return
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = len(reader.pages)
            page_texts = [(page.extract_text() or "") for page in reader.pages]
            visible_text = "\n".join(page_texts)
            toc_heading = re.compile(r"(^|\n)\s*目\s*录\s*(\n|$)")
            visible_toc = bool(toc_heading.search(visible_text))
            toc_page = next(
                (index + 1 for index, text in enumerate(page_texts) if toc_heading.search(text)),
                None,
            )
            toc_entries: List[str] = []
            toc_page_numbers: List[int] = []
            if toc_page is not None:
                # 目录可跨页；从目录标题开始，遇到明显正文标题后停止。
                in_toc = False
                stop_toc = False
                for page_text in page_texts[toc_page - 1:]:
                    if stop_toc:
                        break
                    page_has_entry = False
                    for raw_line in page_text.splitlines():
                        line = re.sub(r"\s+", " ", raw_line).strip()
                        if not in_toc:
                            if re.fullmatch(r"目\s*录", line):
                                in_toc = True
                            continue
                        if not line or re.fullmatch(r"目\s*录", line):
                            continue
                        match = re.match(r"^(.+?)(?:\s*[.·…]{2,}\s*|\s+)\s*(\d{1,4})\s*$", line)
                        if match and not re.fullmatch(r"\d{1,4}", match.group(1).strip()):
                            title = match.group(1).strip(" .·…")
                            toc_entries.append(title)
                            toc_page_numbers.append(int(match.group(2)))
                        elif re.match(r"^(?:第\s*[一二三四五六七八九十百0-9]+\s*章|[一二三四五六七八九十百0-9]+[.、])", line) and not re.search(r"\d{1,4}\s*$", line):
                            # 首个正文章标题意味着目录块已结束，后续页绝不能继续扫描。
                            stop_toc = True
                            break
                        if re.match(r"^(?:第\s*[一二三四五六七八九十百0-9]+\s*章|摘要|Abstract|参考文献|References)", line, re.IGNORECASE) and not re.search(r"\d{1,4}\s*$", line):
                            stop_toc = True
                            break
                        if match:
                            page_has_entry = True
                    if stop_toc:
                        break
                    # 目录标题页若没有任何条目，或后续页不是目录延续，立即结束目录块。
                    if in_toc and not page_has_entry and page_texts.index(page_text) > toc_page - 1:
                        break
            chapter_titles: List[str] = []
            if markdown and markdown.is_file():
                markdown_text = markdown.read_text(encoding="utf-8", errors="replace")
                for match in CHAPTER_HEADING.finditer(markdown_text):
                    title = re.sub(r"^#+\s*", "", match.group(0)).strip()
                    chapter_titles.append(re.sub(r"\s+", "", title).lower())
            matched_chapters = 0
            for title in toc_entries:
                compact = re.sub(r"\s+", "", title).lower()
                if any(compact in chapter or chapter in compact for chapter in chapter_titles):
                    matched_chapters += 1
            self.metrics["pdf"] = {"pages": pages, "visible_toc": visible_toc, "toc_page": toc_page, "toc_entries": len(toc_entries), "toc_page_numbers": len(toc_page_numbers), "toc_chapter_matches": matched_chapters}
            if pages == 0:
                self.error("PDF_NO_PAGES", str(path))
            if require_toc and not visible_toc:
                self.error("PDF_VISIBLE_TOC_MISSING", str(path))
            if require_toc and (len(toc_entries) == 0 or len(toc_page_numbers) != len(toc_entries)):
                self.error("PDF_TOC_ENTRIES_MISSING", "目录必须包含实际条目及页码")
            if require_toc and chapter_titles and matched_chapters == 0:
                self.error("PDF_TOC_CHAPTER_MISMATCH", "目录条目未匹配真实章标题")
            if require_toc and toc_page == 1:
                self.error("THESIS_COVER_TOC_SAME_PAGE", str(path))
        except ImportError:
            if require_toc:
                self.error("PDF_TOC_CHECK_UNAVAILABLE", "THESIS目录核验需要pypdf")
            else:
                self.warning("PDF_DEEP_CHECK_SKIPPED", "当前Python缺少pypdf")
        except Exception as exc:
            self.error("PDF_PARSE_FAILED", str(exc))

    def verify_run_manifest(self, manifest_path: Path, markdown: Path) -> None:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("RUN_MANIFEST_INVALID", str(exc))
            return
        if not isinstance(manifest, dict):
            self.error("RUN_MANIFEST_SHAPE", "根对象必须是对象")
            return
        document_profile = manifest.get("document_profile")
        if document_profile not in DOCUMENT_PROFILES:
            self.error("DOCUMENT_PROFILE_INVALID", str(document_profile))
            document_profile = "THESIS"
        language = str(manifest.get("manuscript_language") or "zh-CN")
        abstract_contract = manifest.get("abstract_contract")
        if abstract_contract not in {"BILINGUAL", "PRIMARY_ONLY", "TEMPLATE_DEFINED"}:
            abstract_contract = "BILINGUAL" if document_profile in {"THESIS", "JOURNAL"} and language.lower().startswith("zh") else "PRIMARY_ONLY"
        self.verify_abstracts(markdown, abstract_contract)
        format_contract = manifest.get("format_contract")
        minimum_body_font_pt = 11.5
        requires_pdf_toc = document_profile == "THESIS"
        if document_profile == "CUSTOM":
            if not isinstance(format_contract, dict):
                self.error("FORMAT_CONTRACT_MISSING", "CUSTOM需要format_contract")
            else:
                value = format_contract.get("minimum_body_font_pt")
                if isinstance(value, (int, float)) and value > 0:
                    minimum_body_font_pt = float(value)
                requires_pdf_toc = bool(format_contract.get("requires_pdf_toc", False))

        figure_report_value = manifest.get("figure_verification_report", "figures/figure-verification.json")
        figure_report = self.resolve_relative_file(figure_report_value, "figure_verification_report")
        figure_visual_status: Optional[str] = None
        if figure_report:
            try:
                figure_payload = json.loads(figure_report.read_text(encoding="utf-8"))
                if figure_payload.get("mechanical_status") != "PASS" or figure_payload.get("status") != "STRUCTURE_OK":
                    self.error("FIGURE_VERIFICATION_NOT_PASS", str(figure_report_value))
                figure_visual_status = figure_payload.get("visual_status")
                if figure_visual_status not in {"PASS", "PARTIAL"}:
                    self.error("FIGURE_VISUAL_STATUS_INVALID", str(figure_visual_status))
            except (UnicodeError, json.JSONDecodeError) as exc:
                self.error("FIGURE_VERIFICATION_INVALID", str(exc))
        formula_report_value = manifest.get("formula_verification_report", "equations/formula-verification.json")
        formula_report = self.resolve_relative_file(formula_report_value, "formula_verification_report")
        formula_status: Optional[str] = None
        formula_payload: Optional[Dict[str, Any]] = None
        if formula_report:
            try:
                loaded_formula_payload = json.loads(formula_report.read_text(encoding="utf-8"))
                if not isinstance(loaded_formula_payload, dict):
                    self.error("FORMULA_VERIFICATION_INVALID", "根对象必须是对象")
                else:
                    formula_payload = loaded_formula_payload
                    formula_status = formula_payload.get("status")
                    if formula_status != "FORMULA_OK":
                        self.error("FORMULA_VERIFICATION_NOT_PASS", str(formula_report_value))
                    hashes = formula_payload.get("hashes")
                    if not isinstance(hashes, dict):
                        self.error("FORMULA_VERIFICATION_HASHES_MISSING", str(formula_report_value))
                    else:
                        markdown_hash = hashes.get("markdown_sha256")
                        if not isinstance(markdown_hash, str) or markdown_hash.lower() != self.sha256(markdown):
                            self.error("FORMULA_MARKDOWN_HASH_MISMATCH", str(formula_report_value))
            except (UnicodeError, json.JSONDecodeError) as exc:
                self.error("FORMULA_VERIFICATION_INVALID", str(exc))
        docx_value = manifest.get("docx")
        pdf_value = manifest.get("pdf")
        docx = self.resolve_relative_file(docx_value, "docx")
        pdf = self.resolve_relative_file(pdf_value, "pdf")
        for value, extension in [(docx_value, "docx"), (pdf_value, "pdf")]:
            if isinstance(value, str) and not TIMESTAMPED_NAME.fullmatch(Path(value).name):
                self.error("FINAL_FILENAME_INVALID", f"{extension}: {value}")
        if isinstance(docx_value, str) and isinstance(pdf_value, str):
            if Path(docx_value).stem != Path(pdf_value).stem:
                self.error("FINAL_FILENAME_PAIR_MISMATCH", f"{docx_value} / {pdf_value}")

        declared_tables = manifest.get("tables") if isinstance(manifest.get("tables"), int) else None
        if docx:
            declared = manifest.get("docx_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(docx):
                self.error("DOCX_HASH_MISMATCH", str(docx_value))
            if formula_payload is not None:
                hashes = formula_payload.get("hashes")
                formula_docx_hash = hashes.get("docx_sha256") if isinstance(hashes, dict) else None
                if not isinstance(formula_docx_hash, str) or formula_docx_hash.lower() != self.sha256(docx):
                    self.error("FORMULA_DOCX_HASH_MISMATCH", str(formula_report_value))
            enforce_body_font = document_profile == "THESIS" or (
                document_profile == "CUSTOM" and isinstance(format_contract, dict) and "minimum_body_font_pt" in format_contract
            )
            self.verify_docx(
                docx, declared_tables, markdown, requires_pdf_toc, enforce_body_font, minimum_body_font_pt
            )
        if pdf:
            declared = manifest.get("pdf_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(pdf):
                self.error("PDF_HASH_MISMATCH", str(pdf_value))
            if formula_payload is not None:
                hashes = formula_payload.get("hashes")
                formula_pdf_hash = hashes.get("pdf_sha256") if isinstance(hashes, dict) else None
                if not isinstance(formula_pdf_hash, str) or formula_pdf_hash.lower() != self.sha256(pdf):
                    self.error("FORMULA_PDF_HASH_MISMATCH", str(formula_report_value))
            self.verify_pdf(pdf, requires_pdf_toc, markdown)

        research_status = manifest.get("research_status")
        delivery_status = manifest.get("delivery_status")
        final_status = manifest.get("final_status")
        derived_only = manifest.get("state_contract") == "DERIVED_ONLY"
        if not derived_only and research_status not in {"PASS", "PARTIAL", "FAIL"}:
            self.error("RESEARCH_STATUS_INVALID", str(research_status))
        if not derived_only and delivery_status not in {"PASS", "PARTIAL", "FAIL"}:
            self.error("DELIVERY_STATUS_INVALID", str(delivery_status))
        if not derived_only and figure_visual_status == "PARTIAL" and delivery_status == "PASS":
            self.error("DELIVERY_VISUAL_STATUS_CONFLICT", "视觉未核验时delivery_status不能为PASS")
        if not derived_only and research_status in {"PASS", "PARTIAL", "FAIL"} and delivery_status in {"PASS", "PARTIAL", "FAIL"}:
            if research_status == "FAIL" or delivery_status == "FAIL":
                expected_final = "FAIL"
            elif research_status == "PASS" and delivery_status == "PASS":
                expected_final = "PASS"
            else:
                expected_final = "PARTIAL"
            if final_status != expected_final:
                self.error("FINAL_STATUS_MISMATCH", f"声明{final_status}，应为{expected_final}")
        self.metrics["status"] = {
            "research_status": research_status,
            "delivery_status": delivery_status,
            "final_status": final_status,
            "figure_visual_status": figure_visual_status,
            "formula_status": formula_status,
            "document_profile": document_profile,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验AIWritePaper正文、证据与最终文档交付")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--markdown", type=Path, default=Path("07-paper-full.md"))
    parser.add_argument("--evidence-matrix", type=Path, default=Path("03-evidence-matrix.csv"))
    parser.add_argument("--bibliography", type=Path, default=Path("references.bib"))
    parser.add_argument("--run-manifest", type=Path, default=Path("run-manifest.json"))
    parser.add_argument("--target", type=int, default=25000)
    parser.add_argument("--minimum", type=int, default=22500)
    parser.add_argument("--maximum", type=int, default=27500)
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def rooted(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    verifier = DeliveryVerifier(root, args.minimum, args.maximum, args.target)
    markdown = rooted(root, args.markdown)
    matrix_path = rooted(root, args.evidence_matrix)
    bibliography_path = rooted(root, args.bibliography)
    manifest_path = rooted(root, args.run_manifest)
    verifier.verify_body_length(markdown)
    citation_mode = "NUMERIC"
    try:
        manifest_for_citations = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(manifest_for_citations, dict):
            citation_mode = str(manifest_for_citations.get("citation_mode") or "NUMERIC")
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    verifier.verify_evidence_matrix(
        matrix_path, markdown, bibliography_path, citation_mode
    )
    verifier.verify_run_manifest(manifest_path, markdown)
    input_sha256: Dict[str, str] = {}
    input_paths = [markdown, matrix_path, bibliography_path, manifest_path]
    try:
        run_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for field, default in [
            ("figure_verification_report", "figures/figure-verification.json"),
            ("formula_verification_report", "equations/formula-verification.json"),
            ("docx", None), ("pdf", None),
        ]:
            value = run_payload.get(field, default)
            if isinstance(value, str):
                input_paths.append(root / value)
    except (OSError, UnicodeError, json.JSONDecodeError):
        pass
    for path in input_paths:
        if path.is_file():
            try:
                input_sha256[str(path.resolve().relative_to(root))] = verifier.sha256(path)
            except ValueError:
                pass
    payload = {
        "schema_version": "1.0",
        "status": "DELIVERY_OK" if not verifier.errors else "DELIVERY_FAIL",
        "errors": verifier.errors,
        "warnings": verifier.warnings,
        "metrics": verifier.metrics,
        "input_sha256": input_sha256,
        "verifier": {
            "name": Path(__file__).name, "version": "2.1.0-rc.1",
            "sha256": verifier.sha256(Path(__file__).resolve()),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "scope_note": "交付通过不代表研究数据、实验或学术结论已经完成",
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        report = rooted(root, args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not verifier.errors else 1


if __name__ == "__main__":
    sys.exit(main())
