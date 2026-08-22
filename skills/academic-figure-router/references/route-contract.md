# 配图路由交接契约

每张计划图先生成一个 `figure-route.json` 条目，再进入绘图。缺少关键输入时必须默认阻断，不得生成看似完整的终稿。

```json
{
  "figure_id": "fig-4-1",
  "figure_type": "precise-flowchart",
  "route": "image-generation-with-verified-structure",
  "status": "PASS",
  "reason": "客户端已暴露图片工具，流程节点与连线均有正文来源",
  "required_inputs": ["流程节点清单", "边清单", "逐字中文标签", "版面要求"],
  "source_refs": ["05-outline.md#研究流程", "07-paper-full.md#方法流程"],
  "forbidden": ["新增或遗漏节点", "改变箭头方向", "用纯 SVG 替代图片调用"],
  "deliverables": ["fig-4-1-prompt.md", "fig-4-1.png", "figure-manifest.json"],
  "capability": {
    "native_image_output": false,
    "client_tool_exposed": true,
    "called_and_saved": true,
    "tool_or_model": "Codex built-in imagegen/image_gen",
    "artifact_path": "figures/fig-4-1.png"
  },
  "physical_width_mm": 150,
  "pixel_width": null,
  "effective_dpi": null,
  "human_verified": true
}
```

## 状态

- `READY`：输入、来源和工具都已满足，可以开始绘制。
- `INPUT_REQUIRED`：缺真实 schema、数据、流程、事实关系、文字或版式参数。
- `CAPABILITY_GAP`：所选路径需要的图片工具、领域工具或文件能力不可用。
- `VISUAL_QA_BLOCKED`：源文件已生成，但缺少可用渲染器或无法在最终载体检查。
- `PASS`：结构、事实、渲染、版面和交付均已验证。
- `FAIL`：存在事实错误、虚构证据、损坏文件或未关闭的关键问题。

## 图片生成组合门

`FULL_BUILD` 与 `FIGURES_ONLY` 的 `figures/figure-manifest.json` 顶层必须增加：

```json
{
  "image_generation_policy": {
    "client_tool_exposed": true,
    "required": true,
    "eligible_figure_ids": ["fig-2-1"],
    "attempted": true,
    "tool_or_model": "Codex built-in imagegen/image_gen",
    "generated_by_figure": {
      "fig-2-1": "figures/fig-2-1-concept.png"
    },
    "prompt_by_figure": {
      "fig-2-1": "figures/fig-2-1-prompt.md"
    },
    "not_used_reason": null,
    "explicit_user_opt_out": false,
    "venue_prohibits_ai_images": false
  }
}
```

当前客户端暴露图片工具时，默认 `required=true`。流程、架构、框架、组织、ER/UML、机制、装置和场景类图全部进入 `eligible_figure_ids`，`prompt_by_figure` 与 `generated_by_figure` 必须逐项覆盖；统计数据图、原始科研影像和领域工具图不列入。只有用户明确退出或目标期刊明确禁止 AI 图片时才能设为豁免；工具调用失败应保持 `required=true`、记录真实错误并使交付降级，不能静默改为全 SVG。

## 来源闸门

ER 图的实体、字段和关系，时序图的参与者和消息，流程图的步骤与判断，研究框架的构念与假设，都必须有 `source_ref`。缺少任一关键来源时状态不得高于 `INPUT_REQUIRED`，最多输出明确标记的待确认模板。
