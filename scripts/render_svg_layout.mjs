#!/usr/bin/env node

/**
 * 无第三方依赖的 figure-spec SVG 布局编译器。
 *
 * 本文件只负责把结构化的节点、边、分组和标签排成可读的 SVG。
 * 它不判断图中内容是否正确，也不访问网络或加载远程资源。
 */

import fs from "node:fs";
import path from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const FONT_STACK =
  "Noto Sans CJK SC, Source Han Sans SC, PingFang SC, Microsoft YaHei, " +
  "WenQuanYi Micro Hei, SimHei, sans-serif";

const DEFAULT_OPTIONS = Object.freeze({
  margin: 36,
  rankGap: 88,
  nodeGap: 32,
  groupPadding: 20,
  groupLabelGap: 8,
  nodePaddingX: 18,
  nodePaddingY: 14,
  minNodeWidth: 108,
  maxNodeWidth: 220,
  minNodeHeight: 58,
  fontSize: 14,
  lineHeight: 20,
  edgeLabelFontSize: 12,
  maxGlobalLabelWidth: 620,
});

const VALID_DIRECTIONS = new Set(["LR", "TB"]);
const VALID_KINDS = new Set(["layered", "process", "hierarchy", "architecture"]);
const VALID_SHAPES = new Set(["rect", "rounded", "ellipse", "circle", "diamond", "hexagon", "pill"]);

class DiagnosticBag {
  constructor(initial = []) {
    this.errors = [];
    this.warnings = [];
    for (const item of initial) this.add(item.level, item.code, item.message, item.details);
  }

  add(level, code, message, details = undefined) {
    const item = { code, message };
    if (details !== undefined) item.details = details;
    if (level === "error") this.errors.push(item);
    else this.warnings.push(item);
    return item;
  }

  error(code, message, details = undefined) {
    return this.add("error", code, message, details);
  }

  warning(code, message, details = undefined) {
    return this.add("warning", code, message, details);
  }
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function asText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => asText(item)).join("\n");
  if (isObject(value)) {
    return asText(value.text ?? value.label ?? value.title ?? value.name, fallback);
  }
  return fallback;
}

function asId(value) {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return "";
}

function cloneObject(value) {
  return isObject(value) ? { ...value } : {};
}

function toRecordArray(value, keyName = "id") {
  if (Array.isArray(value)) return value.map((entry) => cloneObject(entry));
  if (!isObject(value)) return [];
  return Object.entries(value).map(([key, entry]) => {
    if (typeof entry === "string" || typeof entry === "number") {
      return { [keyName]: key, label: String(entry) };
    }
    return { ...cloneObject(entry), [keyName]: cloneObject(entry)[keyName] ?? key };
  });
}

function normaliseDirection(raw, bag) {
  const candidate = asText(raw, "TB").trim().toUpperCase();
  const direction = candidate === "RL" ? "LR" : candidate === "BT" ? "TB" : candidate;
  if (!VALID_DIRECTIONS.has(direction)) {
    bag.error("DIRECTION_INVALID", `布局方向“${candidate || "空"}”无效，只支持 LR 或 TB。`);
    return "TB";
  }
  return direction;
}

function normaliseKind(raw, bag) {
  const candidate = asText(raw, "process").trim().toLowerCase();
  if (!VALID_KINDS.has(candidate)) {
    bag.error(
      "LAYOUT_TYPE_INVALID",
      `布局类型“${candidate || "空"}”无效，只支持 layered、process、hierarchy、architecture。`,
    );
    return "process";
  }
  return candidate;
}

function normaliseShape(raw, bag, id) {
  const candidate = asText(raw, "rect").trim().toLowerCase();
  const aliases = {
    rectangle: "rect",
    box: "rect",
    roundrect: "rounded",
    roundedrect: "rounded",
    lozenge: "diamond",
  };
  const shape = aliases[candidate] ?? candidate;
  if (!VALID_SHAPES.has(shape)) {
    bag.warning("SHAPE_FALLBACK", `节点“${id}”的形状“${candidate}”不支持，已使用矩形。`);
    return "rect";
  }
  return shape;
}

function getLayoutOptions(raw) {
  const source = isObject(raw?.options)
    ? raw.options
    : isObject(raw?.layout) && isObject(raw.layout.options)
      ? raw.layout.options
      : {};
  const options = { ...DEFAULT_OPTIONS };
  const numericKeys = [
    "margin",
    "rankGap",
    "nodeGap",
    "groupPadding",
    "groupLabelGap",
    "nodePaddingX",
    "nodePaddingY",
    "minNodeWidth",
    "maxNodeWidth",
    "minNodeHeight",
    "fontSize",
    "lineHeight",
    "edgeLabelFontSize",
    "maxGlobalLabelWidth",
  ];
  for (const key of numericKeys) {
    const candidate = Number(source[key]);
    if (Number.isFinite(candidate) && candidate > 0) options[key] = candidate;
  }
  if (options.maxNodeWidth < options.minNodeWidth) {
    options.maxNodeWidth = options.minNodeWidth;
  }
  return options;
}

function normaliseLabels(value, bag) {
  const rawLabels = Array.isArray(value)
    ? value
    : typeof value === "string" || typeof value === "number"
      ? [{ text: String(value) }]
      : isObject(value)
        ? Object.entries(value).map(([id, entry]) => ({
            ...cloneObject(entry),
            id: cloneObject(entry).id ?? id,
            text: cloneObject(entry).text ?? cloneObject(entry).label ?? String(entry),
          }))
        : [];
  return rawLabels.map((entry, index) => {
    const item = cloneObject(entry);
    const id = asId(item.id) || `label-${index + 1}`;
    const target = asId(item.target ?? item.for ?? item.node ?? item.group ?? item.edge);
    const text = asText(item.text ?? item.label ?? item.title ?? item.name, id);
    if (!text.trim()) bag.warning("EMPTY_LABEL", `标签“${id}”为空。`);
    return {
      id,
      text,
      target,
      targetType: asText(item.targetType ?? item.target_type, "").toLowerCase(),
      kind: asText(item.kind ?? item.role, "annotation").toLowerCase(),
    };
  });
}

