#!/usr/bin/env python3
"""机械校验图表Manifest、文件、哈希与文档嵌入路由，不判断学术正确性。"""

from __future__ import annotations

import argparse
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
FINAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
CJK_FONTS = ["Noto Sans CJK", "Source Han Sans", "PingFang SC", "Microsoft YaHei", "WenQuanYi", "SimHei"]
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
REQUIRED_FIELDS = {
    "figure_id", "display_number", "title", "figure_type", "imagegen_eligible", "route_exemption",
    "claim_bearing", "generation_route",
    "data_status", "prompt_file", "generated_file", "fallback_file", "source_data",
    "transformation", "caption_claim", "supported_manuscript_claims", "limitations",
    "canvas_contains_figure_number_or_caption", "final_embed_file", "generation_receipt",
    "svg_layout_mode", "svg_layout", "vlm_verification",
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
        if not isinstance(report, dict) or report.get("schema_version") != "1.0":
            self.error("CAPABILITY_SCHEMA_VERSION", "当前仅接受schema_version=1.0")
            return report if isinstance(report, dict) else {}
        adapter = report.get("agent_adapter")
        if not isinstance(adapter, str) or not adapter.strip():
            self.error("CAPABILITY_ADAPTER_MISSING", "agent_adapter")
        image_generation = report.get("image_generation")
        if not isinstance(image_generation, dict) or not isinstance(image_generation.get("available"), bool):
            self.error("CAPABILITY_IMAGE_INVALID", "image_generation.available必须为布尔值")
            return report
        self.image_generation_available = image_generation["available"]
        callers = image_generation.get("callers")
        tools = image_generation.get("tools")
        evidence = image_generation.get("evidence")
        if not isinstance(callers, list) or not isinstance(tools, list) or not isinstance(evidence, str) or not evidence.strip():
            self.error("CAPABILITY_IMAGE_EVIDENCE", "callers、tools或evidence无效")
        if self.image_generation_available and (not callers or not tools):
            self.error("CAPABILITY_IMAGE_TOOLS_MISSING", "图片能力可用时必须记录调用层和工具")
        return report

    def verify_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            self.error("MANIFEST_INVALID", str(exc))
            return {}
        if not isinstance(manifest, dict) or not isinstance(manifest.get("figures"), list):
            self.error("MANIFEST_SHAPE", "根对象必须包含figures数组")
            return manifest if isinstance(manifest, dict) else {}
        if manifest.get("schema_version") != "1.3":
            self.error("SCHEMA_VERSION", "当前仅接受schema_version=1.3")

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
            imagegen_eligible = figure.get("imagegen_eligible")
            if not isinstance(imagegen_eligible, bool):
                self.error("IMAGEGEN_ELIGIBLE_INVALID", figure_id)
            exemption = figure.get("route_exemption")
            if exemption not in ROUTE_EXEMPTIONS:
                self.error("ROUTE_EXEMPTION_INVALID", f"{figure_id}: {exemption}")
            if imagegen_eligible is True and self.image_generation_available is True and route != "IMAGE_GENERATION":
                if exemption not in {"USER_REQUESTED_VECTOR", "PUBLICATION_RESTRICTION"}:
                    self.error("IMAGEGEN_BYPASSED", f"{figure_id}: 图片工具可用但路线为{route}")
            if exemption == "IMAGE_TOOL_UNAVAILABLE" and self.image_generation_available is True:
                self.error("FALSE_IMAGE_TOOL_GAP", figure_id)
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
            self.verify_vlm_receipt(vlm, final_path, figure_id)

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

    def verify_vlm_receipt(self, vlm: Any, final_path: Optional[Path], figure_id: str) -> None:
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
        if status == "SKIPPED":
            if not isinstance(vlm.get("reason"), str) or not vlm.get("reason", "").strip():
                self.error("VLM_SKIP_REASON_MISSING", figure_id)
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

    def verify_svg_geometry(self, root: ET.Element, figure_id: str) -> None:
        segments: List[tuple[tuple[float, float], tuple[float, float]]] = []
        rectangles: List[tuple[float, float, float, float]] = []
        has_unchecked_paths = False
        for element in root.iter():
            tag = element.tag.rsplit("}", 1)[-1]
            if tag == "line":
                coords = [self._number(element.get(name)) for name in ("x1", "y1", "x2", "y2")]
                if all(value is not None for value in coords):
                    x1, y1, x2, y2 = (float(value) for value in coords)
                    segments.append(((x1, y1), (x2, y2)))
            elif tag in {"polyline", "polygon"}:
                values = [self._number(token) for token in re.split(r"[ ,]+", element.get("points", "").strip())]
                clean = [value for value in values if value is not None]
                points = [(float(clean[i]), float(clean[i + 1])) for i in range(0, len(clean) - 1, 2)]
                segments.extend(zip(points, points[1:]))
            elif tag == "rect":
                values = [self._number(element.get(name)) for name in ("x", "y", "width", "height")]
                if all(value is not None for value in values):
                    x, y, width, height = (float(value) for value in values)
                    rectangles.append((x, y, x + width, y + height))
            elif tag == "path" and element.get("d"):
                has_unchecked_paths = True

        for index, (start, end) in enumerate(segments):
            for other_start, other_end in segments[index + 1:]:
                if self._segments_cross(start, end, other_start, other_end):
                    self.error("SVG_LINE_CROSSING", figure_id)
                    break
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
    parser.add_argument("--skip-documents", action="store_true", help="FIGURES_ONLY且没有文档交付时使用")
    parser.add_argument("--report", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    verifier = FigureVerifier(root)
    capability_report = args.capability_report if args.capability_report.is_absolute() else root / args.capability_report
    verifier.verify_capability_report(capability_report)
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    verifier.verify_manifest(manifest)
    summary = args.manifest_summary if args.manifest_summary.is_absolute() else root / args.manifest_summary
    verifier.verify_manifest_summary(summary)
    markdown = args.markdown if args.markdown.is_absolute() else root / args.markdown
    verifier.verify_markdown(markdown)
    docx_value = args.docx
    pdf_value = args.pdf
    if not args.skip_documents and (docx_value is None or pdf_value is None):
        run_manifest = args.run_manifest if args.run_manifest.is_absolute() else root / args.run_manifest
        try:
            run_payload = json.loads(run_manifest.read_text(encoding="utf-8"))
            if docx_value is None and isinstance(run_payload.get("docx"), str):
                docx_value = Path(run_payload["docx"])
            if pdf_value is None and isinstance(run_payload.get("pdf"), str):
                pdf_value = Path(run_payload["pdf"])
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            verifier.error("RUN_MANIFEST_INVALID", str(exc))
    if not args.skip_documents:
        if docx_value is None:
            verifier.error("DOCX_PATH_MISSING", "run-manifest.json未记录docx")
        else:
            verifier.verify_docx(docx_value if docx_value.is_absolute() else root / docx_value)
        if pdf_value is None:
            verifier.error("PDF_PATH_MISSING", "run-manifest.json未记录pdf")
        else:
            verifier.verify_pdf(pdf_value if pdf_value.is_absolute() else root / pdf_value)

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
