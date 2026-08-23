import test from "node:test";
import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SCRIPT = path.join(ROOT, "scripts", "render_svg_layout.mjs");

function temporaryCase() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "svg-layout-test-"));
}

function runCompiler(spec, options = {}) {
  const directory = temporaryCase();
  const input = path.join(directory, "figure-spec.json");
  const output = path.join(directory, options.outputName ?? "figure.svg");
  const report = path.join(directory, "figure.report.json");
  fs.writeFileSync(input, `${JSON.stringify(spec, null, 2)}\n`, "utf8");
  const result = spawnSync(process.execPath, [SCRIPT, "--input", input, "--output", output, "--report", report], {
    encoding: "utf8",
  });
  const parsedReport = fs.existsSync(report) ? JSON.parse(fs.readFileSync(report, "utf8")) : null;
  return { directory, input, output, report, result, parsedReport, svg: fs.existsSync(output) ? fs.readFileSync(output, "utf8") : "" };
}

function baseSpec(direction = "LR") {
  return {
    version: "1.0",
    figure_id: `figure-${direction.toLowerCase()}`,
    template: "process",
    direction,
    title: "基础流程图",
    nodes: [
      { id: "input", label: "输入", shape: "rect" },
      { id: "model", label: "处理", shape: "rounded" },
      { id: "output", label: "输出", shape: "rect" },
    ],
    edges: [
      { from: "input", to: "model", label: "处理" },
      { from: "model", to: "output" },
    ],
    groups: [],
  };
}

test("有效 LR 图生成自包含 SVG", () => {
  const result = runCompiler(baseSpec("LR"));
  assert.equal(result.result.status, 0, result.result.stderr);
  assert.equal(result.parsedReport.status, "PASS");
  assert.equal(result.parsedReport.direction, "LR");
  assert.ok(result.svg.includes("marker-end=\"url(#arrow)\""));
  assert.ok(result.svg.includes("data-from=\"input\""));
});

test("有效 TB 图生成正交布局", () => {
  const result = runCompiler(baseSpec("TB"));
  assert.equal(result.result.status, 0, result.result.stderr);
  assert.equal(result.parsedReport.status, "PASS");
  assert.equal(result.parsedReport.direction, "TB");
  const input = result.parsedReport.nodes.find((node) => node.id === "input");
  const model = result.parsedReport.nodes.find((node) => node.id === "model");
  assert.ok(model.y > input.y);
  assert.equal(result.parsedReport.edges[0].route, "orthogonal");
});

test("重复 ID 会失败并写出失败报告", () => {
  const spec = baseSpec("LR");
  spec.nodes[1].id = "input";
  const result = runCompiler(spec);
  assert.equal(result.result.status, 1);
  assert.equal(result.parsedReport.status, "FAIL");
  assert.ok(result.parsedReport.errors.some((item) => item.code === "DUPLICATE_ID"));
  assert.equal(fs.existsSync(result.output), false);
});

test("悬空边会失败并指出端点", () => {
  const spec = baseSpec("LR");
  spec.edges[0].to = "missing";
  const result = runCompiler(spec);
  assert.equal(result.result.status, 1);
  assert.ok(result.parsedReport.errors.some((item) => item.code === "DANGLING_EDGE"));
});

test("中文标签会自动按字符换行", () => {
  const spec = baseSpec("LR");
  spec.nodes[0].label = "这是一个用于检查中文自动换行行为的较长节点标签";
  const result = runCompiler(spec);
  assert.equal(result.result.status, 0, result.result.stderr);
  const node = result.parsedReport.nodes.find((item) => item.id === "input");
  assert.ok(node.lines.length > 1);
  assert.ok((result.svg.match(/<tspan /g) ?? []).length >= 4);
});

test("SVG 不包含远程资源并声明 CJK 字体栈", () => {
  const result = runCompiler(baseSpec("LR"));
  assert.equal(result.result.status, 0, result.result.stderr);
  assert.doesNotMatch(result.svg, /(?:href|src)=['"]https?:\/\//iu);
  assert.doesNotMatch(result.svg, /@import\s+url\(/iu);
  assert.doesNotMatch(result.svg, /<image\b/u);
  assert.match(result.svg, /Noto Sans CJK|Source Han Sans|PingFang SC/u);
  assert.match(result.svg, /<rect width="100%" height="100%" fill="#ffffff" \/>/u);
});

test("报告包含哈希、状态和校验结果", () => {
  const result = runCompiler(baseSpec("TB"));
  assert.equal(result.result.status, 0, result.result.stderr);
  const report = result.parsedReport;
  assert.match(report.input_sha256, /^[0-9a-f]{64}$/u);
  assert.match(report.output_sha256, /^[0-9a-f]{64}$/u);
  assert.equal(report.renderer_version, "1.0.0");
  assert.equal(report.checks.node_overlap, true);
  const actualHash = crypto.createHash("sha256").update(result.svg).digest("hex");
  assert.equal(report.output_sha256, actualHash);
  assert.ok(report.counts.nodes >= 3);
});

test("标准输入短横线可作为合法输入值", () => {
  const directory = temporaryCase();
  const output = path.join(directory, "stdin.svg");
  const report = path.join(directory, "stdin.report.json");
  const result = spawnSync(process.execPath, [SCRIPT, "--input", "-", "--output", output, "--report", report], {
    encoding: "utf8",
    input: `${JSON.stringify(baseSpec("LR"))}\n`,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(JSON.parse(fs.readFileSync(report, "utf8")).status, "PASS");
  assert.ok(fs.existsSync(output));
});

test("反馈边不会被路由到画布外", () => {
  const spec = baseSpec("LR");
  spec.edges.push({ from: "output", to: "model", label: "反馈" });
  const result = runCompiler(spec);
  assert.equal(result.result.status, 0, result.result.stderr);
  const { width, height } = result.parsedReport.dimensions;
  for (const edge of result.parsedReport.edges) {
    for (const point of edge.points) {
      assert.ok(point.x >= 0 && point.x <= width, `${edge.id} x越界`);
      assert.ok(point.y >= 0 && point.y <= height, `${edge.id} y越界`);
    }
  }
});