function normaliseSpec(raw) {
  const bag = new DiagnosticBag();
  if (!isObject(raw)) {
    bag.error("SPEC_INVALID", "figure-spec 的根对象必须是 JSON 对象。屋顶级数组或字符串不受支持。".replace("屋顶级", "顶级"));
    return {
      model: { id: "figure", direction: "TB", kind: "process", options: { ...DEFAULT_OPTIONS }, nodes: [], edges: [], groups: [], labels: [] },
      bag,
    };
  }

  const layoutValue = raw.layout;
  const direction = normaliseDirection(
    raw.direction ?? raw.rankdir ?? raw.rankDir ?? raw.orientation ?? (typeof layoutValue === "string" ? layoutValue : layoutValue?.direction),
    bag,
  );
  const kind = normaliseKind(
    raw.kind ?? raw.template ?? raw.layoutType ?? raw.layout_type ?? raw.type ?? (isObject(layoutValue) ? layoutValue.kind ?? layoutValue.type : undefined),
    bag,
  );
  const options = getLayoutOptions(raw);
  const model = {
    id: asId(raw.id ?? raw.figure_id ?? raw.figureId) || "figure",
    version: asText(raw.version, "1.0"),
    title: asText(raw.title ?? raw.name, ""),
    direction,
    kind,
    options,
    nodes: [],
    edges: [],
    groups: [],
    labels: normaliseLabels(raw.labels ?? raw.annotations, bag),
  };

  if (raw.version !== undefined && model.version !== "1.0") {
    bag.error("VERSION_INVALID", `figure-spec version“${model.version}”不受支持，当前只接受 1.0。`);
  }

  const nodeRecords = toRecordArray(raw.nodes, "id");
  const forbiddenCoordinateKeys = new Set(["x", "y", "cx", "cy", "left", "top", "right", "bottom", "position", "positions", "coordinates", "coordinate", "coord", "bbox"]);
  function rejectCoordinates(record, where) {
    for (const key of Object.keys(record)) {
      if (forbiddenCoordinateKeys.has(key)) {
        bag.error("COORDINATE_INPUT_FORBIDDEN", `${where}包含坐标键“${key}”；坐标必须由布局编译器计算。`);
      }
    }
  }
  const nodeIds = new Set();
  const allIds = new Set();
  for (let index = 0; index < nodeRecords.length; index += 1) {
    const source = nodeRecords[index];
    rejectCoordinates(source, `nodes[${index}]`);
    const id = asId(source.id ?? source.node_id ?? source.nodeId);
    if (!id) {
      bag.error("NODE_ID_MISSING", `nodes[${index}] 缺少非空 id。`);
      continue;
    }
    if (nodeIds.has(id) || allIds.has(id)) {
      bag.error("DUPLICATE_ID", `节点 id“${id}”重复，布局无法唯一确定。`);
    }
    nodeIds.add(id);
    allIds.add(id);
    const label = asText(source.label ?? source.text ?? source.title ?? source.name, id);
    const groupValues = source.groups ?? source.group ?? [];
    const groups = Array.isArray(groupValues) ? groupValues.map(asId).filter(Boolean) : [asId(groupValues)].filter(Boolean);
    model.nodes.push({
      id,
      label,
      shape: normaliseShape(source.shape, bag, id),
      style: isObject(source.style) ? { ...source.style } : {},
      groups,
      rankHint: Number.isFinite(Number(source.rank ?? source.layer)) ? Number(source.rank ?? source.layer) : null,
      sourceIndex: index,
    });
  }

  const groupRecords = toRecordArray(raw.groups, "id");
  const groupIds = new Set();
  for (let index = 0; index < groupRecords.length; index += 1) {
    const source = groupRecords[index];
    rejectCoordinates(source, `groups[${index}]`);
    const id = asId(source.id ?? source.group_id ?? source.groupId);
    if (!id) {
      bag.error("GROUP_ID_MISSING", `groups[${index}] 缺少非空 id。`);
      continue;
    }
    if (groupIds.has(id) || allIds.has(id)) {
      bag.error("DUPLICATE_ID", `分组或节点 id“${id}”重复，布局无法唯一确定。`);
    }
    groupIds.add(id);
    allIds.add(id);
    const memberValues = source.nodes ?? source.members ?? source.childrenNodes ?? [];
    const members = Array.isArray(memberValues) ? memberValues.map(asId).filter(Boolean) : [asId(memberValues)].filter(Boolean);
    const childValues = source.groups ?? source.children ?? [];
    const children = Array.isArray(childValues) ? childValues.map(asId).filter(Boolean) : [asId(childValues)].filter(Boolean);
    const parent = asId(source.parent ?? source.parentId ?? source.parent_group);
    model.groups.push({
      id,
      label: asText(source.label ?? source.text ?? source.title ?? source.name, id),
      shape: normaliseShape(source.shape ?? "rounded", bag, id),
      style: isObject(source.style) ? { ...source.style } : {},
      members,
      children,
      parent,
      sourceIndex: index,
    });
  }

  for (const node of model.nodes) {
    for (const groupId of node.groups) {
      const group = model.groups.find((item) => item.id === groupId);
      if (group && !group.members.includes(node.id)) group.members.push(node.id);
      else if (!group) bag.error("GROUP_NODE_MISSING", `节点“${node.id}”引用了不存在的分组“${groupId}”。`);
    }
  }
  for (const group of model.groups) {
    for (const member of group.members) {
      if (!nodeIds.has(member)) bag.error("GROUP_NODE_MISSING", `分组“${group.id}”引用了不存在的节点“${member}”。`);
    }
    for (const child of group.children) {
      if (!groupIds.has(child)) bag.error("GROUP_CHILD_MISSING", `分组“${group.id}”引用了不存在的子分组“${child}”。`);
    }
    if (group.parent && !groupIds.has(group.parent)) {
      bag.error("GROUP_PARENT_MISSING", `分组“${group.id}”引用了不存在的父分组“${group.parent}”。`);
    }
  }
  for (const group of model.groups) {
    if (group.parent) {
      const parent = model.groups.find((item) => item.id === group.parent);
      if (parent && !parent.children.includes(group.id)) parent.children.push(group.id);
    }
  }

  const edgeRecords = toRecordArray(raw.edges, "id");
  const edgeIds = new Set();
  for (let index = 0; index < edgeRecords.length; index += 1) {
    const source = edgeRecords[index];
    rejectCoordinates(source, `edges[${index}]`);
    const id = asId(source.id ?? source.edge_id ?? source.edgeId) || `edge-${index + 1}`;
    if (edgeIds.has(id)) bag.error("DUPLICATE_ID", `边 id“${id}”重复。`);
    edgeIds.add(id);
    const from = asId(source.from ?? source.source ?? source.start ?? source.u);
    const to = asId(source.to ?? source.target ?? source.end ?? source.v);
    if (!from || !to || !nodeIds.has(from) || !nodeIds.has(to)) {
      bag.error(
        "DANGLING_EDGE",
        `边“${id}”的端点无效：${from || "空"} → ${to || "空"}。边必须连接已声明节点。`,
      );
    }
    model.edges.push({
      id,
      from,
      to,
      label: asText(source.label ?? source.text ?? source.name, ""),
      arrow: source.arrow !== false && source.markerEnd !== false,
      style: isObject(source.style) ? { ...source.style } : {},
      sourceIndex: index,
    });
  }
  return { model, bag };
}

function isCjk(codePoint) {
  return (
    (codePoint >= 0x2e80 && codePoint <= 0x2fff) ||
    (codePoint >= 0x3040 && codePoint <= 0x30ff) ||
    (codePoint >= 0x3400 && codePoint <= 0x4dbf) ||
    (codePoint >= 0x4e00 && codePoint <= 0x9fff) ||
    (codePoint >= 0xf900 && codePoint <= 0xfaff) ||
    (codePoint >= 0xac00 && codePoint <= 0xd7af)
  );
}

function estimatedCharWidth(character, fontSize) {
  const codePoint = character.codePointAt(0) ?? 0;
  if (character === "\t") return fontSize * 1.4;
  if (/\s/u.test(character)) return fontSize * 0.35;
  if (isCjk(codePoint) || codePoint >= 0x1f300) return fontSize;
  if (/[A-Z0-9]/u.test(character)) return fontSize * 0.64;
  if (/[a-z]/u.test(character)) return fontSize * 0.56;
  return fontSize * 0.62;
}

function estimateTextWidth(text, fontSize) {
  let width = 0;
  for (const character of Array.from(String(text))) width += estimatedCharWidth(character, fontSize);
  return width;
}

