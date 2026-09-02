# 一份任务记录与两个入口

只在准备阶段读取本说明。原来的run-params、能力报告、Profile选择和task-selection改为由paper.py prepare一次生成；不是删去真实能力检查，而是不再重复填写四份文件。

## paper-request.json

模型根据用户材料填写，不让脚本判断方向、方法或专业正确性：

| 字段 | 含义 |
|---|---|
| schema_version | 1.0 |
| paper_title | 用户题目；改题必须有授权 |
| direction_id | 从routing.md选出的唯一方向 |
| model_label | 实际模型与客户端；未知写UNKNOWN |
| agent_adapter | codex、grok、gemini-antigravity、claude-cursor、kimi-workbuddy或universal-terminal，按真实工具选择 |
| observed_at | 带时区的真实能力观察时间 |
| capabilities | 四项实际能力记录，结构见模板；不复制示例、账号令牌或Cookie |
| run_mode | 默认FULL_BUILD；其余按用户任务范围 |
| features | 显式选择figures、statistics、svg、formulas、documents；statistics/svg包含配图基础规则 |
| document_profile / paper_level / language | 默认THESIS / UNSPECIFIED / zh-CN；只按已知要求填写 |
| target_length / min_length / max_length | 用户或模板指定时填写；否则统一解析默认值，不重复计算 |
| min_references / target_figures / target_tables | 本次明确目标，由用户要求或模型的方向计划决定，不强制所有学科相同数量 |
| citation_mode / citation_style | NUMERIC或AUTHOR_YEAR及实际引用规范；未指定模式时默认NUMERIC |
| research_claim_level | 按真实材料决定OBSERVED_STUDY、DESIGN_ONLY、PROTOCOL_ONLY、REVIEW_SYNTHESIS；尚未确定可暂不填，完成研究后显式登记 |
| research_question / research_method / materials / constraints | 保留研究问题、方法、实际材料与用户原始限制，不能提前填写结果 |
| execution_profile / prior_adjudications | 仅显式需要辅助或授权历史记录时填；不扫描其他模型目录 |

使用[示例](paper-request.example.json)时必须替换为实际观察并移除example_only；工具拒绝直接执行示例。available=true必须有实际工具名、调用层和观察依据。工具不会联网探测、登录账户或生成试验图片，也不会根据模型品牌自动标记能力。

## 准备

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" prepare --root "<OUTPUT_DIR>" --request paper-request.json
```

--preview仅检查输入并显示将选模块，不写文件。已有准备结果则拒绝覆盖，改用resume继续；没有题目或只做ROUTE_ONLY时无需创建生产目录。准备不写任何PASS、正式论文文件或分数。

生成的run-manifest.json采用state_contract:DERIVED_ONLY：最终状态由检查器计算，模型不需要反复填写research_status/delivery_status/final_status。研究性质和引用方式仍是语义判断，必须由模型或用户明确；不由工具猜测。正式导出文件出现以后，只登记真实路径，检查入口自动计算文件摘要。

## 检查

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" check --root "<OUTPUT_DIR>" --docx "论文_时间戳.docx" --pdf "论文_时间戳.pdf"
```

必要时增加--claim-level明确研究性质。已有路径不必重复指定；--plan只显示计划。qa-review.json存在时自动派生审计视图，不再单独调用prepare_audit_views.py；它只能记录已完成的真实观察，未做独立评分就不填分数。

只读审计使用：

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" check AUDIT_ONLY --root "<原稿目录>" --audit-dir "<原稿之外的新审计目录>"
```

副本中的新报告不改写原稿。含符号链接的源包会被保守拒绝，应提供明确且无链接的审计副本，避免递归复制或访问越界。

## 回执和旧格式

兼容文件依旧用于定位和验收，但不再是独立手填任务。旧报告保存在.audit-logs/<本次运行>/upstream；本次stdout/stderr与汇总也在那里。检查失败时报告真实错误，不读取旧成功状态。不适用项必须符合模式；未变化复用必须绑定有效原报告和输入，缺失时不能伪造跳过。

完整与紧凑提示词仍共用模块源；compact不是旧15KB短提示词。此次减少准备动作，不声称弱模型输入预算或生成质量已经改善。实际A/B测试仍待完成。
