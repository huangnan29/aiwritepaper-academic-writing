#!/usr/bin/env python3
"""核验文献题录、正文引用和数据来源，不代替学术判断。"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from difflib import SequenceMatcher
import hashlib
import html
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import unicodedata
import urllib.error
import urllib.parse
import urllib.request


SKILL_ROOT = Path(__file__).resolve().parents[1]
VALID_STATUSES = {"VERIFIED_FULLTEXT", "VERIFIED_METADATA", "UNVERIFIED", "REJECTED"}
VALID_CITATION_MODES = {"NUMERIC", "AUTHOR_YEAR"}
VALID_CLAIM_LEVELS = {"OBSERVED_STUDY", "DESIGN_ONLY", "PROTOCOL_ONLY", "REVIEW_SYNTHESIS"}
VALID_RUN_MODES = {"FULL_BUILD", "RESUME", "REVISE_ONLY", "FIGURES_ONLY", "EXPORT_ONLY", "AUDIT_ONLY", "PROPOSAL_ONLY", "DEFENSE_ONLY"}
VALID_DATA_ORIGINS = {
    "USER_PROVIDED", "AUTHOR_OBSERVED", "OFFICIAL_DOWNLOAD", "FORMAL_SIMULATION",
    "CALCULATED", "MODEL_SYNTHETIC", "MANUSCRIPT_CONTEXT",
}
VALID_CLAIM_ROLES = {
    "RESULT", "SIMULATION_RESULT", "DESIGN_CALCULATION", "ILLUSTRATION", "CONTEXT_ONLY",
}
DISCOVERY_ONLY = re.compile(
    r"^\s*(?:Crossref|OpenAlex|Semantic Scholar|Web of Science|Scopus|CNKI题录|"
    r"万方题录|维普题录)(?:\s*[|/,;+]\s*(?:Crossref|OpenAlex|Semantic Scholar|"
    r"Web of Science|Scopus|CNKI题录|万方题录|维普题录))*\s*$",
    re.IGNORECASE,
)
REFERENCE_HEADING = re.compile(r"^#{1,6}\s*(?:参考文献|References)\s*$", re.MULTILINE | re.IGNORECASE)
SELF_RESULT_PATTERN = re.compile(
    r"(?:本研究|本系统|本节点|本实验|实验班|对照班|研究结果|测试结果|实验结果|"
    r"SPICE仿真与实测).{0,180}?(?:实测|显著|提升(?:了)?\s*\d|降低(?:了)?\s*\d|"
    r"达到\s*\d|优于|p\s*[<=>]|R\s*(?:\^?2|²)|满意度|通过(?:了)?\s*[^，。；]{0,40}测试)",
    re.IGNORECASE | re.DOTALL,
)
FIELD_ALIASES = {
    "title": ["title", "题名"],
    "authors": ["authors", "author", "作者"],
    "year": ["year", "年份"],
    "doi": ["doi", "DOI"],
    "url": ["url", "URL", "source_url"],
    "verification_source": ["verification_source", "核验来源"],
    "supported_claims": ["supported_claims", "supported_claim", "supports_claim", "支持主张"],
    "chapters": ["chapters", "chapter", "章节"],
    "status": ["status", "状态"],
    "notes": ["notes", "备注"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verifier_identity() -> Dict[str, str]:
    script = Path(__file__).resolve()
    return {
        "name": script.name,
        "version": "1.9.0",
        "sha256": sha256(script),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def clean_title(value: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value or ""))


def resolve_under_root(root: Path, value: Any) -> Optional[Path]:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def expand_numeric_citations(text: str) -> Set[int]:
    numbers: Set[int] = set()
    for block in re.findall(r"\[([0-9,，;；\-–—\s]+)\]", text):
        for start, end in re.findall(r"(\d+)\s*[-–—]\s*(\d+)", block):
            left, right = int(start), int(end)
            if 0 < left <= right <= left + 200:
                numbers.update(range(left, right + 1))
        reduced = re.sub(r"\d+\s*[-–—]\s*\d+", "", block)
        numbers.update(int(item) for item in re.findall(r"\d+", reduced))
    return numbers


class EvidenceVerifier:
    def __init__(self, root: Path, offline: bool = False) -> None:
        self.root = root.resolve()
        self.offline = offline
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.capability_gap = False

    def error(self, code: str, detail: str) -> None:
        self.errors.append(f"{code}: {detail}")

    def warning(self, code: str, detail: str) -> None:
        self.warnings.append(f"{code}: {detail}")

    def load_manifest(self, path: Path) -> Dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("RUN_MANIFEST_INVALID", str(exc))
            return {}
        if not isinstance(payload, dict):
            self.error("RUN_MANIFEST_SHAPE", "根对象必须为对象")
            return {}
        for field in [
            "model_label", "skill_version", "citation_mode", "research_claim_level",
            "execution_profile", "profile_selection_report", "run_mode",
        ]:
            if not isinstance(payload.get(field), str) or not payload.get(field, "").strip():
                self.error("RUN_MANIFEST_FIELD_MISSING", field)
        if payload.get("citation_mode") not in VALID_CITATION_MODES:
            self.error("CITATION_MODE_INVALID", str(payload.get("citation_mode")))
        if payload.get("research_claim_level") not in VALID_CLAIM_LEVELS:
            self.error("RESEARCH_CLAIM_LEVEL_INVALID", str(payload.get("research_claim_level")))
        if payload.get("execution_profile") not in {"FULL_AUTONOMY", "GUIDED", "WEAK_MODEL"}:
            self.error("EXECUTION_PROFILE_INVALID", str(payload.get("execution_profile")))
        if payload.get("run_mode") not in VALID_RUN_MODES:
            self.error("RUN_MODE_INVALID", str(payload.get("run_mode")))
        return payload

    def verify_profile_selection(self, manifest: Dict[str, Any]) -> List[Path]:
        paths: List[Path] = []
        report = resolve_under_root(self.root, manifest.get("profile_selection_report"))
        if report is None or not report.is_file() or report.stat().st_size == 0:
            self.error("PROFILE_SELECTION_REPORT_MISSING", str(manifest.get("profile_selection_report")))
            return paths
        paths.append(report)
        try:
            payload = json.loads(report.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            self.error("PROFILE_SELECTION_REPORT_INVALID", str(exc))
            return paths
        if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
            self.error("PROFILE_SELECTION_SCHEMA", "当前仅接受schema_version=1.0")
            return paths
        if payload.get("selected_profile") != manifest.get("execution_profile"):
            self.error("PROFILE_SELECTION_MISMATCH", str(payload.get("selected_profile")))
        if payload.get("model_label") != manifest.get("model_label"):
            self.error("PROFILE_MODEL_LABEL_MISMATCH", str(payload.get("model_label")))
        selector = payload.get("selector")
        selector_script = SKILL_ROOT / "scripts" / "select_execution_profile.py"
        if not isinstance(selector, dict) or selector.get("name") != selector_script.name:
            self.error("PROFILE_SELECTOR_IDENTITY_MISSING", str(selector))
        elif selector.get("sha256") != sha256(selector_script):
            self.error("PROFILE_SELECTOR_STALE", selector_script.name)
        capability = Path(str(payload.get("capability_report") or "")).expanduser()
        if not capability.is_absolute():
            capability = (self.root / capability).resolve()
        try:
            capability.relative_to(self.root)
        except ValueError:
            self.error("PROFILE_CAPABILITY_PATH_ESCAPE", str(capability))
            return paths
        if not capability.is_file() or capability.stat().st_size == 0:
            self.error("PROFILE_CAPABILITY_REPORT_MISSING", str(capability))
        else:
            paths.append(capability)
            if payload.get("capability_report_sha256") != sha256(capability):
                self.error("PROFILE_CAPABILITY_HASH_MISMATCH", str(capability))
        self.metrics["execution_profile"] = manifest.get("execution_profile")
        return paths

    def load_matrix(self, path: Path) -> List[Dict[str, str]]:
        required_exact = {
            "source_id", "evidence_role", "access_mode", "publication_status",
            "fulltext_locator", "page_locator",
        }
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, restkey="__extra__", restval="__missing__")
                fields = set(reader.fieldnames or [])
                for field in sorted(required_exact - fields):
                    self.error("EVIDENCE_MATRIX_REQUIRED_FIELD", field)
                for canonical, aliases in FIELD_ALIASES.items():
                    if canonical == "url":
                        continue
                    if not any(alias in fields for alias in aliases):
                        self.error("EVIDENCE_MATRIX_REQUIRED_FIELD", canonical)
                rows = list(reader)
        except (OSError, UnicodeError, csv.Error) as exc:
            self.error("EVIDENCE_MATRIX_INVALID", str(exc))
            return []
        ids: List[str] = []
        for number, row in enumerate(rows, start=2):
            for canonical, aliases in FIELD_ALIASES.items():
                if canonical not in row or not str(row.get(canonical) or "").strip():
                    for alias in aliases:
                        if str(row.get(alias) or "").strip():
                            row[canonical] = str(row[alias])
                            break
            if row.get("__extra__") or "__missing__" in row.values():
                self.error("EVIDENCE_MATRIX_ROW", f"第{number}行列数不一致")
            source_id = str(row.get("source_id") or "").strip()
            ids.append(source_id)
            status = str(row.get("status") or "").strip()
            if status not in VALID_STATUSES:
                self.error("EVIDENCE_STATUS_INVALID", f"{source_id or number}: {status}")
            if status in {"VERIFIED_FULLTEXT", "VERIFIED_METADATA"}:
                for field in [
                    "title", "authors", "year", "verification_source", "supported_claims",
                    "chapters", "evidence_role", "access_mode", "publication_status", "notes",
                ]:
                    if not str(row.get(field) or "").strip():
                        self.error("EVIDENCE_FIELD_EMPTY", f"{source_id or number}.{field}")
                if not any(str(row.get(field) or "").strip() for field in ["doi", "url", "fulltext_locator"]):
                    self.error("EVIDENCE_IDENTIFIER_EMPTY", source_id or str(number))
            if status == "VERIFIED_FULLTEXT":
                source = str(row.get("verification_source") or "").strip()
                if DISCOVERY_ONLY.fullmatch(source):
                    self.error("FULLTEXT_DISCOVERY_ONLY", f"{source_id}: {source}")
                locator = str(row.get("fulltext_locator") or "").strip()
                if not locator:
                    self.error("FULLTEXT_LOCATOR_MISSING", source_id)
                if not str(row.get("page_locator") or "").strip():
                    self.error("FULLTEXT_PAGE_LOCATOR_MISSING", source_id)
                source_file = str(row.get("source_file") or "").strip()
                if source_file:
                    file_path = resolve_under_root(self.root, source_file)
                    if file_path is None or not file_path.is_file() or file_path.stat().st_size == 0:
                        self.error("FULLTEXT_SOURCE_FILE_MISSING", f"{source_id}: {source_file}")
                    else:
                        declared = str(row.get("source_sha256") or "").strip().lower()
                        if not declared or declared != sha256(file_path):
                            self.error("FULLTEXT_SOURCE_HASH_MISMATCH", source_id)
                elif locator and not re.match(r"^https?://", locator, re.IGNORECASE):
                    self.error("FULLTEXT_LOCATOR_INVALID", f"{source_id}: {locator}")
                if re.search(r"(?:api\.crossref\.org|openalex\.org/works|semanticscholar)", locator, re.IGNORECASE):
                    self.error("FULLTEXT_LOCATOR_DISCOVERY_ONLY", f"{source_id}: {locator}")
        if any(not item for item in ids):
            self.error("EVIDENCE_SOURCE_ID_MISSING", "存在空source_id")
        if len(ids) != len(set(ids)):
            self.error("EVIDENCE_SOURCE_ID_DUPLICATE", "source_id不唯一")
        self.metrics["evidence_rows"] = len(rows)
        self.metrics["verified_fulltext"] = sum(row.get("status") == "VERIFIED_FULLTEXT" for row in rows)
        self.metrics["verified_metadata"] = sum(row.get("status") == "VERIFIED_METADATA" for row in rows)
        return rows

    def verify_citations(self, markdown: Path, rows: List[Dict[str, str]], mode: str) -> None:
        if not markdown.is_file():
            self.error("MARKDOWN_MISSING", str(markdown))
            return
        text = markdown.read_text(encoding="utf-8", errors="replace")
        heading = REFERENCE_HEADING.search(text)
        if not heading:
            self.error("REFERENCE_HEADING_MISSING", str(markdown))
            return
        body = text[:heading.start()]
        references = text[heading.end():]
        numbered = re.findall(r"^\s*(?:[-*]\s*)?\[(\d+)\]", references, re.MULTILINE)
        accepted = [row for row in rows if row.get("status") not in {"REJECTED", "UNVERIFIED"}]
        if mode == "NUMERIC":
            if not numbered:
                self.error("NUMERIC_REFERENCES_MISSING", "citation_mode=NUMERIC但文末没有编号文献")
                return
            reference_numbers = {int(item) for item in numbered}
            cited = expand_numeric_citations(body)
            missing = sorted(reference_numbers - cited)
            extra = sorted(cited - reference_numbers)
            if missing:
                self.error("REFERENCES_NOT_CITED", ",".join(map(str, missing[:30])))
            if extra:
                self.error("CITATIONS_OUT_OF_RANGE", ",".join(map(str, extra[:30])))
            if len(numbered) != len(accepted):
                self.error(
                    "REFERENCE_MATRIX_COUNT_MISMATCH",
                    f"文末={len(numbered)}，可用证据矩阵={len(accepted)}",
                )
            self.metrics["citations"] = {
                "mode": mode, "reference_count": len(numbered), "cited_unique": len(cited),
                "uncited_count": len(missing),
            }
        elif mode == "AUTHOR_YEAR":
            if numbered:
                self.error("CITATION_STYLE_MIXED", "正文声明作者—年份制，但文末仍使用编号列表")
            missing_tokens: List[str] = []
            seen_tokens: Set[str] = set()
            for row in accepted:
                token = str(row.get("citation_token") or "").strip()
                if not token:
                    missing_tokens.append(str(row.get("source_id") or ""))
                    continue
                if token in seen_tokens:
                    self.error("CITATION_TOKEN_DUPLICATE", token)
                seen_tokens.add(token)
                if token not in body:
                    self.error("AUTHOR_YEAR_CITATION_MISSING", f"{row.get('source_id')}: {token}")
            if missing_tokens:
                self.error("CITATION_TOKEN_MISSING", ",".join(missing_tokens[:30]))
            self.metrics["citations"] = {
                "mode": mode, "reference_count": len(accepted),
                "citation_tokens": len(seen_tokens),
            }

    @staticmethod
    def crossref_lookup(item: Tuple[str, str, str]) -> Dict[str, Any]:
        source_id, doi, declared_title = item
        url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
        request = urllib.request.Request(
            url, headers={"User-Agent": "AIWritePaper/1.4 evidence verifier (mailto:openai@example.com)"}
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                message = json.load(response).get("message", {})
            actual_title = " ".join(message.get("title") or [""])
            declared_clean = clean_title(declared_title)
            actual_clean = clean_title(actual_title)
            similarity: Optional[float] = None
            mismatch = False
            if declared_clean and actual_clean and not contains_cjk(declared_title):
                similarity = SequenceMatcher(None, declared_clean, actual_clean).ratio()
                mismatch = similarity < 0.55
            return {
                "source_id": source_id, "doi": doi, "status": "RESOLVED_CROSSREF",
                "declared_title": declared_title, "resolved_title": actual_title,
                "similarity": round(similarity, 3) if similarity is not None else None,
                "mismatch": mismatch,
            }
        except urllib.error.HTTPError as exc:
            return {
                "source_id": source_id, "doi": doi,
                "status": "NOT_IN_CROSSREF" if exc.code == 404 else f"HTTP_{exc.code}",
                "declared_title": declared_title, "resolved_title": "", "similarity": None,
                "mismatch": False,
            }
        except Exception as exc:
            return {
                "source_id": source_id, "doi": doi, "status": "NETWORK_ERROR",
                "declared_title": declared_title, "resolved_title": "", "similarity": None,
                "mismatch": False, "error": type(exc).__name__,
            }

    def verify_dois(self, rows: List[Dict[str, str]]) -> None:
        items = [
            (str(row.get("source_id") or ""), str(row.get("doi") or "").strip(), str(row.get("title") or ""))
            for row in rows
            if row.get("status") not in {"REJECTED", "UNVERIFIED"} and str(row.get("doi") or "").strip()
        ]
        if not items:
            self.metrics["doi"] = {"checked": 0, "resolved": 0, "mismatched": 0}
            return
        if self.offline:
            self.capability_gap = True
            self.warning("DOI_CHECK_CAPABILITY_GAP", "离线模式未执行DOI解析")
            self.metrics["doi"] = {"checked": 0, "pending": len(items)}
            return
        try:
            with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
                results = list(pool.map(self.crossref_lookup, items))
        except Exception as exc:
            self.capability_gap = True
            self.warning("DOI_CHECK_CAPABILITY_GAP", str(exc))
            self.metrics["doi"] = {"checked": 0, "pending": len(items)}
            return
        network_errors = sum(item.get("status") == "NETWORK_ERROR" for item in results)
        if network_errors == len(results):
            self.capability_gap = True
            self.warning("DOI_CHECK_CAPABILITY_GAP", "Crossref网络检查全部失败")
        for item in results:
            if item.get("mismatch"):
                self.error(
                    "DOI_TITLE_MISMATCH",
                    f"{item['source_id']}: {item['doi']} -> {item['resolved_title']}",
                )
            elif item.get("status") == "NOT_IN_CROSSREF":
                self.warning("DOI_NOT_IN_CROSSREF", f"{item['source_id']}: {item['doi']}")
        self.metrics["doi"] = {
            "checked": len(results),
            "resolved": sum(item.get("status") == "RESOLVED_CROSSREF" for item in results),
            "not_in_crossref": sum(item.get("status") == "NOT_IN_CROSSREF" for item in results),
            "network_errors": network_errors,
            "mismatched": sum(bool(item.get("mismatch")) for item in results),
            "records": results,
        }

    def verify_provenance(self, path: Path, markdown: Path, claim_level: str) -> None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("DATA_PROVENANCE_INVALID", str(exc))
            return
        if not isinstance(payload, dict) or payload.get("schema_version") != "1.0":
            self.error("DATA_PROVENANCE_SCHEMA", "当前仅接受schema_version=1.0")
            return
        if payload.get("research_claim_level") != claim_level:
            self.error("DATA_PROVENANCE_CLAIM_LEVEL_MISMATCH", str(payload.get("research_claim_level")))
        datasets = payload.get("datasets")
        if not isinstance(datasets, list):
            self.error("DATA_PROVENANCE_DATASETS", "datasets必须为数组")
            return
        observed_count = 0
        result_count = 0
        for index, dataset in enumerate(datasets):
            if not isinstance(dataset, dict):
                self.error("DATASET_SHAPE", str(index))
                continue
            dataset_id = str(dataset.get("dataset_id") or index)
            origin = dataset.get("origin")
            role = dataset.get("claim_role")
            if origin not in VALID_DATA_ORIGINS:
                self.error("DATASET_ORIGIN_INVALID", f"{dataset_id}: {origin}")
            if role not in VALID_CLAIM_ROLES:
                self.error("DATASET_CLAIM_ROLE_INVALID", f"{dataset_id}: {role}")
            if role in {"RESULT", "SIMULATION_RESULT"}:
                result_count += 1
            if origin in {"USER_PROVIDED", "AUTHOR_OBSERVED"}:
                observed_count += 1
            if origin == "MODEL_SYNTHETIC" and role in {"RESULT", "SIMULATION_RESULT", "DESIGN_CALCULATION"}:
                self.error("MODEL_SYNTHETIC_RESULT_FORBIDDEN", dataset_id)
            if origin == "CALCULATED" and role == "RESULT":
                self.error("CALCULATED_OBSERVED_RESULT_FORBIDDEN", dataset_id)
            file_path = resolve_under_root(self.root, dataset.get("file"))
            if file_path is None or not file_path.is_file() or file_path.stat().st_size == 0:
                self.error("DATASET_FILE_MISSING", dataset_id)
            else:
                declared = str(dataset.get("sha256") or "").lower()
                if not declared or declared != sha256(file_path):
                    self.error("DATASET_HASH_MISMATCH", dataset_id)
            if origin in {"USER_PROVIDED", "AUTHOR_OBSERVED"}:
                receipt = resolve_under_root(self.root, dataset.get("observation_receipt"))
                if receipt is None or not receipt.is_file() or receipt.stat().st_size == 0:
                    self.error("OBSERVATION_RECEIPT_MISSING", dataset_id)
                else:
                    declared_receipt = str(dataset.get("observation_receipt_sha256") or "").lower()
                    if not declared_receipt or declared_receipt != sha256(receipt):
                        self.error("OBSERVATION_RECEIPT_HASH_MISMATCH", dataset_id)
            if origin == "OFFICIAL_DOWNLOAD":
                receipt = resolve_under_root(self.root, dataset.get("acquisition_receipt"))
                if receipt is None or not receipt.is_file() or receipt.stat().st_size == 0:
                    self.error("ACQUISITION_RECEIPT_MISSING", dataset_id)
                else:
                    declared_receipt = str(dataset.get("acquisition_receipt_sha256") or "").lower()
                    if not declared_receipt or declared_receipt != sha256(receipt):
                        self.error("ACQUISITION_RECEIPT_HASH_MISMATCH", dataset_id)
            if origin in {"FORMAL_SIMULATION", "CALCULATED"} and role in {
                "SIMULATION_RESULT", "DESIGN_CALCULATION", "RESULT"
            }:
                receipt = resolve_under_root(self.root, dataset.get("execution_receipt"))
                if receipt is None or not receipt.is_file() or receipt.stat().st_size == 0:
                    self.error("DATA_EXECUTION_RECEIPT_MISSING", dataset_id)
                else:
                    declared_receipt = str(dataset.get("execution_receipt_sha256") or "").lower()
                    if not declared_receipt or declared_receipt != sha256(receipt):
                        self.error("DATA_EXECUTION_RECEIPT_HASH_MISMATCH", dataset_id)
            claims = dataset.get("supports_claims")
            if not isinstance(claims, list):
                self.error("DATASET_CLAIMS_INVALID", dataset_id)
        text = markdown.read_text(encoding="utf-8", errors="replace") if markdown.is_file() else ""
        suspicious = [re.sub(r"\s+", " ", item.group(0)).strip() for item in SELF_RESULT_PATTERN.finditer(text)]
        if suspicious and observed_count == 0 and claim_level != "REVIEW_SYNTHESIS":
            self.error("OBSERVED_RESULT_WITHOUT_DATA", " | ".join(suspicious[:5]))
        if claim_level == "OBSERVED_STUDY" and observed_count == 0:
            self.error("OBSERVED_STUDY_DATA_MISSING", "没有USER_PROVIDED或AUTHOR_OBSERVED数据")
        self.metrics["data_provenance"] = {
            "datasets": len(datasets), "observed_datasets": observed_count,
            "result_datasets": result_count, "suspicious_self_result_claims": len(suspicious),
        }


def rooted(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="核验AIWritePaper文献、引用和数据来源")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--matrix", type=Path, default=Path("03-evidence-matrix.csv"))
    parser.add_argument("--markdown", type=Path, default=Path("07-paper-full.md"))
    parser.add_argument("--provenance", type=Path, default=Path("data/data-provenance.json"))
    parser.add_argument("--run-manifest", type=Path, default=Path("run-manifest.json"))
    parser.add_argument("--offline", action="store_true", help="不联网解析DOI；报告降为PARTIAL")
    parser.add_argument("--report", type=Path, default=Path("04-evidence-verification.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    verifier = EvidenceVerifier(root, args.offline)
    manifest_path = rooted(root, args.run_manifest)
    matrix_path = rooted(root, args.matrix)
    markdown_path = rooted(root, args.markdown)
    provenance_path = rooted(root, args.provenance)
    manifest = verifier.load_manifest(manifest_path)
    profile_input_paths = verifier.verify_profile_selection(manifest)
    rows = verifier.load_matrix(matrix_path)
    verifier.verify_citations(
        markdown_path, rows, str(manifest.get("citation_mode") or "")
    )
    verifier.verify_dois(rows)
    verifier.verify_provenance(
        provenance_path, markdown_path,
        str(manifest.get("research_claim_level") or ""),
    )
    if verifier.errors:
        status = "EVIDENCE_FAIL"
    elif verifier.capability_gap:
        status = "EVIDENCE_PARTIAL"
    else:
        status = "EVIDENCE_OK"
    input_sha256: Dict[str, str] = {}
    for path in [manifest_path, matrix_path, markdown_path, provenance_path, *profile_input_paths]:
        if path.is_file():
            try:
                relative = str(path.resolve().relative_to(root))
            except ValueError:
                continue
            input_sha256[relative] = sha256(path)
    payload = {
        "schema_version": "1.0", "status": status,
        "errors": verifier.errors, "warnings": verifier.warnings,
        "metrics": verifier.metrics, "input_sha256": input_sha256,
        "verifier": verifier_identity(),
        "scope_note": "题录与来源机械通过不代表研究结论、全文解释或因果推断正确",
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    report = rooted(root, args.report)
    try:
        report.resolve().relative_to(root)
    except ValueError:
        print("报告路径必须位于输出目录内", file=sys.stderr)
        return 1
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if status != "EVIDENCE_FAIL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
