#!/usr/bin/env python3
"""机械校验图表Manifest、文件、哈希与文档嵌入路由，不判断学术正确性。"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
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
RECEIPT_LEVELS = {"NATIVE_TOOL_RESULT", "CLIENT_TRANSCRIPT", "DECLARED_ONLY"}
VLM_EVIDENCE_LEVELS = {"VISUAL_TOOL_RESULT", "CLIENT_TRANSCRIPT", "DECLARED_ONLY"}
ROUTE_EXEMPTIONS = {
    "USER_REQUESTED_VECTOR", "PUBLICATION_RESTRICTION", "IMAGE_TOOL_UNAVAILABLE",
    "DOMAIN_EXACTNESS", "EVIDENCE_REQUIRED", None,
}
EXACTNESS_CLASSES = {"SEMANTIC_STRUCTURE", "DOMAIN_EXACT", "DATA_GRAPH", "EVIDENCE_IMAGE"}
TEXT_RENDER_STRATEGIES = {"DIRECT_IMAGE_TEXT", "DETERMINISTIC_OVERLAY", "DOMAIN_VECTOR_TEXT", "NO_CANVAS_TEXT"}
LANGUAGE_CHECK_STATUSES = {"PASS", "PASS_WITH_NOTES", "NEEDS_REVIEW", "SKIPPED"}
DATA_ORIGINS = {
    "USER_PROVIDED", "OFFICIAL_DOWNLOAD", "AUTHOR_OBSERVED", "FORMAL_SIMULATION",
    "CALCULATED", "MODEL_SYNTHETIC", "SYNTHETIC_DEMO", "MANUSCRIPT_CONTEXT",
}
EXACTNESS_TITLE_TERMS = [
    "电路", "接线", "引脚", "原理图", "化学结构", "晶体结构", "能带",
    "分子结构", "反应式", "电极体系", "载荷位置", "尺寸标注", "疲劳校核",
    "焊接接头", "信号链", "精确通路",
]
FINAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CJK_FONTS = ["Noto Sans CJK", "Source Han Sans", "PingFang SC", "Microsoft YaHei", "WenQuanYi", "SimHei"]
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
REQUIRED_FIELDS = {
    "figure_id", "display_number", "title", "figure_type", "exactness_class", "imagegen_eligible", "route_exemption",
    "claim_bearing", "generation_route",
    "data_status", "prompt_file", "generated_file", "fallback_file", "source_data",
    "transformation", "caption_claim", "supported_manuscript_claims", "limitations",
    "canvas_contains_figure_number_or_caption", "final_embed_file", "generation_receipt",
    "svg_layout_mode", "svg_layout", "language_contract", "text_render_strategy", "text_overlay", "vlm_verification",
}


class FigureVerifier:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.final_files: Dict[str, Path] = {}
        self.figure_titles: Dict[str, str] = {}
        self.figure_numbers: Dict[str, str] = {}
        self.image_generation_available: Optional[bool] = None
        self.visual_status = "PASS"

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

    def verify_capability_report(self, report_path: Path) -> Dict[str, Any]:
        """读取机器能力报告，阻止父层可生图时被子执行器降级为SVG。"""
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("CAPABILITY_REPORT_INVALID", str(exc))
            return {}
        if not isinstance(report, dict) or report.get("schema_version") not in {"1.0", "2.1"}:
            self.error("CAPABILITY_SCHEMA_VERSION", "当前只接受schema_version=1.0或2.1")
            return report if isinstance(report, dict) else {}
        adapter = report.get("agent_adapter")
        if not isinstance(adapter, str) or not adapter.strip():
            self.error("CAPABILITY_ADAPTER_MISSING", "agent_adapter")
        image_generation = report.get("image_generation")
        if not isinstance(image_generation, dict) or image_generation.get("available") not in {True, False, None}:
            self.error("CAPABILITY_IMAGE_INVALID", "image_generation.available必须为true、false或null")
            return report
        self.image_generation_available = image_generation["available"]
        if report.get("schema_version") == "1.0":
            callers = image_generation.get("callers")
            tools = image_generation.get("tools")
            if self.image_generation_available and (not callers or not tools):
                self.error("CAPABILITY_IMAGE_TOOLS_MISSING", "图片能力可用时必须记录调用层和工具")
        else:
            caller = image_generation.get("caller")
            tool = image_generation.get("tool")
            if caller is not None and caller not in {"CURRENT_AGENT", "PARENT_AGENT", "CLIENT", "MCP_OR_PLUGIN"}:
                self.error("CAPABILITY_IMAGE_CALLER_INVALID", str(caller))
            if self.image_generation_available is True and not tool:
                self.warning("CAPABILITY_IMAGE_TOOL_UNNAMED", "能力已确认但客户端未暴露工具名")
        return report

    def verify_direction_contracts(self, direction_id: Any, manifest: Dict[str, Any]) -> List[Path]:
        """只核对专业源表存在与列结构，不声称电气、理论或分类语义正确。"""
        paths: List[Path] = []
        figures = manifest.get("figures", []) if isinstance(manifest, dict) else []
        requirements: List[tuple[Path, set[str], str]] = []
        if direction_id == "electronic-circuit-design" and any(
            isinstance(item, dict) and item.get("exactness_class") == "DOMAIN_EXACT" for item in figures
        ):
            requirements.append((self.root / "figures/connection-table.csv",
                                 {"from_component", "from_pin", "to_component", "to_pin", "net", "voltage_domain", "source"},
                                 "CIRCUIT_CONNECTION_TABLE"))
        if direction_id == "mathematics-education" and any(
            isinstance(item, dict) and re.search(r"APOS|概念|认知|图式|过程|对象", str(item.get("title", "")), re.IGNORECASE)
            for item in figures
        ):
            requirements.append((self.root / "figures/concept-edge-table.csv",
                                 {"from_concept", "to_concept", "relation", "direction", "evidence", "figure_id"},
                                 "MATH_CONCEPT_EDGE_TABLE"))
        if direction_id == "literature-review-synthesis" and any(
            isinstance(item, dict) and (item.get("generation_route") == "DATA_CODE" or re.search(r"分类|证据图|趋势", str(item.get("title", ""))))
            for item in figures
        ):
            requirements.append((self.root / "review/screening-audit.csv",
                                 {"record_id", "title", "set_role", "classification", "decision_basis", "reviewer_status", "notes"},
                                 "REVIEW_SCREENING_AUDIT"))
        for path, required, code in requirements:
            if not path.is_file() or path.stat().st_size == 0:
                self.error(f"{code}_MISSING", str(path.relative_to(self.root)))
                continue
            try:
                with path.open(encoding="utf-8-sig", newline="") as handle:
                    reader = csv.DictReader(handle)
                    fields = set(reader.fieldnames or [])
                    rows = list(reader)
                if not required.issubset(fields):
                    self.error(f"{code}_FIELDS", ",".join(sorted(required - fields)))
                if not rows:
                    self.error(f"{code}_EMPTY", str(path.relative_to(self.root)))
                else:
                    paths.append(path)
            except (OSError, csv.Error, UnicodeError) as exc:
                self.error(f"{code}_INVALID", str(exc))
        return paths

    def verify_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("MANIFEST_INVALID", str(exc))
            return {}
        if not isinstance(manifest, dict) or not isinstance(manifest.get("figures"), list):
            self.error("MANIFEST_SHAPE", "根对象必须包含figures数组")
            return manifest if isinstance(manifest, dict) else {}
        if manifest.get("schema_version") != "1.5":
            self.error("SCHEMA_VERSION", "当前仅接受schema_version=1.5")

        seen_ids: Set[str] = set()
        seen_numbers: Set[str] = set()
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

            display_number = figure.get("display_number")
            if not isinstance(display_number, str) or not re.fullmatch(r"[0-9]+(?:-[0-9]+)*", display_number):
                self.error("DISPLAY_NUMBER_INVALID", figure_id)
            else:
                if display_number in seen_numbers:
                    self.error("DUPLICATE_DISPLAY_NUMBER", display_number)
                seen_numbers.add(display_number)
                self.figure_numbers[figure_id] = display_number

            route = figure.get("generation_route")
            if route not in ROUTES:
                self.error("ROUTE_INVALID", f"{figure_id}: {route}")
            if figure.get("figure_type") not in FIGURE_TYPES:
                self.error("FIGURE_TYPE_INVALID", f"{figure_id}: {figure.get('figure_type')}")
            exactness_class = figure.get("exactness_class")
            if exactness_class not in EXACTNESS_CLASSES:
                self.error("EXACTNESS_CLASS_INVALID", f"{figure_id}: {exactness_class}")
            language_contract = figure.get("language_contract")
            if not isinstance(language_contract, dict):
                self.error("LANGUAGE_CONTRACT_INVALID", figure_id)
                language_contract = {}
            manuscript_language = language_contract.get("manuscript_language")
            label_language = language_contract.get("label_language")
            exact_labels = language_contract.get("exact_labels")
            allowed_foreign_tokens = language_contract.get("allowed_foreign_tokens")
            for field, value in [
                ("manuscript_language", manuscript_language), ("label_language", label_language),
            ]:
                if not isinstance(value, str) or not value.strip():
                    self.error("LANGUAGE_CONTRACT_FIELD", f"{figure_id}.{field}")
            for field, value in [
                ("exact_labels", exact_labels), ("allowed_foreign_tokens", allowed_foreign_tokens),
            ]:
                if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                    self.error("LANGUAGE_CONTRACT_FIELD", f"{figure_id}.{field}")
            text_render_strategy = figure.get("text_render_strategy")
            if text_render_strategy not in TEXT_RENDER_STRATEGIES:
                self.error("TEXT_RENDER_STRATEGY_INVALID", f"{figure_id}: {text_render_strategy}")
            if isinstance(exact_labels, list):
                if text_render_strategy == "NO_CANVAS_TEXT" and exact_labels:
                    self.error("NO_CANVAS_TEXT_HAS_LABELS", figure_id)
                elif text_render_strategy != "NO_CANVAS_TEXT" and not exact_labels:
                    self.error("EXACT_LABELS_MISSING", figure_id)
            if (
                isinstance(manuscript_language, str) and manuscript_language.lower().startswith("zh")
                and text_render_strategy != "NO_CANVAS_TEXT"
                and (not isinstance(label_language, str) or not label_language.lower().startswith("zh"))
            ):
                self.error("FIGURE_LANGUAGE_MISMATCH", f"{figure_id}: {manuscript_language}->{label_language}")
            if text_render_strategy == "DETERMINISTIC_OVERLAY" and route != "IMAGE_GENERATION":
                self.error("TEXT_OVERLAY_ROUTE_INVALID", figure_id)
            if route == "IMAGE_GENERATION" and text_render_strategy == "DOMAIN_VECTOR_TEXT":
                self.error("IMAGEGEN_TEXT_STRATEGY_INVALID", figure_id)
            if route != "IMAGE_GENERATION" and text_render_strategy == "DIRECT_IMAGE_TEXT":
                self.error("DIRECT_IMAGE_TEXT_ROUTE_INVALID", figure_id)
            imagegen_eligible = figure.get("imagegen_eligible")
            if not isinstance(imagegen_eligible, bool):
                self.error("IMAGEGEN_ELIGIBLE_INVALID", figure_id)
            exemption = figure.get("route_exemption")
            if exemption not in ROUTE_EXEMPTIONS:
                self.error("ROUTE_EXEMPTION_INVALID", f"{figure_id}: {exemption}")
            if exemption in {"USER_REQUESTED_VECTOR", "PUBLICATION_RESTRICTION"}:
                exemption_evidence = figure.get("route_exemption_evidence")
                expected_source = "USER_REQUEST" if exemption == "USER_REQUESTED_VECTOR" else "PUBLICATION_RULE"
                if (
                    not isinstance(exemption_evidence, dict)
                    or exemption_evidence.get("source") != expected_source
                    or not isinstance(exemption_evidence.get("quote"), str)
                    or not exemption_evidence.get("quote", "").strip()
                    or not isinstance(exemption_evidence.get("locator"), str)
                    or not exemption_evidence.get("locator", "").strip()
                ):
                    self.error("ROUTE_EXEMPTION_EVIDENCE_MISSING", figure_id)
            if imagegen_eligible is True and self.image_generation_available is True and route != "IMAGE_GENERATION":
                if exemption not in {"USER_REQUESTED_VECTOR", "PUBLICATION_RESTRICTION"}:
                    self.error("IMAGEGEN_BYPASSED", f"{figure_id}: 图片工具可用但路线为{route}")
            if exemption == "IMAGE_TOOL_UNAVAILABLE" and self.image_generation_available is True:
                self.error("FALSE_IMAGE_TOOL_GAP", figure_id)
            if (
                exactness_class == "SEMANTIC_STRUCTURE"
                and self.image_generation_available is True
                and imagegen_eligible is not True
                and exemption not in {"USER_REQUESTED_VECTOR", "PUBLICATION_RESTRICTION"}
            ):
                self.error("SEMANTIC_IMAGEGEN_ELIGIBILITY_FALSE", figure_id)
            if exactness_class == "DOMAIN_EXACT":
                if route == "IMAGE_GENERATION" or imagegen_eligible is not False:
                    self.error("DOMAIN_EXACT_IMAGEGEN_FORBIDDEN", figure_id)
                if route == "SVG_FALLBACK" and exemption != "DOMAIN_EXACTNESS":
                    self.error("DOMAIN_EXACT_EXEMPTION_MISSING", figure_id)
            elif exactness_class == "DATA_GRAPH" and route != "DATA_CODE":
                self.error("DATA_GRAPH_ROUTE_INVALID", figure_id)
            elif exactness_class == "EVIDENCE_IMAGE" and route != "EVIDENCE_FILE":
                self.error("EVIDENCE_IMAGE_ROUTE_INVALID", figure_id)
            if figure.get("figure_type") in {"ARCHITECTURE", "PROCESS", "ER_UML"} and exactness_class == "DATA_GRAPH":
                self.error("FIGURE_TYPE_EXACTNESS_MISMATCH", figure_id)
            if exactness_class == "SEMANTIC_STRUCTURE" and isinstance(figure.get("title"), str):
                if any(term in figure["title"] for term in EXACTNESS_TITLE_TERMS):
                    self.warning("EXACTNESS_CLASS_REVIEW", f"{figure_id}: {figure['title']}")
                    self.visual_status = "PARTIAL"
            if not isinstance(figure.get("title"), str) or not figure.get("title").strip():
                self.error("TITLE_MISSING", figure_id)
            else:
                self.figure_titles[figure_id] = figure["title"].strip()
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
            self.verify_vlm_receipt(vlm, final_path, figure_id, language_contract, text_render_strategy)

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
                origin = source.get("origin") if isinstance(source, dict) else None
                if origin not in DATA_ORIGINS:
                    self.error("SOURCE_DATA_ORIGIN_INVALID", f"{figure_id}[{pos}]: {origin}")
                if origin in {"MODEL_SYNTHETIC", "SYNTHETIC_DEMO"} and (route == "DATA_CODE" or figure.get("claim_bearing")):
                    self.error("MODEL_SYNTHETIC_RESULT_FORBIDDEN", f"{figure_id}[{pos}]")
                if origin == "OFFICIAL_DOWNLOAD":
                    receipt = source.get("acquisition_receipt")
                    if not isinstance(receipt, dict):
                        self.error("ACQUISITION_RECEIPT_MISSING", f"{figure_id}[{pos}]")
                    else:
                        receipt_path = self.resolve_file(
                            receipt.get("receipt_file"), f"source_data[{pos}].acquisition_receipt.receipt_file", figure_id
                        )
                        if receipt_path and receipt.get("receipt_sha256", "").lower() != self.sha256(receipt_path):
                            self.error("ACQUISITION_RECEIPT_HASH_MISMATCH", f"{figure_id}[{pos}]")
                        for field in ["source_url", "downloaded_at"]:
                            if not isinstance(receipt.get(field), str) or not receipt.get(field, "").strip():
                                self.error("ACQUISITION_RECEIPT_FIELD", f"{figure_id}[{pos}].{field}")
                if source_path:
                    source_paths.append(source_path)
                    declared_source_hash = source.get("sha256")
                    if not isinstance(declared_source_hash, str) or declared_source_hash.lower() != self.sha256(source_path):
                        self.error("SOURCE_DATA_HASH_MISMATCH", f"{figure_id}[{pos}]")
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
                prompt = self.resolve_file(figure.get("prompt_file"), "prompt_file", figure_id)
                generated = self.resolve_file(figure.get("generated_file"), "generated_file", figure_id)
                self.verify_generation_receipt(figure.get("generation_receipt"), prompt, generated, figure_id)
                if prompt and isinstance(exact_labels, list) and text_render_strategy != "NO_CANVAS_TEXT":
                    prompt_text = prompt.read_text(encoding="utf-8", errors="replace")
                    for label in exact_labels:
                        if isinstance(label, str) and label not in prompt_text:
                            self.error("PROMPT_EXACT_LABEL_MISSING", f"{figure_id}: {label}")
                if text_render_strategy == "DETERMINISTIC_OVERLAY":
                    self.verify_text_overlay(figure.get("text_overlay"), generated, final_path, figure_id)
                elif figure.get("text_overlay") not in (None, {}):
                    self.error("TEXT_OVERLAY_UNEXPECTED", figure_id)
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
                self.verify_data_execution(
                    transformation.get("execution_receipt"), script, source_paths, final_path, figure_id
                )

            elif route == "SVG_FALLBACK":
                if self.image_generation_available is None:
                    self.error("IMAGE_CAPABILITY_UNKNOWN", f"{figure_id}: 未完成图片工具检查，不能声明SVG降级")
                fallback = self.resolve_file(figure.get("fallback_file"), "fallback_file", figure_id)
                if fallback and fallback.suffix.lower() != ".svg":
                    self.error("FALLBACK_NOT_SVG", figure_id)
                elif fallback:
                    self.verify_svg(fallback, figure_id)
                if not figure.get("capability_gap"):
                    self.error("CAPABILITY_GAP_MISSING", figure_id)
                mode = figure.get("svg_layout_mode")
                if mode not in {"NATIVE", "COMPILED"}:
                    self.error("SVG_LAYOUT_MODE_INVALID", figure_id)
                elif mode == "COMPILED":
                    self.verify_compiled_svg_layout(figure.get("svg_layout"), fallback, figure_id)

            elif route in {"DOMAIN_TOOL", "EVIDENCE_FILE"}:
                if not source_paths:
                    self.error("SOURCE_FILE_MISSING", figure_id)
                if not transformation.get("method"):
                    self.error("METHOD_MISSING", figure_id)
        return manifest

    def verify_compiled_svg_layout(
        self, layout: Any, fallback: Optional[Path], figure_id: str
    ) -> None:
        if not isinstance(layout, dict):
            self.error("SVG_LAYOUT_MISSING", figure_id)
            return
        spec = self.resolve_file(layout.get("spec_file"), "svg_layout.spec_file", figure_id)
        report = self.resolve_file(layout.get("report_file"), "svg_layout.report_file", figure_id)
        for field, path in [("spec_sha256", spec), ("report_sha256", report)]:
            if path and layout.get(field, "").lower() != self.sha256(path):
                self.error("SVG_LAYOUT_HASH_MISMATCH", f"{figure_id}.{field}")
        renderer = Path(__file__).with_name("render_svg_layout.mjs")
        if not renderer.is_file():
            self.error("SVG_LAYOUT_RENDERER_MISSING", figure_id)
        elif layout.get("renderer_sha256", "").lower() != self.sha256(renderer):
            self.error("SVG_LAYOUT_RENDERER_HASH_MISMATCH", figure_id)
        if not isinstance(layout.get("renderer"), str) or not layout.get("renderer", "").strip():
            self.error("SVG_LAYOUT_RENDERER_ID_MISSING", figure_id)
        if report:
            try:
                payload = json.loads(report.read_text(encoding="utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                self.error("SVG_LAYOUT_REPORT_INVALID", f"{figure_id}: {exc}")
                return
            if payload.get("status") != "PASS":
                self.error("SVG_LAYOUT_REPORT_FAIL", figure_id)
            if fallback and payload.get("output_sha256", "").lower() != self.sha256(fallback):
                self.error("SVG_LAYOUT_OUTPUT_MISMATCH", figure_id)
            if spec and payload.get("input_sha256", "").lower() != self.sha256(spec):
                self.error("SVG_LAYOUT_INPUT_MISMATCH", figure_id)

    def verify_generation_receipt(
        self, receipt: Any, prompt: Optional[Path], generated: Optional[Path], figure_id: str
    ) -> None:
        """核对图片工具回执与Prompt、原始生成文件之间的防篡改摘要。"""
        if not isinstance(receipt, dict):
            self.error("GENERATION_RECEIPT_MISSING", figure_id)
            return
        level = receipt.get("evidence_level")
        if level not in RECEIPT_LEVELS:
            self.error("GENERATION_RECEIPT_LEVEL", figure_id)
        elif level == "DECLARED_ONLY":
            self.error("GENERATION_RECEIPT_UNVERIFIED", figure_id)

        for field in ["tool", "provider", "model", "invoked_at", "call_id"]:
            value = receipt.get(field)
            if not isinstance(value, str) or not value.strip():
                self.error("GENERATION_RECEIPT_FIELD", f"{figure_id}.{field}")
        invoked_at = receipt.get("invoked_at")
        if isinstance(invoked_at, str) and invoked_at.strip():
            try:
                datetime.fromisoformat(invoked_at.replace("Z", "+00:00"))
            except ValueError:
                self.error("GENERATION_RECEIPT_TIME", figure_id)
        if level == "NATIVE_TOOL_RESULT" and receipt.get("call_id") == "NOT_EXPOSED":
            self.error("GENERATION_CALL_ID_MISSING", figure_id)

        receipt_file = self.resolve_file(receipt.get("receipt_file"), "generation_receipt.receipt_file", figure_id)
        if receipt_file:
            declared = receipt.get("receipt_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(receipt_file):
                self.error("GENERATION_RECEIPT_HASH_MISMATCH", figure_id)
        if prompt:
            declared = receipt.get("prompt_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(prompt):
                self.error("GENERATION_PROMPT_HASH_MISMATCH", figure_id)
        if generated:
            declared = receipt.get("generated_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(generated):
                self.error("GENERATION_FILE_HASH_MISMATCH", figure_id)

    def verify_vlm_receipt(
        self, vlm: Any, final_path: Optional[Path], figure_id: str,
        language_contract: Dict[str, Any], text_render_strategy: Any,
    ) -> None:
        if not isinstance(vlm, dict) or vlm.get("status") not in VLM_STATUSES:
            self.error("VLM_STATUS_INVALID", figure_id)
            return
        status = vlm.get("status")
        if not isinstance(vlm.get("remaining_issues"), list):
            self.error("VLM_ISSUES_INVALID", figure_id)
        if status == "NEEDS_REVIEW":
            self.error("VLM_NEEDS_REVIEW", figure_id)
        if status == "PASS" and vlm.get("remaining_issues"):
            self.error("VLM_PASS_WITH_ISSUES", figure_id)
        vlm_skipped = status == "SKIPPED"
        if vlm_skipped:
            self.visual_status = "PARTIAL"
            if not isinstance(vlm.get("reason"), str) or not vlm.get("reason", "").strip():
                self.error("VLM_SKIP_REASON_MISSING", figure_id)

        language_check = vlm.get("language_check")
        if not isinstance(language_check, dict):
            self.error("LANGUAGE_CHECK_MISSING", figure_id)
        else:
            language_status = language_check.get("status")
            if language_status not in LANGUAGE_CHECK_STATUSES:
                self.error("LANGUAGE_CHECK_STATUS", figure_id)
            elif language_status == "NEEDS_REVIEW":
                self.error("LANGUAGE_CHECK_NEEDS_REVIEW", figure_id)
            elif language_status == "PASS_WITH_NOTES":
                self.visual_status = "PARTIAL"
            elif language_status == "SKIPPED":
                self.visual_status = "PARTIAL"
                if not isinstance(language_check.get("reason"), str) or not language_check.get("reason", "").strip():
                    self.error("LANGUAGE_CHECK_SKIP_REASON", figure_id)
            target_language = language_check.get("target_language")
            if target_language != language_contract.get("label_language"):
                self.error("LANGUAGE_CHECK_TARGET_MISMATCH", figure_id)
            observed_language = language_check.get("observed_language")
            if not isinstance(observed_language, str) or not observed_language.strip():
                self.error("LANGUAGE_CHECK_OBSERVED_MISSING", figure_id)
            elif (
                language_status != "SKIPPED"
                and
                isinstance(target_language, str) and target_language.lower().startswith("zh")
                and text_render_strategy != "NO_CANVAS_TEXT"
                and not observed_language.lower().startswith("zh")
            ):
                self.error("LANGUAGE_CHECK_OBSERVED_MISMATCH", f"{figure_id}: {observed_language}")
            unintended = language_check.get("unintended_foreign_text")
            if not isinstance(unintended, list) or any(not isinstance(item, str) for item in unintended):
                self.error("LANGUAGE_CHECK_FOREIGN_TEXT_INVALID", figure_id)
            elif unintended:
                self.error("LANGUAGE_CHECK_FOREIGN_TEXT", f"{figure_id}: {unintended}")
            if language_check.get("allowed_foreign_tokens_verified") is not True:
                self.error("LANGUAGE_CHECK_TOKEN_VERIFICATION", figure_id)
            exact_labels = language_contract.get("exact_labels")
            if isinstance(exact_labels, list) and exact_labels and language_check.get("exact_labels_verified") is not True:
                self.error("LANGUAGE_CHECK_EXACT_LABELS", figure_id)

        if vlm_skipped:
            return

        level = vlm.get("evidence_level")
        if level not in VLM_EVIDENCE_LEVELS:
            self.error("VLM_EVIDENCE_LEVEL", figure_id)
        elif level == "DECLARED_ONLY":
            self.error("VLM_RECEIPT_UNVERIFIED", figure_id)
        for field in ["tool", "checked_at"]:
            value = vlm.get(field)
            if not isinstance(value, str) or not value.strip():
                self.error("VLM_RECEIPT_FIELD", f"{figure_id}.{field}")
        checked_at = vlm.get("checked_at")
        if isinstance(checked_at, str) and checked_at.strip():
            try:
                datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
            except ValueError:
                self.error("VLM_RECEIPT_TIME", figure_id)
        receipt_file = self.resolve_file(vlm.get("receipt_file"), "vlm_verification.receipt_file", figure_id)
        if receipt_file:
            declared = vlm.get("receipt_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(receipt_file):
                self.error("VLM_RECEIPT_HASH_MISMATCH", figure_id)
        if final_path:
            declared = vlm.get("checked_file_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(final_path):
                self.error("VLM_CHECKED_FILE_MISMATCH", figure_id)

    def verify_text_overlay(
        self, overlay: Any, generated: Optional[Path], final_path: Optional[Path], figure_id: str
    ) -> None:
        if not isinstance(overlay, dict):
            self.error("TEXT_OVERLAY_MISSING", figure_id)
            return
        source = self.resolve_file(overlay.get("source_file"), "text_overlay.source_file", figure_id)
        receipt = self.resolve_file(overlay.get("receipt_file"), "text_overlay.receipt_file", figure_id)
        for field, path in [("source_sha256", source), ("receipt_sha256", receipt)]:
            if path and overlay.get(field, "").lower() != self.sha256(path):
                self.error("TEXT_OVERLAY_HASH_MISMATCH", f"{figure_id}.{field}")
        if generated and overlay.get("base_generated_sha256", "").lower() != self.sha256(generated):
            self.error("TEXT_OVERLAY_BASE_MISMATCH", figure_id)
        if final_path and overlay.get("final_sha256", "").lower() != self.sha256(final_path):
            self.error("TEXT_OVERLAY_FINAL_MISMATCH", figure_id)
        if not isinstance(overlay.get("method"), str) or not overlay.get("method", "").strip():
            self.error("TEXT_OVERLAY_METHOD_MISSING", figure_id)

    def verify_data_execution(
        self,
        receipt: Any,
        script: Optional[Path],
        source_paths: List[Path],
        final_path: Optional[Path],
        figure_id: str,
    ) -> None:
        """核对统计图执行记录与源数据、脚本和最终输出摘要。"""
        if not isinstance(receipt, dict):
            self.error("DATA_EXECUTION_RECEIPT_MISSING", figure_id)
            return
        command = receipt.get("command")
        if not isinstance(command, str) or not command.strip():
            self.error("DATA_EXECUTION_COMMAND_MISSING", figure_id)
        receipt_file = self.resolve_file(receipt.get("receipt_file"), "transformation.execution_receipt.receipt_file", figure_id)
        if receipt_file:
            declared = receipt.get("receipt_sha256")
            if not isinstance(declared, str) or declared.lower() != self.sha256(receipt_file):
                self.error("DATA_EXECUTION_RECEIPT_HASH_MISMATCH", figure_id)
        inputs = receipt.get("inputs")
        if not isinstance(inputs, list):
            self.error("DATA_EXECUTION_INPUTS_INVALID", figure_id)
            inputs = []
        declared_inputs = {
            row.get("file"): row.get("sha256")
            for row in inputs if isinstance(row, dict) and isinstance(row.get("file"), str)
        }
        for source_path in source_paths:
            relative = str(source_path.relative_to(self.root))
            if declared_inputs.get(relative, "").lower() != self.sha256(source_path):
                self.error("DATA_EXECUTION_INPUT_MISMATCH", f"{figure_id}: {relative}")
        if script:
            relative_script = str(script.relative_to(self.root))
            if receipt.get("script_sha256", "").lower() != self.sha256(script):
                self.error("DATA_EXECUTION_SCRIPT_MISMATCH", figure_id)
            if isinstance(command, str) and script.name not in command and relative_script not in command:
                self.error("DATA_EXECUTION_COMMAND_SCRIPT_MISSING", figure_id)
        if final_path and receipt.get("output_sha256", "").lower() != self.sha256(final_path):
            self.error("DATA_EXECUTION_OUTPUT_MISMATCH", figure_id)

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
        self.verify_svg_geometry(root, figure_id)

    @staticmethod
    def _number(value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        match = re.match(r"^\s*(-?\d+(?:\.\d+)?)", value)
        return float(match.group(1)) if match else None

    @staticmethod
    def _segments_cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float], d: tuple[float, float]) -> bool:
        def orient(p: tuple[float, float], q: tuple[float, float], r: tuple[float, float]) -> float:
            return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
        if any(abs(x - y) < 1e-6 and abs(u - v) < 1e-6 for (x, u) in (a, b) for (y, v) in (c, d)):
            return False
        o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
        return o1 * o2 < 0 and o3 * o4 < 0

    @staticmethod
    def _segments_collinear_overlap(
        a: tuple[float, float], b: tuple[float, float],
        c: tuple[float, float], d: tuple[float, float],
    ) -> bool:
        """识别两条共线线段是否共享了非零长度，端点相接不算重叠。"""
        ab = (b[0] - a[0], b[1] - a[1])
        cd = (d[0] - c[0], d[1] - c[1])
        if abs(ab[0]) < 1e-9 and abs(ab[1]) < 1e-9:
            return False
        if abs(cd[0]) < 1e-9 and abs(cd[1]) < 1e-9:
            return False

        def cross(left: tuple[float, float], right: tuple[float, float]) -> float:
            return left[0] * right[1] - left[1] * right[0]

        if abs(cross(ab, (c[0] - a[0], c[1] - a[1]))) > 1e-6:
            return False
        if abs(cross(ab, (d[0] - a[0], d[1] - a[1]))) > 1e-6:
            return False

        axis = 0 if abs(ab[0]) >= abs(ab[1]) else 1
        first = sorted((a[axis], b[axis]))
        second = sorted((c[axis], d[axis]))
        overlap = min(first[1], second[1]) - max(first[0], second[0])
        return overlap > 1e-6

    def verify_svg_geometry(self, root: ET.Element, figure_id: str) -> None:
        segments: List[
            tuple[tuple[float, float], tuple[float, float], int, str]
        ] = []
        rectangles: List[tuple[float, float, float, float]] = []
        has_unchecked_paths = False
        for owner, element in enumerate(root.iter()):
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "line":
                coords = [self._number(element.get(name)) for name in ("x1", "y1", "x2", "y2")]
                if all(value is not None for value in coords):
                    x1, y1, x2, y2 = (float(value) for value in coords)
                    segments.append(((x1, y1), (x2, y2), owner, tag))
            elif tag in {"polyline", "polygon"}:
                values = [self._number(token) for token in re.split(r"[ ,]+", element.get("points", "").strip())]
                clean = [value for value in values if value is not None]
                points = [(float(clean[i]), float(clean[i + 1])) for i in range(0, len(clean) - 1, 2)]
                segments.extend((start, end, owner, tag) for start, end in zip(points, points[1:]))
            elif tag == "rect":
                values = [self._number(element.get(name)) for name in ("x", "y", "width", "height")]
                if all(value is not None for value in values):
                    x, y, width, height = (float(value) for value in values)
                    rectangles.append((x, y, x + width, y + height))
            elif tag == "path" and element.get("d"):
                has_unchecked_paths = True

        crossing_reported = False
        overlap_reported = False
        for index, (start, end, owner, tag) in enumerate(segments):
            for other_start, other_end, other_owner, other_tag in segments[index + 1:]:
                if self._segments_cross(start, end, other_start, other_end):
                    if not crossing_reported:
                        self.error("SVG_LINE_CROSSING", figure_id)
                        crossing_reported = True
                if (
                    owner != other_owner
                    and tag in {"line", "polyline"}
                    and other_tag in {"line", "polyline"}
                    and self._segments_collinear_overlap(start, end, other_start, other_end)
                    and not overlap_reported
                ):
                    self.error(
                        "SVG_LINE_COLLINEAR_OVERLAP",
                        f"{figure_id}: {start}->{end} 与 {other_start}->{other_end}",
                    )
                    overlap_reported = True
            for left, top, right, bottom in rectangles:
                endpoint_inside = any(left <= p[0] <= right and top <= p[1] <= bottom for p in (start, end))
                if endpoint_inside:
                    continue
                edges = [
                    ((left, top), (right, top)), ((right, top), (right, bottom)),
                    ((right, bottom), (left, bottom)), ((left, bottom), (left, top)),
                ]
                intersections = sum(self._segments_cross(start, end, edge_start, edge_end) for edge_start, edge_end in edges)
                if intersections >= 2:
                    self.error("SVG_LINE_THROUGH_NODE", figure_id)
                    break
        if has_unchecked_paths:
            self.warning("SVG_GEOMETRY_PARTIAL", f"{figure_id}: 贝塞尔path仍需VLM检查")

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

    def verify_manifest_summary(self, summary: Path) -> None:
        if not summary.is_file():
            self.error("MANIFEST_SUMMARY_MISSING", str(summary))
            return
        text = summary.read_text(encoding="utf-8", errors="replace")
        for figure_id, final_path in self.final_files.items():
            relative = str(final_path.relative_to(self.root))
            id_count = len(re.findall(rf"\|\s*{re.escape(figure_id)}\s*\|", text))
            if id_count != 1:
                self.error("MANIFEST_SUMMARY_ID", f"{figure_id}作为表格字段出现{id_count}次")
            if text.count(relative) != 1:
                self.error("MANIFEST_SUMMARY_ROUTE", f"{relative}出现{text.count(relative)}次")

    def verify_docx(self, docx: Path) -> None:
        if not docx.is_file() or not zipfile.is_zipfile(docx):
            self.error("DOCX_INVALID", str(docx))
            return
        with zipfile.ZipFile(docx) as archive:
            names = set(archive.namelist())
            media_hashes = {
                hashlib.sha256(archive.read(name)).hexdigest()
                for name in archive.namelist()
                if name.startswith("word/media/") and not name.endswith("/")
            }
            if "word/document.xml" not in names:
                self.error("DOCX_DOCUMENT_XML_MISSING", str(docx))
                return
            try:
                document_root = ET.fromstring(archive.read("word/document.xml"))
            except ET.ParseError as exc:
                self.error("DOCX_DOCUMENT_XML_INVALID", str(exc))
                return
            paragraphs: List[tuple[str, str]] = []
            for paragraph in document_root.findall(".//w:p", WORD_NS):
                text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
                style_node = paragraph.find("./w:pPr/w:pStyle", WORD_NS)
                style = style_node.get(f"{{{WORD_NS['w']}}}val", "") if style_node is not None else ""
                paragraphs.append((style, text))

            style_counts = {
                level: sum(1 for style, _ in paragraphs if style.lower() == f"heading{level}")
                for level in (1, 2, 3)
            }
            if style_counts[1] == 0:
                self.error("DOCX_HEADING1_MISSING", str(docx))
            if style_counts[2] == 0:
                self.error("DOCX_HEADING2_MISSING", str(docx))
            if style_counts[3] == 0:
                self.warning("DOCX_HEADING3_NOT_USED", str(docx))

            field_text = " ".join(
                node.text or "" for node in document_root.findall(".//w:instrText", WORD_NS)
            )
            field_text += " " + " ".join(
                node.get(f"{{{WORD_NS['w']}}}instr", "")
                for node in document_root.findall(".//w:fldSimple", WORD_NS)
            )
            if not re.search(r"\bTOC\b", field_text, re.IGNORECASE):
                self.error("DOCX_TOC_FIELD_MISSING", str(docx))

            caption_counts: Dict[str, int] = {}
            for _, text in paragraphs:
                match = re.match(r"^\s*图\s*([0-9]+(?:\s*[-－—.]\s*[0-9]+)*)\b", text)
                if match:
                    number = re.sub(r"\s+", "", match.group(1)).replace("－", "-").replace("—", "-").replace(".", "-")
                    caption_counts[number] = caption_counts.get(number, 0) + 1
            for figure_id in self.final_files:
                number = self.figure_numbers.get(figure_id, "")
                count = caption_counts.get(number, 0)
                if count == 0:
                    self.error("DOCX_FIGURE_CAPTION_MISSING", figure_id)
                elif count > 1:
                    self.error("DOCX_FIGURE_CAPTION_DUPLICATE", f"{figure_id}: {count}")
        for figure_id, path in self.final_files.items():
            if self.sha256(path) not in media_hashes:
                self.error("DOCX_MEDIA_MISMATCH", figure_id)

    def verify_pdf(self, pdf: Path) -> None:
        if not pdf.is_file() or pdf.stat().st_size < 8:
            self.error("PDF_INVALID", str(pdf))
            return
        if not pdf.read_bytes()[:5] == b"%PDF-":
            self.error("PDF_HEADER_INVALID", str(pdf))
            return
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf))
            if len(reader.pages) == 0:
                self.error("PDF_NO_PAGES", str(pdf))
                return
            blank_pages = []
            image_objects = 0
            for index, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                resources = page.get("/Resources") or {}
                xobjects = resources.get("/XObject") if hasattr(resources, "get") else None
                page_images = 0
                if xobjects:
                    try:
                        for obj in xobjects.get_object().values():
                            resolved = obj.get_object()
                            if resolved.get("/Subtype") == "/Image":
                                page_images += 1
                    except Exception:
                        self.warning("PDF_IMAGE_SCAN_PARTIAL", f"第{index}页")
                image_objects += page_images
                if not text and page_images == 0:
                    blank_pages.append(index)
            if blank_pages:
                self.warning("PDF_POSSIBLE_BLANK_PAGES", ",".join(map(str, blank_pages)))
            if self.final_files and image_objects < len(self.final_files):
                self.warning("PDF_IMAGE_COUNT_LOW", f"检测到{image_objects}个图像对象，Manifest有{len(self.final_files)}张图")
        except ImportError:
            self.warning("PDF_DEEP_CHECK_SKIPPED", "当前Python缺少pypdf")
        except Exception as exc:
            self.error("PDF_PARSE_FAILED", str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验AIWritePaper图表包的机械一致性")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=Path("figures/figure-manifest.json"))
    parser.add_argument("--capability-report", type=Path, default=Path("00-capability-report.json"))
    parser.add_argument("--markdown", type=Path, default=Path("07-paper-full.md"))
    parser.add_argument("--manifest-summary", type=Path, default=Path("figures/figure-manifest.md"))
    parser.add_argument("--run-manifest", type=Path, default=Path("run-manifest.json"))
    parser.add_argument("--docx", type=Path, default=None)
    parser.add_argument("--pdf", type=Path, default=None)
    parser.add_argument("--preflight-svg", type=Path, default=None, help="只预检单个SVG的字体、远程资源与可解析几何")
    parser.add_argument("--skip-documents", action="store_true", help="FIGURES_ONLY且没有文档交付时使用")
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    verifier = FigureVerifier(root)
    if args.preflight_svg is not None:
        svg = args.preflight_svg if args.preflight_svg.is_absolute() else root / args.preflight_svg
        if not svg.is_file():
            verifier.error("SVG_FILE_MISSING", str(svg))
        else:
            verifier.verify_svg(svg, svg.stem)
        payload = {
            "status": "SVG_PREFLIGHT_OK" if not verifier.errors else "SVG_PREFLIGHT_FAIL",
            "errors": verifier.errors,
            "warnings": verifier.warnings,
            "scope_note": "预检只覆盖可解析直线、折线、矩形、CJK字体声明与远程资源；文字视觉边界仍需查看最终PNG",
        }
        rendered = json.dumps(payload, ensure_ascii=False, indent=2)
        print(rendered)
        if args.report:
            report = args.report if args.report.is_absolute() else root / args.report
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(rendered + "\n", encoding="utf-8")
        return 0 if not verifier.errors else 1
    capability_report = args.capability_report if args.capability_report.is_absolute() else root / args.capability_report
    verifier.verify_capability_report(capability_report)
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    figure_payload = verifier.verify_manifest(manifest)
    summary = args.manifest_summary if args.manifest_summary.is_absolute() else root / args.manifest_summary
    verifier.verify_manifest_summary(summary)
    markdown = args.markdown if args.markdown.is_absolute() else root / args.markdown
    verifier.verify_markdown(markdown)
    docx_value = args.docx
    pdf_value = args.pdf
    run_manifest_path = args.run_manifest if args.run_manifest.is_absolute() else root / args.run_manifest
    run_payload: Dict[str, Any] = {}
    if not args.skip_documents and (docx_value is None or pdf_value is None):
        try:
            run_payload = json.loads(run_manifest_path.read_text(encoding="utf-8"))
            if docx_value is None and isinstance(run_payload.get("docx"), str):
                docx_value = Path(run_payload["docx"])
            if pdf_value is None and isinstance(run_payload.get("pdf"), str):
                pdf_value = Path(run_payload["pdf"])
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            verifier.error("RUN_MANIFEST_INVALID", str(exc))
    elif run_manifest_path.is_file():
        try:
            run_payload = json.loads(run_manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            verifier.error("RUN_MANIFEST_INVALID", str(exc))
    direction_inputs = verifier.verify_direction_contracts(run_payload.get("direction_id"), figure_payload)
    if not args.skip_documents:
        if docx_value is None:
            verifier.error("DOCX_PATH_MISSING", "run-manifest.json未记录docx")
        else:
            verifier.verify_docx(docx_value if docx_value.is_absolute() else root / docx_value)
        if pdf_value is None:
            verifier.error("PDF_PATH_MISSING", "run-manifest.json未记录pdf")
        else:
            verifier.verify_pdf(pdf_value if pdf_value.is_absolute() else root / pdf_value)

    input_paths = [capability_report, manifest, summary, markdown, run_manifest_path, *direction_inputs]
    if docx_value is not None:
        input_paths.append(docx_value if docx_value.is_absolute() else root / docx_value)
    if pdf_value is not None:
        input_paths.append(pdf_value if pdf_value.is_absolute() else root / pdf_value)
    input_sha256: Dict[str, str] = {}
    for path in input_paths:
        if path.is_file():
            try:
                input_sha256[str(path.resolve().relative_to(root))] = verifier.sha256(path)
            except ValueError:
                pass
    payload = {
        "schema_version": "1.0",
        "status": "STRUCTURE_OK" if not verifier.errors else "STRUCTURE_FAIL",
        "mechanical_status": "PASS" if not verifier.errors else "FAIL",
        "visual_status": verifier.visual_status if not verifier.errors else "FAIL",
        "figures_checked": len(verifier.final_files),
        "errors": verifier.errors,
        "warnings": verifier.warnings,
        "input_sha256": input_sha256,
        "verifier": {
            "name": Path(__file__).name, "version": "2.1.0-rc.2",
            "sha256": verifier.sha256(Path(__file__).resolve()),
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
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