function wrapText(text, maxWidth, fontSize) {
  const safeText = asText(text, "");
  const result = [];
  const explicitLines = safeText.split(/\r?\n/u);
  for (const explicitLine of explicitLines) {
    if (!explicitLine) {
      result.push("");
      continue;
    }
    let current = "";
    let currentWidth = 0;
    for (const character of Array.from(explicitLine)) {
      const characterWidth = estimatedCharWidth(character, fontSize);
      if (current && currentWidth + characterWidth > maxWidth) {
        result.push(current.trimEnd());
        current = "";
        currentWidth = 0;
      }
      current += character;
      currentWidth += characterWidth;
    }
    result.push(current.trimEnd());
  }
  return result.length ? result : [""];
}

function fitText(text, maxWidth, fontSize) {
  const lines = wrapText(text, Math.max(1, maxWidth), fontSize);
  return {
    lines,
    maxLineWidth: Math.max(...lines.map((line) => estimateTextWidth(line, fontSize)), 0),
  };
}

function nodeDimensions(node, options) {
  const availableWidth = Math.max(1, options.maxNodeWidth - options.nodePaddingX * 2);
  const text = fitText(node.label, availableWidth, options.fontSize);
  let width = Math.max(options.minNodeWidth, text.maxLineWidth + options.nodePaddingX * 2);
  width = Math.min(options.maxNodeWidth, width);
  if (Number.isFinite(Number(node.width)) && Number(node.width) > 0) width = Math.max(width, Number(node.width));
  width = Math.max(options.minNodeWidth, width);
  const height = Math.max(options.minNodeHeight, text.lines.length * options.lineHeight + options.nodePaddingY * 2);
  return {
    width,
    height,
    textLines: text.lines,
    maxTextWidth: text.maxLineWidth,
  };
}

function compareNumber(a, b) {
  return a < b ? -1 : a > b ? 1 : 0;
}

function assignRanks(model, nodesById, bag) {
  const ranks = new Map(model.nodes.map((node) => [node.id, 0]));
  const indegree = new Map(model.nodes.map((node) => [node.id, 0]));
  const outgoing = new Map(model.nodes.map((node) => [node.id, []]));
  const validEdges = [];
  for (const edge of model.edges) {
    if (!nodesById.has(edge.from) || !nodesById.has(edge.to)) continue;
    validEdges.push(edge);
    indegree.set(edge.to, (indegree.get(edge.to) ?? 0) + 1);
    outgoing.get(edge.from)?.push(edge);
  }
  for (const node of model.nodes) {
    if (node.rankHint !== null) ranks.set(node.id, Math.max(0, Math.floor(node.rankHint)));
  }
  const queue = model.nodes
    .filter((node) => (indegree.get(node.id) ?? 0) === 0)
    .sort((a, b) => compareNumber(a.sourceIndex, b.sourceIndex));
  const processed = new Set();
  while (queue.length) {
    const node = queue.shift();
    if (!node || processed.has(node.id)) continue;
    processed.add(node.id);
    for (const edge of outgoing.get(node.id) ?? []) {
      const candidate = (ranks.get(node.id) ?? 0) + 1;
      ranks.set(edge.to, Math.max(ranks.get(edge.to) ?? 0, candidate));
      const next = (indegree.get(edge.to) ?? 0) - 1;
      indegree.set(edge.to, next);
      if (next === 0) queue.push(nodesById.get(edge.to));
    }
  }
  if (processed.size !== model.nodes.length && validEdges.length) {
    bag.warning("CYCLE_OR_UNRESOLVED", "图中存在环或无法按拓扑顺序展开的边，已使用稳定回退层级。", {
      unresolved: model.nodes.filter((node) => !processed.has(node.id)).map((node) => node.id),
    });
    let nextRank = Math.max(...ranks.values(), 0) + 1;
    for (const node of model.nodes) {
      if (!processed.has(node.id) && node.rankHint === null) {
        ranks.set(node.id, nextRank);
        nextRank += 1;
      }
    }
  }
  if (!validEdges.length && model.kind === "hierarchy" && model.groups.length) {
    const depth = groupDepths(model.groups, bag);
    for (const node of model.nodes) {
      const containing = model.groups.filter((group) => group.members.includes(node.id));
      if (containing.length) ranks.set(node.id, Math.max(...containing.map((group) => depth.get(group.id) ?? 0)));
    }
  }
  return ranks;
}

function groupDepths(groups, bag) {
  const byId = new Map(groups.map((group) => [group.id, group]));
  const depths = new Map();
  const visiting = new Set();
  function visit(id) {
    if (depths.has(id)) return depths.get(id);
    if (visiting.has(id)) {
      bag.warning("GROUP_CYCLE", `分组“${id}”存在嵌套环，已按顶层分组处理。`);
      return 0;
    }
    visiting.add(id);
    const group = byId.get(id);
    const parent = group?.parent;
    const depth = parent && byId.has(parent) ? visit(parent) + 1 : 0;
    visiting.delete(id);
    depths.set(id, depth);
    return depth;
  }
  for (const group of groups) visit(group.id);
  return depths;
}

function orderRanks(model, ranks) {
  const buckets = new Map();
  for (const node of model.nodes) {
    const rank = ranks.get(node.id) ?? 0;
    if (!buckets.has(rank)) buckets.set(rank, []);
    buckets.get(rank).push(node);
  }
  for (const nodes of buckets.values()) nodes.sort((a, b) => compareNumber(a.sourceIndex, b.sourceIndex));
  const neighbours = (nodeId, rank, incoming) => {
    const values = [];
    for (const edge of model.edges) {
      const endpoint = incoming ? edge.to : edge.from;
      const other = incoming ? edge.from : edge.to;
      if (endpoint === nodeId && (ranks.get(other) ?? 0) !== rank) values.push(other);
    }
    return values;
  };
  const rankValues = [...buckets.keys()].sort(compareNumber);
  for (let pass = 0; pass < 4; pass += 1) {
    const position = new Map();
    for (const [rank, nodes] of buckets) nodes.forEach((node, index) => position.set(node.id, index));
    for (const rank of rankValues) {
      const nodes = buckets.get(rank);
      if (!nodes || nodes.length < 2) continue;
      const scored = nodes.map((node, index) => {
        const adjacent = neighbours(node.id, rank, pass % 2 === 0);
        const score = adjacent.length
          ? adjacent.reduce((sum, id) => sum + (position.get(id) ?? index), 0) / adjacent.length
          : index;
        return { node, index, score };
      });
      scored.sort((a, b) => a.score - b.score || a.index - b.index || a.node.sourceIndex - b.node.sourceIndex);
      buckets.set(rank, scored.map((entry) => entry.node));
      scored.forEach((entry, index) => position.set(entry.node.id, index));
    }
    for (const rank of [...rankValues].reverse()) {
      const nodes = buckets.get(rank);
      if (!nodes || nodes.length < 2) continue;
      const scored = nodes.map((node, index) => {
        const adjacent = neighbours(node.id, rank, pass % 2 !== 0);
        const score = adjacent.length
          ? adjacent.reduce((sum, id) => sum + (position.get(id) ?? index), 0) / adjacent.length
          : index;
        return { node, index, score };
      });
      scored.sort((a, b) => a.score - b.score || a.index - b.index || a.node.sourceIndex - b.node.sourceIndex);
      buckets.set(rank, scored.map((entry) => entry.node));
      scored.forEach((entry, index) => position.set(entry.node.id, index));
    }
  }
  return buckets;
}

