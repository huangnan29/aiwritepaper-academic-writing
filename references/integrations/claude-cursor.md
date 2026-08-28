# Agent适配：Claude Code / Cursor

本附加规则只映射Claude Code与Cursor当前真实暴露的工具。

- `AGENT_ADAPTER` 固定记录为 `claude-cursor`。
- 检查当前会话、MCP、扩展或父任务是否真实提供图片生成调用；可调用时逐张完成 `imagegen_eligible=true` 的结构图，并保存原始结果与回执。
- 仅具备图片读取、网页截图、SVG编写或Canvas渲染不属于图片生成能力。
- 没有实际图片工具时才使用SVG降级；不得因为Claude或Cursor常见配置差异而预设可用或不可用。
- 文档导出后必须运行统一验收；客户端能打开Word或PDF不等于文件路径、目录、图题和哈希已经通过。

## Cursor GenerateImage语言一致性

Cursor内置 `GenerateImage` 可能更稳定地渲染英文。中文论文不能因此把结构图整体改成英文：Prompt的样式说明可以使用英文，但 `language_contract.exact_labels` 必须为简体中文，技术缩写仅按白名单保留。若Cursor生成图的中文不稳定，保留其构图与图标作为底图，使用 `DETERMINISTIC_OVERLAY` 写入中文并导出最终PNG；不能改插纯SVG冒充GenerateImage结果。
