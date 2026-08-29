# 执行Profile：GUIDED

本Profile不改变完整方向提示词，只增加内部阶段检查，适用于工具基本齐全但长任务容易漏文件、漏图或漏验收的执行器。

- 全程自动执行，不要求用户逐阶段批准。
- 使用本最终提示词内嵌的阶段模板创建 `00-execution-checkpoints.json`，把 `execution_profile` 设为 `GUIDED`，依次记录 `EVIDENCE`、`OUTLINE`、`DRAFT`、`FIGURES`、`DOCUMENTS`、`VALIDATION` 六阶段的输入、输出、实际计数、错误和状态。
- 阶段状态只能为 `PENDING`、`IN_PROGRESS`、`PASS`、`PARTIAL`、`FAIL`；只有真实文件存在并达到该阶段条件时才可PASS。
- 每完成一章记录不超过300字状态摘要；进入下一章只加载研究契约、大纲、论证地图、证据矩阵和上一章摘要，不反复加载全部历史正文。
- 检查器返回错误时，按错误码回到对应阶段；一次只修复文献、数据、图表、公式或文档中的一类问题。已经通过且摘要未变化的文件保持冻结。
- 最终状态只读 `14-adjudicated-status.json`。