function rectOf(x, y, width, height) {
  return { x, y, width, height, right: x + width, bottom: y + height };
}

function placeNodes(model, ranks, buckets, options, globalLabelHeight) {
  const rankValues = [...buckets.keys()].sort(compareNumber);
  const nodes = new Map();
  const rankWidths = new Map();
  const rankHeights = new Map();
  for (const rank of rankValues) {
    const items = buckets.get(rank) ?? [];
    const width = Math.max(...items.map((node) => node.width), 0);
    const height = items.reduce((sum, node, index) => sum + node.height + (index ? options.nodeGap : 0), 0);
    rankWidths.set(rank, width);
    rankHeights.set(rank, height);
  }
  const contentHeight = Math.max(...rankValues.map((rank) => rankHeights.get(rank) ?? 0), 0);
  const rankGap = options.rankGap;
  const originX = options.margin;
  const originY = options.margin + globalLabelHeight;
  let cursorX = originX;
  if (model.direction === "LR") {
    for (const rank of rankValues) {
      const items = buckets.get(rank) ?? [];
      let cursorY = originY + (contentHeight - (rankHeights.get(rank) ?? 0)) / 2;
      for (const node of items) {
        const x = cursorX + ((rankWidths.get(rank) ?? node.width) - node.width) / 2;
        const y = cursorY;
        nodes.set(node.id, { ...node, ...rectOf(x, y, node.width, node.height), rank, textLines: node.textLines });
        cursorY += node.height + options.nodeGap;
      }
      cursorX += (rankWidths.get(rank) ?? 0) + rankGap;
    }
  } else {
    let cursorY = originY;
    const contentWidth = Math.max(...rankValues.map((rank) => {
      const items = buckets.get(rank) ?? [];
      return items.reduce((sum, node, index) => sum + node.width + (index ? options.nodeGap : 0), 0);
    }), 0);
    for (const rank of rankValues) {
      const items = buckets.get(rank) ?? [];
      let cursorXInRank = originX + (contentWidth - (items.reduce((sum, node, index) => sum + node.width + (index ? options.nodeGap : 0), 0))) / 2;
      for (const node of items) {
        const y = cursorY + ((rankHeights.get(rank) ?? node.height) - node.height) / 2;
        nodes.set(node.id, { ...node, ...rectOf(cursorXInRank, y, node.width, node.height), rank, textLines: node.textLines });
        cursorXInRank += node.width + options.nodeGap;
      }
      cursorY += (rankHeights.get(rank) ?? 0) + rankGap;
    }
  }
  return nodes;
}

function boxExtents(boxes) {
  if (!boxes.length) return null;
  return {
    left: Math.min(...boxes.map((box) => box.x)),
    top: Math.min(...boxes.map((box) => box.y)),
    right: Math.max(...boxes.map((box) => box.right)),
    bottom: Math.max(...boxes.map((box) => box.bottom)),
  };
}

function groupBoxes(model, nodeMap, options, bag) {
  const byId = new Map(model.groups.map((group) => [group.id, group]));
  const result = new Map();
  const visiting = new Set();
  function visit(id) {
    if (result.has(id)) return result.get(id);
    const group = byId.get(id);
    if (!group) return null;
    if (visiting.has(id)) {
      bag.warning("GROUP_CYCLE", `分组“${id}”存在嵌套环，已忽略循环子分组。`);
      return null;
    }
    visiting.add(id);
    const memberBoxes = group.members.map((member) => nodeMap.get(member)).filter(Boolean);
    const childBoxes = group.children.map((child) => visit(child)).filter(Boolean);
    const extents = boxExtents([...memberBoxes, ...childBoxes]);
    let box;
    if (extents) {
      const labelFit = fitText(group.label, Math.max(40, extents.right - extents.left), options.fontSize * 0.9);
      const labelWidth = labelFit.maxLineWidth + options.groupPadding * 2;
      const width = Math.max(extents.right - extents.left + options.groupPadding * 2, labelWidth);
      const height = Math.max(
        extents.bottom - extents.top + options.groupPadding * 2,
        labelFit.lines.length * options.lineHeight * 0.9 + options.groupPadding * 2,
      );
      box = {
        ...rectOf(extents.left - options.groupPadding, extents.top - options.groupPadding, width, height),
        id: group.id,
        label: group.label,
        shape: group.shape,
        style: group.style,
        textLines: labelFit.lines,
        depth: group.parent ? 1 : 0,
        members: [...group.members],
        children: [...group.children],
      };
    } else {
      bag.warning("EMPTY_GROUP", `分组“${group.id}”没有可布局的成员，已放置为空分组。`);
      box = {
        ...rectOf(options.margin, options.margin, 180, 76),
        id: group.id,
        label: group.label,
        shape: group.shape,
        style: group.style,
        textLines: wrapText(group.label, 140, options.fontSize * 0.9),
        depth: group.parent ? 1 : 0,
        members: [...group.members],
        children: [...group.children],
      };
    }
    visiting.delete(id);
    result.set(id, box);
    return box;
  }
  for (const group of model.groups) visit(group.id);
  // 子分组如果比父分组更大，重新向外扩展父分组；这样嵌套组仍能完整包围内容。
  for (const group of model.groups) {
    const current = result.get(group.id);
    if (!current) continue;
    const children = group.children.map((child) => result.get(child)).filter(Boolean);
    const extents = boxExtents([current, ...children]);
    if (extents && (extents.left < current.x || extents.top < current.y || extents.right > current.right || extents.bottom > current.bottom)) {
      current.x = extents.left - options.groupPadding;
      current.y = extents.top - options.groupPadding;
      current.right = extents.right + options.groupPadding;
      current.bottom = extents.bottom + options.groupPadding;
      current.width = current.right - current.x;
      current.height = current.bottom - current.y;
    }
  }
  return result;
}

function point(x, y) {
  return { x, y };
}

function simplifyPoints(points) {
  const output = [];
  for (const current of points) {
    const last = output[output.length - 1];
    if (last && Math.abs(last.x - current.x) < 0.001 && Math.abs(last.y - current.y) < 0.001) continue;
    output.push({ x: current.x, y: current.y });
  }
  let changed = true;
  while (changed && output.length > 2) {
    changed = false;
    for (let index = 1; index < output.length - 1; index += 1) {
      const before = output[index - 1];
      const current = output[index];
      const after = output[index + 1];
      const collinear = (Math.abs(before.x - current.x) < 0.001 && Math.abs(current.x - after.x) < 0.001) ||
        (Math.abs(before.y - current.y) < 0.001 && Math.abs(current.y - after.y) < 0.001);
      if (collinear) {
        output.splice(index, 1);
        changed = true;
        break;
      }
    }
  }
  return output;
}

function sideCenter(node, side) {
  if (side === "left") return point(node.x, node.y + node.height / 2);
  if (side === "right") return point(node.right, node.y + node.height / 2);
  if (side === "top") return point(node.x + node.width / 2, node.y);
  return point(node.x + node.width / 2, node.bottom);
}

