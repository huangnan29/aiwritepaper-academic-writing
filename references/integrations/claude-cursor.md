# 适配：Claude Code / Cursor

记录`AGENT_ADAPTER=claude-cursor`。检查当前会话、扩展、MCP和父层是否真实提供GenerateImage；可用时逐张处理普通结构图并保存回执。Cursor生成中文不稳时保留构图，用DETERMINISTIC_OVERLAY写入`exact_labels`中的简体中文，技术缩写按白名单保留；不得把中文论文全图改英文，也不得用SVG替换成功生图。文档必须经实际导出与页面核验。
