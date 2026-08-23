#!/usr/bin/env python3
"""机械校验图表Manifest、文件、哈希与文档嵌入路由，不判断学术正确性。"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


ROUTES = {"IMAGE_GENERATION", "DATA_CODE", "DOMAIN_TOOL", "EVIDENCE_FILE", "SVG_FALLBACK"}
FIGURE_TYPES = {"ARCHITECTURE", "PROCESS", "ER_UML", "STATISTICAL", "NETWORK_DATA", "DOMAIN", "EVIDENCE_IMAGE"}
DATA_STATUSES = {"OBSERVED", "VERIFIED_EXTERNAL", "SIMULATED_RESEARCH", "NOT_APPLICABLE"}
VLM_STATUSES = {"PASS", "PASS_WITH_NOTES", "NEEDS_REVIEW", "SKIPPED"}
FINAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CJK_FONTS = ["Noto Sans CJK", "Source Han Sans", "PingFang SC", "Microsoft YaHei", "WenQuanYi", "SimHei"]
REQUIRED_FIELDS = {
    "figure_id", "title", "figure_type", "claim_bearing", "generation_route",
    "data_status", "prompt_file", "generated_file", "fallback_file", "source_data",
    "transformation", "caption_claim", "supported_manuscript_claims", "limitations",
    "canvas_contains_figure_number_or_caption", "final_embed_file", "vlm_verification",
}


class FigureVerifier:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.final_files: Dict[str, Path] = {}

    def error(self, code: str, detail: str) -> None:
        self.errors.append(f"{code}: {detail}")

    def warning(self, code: str, detail: str) -> None:
        self.warnings.append(f"{code}: {detail}")

    def resolve_file(self, value: Any, field: str, figure_id: str, required: bool = True) -> Optional[Path]:
        if value in (None, ""):
            if required:
                self.error("MISSING_PATH", f"{figure_id}.{field}")
            return None
        if not isinstance(value, str):
            self.error("INVALID_PATH", f"{figure_id}.{field}必须是字符串或null")
            return None
        candidate = (self.root / value).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            self.error("PATH_ESCAPE", f"{figure_id}.{field}越出输出目录: {value}")
            return None
        if not candidate.is_file() or candidate.stat().st_size == 0:
            self.error("FILE_MISSING", f"{figure_id}.{field}: {value}")
            return None
        return candidate

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def verify_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("MANIFEST_INVALID", str(exc))
            return {}
        if not isinstance(manifest, dict) or not isinstance(manifest.get("figures"), list):
            self.error("MANIFEST_SHAPE", "根对象必须包含figures数组")
            return manifest if isinstance(manifest, dict) else {}
        if manifest.get("schema_version") != "1.0":
            self.error("SCHEMA_VERSION", "当前仅接受schema_version=1.0")

        seen_ids: Set[str] = set()
        seen_final: Set[str] = set()
        for index, figure in enumerate(manifest["figures"]):
            if not isinstance(figure, dict):
                self.error("FIGURE_SHAPE", f"figures[{index}]不是对象")
                continue
            figure_id = str(figure.get("figure_id") or f"index-{index}")
            missing = sorted(REQUIRED_FIELDS - set(figure))
            if missing:
                self.error("FIELDS_MISSING", f"{figure_id}: {', '.join(missing)}")
            if figure_id in seen_ids:
                self.error("DUPLICATE_ID", figure_id)
            seen_ids.add(figure_id)

            route = figure.get("generation_route")
            if route not in ROUTES:
                self.error("ROUTE_INVALID", f"{figure_id}: {route}")
            if figure.get("figure_type") not in FIGURE_TYPES:
                self.error("FIGURE_TYPE_INVALID", f"{figure_id}: {figure.get('figure_type')}")
            if not isinstance(figure.get("title"), str) or not figure.get("title").strip():
                self.error("TITLE_MISSING", figure_id)
            data_status = figure.get("data_status")
            if data_status not in DATA_STATUSES:
                self.error("DATA_STATUS_INVALID", f"{figure_id}: {data_status}")
            if not isinstance(figure.get("claim_bearing"), bool):
                self.error("CLAIM_BEARING_INVALID", figure_id)
            if figure.get("canvas_contains_figure_number_or_caption") is not False:
                self.error("CAPTION_IN_CANVAS", figure_id)
            if not isinstance(figure.get("limitations"), list):
                self.error("LIMITATIONS_INVALID", figure_id)
            if not isinstance(figure.get("supported_manuscript_claims"), list):
                self.error("CLAIMS_INVALID", figure_id)

            final_value = figure.get("final_embed_file")
            final_path = self.resolve_file(final_value, "final_embed_file", figure_id)
            if isinstance(final_value, str):
                if final_value in seen_final:
                    self.error("DUPLICATE_FINAL", final_value)
                seen_final.add(final_value)
                if Path(final_value).suffix.lower() not in FINAL_EXTENSIONS:
                    self.error("FINAL_FORMAT", f"{figure_id}: 最终嵌入文件必须是位图")
            if final_path:
                self.final_files[figure_id] = final_path

            vlm = figure.get("vlm_verification")
            if not isinstance(vlm, dict) or vlm.get("status") not in VLM_STATUSES:
                self.error("VLM_STATUS_INVALID", figure_id)
            elif vlm.get("status") == "NEEDS_REVIEW":
                self.error("VLM_NEEDS_REVIEW", figure_id)
            elif not isinstance(vlm.get("remaining_issues"), list):
                self.error("VLM_ISSUES_INVALID", figure_id)
            elif vlm.get("status") == "PASS" and vlm.get("remaining_issues"):
                self.error("VLM_PASS_WITH_ISSUES", figure_id)

            source_data = figure.get("source_data")
            if not isinstance(source_data, list):
                self.error("SOURCE_DATA_INVALID", figure_id)
                source_data = []
            source_paths: List[Path] = []
            for pos, source in enumerate(source_data):
                if not isinstance(source, dict) or not source.get("file"):
                    self.error("SOURCE_DATA_ROW", f"{figure_id}[{pos}]")
                    continue
                source_path = self.resolve_file(source.get("file"), f"source_data[{pos}].file", figure_id)
                if source_path:
                    source_paths.append(source_path)
            if figure.get("claim_bearing"):
                if not source_paths:
                    self.error("CLAIM_SOURCE_MISSING", figure_id)
                if not isinstance(figure.get("caption_claim"), str) or not figure.get("caption_claim").strip():
                    self.error("CAPTION_CLAIM_MISSING", figure_id)
                if not isinstance(figure.get("supported_manuscript_claims"), list) or not figure.get("supported_manuscript_claims"):
                    self.error("MANUSCRIPT_CLAIMS_MISSING", figure_id)

            transformation = figure.get("transformation")
            if not isinstance(transformation, dict):
                self.error("TRANSFORMATION_INVALID", figure_id)
                transformation = {}

            if route == "IMAGE_GENERATION":
                self.resolve_file(figure.get("prompt_file"), "prompt_file", figure_id)
                generated = self.resolve_file(figure.get("generated_file"), "generated_file", figure_id)
                if generated and final_path and generated != final_path and not transformation.get("method"):
                    self.error("COMPOSITE_UNDECLARED", figure_id)
                if isinstance(final_value, str) and final_value.lower().endswith(".svg"):
                    self.error("GENERATED_REPLACED_BY_SVG", figure_id)

            elif route == "DATA_CODE":
                if not source_paths:
                    self.error("DATA_SOURCE_MISSING", figure_id)
                if figure.get("claim_bearing") and data_status == "NOT_APPLICABLE":
                    self.error("CLAIM_DATA_STATUS", figure_id)
                script = self.resolve_file(transformation.get("script"), "transformation.script", figure_id)
                declared_hash = transformation.get("sha256")
                if script:
                    actual_hash = self.sha256(script)
                    if not isinstance(declared_hash, str) or declared_hash.lower() != actual_hash:
                        self.error("SCRIPT_HASH_MISMATCH", figure_id)
                    script_text = script.read_text(encoding="utf-8", errors="replace")
                    forbidden = ["replace with actual data", "dummy data", "hardcoded_example", "example_data"]
                    if any(token in script_text.lower() for token in forbidden):
                        self.error("DEMO_DATA_MARKER", figure_id)
                    random_tokens = ["np.random", "random.", "rnorm(", "runif("]
                    if any(token in script_text.lower() for token in random_tokens):
                        randomness = figure.get("randomness")
                        if not isinstance(randomness, dict) or not randomness.get("purpose") or randomness.get("seed") is None:
                            self.error("RANDOMNESS_UNDECLARED", figure_id)

            elif route == "SVG_FALLBACK":
                fallback = self.resolve_file(figure.get("fallback_file"), "fallback_file", figure_id)
                if fallback and fallback.suffix.lower() != ".svg":
                    self.error("FALLBACK_NOT_SVG", figure_id)
                elif fallback:
                    self.verify_svg(fallback, figure_id)
                if not figure.get("capability_gap"):
                    self.error("CAPABILITY_GAP_MISSING", figure_id)

            elif route in {"DOMAIN_TOOL", "EVIDENCE_FILE"}:
                if not source_paths:
                    self.error("SOURCE_FILE_MISSING", figure_id)
                if not transformation.get("method"):
                    self.error("METHOD_MISSING", figure_id)
        return manifest

    def verify_svg(self, path: Path, figure_id: str) -> None:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"(?:href|src)\s*=\s*[\"']https?://", raw, re.IGNORECASE):
            self.error("SVG_REMOTE_RESOURCE", figure_id)
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            self.error("SVG_XML_INVALID", f"{figure_id}: {exc}")
            return
        cjk_text = "".join("".join(element.itertext()) for element in root.iter())
        if re.search(r"[\u3400-\u9fff]", cjk_text) and not any(font in raw for font in CJK_FONTS):
            self.error("SVG_CJK_FONT_MISSING", figure_id)

    def verify_markdown(self, markdown: Path) -> None:
        if not markdown.is_file():
            self.error("MARKDOWN_MISSING", str(markdown))
            return
        text = markdown.read_text(encoding="utf-8")
        links = re.findall(r"!\[[^\]]*\]\((?:<)?([^)>]+)(?:>)?\)", text)
        normalized = [str((self.root / link).resolve()) for link in links if not re.match(r"^[a-z]+://", link)]
        expected = {str(path.resolve()) for path in self.final_files.values()}
        for path in expected:
            count = normalized.count(path)
            if count != 1:
                self.error("MARKDOWN_ROUTE", f"{path}出现{count}次")
        extras = sorted(set(normalized) - expected)
        if extras:
            self.error("MARKDOWN_EXTRA_IMAGES", ", ".join(extras))

    def verify_docx(self, docx: Path) -> None:
        if not docx.is_file() or not zipfile.is_zipfile(docx):
            self.error("DOCX_INVALID", str(docx))
            return
        with zipfile.ZipFile(docx) as archive:
            media_hashes = {
                hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist()
                if name.startswith("word/media/") and not name.endswith("/")
            }
        for figure_id, path in self.final_files.items():
            if self.sha256(path) not in media_hashes:
                self.error("DOCX_MEDIA_MISMATCH", figure_id)

    def verify_pdf(self, pdf: Path) -> None:
        if not pdf.is_file() or pdf.stat().st_size < 8:
            self.error("PDF_INVALID", str(pdf))
            return
        if not pdf.read_bytes()[:5] == b"%PDF-":
            self.error("PDF_HEADER_INVALID", str(pdf))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验AIWritePaper图表包的机械一致性")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=Path("figures/figure-manifest.json"))
    parser.add_argument("--markdown", type=Path, default=Path("07-paper-full.md"))
    parser.add_argument("--docx", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    verifier = FigureVerifier(root)
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    verifier.verify_manifest(manifest)
    markdown = args.markdown if args.markdown.is_absolute() else root / args.markdown
    verifier.verify_markdown(markdown)
    if args.docx:
        verifier.verify_docx(args.docx if args.docx.is_absolute() else root / args.docx)
    if args.pdf:
        verifier.verify_pdf(args.pdf if args.pdf.is_absolute() else root / args.pdf)

    payload = {
        "status": "STRUCTURE_OK" if not verifier.errors else "STRUCTURE_FAIL",
        "figures_checked": len(verifier.final_files),
        "errors": verifier.errors,
        "warnings": verifier.warnings,
        "scope_note": "结构通过不代表图表的学术结论正确",
    }
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    print(rendered)
    if args.report:
        report = args.report if args.report.is_absolute() else root / args.report
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(rendered + "\n", encoding="utf-8")
    return 0 if not verifier.errors else 1


if __name__ == "__main__":
    sys.exit(main())