function routeEdges(model, nodeMap, options) {
  const allNodes = [...nodeMap.values()];
  const minX = Math.min(...allNodes.map((node) => node.x), options.margin);
  const minY = Math.min(...allNodes.map((node) => node.y), options.margin);
  const maxX = Math.max(...allNodes.map((node) => node.right), options.margin);
  const maxY = Math.max(...allNodes.map((node) => node.bottom), options.margin);
  const routes = new Map();
  let laneIndex = 0;
  for (const edge of model.edges) {
    const source = nodeMap.get(edge.from);
    const target = nodeMap.get(edge.to);
    if (!source || !target) continue;
    const forward = model.direction === "LR"
      ? target.x > source.x + 0.5
      : target.y > source.y + 0.5;
    const adjacent = Math.abs((source.rank ?? 0) - (target.rank ?? 0)) === 1;
    let points;
    if (model.direction === "LR" && forward && adjacent) {
      const start = sideCenter(source, "right");
      const end = sideCenter(target, "left");
      const channel = (start.x + end.x) / 2;
      points = [start, point(channel, start.y), point(channel, end.y), end];
    } else if (model.direction === "TB" && forward && adjacent) {
      const start = sideCenter(source, "bottom");
      const end = sideCenter(target, "top");
      const channel = (start.y + end.y) / 2;
      points = [start, point(start.x, channel), point(end.x, channel), end];
    } else if (model.direction === "LR") {
      const lane = maxY + 26 + laneIndex * 14;
      const startSide = forward ? "right" : "left";
      const endSide = forward ? "left" : "right";
      const start = sideCenter(source, startSide);
      const end = sideCenter(target, endSide);
      points = [start, point(start.x, lane), point(end.x, lane), end];
      laneIndex += 1;
    } else {
      const lane = maxX + 26 + laneIndex * 14;
      const startSide = forward ? "bottom" : "top";
      const endSide = forward ? "top" : "bottom";
      const start = sideCenter(source, startSide);
      const end = sideCenter(target, endSide);
      points = [start, point(lane, start.y), point(lane, end.y), end];
      laneIndex += 1;
    }
    routes.set(edge.id, simplifyPoints(points));
  }
  return routes;
}

function routeLength(points) {
  let total = 0;
  for (let index = 1; index < points.length; index += 1) {
    total += Math.hypot(points[index].x - points[index - 1].x, points[index].y - points[index - 1].y);
  }
  return total;
}

function pointAlongRoute(points, fraction = 0.5) {
  const total = routeLength(points);
  if (!total) return points[0] ?? point(0, 0);
  let remaining = total * fraction;
  for (let index = 1; index < points.length; index += 1) {
    const a = points[index - 1];
    const b = points[index];
    const length = Math.hypot(b.x - a.x, b.y - a.y);
    if (remaining <= length) {
      const ratio = length ? remaining / length : 0;
      return point(a.x + (b.x - a.x) * ratio, a.y + (b.y - a.y) * ratio);
    }
    remaining -= length;
  }
  return points[points.length - 1];
}

function buildLayout(model, bag) {
  const options = model.options;
  const nodesById = new Map();
  for (const node of model.nodes) {
    const dimensions = nodeDimensions(node, options);
    const prepared = { ...node, ...dimensions };
    if (!nodesById.has(node.id)) nodesById.set(node.id, prepared);
  }
  const ranks = assignRanks(model, nodesById, bag);
  const buckets = orderRanks(model, ranks);
  for (const [rank, items] of buckets) {
    buckets.set(rank, items.map((node) => nodesById.get(node.id)).filter(Boolean));
  }
  const globalLabels = model.labels.filter((label) => !label.target);
  const globalLabelLines = globalLabels.flatMap((label) => wrapText(label.text, options.maxGlobalLabelWidth, options.fontSize * 1.05));
  const globalLabelHeight = globalLabelLines.length ? globalLabelLines.length * options.lineHeight + 18 : 0;
  const placedNodes = placeNodes(model, ranks, buckets, options, globalLabelHeight);
  const placedGroups = groupBoxes(model, placedNodes, options, bag);
  const routes = routeEdges(model, placedNodes, options);
  const maxX = Math.max(
    options.margin + 180,
    ...[...placedNodes.values(), ...placedGroups.values()].map((box) => box.right + options.margin),
    ...[...routes.values()].flat().map((item) => item.x + options.margin),
  );
  const maxY = Math.max(
    options.margin + globalLabelHeight + 80,
    ...[...placedNodes.values(), ...placedGroups.values()].map((box) => box.bottom + options.margin),
    ...[...routes.values()].flat().map((item) => item.y + options.margin),
  );
  const width = Math.ceil(maxX);
  const height = Math.ceil(maxY);
  const globalLabelLayout = [];
  let globalY = options.margin + options.fontSize;
  for (const label of globalLabels) {
    const fitted = fitText(label.text, options.maxGlobalLabelWidth, options.fontSize * 1.05);
    globalLabelLayout.push({ ...label, ...fitted, x: width / 2, y: globalY });
    globalY += fitted.lines.length * options.lineHeight;
  }
  return {
    direction: model.direction,
    kind: model.kind,
    width,
    height,
    nodes: placedNodes,
    groups: placedGroups,
    edges: routes,
    globalLabels: globalLabelLayout,
    allLabels: model.labels,
  };
}

