#!/usr/bin/env python3
"""机械校验正文计数、证据矩阵与最终DOCX/PDF交付，不参与学术内容决策。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
VALID_REFERENCE_STATUSES = {"VERIFIED_FULLTEXT", "VERIFIED_METADATA", "UNVERIFIED", "REJECTED"}
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
        body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)
        body = re.sub(r"<[^>]+>", "", body)
        kept: List[str] = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("|"):
                continue
            if re.match(r"^(?:图|表)\s*[0-9]+(?:[-－—.][0-9]+)*\s+", stripped):
                continue
            kept.append(re.sub(r"^#{1,6}\s*", "", line))
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
        if units < self.minimum:
            self.error("BODY_LENGTH_LOW", f"实际{units}，最低{self.minimum}")
        elif units > self.maximum:
            self.error("BODY_LENGTH_HIGH", f"实际{units}，最高{self.maximum}")

    def verify_evidence_matrix(self, matrix: Path, markdown: Path, bibliography: Path) -> None:
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
                for line_number, row in enumerate(reader, start=2):
                    rows.append(row)
                    if row.get("__extra__") or "__missing__" in row.values():
                        self.error("EVIDENCE_MATRIX_ROW", f"第{line_number}行列数不一致")
                    status = str(row.get("status") or "").strip()
                    if status not in VALID_REFERENCE_STATUSES:
                        self.error("EVIDENCE_STATUS_INVALID", f"第{line_number}行: {status}")
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
        final_references = len(re.findall(r"^\s*(?:[-*]\s*)?\[[0-9]+\]", reference_section, re.MULTILINE))
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
        }
        if final_references == 0:
            self.error("FINAL_REFERENCES_MISSING", "最终正文没有编号参考文献")
        if bib_entries != final_references:
            self.error("BIB_FINAL_COUNT_MISMATCH", f"BibTeX={bib_entries}，最终参考文献={final_references}")
        if len(rows) < final_references:
            self.error("EVIDENCE_FINAL_COUNT_MISMATCH", f"证据矩阵={len(rows)}，最终参考文献={final_references}")

    def verify_docx(self, path: Path, declared_tables: Optional[int], markdown: Path) -> None:
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
            table_count = len(root.findall(".//w:tbl", WORD_NS))
            style_counts = {level: 0 for level in (1, 2, 3)}
            for paragraph in root.findall(".//w:p", WORD_NS):
                style_node = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
                style = style_node.get(f"{{{WORD_NS['w']}}}val", "") if style_node is not None else ""
                for level in (1, 2, 3):
                    if style.lower() == f"heading{level}":
                        style_counts[level] += 1
            field_text = " ".join(node.text or "" for node in root.findall(".//w:instrText", WORD_NS))
            field_text += " " + " ".join(
                node.get(f"{{{WORD_NS['w']}}}instr", "") for node in root.findall(".//w:fldSimple", WORD_NS)
            )
            if not re.search(r"\bTOC\b", field_text, re.IGNORECASE):
                self.error("DOCX_TOC_FIELD_MISSING", str(path))
            if style_counts[1] == 0 or style_counts[2] == 0:
                self.error("DOCX_HEADING_HIERARCHY", str(style_counts))
            markdown_text = markdown.read_text(encoding="utf-8", errors="replace") if markdown.is_file() else ""
            if re.search(r"^###\s+", markdown_text, re.MULTILINE) and style_counts[3] == 0:
                self.error("DOCX_HEADING3_MISSING", "Markdown包含三级标题但Word没有Heading 3")
            if isinstance(declared_tables, int) and table_count < declared_tables:
                self.error("DOCX_TABLE_COUNT_LOW", f"Word={table_count}，Manifest={declared_tables}")
            self.metrics["docx"] = {"tables": table_count, "heading_counts": style_counts, "toc": "TOC" in field_text.upper()}

    def verify_pdf(self, path: Path) -> None:
        if path.stat().st_size < 8 or path.read_bytes()[:5] != b"%PDF-":
            self.error("PDF_INVALID", str(path))
            return
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(path)).pages)
            self.metrics["pdf"] = {"pages": pages}
            if pages == 0:
                self.error("PDF_NO_PAGES", str(path))
        except ImportError:
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
            self.verify_docx(docx, declared_tables, markdown)
        if pdf:
            declared = manifest.get("pdf_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(pdf):
                self.error("PDF_HASH_MISMATCH", str(pdf_value))
            self.verify_pdf(pdf)

        research_status = manifest.get("research_status")
        delivery_status = manifest.get("delivery_status")
        if research_status not in {"PASS", "PARTIAL", "FAIL"}:
            self.error("RESEARCH_STATUS_INVALID", str(research_status))
        if delivery_status not in {"PASS", "FAIL"}:
            self.error("DELIVERY_STATUS_INVALID", str(delivery_status))


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
    verifier.verify_body_length(markdown)
    verifier.verify_evidence_matrix(
        rooted(root, args.evidence_matrix), markdown, rooted(root, args.bibliography)
    )
    verifier.verify_run_manifest(rooted(root, args.run_manifest), markdown)
    payload = {
        "status": "DELIVERY_OK" if not verifier.errors else "DELIVERY_FAIL",
        "errors": verifier.errors,
        "warnings": verifier.warnings,
        "metrics": verifier.metrics,
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
