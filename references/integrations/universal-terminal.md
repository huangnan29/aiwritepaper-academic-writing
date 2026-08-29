# Agent适配：通用终端Agent

本附加规则适用于OpenCode、GitHub Copilot、ZCode、DeepSeek-tui及未单列的终端Agent。

- `AGENT_ADAPTER` 固定记录为 `universal-terminal`。
- Profile只读取选择器报告，不根据终端Agent名称推断模型强弱；缺DOCX/PDF工具时使用GUIDED记录降级，历史同模型FAIL时才自动使用WEAK_MODEL。
- 逐层检查当前执行器、父代理、MCP/插件与客户端暴露的真实图片、文档、PDF和视觉工具；能力报告只记录实际看见或成功调用的能力。
- 任一层可调用图片生成时，所有 `imagegen_eligible=true` 的结构图必须逐张调用并保存回执；当前子任务无工具不能代表父层无工具。
- 没有真实图片工具时才允许SVG降级。模型品牌、产品宣传、图片理解、截图和SVG渲染都不能替代真实图片调用。
- 最终完成前运行图表与交付验收；验收失败时保持 `DELIVERY_STATUS=FAIL` 并返回对应阶段修复。