function xmlEscape(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function attr(value) {
  return xmlEscape(value);
}

function pointsAttribute(points) {
  return points.map((item) => `${item.x.toFixed(2)},${item.y.toFixed(2)}`).join(" ");
}

function pathAttribute(points) {
  if (!points.length) return "";
  return points.map((item, index) => `${index ? "L" : "M"}${item.x.toFixed(2)} ${item.y.toFixed(2)}`).join(" ");
}

function renderText(lines, x, y, options, className = "node-label", fontSize = options.fontSize) {
  const safeLines = lines.length ? lines : [""];
  const lineHeight = options.lineHeight;
  const firstY = y - ((safeLines.length - 1) * lineHeight) / 2;
  const tspan = safeLines.map((line, index) =>
    `<tspan x="${x.toFixed(2)}" dy="${index === 0 ? "0" : lineHeight.toFixed(2)}">${xmlEscape(line)}</tspan>`,
  ).join("");
  return `<text class="${attr(className)}" x="${x.toFixed(2)}" y="${firstY.toFixed(2)}" ` +
    `font-size="${fontSize.toFixed(2)}" text-anchor="middle" dominant-baseline="middle">${tspan}</text>`;
}

function shapeMarkup(box, className, fill, stroke, label = "") {
  const common = `class="${attr(className)}" fill="${attr(fill)}" stroke="${attr(stroke)}"`;
  if (box.shape === "ellipse" || box.shape === "circle") {
    return `<ellipse ${common} cx="${(box.x + box.width / 2).toFixed(2)}" cy="${(box.y + box.height / 2).toFixed(2)}" rx="${(box.width / 2).toFixed(2)}" ry="${(box.height / 2).toFixed(2)}"${label}>`;
  }
  if (box.shape === "diamond") {
    const points = [
      point(box.x + box.width / 2, box.y),
      point(box.right, box.y + box.height / 2),
      point(box.x + box.width / 2, box.bottom),
      point(box.x, box.y + box.height / 2),
    ];
    return `<polygon ${common} points="${pointsAttribute(points)}"${label}>`;
  }
  if (box.shape === "hexagon") {
    const inset = Math.min(18, box.width / 5);
    const points = [
      point(box.x + inset, box.y), point(box.right - inset, box.y), point(box.right, box.y + box.height / 2),
      point(box.right - inset, box.bottom), point(box.x + inset, box.bottom), point(box.x, box.y + box.height / 2),
    ];
    return `<polygon ${common} points="${pointsAttribute(points)}"${label}>`;
  }
  const radius = box.shape === "rounded" ? 12 : box.shape === "pill" ? box.height / 2 : 2;
  return `<rect ${common} x="${box.x.toFixed(2)}" y="${box.y.toFixed(2)}" width="${box.width.toFixed(2)}" height="${box.height.toFixed(2)}" rx="${radius.toFixed(2)}"${label}>`;
}

function safePaint(value, fallback) {
  const candidate = asText(value, fallback).trim();
  if (!candidate || /url\s*\(|https?:\/\//iu.test(candidate)) return fallback;
  return candidate;
}

function renderSvg(model, layout) {
  const options = model.options;
  const chunks = [];
  chunks.push(`<?xml version="1.0" encoding="UTF-8"?>`);
  chunks.push(`<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="${layout.width}" height="${layout.height}" viewBox="0 0 ${layout.width} ${layout.height}" role="img" aria-labelledby="figure-title">`);
  chunks.push(`<title id="figure-title">${xmlEscape(model.title || model.id)}</title>`);
  chunks.push(`<desc>由 figure-spec 自动布局的 ${xmlEscape(model.kind)} 图，方向为 ${xmlEscape(model.direction)}。</desc>`);
  chunks.push(`<defs><style><![CDATA[
    text { font-family: ${FONT_STACK}; }
    .group-box { stroke-width: 1.4; stroke-dasharray: 6 4; }
    .node-box { stroke-width: 1.6; }
    .edge { fill: none; stroke: #475569; stroke-width: 1.8; stroke-linejoin: round; stroke-linecap: round; }
    .edge-label-bg { fill: #ffffff; fill-opacity: .94; stroke: #cbd5e1; stroke-width: 1; }
    .group-label { fill: #334155; font-weight: 600; }
    .node-label { fill: #0f172a; }
    .global-label { fill: #0f172a; font-weight: 700; }
  ]]></style><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#475569" /></marker></defs>`);
  chunks.push(`<rect width="100%" height="100%" fill="#ffffff" />`);
  for (const group of [...layout.groups.values()].sort((a, b) => (a.depth ?? 0) - (b.depth ?? 0))) {
    const markup = shapeMarkup(group, "group-box", safePaint(group.style?.fill, "#f8fafc"), safePaint(group.style?.stroke, "#94a3b8"));
    chunks.push(`<g id="group-${attr(group.id)}" data-id="${attr(group.id)}" data-kind="group">${markup}</${group.shape === "ellipse" || group.shape === "circle" ? "ellipse" : group.shape === "diamond" || group.shape === "hexagon" ? "polygon" : "rect"}>`);
    const labelX = group.x + Math.min(group.width / 2, Math.max(group.width / 2, 0));
    chunks.push(renderText(group.textLines, labelX, group.y + options.groupPadding / 2 + options.fontSize * 0.35, options, "group-label", options.fontSize * 0.9));
    chunks.push(`</g>`);
  }
  const edgeById = new Map(model.edges.map((edge) => [edge.id, edge]));
  for (const edge of model.edges) {
    const points = layout.edges.get(edge.id);
    if (!points?.length) continue;
    const marker = edge.arrow ? ` marker-end="url(#arrow)"` : "";
    const edgeStroke = safePaint(edge.style?.stroke ?? edge.style?.color, "#475569");
    chunks.push(`<path id="edge-${attr(edge.id)}" data-id="${attr(edge.id)}" data-from="${attr(edge.from)}" data-to="${attr(edge.to)}" class="edge" stroke="${attr(edgeStroke)}" d="${attr(pathAttribute(points))}"${marker} />`);
    if (edge.label) {
      const middle = pointAlongRoute(points);
      const fitted = fitText(edge.label, 150, options.edgeLabelFontSize);
      const width = Math.max(24, fitted.maxLineWidth + 12);
      const height = fitted.lines.length * (options.lineHeight * 0.78) + 8;
      const labelBox = rectOf(middle.x - width / 2, middle.y - height / 2, width, height);
      chunks.push(`<g class="edge-label" data-edge="${attr(edge.id)}"><rect class="edge-label-bg" x="${labelBox.x.toFixed(2)}" y="${labelBox.y.toFixed(2)}" width="${labelBox.width.toFixed(2)}" height="${labelBox.height.toFixed(2)}" rx="4" />`);
      chunks.push(renderText(fitted.lines, middle.x, middle.y, { ...options, lineHeight: options.lineHeight * 0.78 }, "edge-label-text", options.edgeLabelFontSize));
      chunks.push(`</g>`);
    }
  }
  for (const node of layout.nodes.values()) {
    const markup = shapeMarkup(node, "node-box", safePaint(node.style?.fill, node.shape === "ellipse" ? "#ecfeff" : "#ffffff"), safePaint(node.style?.stroke, "#0f766e"));
    const closeTag = node.shape === "ellipse" || node.shape === "circle" ? "ellipse" : node.shape === "diamond" || node.shape === "hexagon" ? "polygon" : "rect";
    chunks.push(`<g id="node-${attr(node.id)}" data-id="${attr(node.id)}" data-kind="node" data-rank="${node.rank}">${markup}</${closeTag}>`);
    chunks.push(renderText(node.textLines, node.x + node.width / 2, node.y + node.height / 2, options));
    chunks.push(`</g>`);
  }
  for (const label of layout.globalLabels) {
    chunks.push(`<g id="label-${attr(label.id)}" data-id="${attr(label.id)}" data-kind="label">${renderText(label.lines, label.x, label.y, options, "global-label", options.fontSize * 1.05)}</g>`);
  }
  for (const label of model.labels.filter((item) => item.target)) {
    const targetNode = layout.nodes.get(label.target);
    const targetGroup = layout.groups.get(label.target);
    const targetEdge = edgeById.get(label.target);
    let position;
    if (targetNode) position = point(targetNode.x + targetNode.width / 2, targetNode.y - 10);
    else if (targetGroup) position = point(targetGroup.x + targetGroup.width / 2, targetGroup.y - 8);
    else if (targetEdge && layout.edges.get(targetEdge.id)) position = pointAlongRoute(layout.edges.get(targetEdge.id));
    if (!position) continue;
    const fitted = fitText(label.text, 180, options.fontSize * 0.9);
    chunks.push(`<g id="label-${attr(label.id)}" data-id="${attr(label.id)}" data-target="${attr(label.target)}" data-kind="label">${renderText(fitted.lines, position.x, position.y, options, "annotation-label", options.fontSize * 0.9)}</g>`);
  }
  chunks.push(`</svg>`);
  return chunks.join("\n");
}

function boxesOverlap(a, b, epsilon = 0.01) {
  return a.x < b.right - epsilon && a.right > b.x + epsilon && a.y < b.bottom - epsilon && a.bottom > b.y + epsilon;
}

function segmentIntersectsRectInterior(a, b, box) {
  const epsilon = 0.01;
  const left = box.x + epsilon;
  const right = box.right - epsilon;
  const top = box.y + epsilon;
  const bottom = box.bottom - epsilon;
  if (left >= right || top >= bottom) return false;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  let t0 = 0;
  let t1 = 1;
  const clip = (p, q) => {
    if (Math.abs(p) < 1e-9) return q >= 0;
    const ratio = q / p;
    if (p < 0) {
      if (ratio > t1) return false;
      if (ratio > t0) t0 = ratio;
    } else {
      if (ratio < t0) return false;
      if (ratio < t1) t1 = ratio;
    }
    return true;
  };
  return clip(-dx, a.x - left) && clip(dx, right - a.x) && clip(-dy, a.y - top) && clip(dy, bottom - a.y) && t1 - t0 > 1e-5;
}

function orientation(a, b, c) {
  return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
}

function properSegmentIntersection(a, b, c, d) {
  const o1 = orientation(a, b, c);
  const o2 = orientation(a, b, d);
  const o3 = orientation(c, d, a);
  const o4 = orientation(c, d, b);
  const eps = 1e-7;
  if (Math.abs(o1) < eps || Math.abs(o2) < eps || Math.abs(o3) < eps || Math.abs(o4) < eps) return null;
  if ((o1 > 0) === (o2 > 0) || (o3 > 0) === (o4 > 0)) return null;
  const denominator = (a.x - b.x) * (c.y - d.y) - (a.y - b.y) * (c.x - d.x);
  if (Math.abs(denominator) < eps) return null;
  const determinantAB = a.x * b.y - a.y * b.x;
  const determinantCD = c.x * d.y - c.y * d.x;
  return point(
    (determinantAB * (c.x - d.x) - (a.x - b.x) * determinantCD) / denominator,
    (determinantAB * (c.y - d.y) - (a.y - b.y) * determinantCD) / denominator,
  );
}

function collinearSegmentOverlap(a, b, c, d) {
  const eps = 1e-7;
  const ab = point(b.x - a.x, b.y - a.y);
  const cd = point(d.x - c.x, d.y - c.y);
  if (Math.hypot(ab.x, ab.y) < eps || Math.hypot(cd.x, cd.y) < eps) return false;
  if (Math.abs(orientation(a, b, c)) > eps || Math.abs(orientation(a, b, d)) > eps) return false;
  const axis = Math.abs(ab.x) >= Math.abs(ab.y) ? "x" : "y";
  const first = [a[axis], b[axis]].sort((left, right) => left - right);
  const second = [c[axis], d[axis]].sort((left, right) => left - right);
  return Math.min(first[1], second[1]) - Math.max(first[0], second[0]) > eps;
}

function isNearPoint(a, b, epsilon = 0.05) {
  return Math.hypot(a.x - b.x, a.y - b.y) <= epsilon;
}

function routeSegments(points) {
  const segments = [];
  for (let index = 1; index < points.length; index += 1) segments.push([points[index - 1], points[index]]);
  return segments;
}

function validateLayout(model, layout, bag) {
  const nodes = [...layout.nodes.values()];
  const overlapPairs = [];
  for (let left = 0; left < nodes.length; left += 1) {
    for (let right = left + 1; right < nodes.length; right += 1) {
      if (boxesOverlap(nodes[left], nodes[right])) overlapPairs.push([nodes[left].id, nodes[right].id]);
    }
  }
  if (overlapPairs.length) {
    bag.error("NODE_OVERLAP", `检测到 ${overlapPairs.length} 对节点矩形重叠。`, { pairs: overlapPairs });
  }

  for (const node of nodes) {
    const contentWidth = node.width - model.options.nodePaddingX * 2;
    const contentHeight = node.height - model.options.nodePaddingY * 2;
    const widest = Math.max(...node.textLines.map((line) => estimateTextWidth(line, model.options.fontSize)), 0);
    const textHeight = node.textLines.length * model.options.lineHeight;
    if (widest > contentWidth + 0.5 || textHeight > contentHeight + 0.5) {
      bag.error("TEXT_OVERFLOW", `节点“${node.id}”的文字超出节点边界。`, {
        node: node.id,
        widest,
        contentWidth,
        textHeight,
        contentHeight,
      });
    }
  }

  const edgeSegments = [];
  for (const edge of model.edges) {
    const points = layout.edges.get(edge.id);
    if (!points?.length) continue;
    const segments = routeSegments(points);
    edgeSegments.push({ edge, points, segments });
    for (const node of nodes) {
      if (node.id === edge.from || node.id === edge.to) continue;
      if (segments.some(([a, b]) => segmentIntersectsRectInterior(a, b, node))) {
        bag.error("EDGE_THROUGH_NODE", `边“${edge.id}”穿过了非端点节点“${node.id}”。`, { edge: edge.id, node: node.id });
      }
    }
  }
  const crossings = [];
  const collinearOverlaps = [];
  for (let left = 0; left < edgeSegments.length; left += 1) {
    for (let right = left + 1; right < edgeSegments.length; right += 1) {
      const first = edgeSegments[left];
      const second = edgeSegments[right];
      if (first.edge.id === second.edge.id) continue;
      for (const [a, b] of first.segments) {
        for (const [c, d] of second.segments) {
          if (collinearSegmentOverlap(a, b, c, d)) {
            collinearOverlaps.push({ edges: [first.edge.id, second.edge.id], segments: [[a, b], [c, d]] });
            continue;
          }
          const intersection = properSegmentIntersection(a, b, c, d);
          if (!intersection) continue;
          const sharedEndpoint = [a, b].some((item) => isNearPoint(item, intersection)) && [c, d].some((item) => isNearPoint(item, intersection));
          if (sharedEndpoint) continue;
          crossings.push({ edges: [first.edge.id, second.edge.id], at: intersection });
        }
      }
    }
  }
  if (crossings.length) bag.error("EDGE_CROSSING", `检测到 ${crossings.length} 处可识别的边线段交叉。`, { crossings });
  if (collinearOverlaps.length) {
    bag.error("EDGE_COLLINEAR_OVERLAP", `检测到 ${collinearOverlaps.length} 处不同边共线重叠。`, { overlaps: collinearOverlaps });
  }
  return {
    nodeOverlap: overlapPairs,
    edgeCrossing: crossings,
    edgeCollinearOverlap: collinearOverlaps,
    errors: bag.errors,
    warnings: bag.warnings,
  };
}

function serialiseBox(box) {
  return {
    id: box.id,
    label: box.label,
    shape: box.shape,
    x: round(box.x),
    y: round(box.y),
    width: round(box.width),
    height: round(box.height),
    right: round(box.right),
    bottom: round(box.bottom),
    rank: box.rank,
    lines: [...(box.textLines ?? [])],
  };
}

function round(value) {
  return Math.round(Number(value) * 100) / 100;
}

function sha256(value) {
  return createHash("sha256").update(value).digest("hex");
}

function buildReport(model, layout, diagnostics, validation, inputSha256 = null, outputSha256 = null) {
  const errors = diagnostics.errors;
  const warnings = diagnostics.warnings;
  const checks = {
    duplicate_ids: !errors.some((item) => item.code === "DUPLICATE_ID"),
    dangling_edges: !errors.some((item) => item.code === "DANGLING_EDGE"),
    node_overlap: validation.nodeOverlap.length === 0,
    text_overflow: !errors.some((item) => item.code === "TEXT_OVERFLOW"),
    edge_through_node: !errors.some((item) => item.code === "EDGE_THROUGH_NODE"),
    edge_crossing: validation.edgeCrossing.length === 0,
    edge_collinear_overlap: validation.edgeCollinearOverlap.length === 0,
  };
  return {
    schema_version: "1.0",
    renderer_version: "1.1.0",
    compiler: "render_svg_layout.mjs",
    status: errors.length === 0 ? "PASS" : "FAIL",
    ok: errors.length === 0,
    input_sha256: inputSha256,
    output_sha256: outputSha256,
    version: model.version,
    direction: model.direction,
    layout_type: model.kind,
    figure_id: model.id,
    dimensions: { width: layout.width, height: layout.height, viewBox: `0 0 ${layout.width} ${layout.height}` },
    counts: {
      nodes: model.nodes.length,
      edges: model.edges.length,
      groups: model.groups.length,
      labels: model.labels.length,
    },
    nodes: [...layout.nodes.values()].map(serialiseBox),
    groups: [...layout.groups.values()].map(serialiseBox),
    edges: model.edges.map((edge) => ({
      id: edge.id,
      from: edge.from,
      to: edge.to,
      label: edge.label,
      arrow: edge.arrow,
      route: "orthogonal",
      points: (layout.edges.get(edge.id) ?? []).map((item) => ({ x: round(item.x), y: round(item.y) })),
    })),
    checks,
    validation: checks,
    errors,
    warnings,
    diagnostics: { errors, warnings },
  };
}

function compileFigureSpec(spec, overrides = {}) {
  let raw = spec;
  const inputSerialised = typeof spec === "string" ? spec : JSON.stringify(spec) ?? String(spec);
  const inputSha256 = sha256(inputSerialised);
  if (typeof spec === "string") {
    try {
      raw = JSON.parse(spec);
    } catch (error) {
      const bag = new DiagnosticBag();
      bag.error("SPEC_JSON_INVALID", `figure-spec JSON 无法解析：${error.message}`);
      const emptyModel = { id: "figure", direction: "TB", kind: "process", options: { ...DEFAULT_OPTIONS }, nodes: [], edges: [], groups: [], labels: [] };
      const emptyLayout = { width: 300, height: 200, nodes: new Map(), groups: new Map(), edges: new Map(), globalLabels: [], allLabels: [] };
      return { svg: null, report: buildReport(emptyModel, emptyLayout, bag, { nodeOverlap: [], edgeCrossing: [] }, inputSha256, null), model: emptyModel, layout: emptyLayout };
    }
  }
  const { model, bag } = normaliseSpec(raw);
  if (overrides.direction !== undefined) {
    const directionBag = new DiagnosticBag();
    model.direction = normaliseDirection(overrides.direction, directionBag);
    for (const item of directionBag.errors) bag.error(item.code, item.message, item.details);
  }
  model.options = { ...model.options, ...overrides };
  const layout = buildLayout(model, bag);
  const validation = validateLayout(model, layout, bag);
  const svg = bag.errors.length === 0 ? renderSvg(model, layout) : null;
  const report = buildReport(model, layout, bag, validation, inputSha256, svg ? sha256(svg) : null);
  return { svg, report, model, layout };
}

function cliHelp() {
  return [
    "用法：node scripts/render_svg_layout.mjs --input figure-spec.json --output figure.svg [--report report.json]",
    "",
    "参数：",
    "  -i, --input, --spec   输入 figure-spec JSON 文件；使用 - 表示从标准输入读取。",
    "  -o, --output, --svg   输出自包含 SVG 文件。",
    "  -r, --report          输出机器可读 JSON 报告；默认与 SVG 同名并添加 .report.json。",
    "      --direction       覆盖布局方向，只接受 LR 或 TB。",
    "      --help            显示本帮助。",
    "",
    "模型只提供 nodes、edges、groups、labels 和 shape 等结构信息，不需要提供坐标。",
  ].join("\n");
}

function parseArgs(argv) {
  const args = { input: "", output: "", report: "", direction: "" };
  const aliases = new Map([
    ["-i", "input"], ["--input", "input"], ["--spec", "input"],
    ["-o", "output"], ["--output", "output"], ["--svg", "output"],
    ["-r", "report"], ["--report", "report"], ["--direction", "direction"],
  ]);
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--help" || token === "-h") return { help: true, ...args };
    const equals = token.indexOf("=");
    const flag = equals >= 0 ? token.slice(0, equals) : token;
    const inlineValue = equals >= 0 ? token.slice(equals + 1) : null;
    const key = aliases.get(flag);
    if (!key) throw new Error(`未知参数“${token}”。请使用 --help 查看参数说明。`);
    const value = inlineValue ?? argv[++index];
    if (value === undefined || (value !== "-" && value.startsWith("-"))) {
      throw new Error(`参数“${flag}”缺少值。`);
    }
    args[key] = value;
  }
  if (!args.input) throw new Error("缺少 --input；请提供 figure-spec JSON 文件。");
  if (!args.output) throw new Error("缺少 --output；请提供 SVG 输出路径。\n" + cliHelp());
  if (!args.report) {
    const extension = path.extname(args.output);
    args.report = path.join(path.dirname(args.output), `${path.basename(args.output, extension)}.report.json`);
  }
  return args;
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export { FONT_STACK, DEFAULT_OPTIONS, wrapText, normaliseSpec, buildLayout, renderSvg, validateLayout, compileFigureSpec, parseArgs, cliHelp };
export default { compileFigureSpec, renderSvg, wrapText };

export async function main(argv = process.argv.slice(2)) {
  let args;
  try {
    args = parseArgs(argv);
  } catch (error) {
    console.error(`参数错误：${error.message}`);
    return 2;
  }
  if (args.help) {
    console.log(cliHelp());
    return 0;
  }
  let rawText;
  try {
    rawText = args.input === "-" ? fs.readFileSync(0, "utf8") : fs.readFileSync(args.input, "utf8");
  } catch (error) {
    const report = {
      schema_version: "1.0",
      compiler: "render_svg_layout.mjs",
      ok: false,
      diagnostics: { errors: [{ code: "INPUT_READ_FAILED", message: `无法读取输入文件：${error.message}` }], warnings: [] },
    };
    writeJson(args.report, report);
    console.error(`读取失败：${error.message}`);
    return 1;
  }
  const result = compileFigureSpec(rawText, args.direction ? { direction: args.direction } : {});
  writeJson(args.report, result.report);
  if (!result.report.ok || !result.svg) {
    console.error(`布局编译失败：${result.report.diagnostics.errors.map((item) => `${item.code}：${item.message}`).join("；")}`);
    return 1;
  }
  try {
    fs.mkdirSync(path.dirname(path.resolve(args.output)), { recursive: true });
    fs.writeFileSync(args.output, result.svg, "utf8");
  } catch (error) {
    console.error(`SVG 写入失败：${error.message}`);
    return 1;
  }
  console.log(`布局编译成功：SVG=${args.output}，报告=${args.report}`);
  return 0;
}

const thisFile = path.resolve(fileURLToPath(import.meta.url));
const invokedFile = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (thisFile === invokedFile) {
  main().then((code) => {
    process.exitCode = code;
  }).catch((error) => {
    console.error(`未处理的编译错误：${error.stack || error.message}`);
    process.exitCode = 1;
  });
}
