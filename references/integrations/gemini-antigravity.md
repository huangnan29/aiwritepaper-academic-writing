# Agent适配：Gemini CLI / Antigravity

本附加规则只映射Gemini系客户端的实际能力，不根据模型名称虚构工具权限。

- `AGENT_ADAPTER` 固定记录为 `gemini-antigravity`。
- 当前会话、父任务或客户端真实暴露 Nano Banana、Gemini图片生成或等价工具时，记录 `image_generation.available=true` 与真实调用者，并逐张处理所有适合生图的结构图。
- “Gemini模型理论上支持图片”不等于当前CLI可以调用图片工具；只有看见真实工具并能取得结果时才标记可用。
- 图片工具可由父任务代调时，执行器输出完整图片任务单并等待全部结果回传，不能因为当前子任务没有工具就提前生成SVG。
- 中文结构图生成后检查文字、箭头和节点；局部文字问题优先编辑或增加确定性覆盖层，不得静默换成纯SVG。
- DOCX、PDF或视觉工具缺失时记录能力缺口；不得把Markdown、HTML预览或SVG源码冒充最终文档验收。

