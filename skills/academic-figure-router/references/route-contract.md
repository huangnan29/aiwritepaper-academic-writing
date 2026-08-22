# 配图路由交接契约

每张计划图先生成一个 `figure-route.json` 条目，再进入绘图。缺少关键输入时必须默认阻断，不得生成看似完整的终稿。

```json
{
  "figure_id": "fig-4-1",
  "figure_type": "er-diagram",
  "route": "deterministic-svg",
  "status": "INPUT_REQUIRED",
  "reason": "缺少真实数据库 schema",
  "required_inputs": ["schema.sql", "字段说明", "主外键和基数"],
  "source_refs": [],
  "forbidden": ["猜测实体和字段", "使用图片模型"],
  "deliverables": ["editable.svg", "paper.png", "figure-manifest.json"],
  "capability": {
    "native_image_output": false,
    "client_tool_exposed": false,
    "called_and_saved": false,
    "tool_or_model": null,
    "artifact_path": null
  },
  "physical_width_mm": 150,
  "pixel_width": null,
  "effective_dpi": null,
  "human_verified": false
}
```

## 状态

- `READY`：输入、来源和工具都已满足，可以开始绘制。
- `INPUT_REQUIRED`：缺真实 schema、数据、流程、事实关系、文字或版式参数。
- `CAPABILITY_GAP`：所选路径需要的图片工具、领域工具或文件能力不可用。
- `VISUAL_QA_BLOCKED`：源文件已生成，但缺少可用渲染器或无法在最终载体检查。
- `PASS`：结构、事实、渲染、版面和交付均已验证。
- `FAIL`：存在事实错误、虚构证据、损坏文件或未关闭的关键问题。

## 来源闸门

ER 图的实体、字段和关系，时序图的参与者和消息，流程图的步骤与判断，研究框架的构念与假设，都必须有 `source_ref`。缺少任一关键来源时状态不得高于 `INPUT_REQUIRED`，最多输出明确标记的待确认模板。
