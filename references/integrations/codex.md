# Agent适配：Codex

本附加规则只把通用能力映射到Codex实际工具，不改变论文方向、证据和内容决策。

- `AGENT_ADAPTER` 固定记录为 `codex`。
- 当前会话真实暴露 `imagegen`、`image_gen` 或等价图片工具时，`00-capability-report.json` 中 `image_generation.available` 必须为 `true`，调用者记录为 `CURRENT_AGENT`；所有 `imagegen_eligible=true` 的结构图逐张调用，不得只生成封面或第一张概念图。
- 图片工具返回的原生结果、调用ID或客户端回执立即保存到当前论文输出目录；图片生成成功后不得改插同图号SVG。
- 当前会话没有图片工具时，不根据“Codex通常可以生图”推断能力；如桌面父任务真实可以代调，则调用者记录为 `PARENT_AGENT` 并提交完整图片任务单，否则诚实进入SVG降级。
- DOCX/PDF与视觉检查使用当前会话真实可用的文档、PDF和图片查看能力；缺少某项工具时记录能力缺口，不虚报完成。

