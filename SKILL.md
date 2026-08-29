---
name: aiwritepaper-academic-writing
description: 根据题目和材料完成毕业论文、学位论文、期刊论文、开题报告、答辩材料、论文配图、DOCX/PDF导出或质量验收；选择唯一方向提示词并确定性合成为单一执行MD。不用于编造研究、数据、文献、实验结果或规避检测。
license: MIT
metadata:
  author: huangnan29
  version: "2.0.0"
  repository: https://github.com/huangnan29/aiwritepaper-academic-writing
---

# AIWritePaper｜AI学术写作全流程

本Skill负责选择唯一论文方向，并把本次参数与一份自包含方向提示词确定性合成为 `final-execution-prompt.md`。论文生产阶段只执行这一个最终MD，不继续跳转公共规则、方向文件、配图子Skill或维护脚本。

## 一、确定请求类型

- 用户已有完整题目并要求完整论文：`FULL_BUILD`。
- 用户要求“继续、恢复上次、接着完成”且目录已有运行文件：`RESUME`。
- 用户提供导师、评审或修改意见并要求改稿：`REVISE_ONLY`。
- 用户已有正文，只要求新增或优化配图：`FIGURES_ONLY`。
- 用户已有定稿，只要求DOCX/PDF：`EXPORT_ONLY`。
- 用户只要求检查：`AUDIT_ONLY`。
- 用户只要求方向判断：`ROUTE_ONLY`。
- 用户只要求开题报告：`PROPOSAL_ONLY`。
- 用户只要求答辩材料：`DEFENSE_ONLY`。
- 用户没有题目或只有模糊方向：完整读取 [references/topic-selection.md](references/topic-selection.md)，一次收集必要信息并推荐10个题目；用户选定后再进入方向路由，不提前生成论文。

已有题目且用户要求开始执行时，默认 `AUTO_COMPLETE`；`AUTO_BENCHMARK`作为兼容别名。除权限、伦理、凭证、付费或无法继续的硬阻塞外，不停下来等待用户确认。

字数优先级为用户明确值、学校/期刊模板、明确论文层次默认值、25,000兜底。THESIS层次未知时仍使用25,000；详细中英文默认值见最终方向提示词。用户明确值始终优先。

使用 `scripts/resolve_default_length.py` 根据 `DOCUMENT_PROFILE`、`PAPER_LEVEL`、语言和可选用户目标计算 `TARGET_LENGTH/MIN_LENGTH/MAX_LENGTH`，把结果写入 `run-params.md`；脚本只计算默认值，不参与正文。

`RESUME` 不重新路由或重新合成提示词。先运行 `scripts/prepare_resume.py --root <OUTPUT_DIR>`，验证原提示词、Manifest和阶段SHA-256，从 `00-resume-plan.json.resume_from` 继续；只有提示词缺失/损坏或用户明确迁移版本时才确定性恢复。

`REVISE_ONLY` 不重新研究整篇。保存用户意见为 `revision-request.md`，依据 [修改稿规则](references/deliverables/revision.md) 建立影响清单，再用 `compose_revision.py` 生成唯一 `revision-execution-prompt.md`；不覆盖原正式文档。

## 二、选择唯一方向

完整读取 [references/routing.md](references/routing.md)，根据研究对象、研究动作、证据形式和成果形态选择一个且仅一个 `references/compiled-prompts/*-full.md`。不要同时加载首选与备选提示词；材料不足时仍选择同学科方向，但在本次参数中诚实降级研究主张。

`ROUTE_ONLY` 到此结束，只报告题目、研究问题、唯一方向提示词、证据需求、材料缺口和降级方案，不进入论文生产。

## 三、选择当前Agent适配层

根据实际运行客户端选择一个且仅一个适配文件，并把它合入最终执行提示词。适配层只映射工具名称、父子代理能力交接和验收调用，不改变论文方向或内容：

- Codex：`references/integrations/codex.md`
- Grok Build或Grok Bot：`references/integrations/grok.md`
- Gemini CLI或Antigravity：`references/integrations/gemini-antigravity.md`
- Claude Code或Cursor：`references/integrations/claude-cursor.md`
- Kimi Code、WorkBuddy或其承载的MiniMax模型：`references/integrations/kimi-workbuddy.md`
- OpenCode、GitHub Copilot、ZCode、DeepSeek-tui及其他终端Agent：`references/integrations/universal-terminal.md`

优先按实际工具拓扑选择：当前Agent直接生图选直连型适配；需要父任务代调图片选父子交接型；客户端提供GenerateImage和文件查看选客户端集成型；仅有终端与MCP选通用终端型。商品名只是示例，不是永久判断依据。

不要按模型宣传能力推断工具。适配文件要求检查当前执行器、父代理、客户端和MCP/插件实际暴露的能力；任一层可以调用图片生成时，不能把“当前子执行器无工具”当成整个任务无工具。

## 四、能力预检与执行Profile

除 `ROUTE_ONLY` 外，先在输出目录完成真实工具检查并写入 `00-capability-report.json`，再选择执行Profile。不要根据模型品牌或产品宣传推断能力。

`MODEL_LABEL` 必须记录实际模型与客户端，例如 `Grok 4.6 @ Grok Build`、`Gemini Flash @ Antigravity`；无法读取模型名时写 `UNKNOWN @ <客户端>`，不能用Skill版本或目录名冒充模型。多模型测试目录名另记为 `RUN_LABEL`。

使用Profile选择器生成 `00-profile-selection.json`：

```bash
python3 "<SKILL_DIR>/scripts/select_execution_profile.py" \
  --capability-report "<OUTPUT_DIR>/00-capability-report.json" \
  --model-label "<MODEL_LABEL>" \
  --output "<OUTPUT_DIR>/00-profile-selection.json"
```

- 用户明确指定Profile时增加 `--requested-profile FULL_AUTONOMY|GUIDED|WEAK_MODEL`，用户覆盖优先级最高。
- 用户授权使用同一模型、同一客户端的历史结果时，可重复增加 `--prior-adjudication "<历史14-adjudicated-status.json>"`；不得扫描或读取未授权的其他模型目录。
- 没有弱信号时默认 `FULL_AUTONOMY`，保持强模型原执行路径；同模型历史PARTIAL选择 `GUIDED`，同模型历史FAIL选择 `WEAK_MODEL`；DOCX/PDF工具缺口选择 `GUIDED`。
- Profile只改变任务组织与上下文负载，不改变学术标准。不得按Gemini、Grok、Claude、Codex等品牌硬编码档位。

Profile定义见 [FULL_AUTONOMY](references/profiles/full-autonomy.md)、[GUIDED](references/profiles/guided.md) 与 [WEAK_MODEL](references/profiles/weak-model.md)。FULL_AUTONOMY文件只用于说明和维护，合成时不附加，以保持强模型最终提示词字节不变。
GUIDED与WEAK_MODEL把 [阶段模板](references/profiles/execution-checkpoints-template.json) 作为额外 `--addon` 合入唯一最终提示词，再创建输出目录内的 `00-execution-checkpoints.json`。

## 五、确定性合成最终执行提示词

除 `ROUTE_ONLY` 和尚未选题的情况外，在用户输出目录创建 `run-params.md`，只写以下本次运行内容：

1. 真实运行参数：模式、输出目录、`MODEL_LABEL`、`RUN_LABEL`、`EXECUTION_PROFILE`、题目、论文类型、学科、研究对象、核心问题、语言、目标正文长度、引用格式、最低文献数、图片数、表格数、模板和用户材料；
2. 用户明确的目录、工具、真实性、格式和停止条件；
3. 当前Agent适配文件、可能的父代理调用层、能力缺口与降级边界，不提前写研究结果。

`MODEL_LABEL` 与 `RUN_LABEL` 只用于能力适配、对比测试、运行清单和结果区分；不进入论文署名，也不改变正文内容或学术结论。

不要让模型重新生成、复述或复制所选提示词。根据 `00-profile-selection.json.selected_profile` 选择唯一输入：

- `FULL_AUTONOMY`：使用 `references/compiled-prompts/<PROMPT>-full.md`，不附加Profile任务卡；
- `GUIDED`：使用同一 `*-full.md`，附加 `references/profiles/guided.md`；
- `WEAK_MODEL`：使用同方向 `references/compact-prompts/<PROMPT>-compact.md`，附加 `references/profiles/weak-model.md`，不得同时加载完整版。

使用确定性合成工具，把 `run-params.md`、唯一方向提示词、当前Agent适配与对应Profile规则按字节顺序写入 `final-execution-prompt.md`。FULL_AUTONOMY示例：

```bash
python3 "<SKILL_DIR>/scripts/compose_prompt.py" \
  --params "<OUTPUT_DIR>/run-params.md" \
  --compiled "<SKILL_DIR>/references/compiled-prompts/<PROMPT>-full.md" \
  --addon "<SKILL_DIR>/references/integrations/<ADAPTER>.md" \
  --profile-selection "<OUTPUT_DIR>/00-profile-selection.json" \
  --output "<OUTPUT_DIR>/final-execution-prompt.md" \
  --report "<OUTPUT_DIR>/00-prompt-composition.json"
```

GUIDED增加 `--addon "<SKILL_DIR>/references/profiles/execution-checkpoints-template.json"` 与 `--profile-rules "<SKILL_DIR>/references/profiles/guided.md"`。WEAK_MODEL把 `--compiled` 改为同方向 `*-compact.md`，并增加同一个阶段模板addon与 `--profile-rules "<SKILL_DIR>/references/profiles/weak-model.md"`。

REVISE_ONLY使用：

```bash
python3 "<SKILL_DIR>/scripts/compose_revision.py" \
  --base-prompt "<OUTPUT_DIR>/final-execution-prompt.md" \
  --request "<OUTPUT_DIR>/revision-request.md" \
  --rules "<SKILL_DIR>/references/deliverables/revision.md" \
  --output "<OUTPUT_DIR>/revision-execution-prompt.md" \
  --report "<OUTPUT_DIR>/revision-prompt-composition.json"
```

- `PROPOSAL_ONLY` 或用户附加要求开题报告时，增加 `--addon "<SKILL_DIR>/references/deliverables/proposal-report.md"`。
- `DEFENSE_ONLY` 或用户附加要求答辩材料时，增加 `--addon "<SKILL_DIR>/references/deliverables/defense-presentation.md"`。
- Python启动命令依次尝试 `python3`、`python`，Windows再尝试 `py -3`；后续所有示例中的 `python3` 替换为实际可用命令。三者均不可用时读取 [references/prompt-composition.md](references/prompt-composition.md) 使用原生拼接；Profile选择和最终裁决无法执行时记录能力缺口，权威状态不能为PASS。

合成工具只负责文件拼接、UTF-8校验、原文完整性和SHA-256输出，不决定方向、章节、证据、图片或最终状态。`scripts/build_compiled.py` 与 `scripts/verify_compiled.py` 仅供Skill维护，不在论文生产阶段运行。

合成成功后，从头到尾完整读取一次 `final-execution-prompt.md`。后续只把它作为生产指令，不再单独读取 `references/common/`、`references/directions/` 或其他compiled prompts。若无法合成或完整读取，报告硬阻塞；不得用当前 `SKILL.md` 的简短说明替代正式提示词。

用户没有另行指定 `OUTPUT_DIR` 时使用当前工作目录。目录边界明确时，除读取Skill与用户授权材料外，只在该输出目录写入，不访问其他模型结果目录。

## 六、持续执行与闭环验收

按照 `final-execution-prompt.md` 直接执行。已有题目的 `FULL_BUILD` 不输出路由方案后停顿，不要求用户再次批准大纲，不把论文正文只留在聊天窗口。

执行模型自主选择当前可用工具。只有数据统计图、DOCX/PDF导出或本次任务确实需要时，才在输出目录创建项目专用代码；不得调用Skill维护脚本决定正文、证据、章节状态或 `PASS`。

- `verify_evidence_integrity.py`：核对题录、引用、全文状态和数据来源。
- `verify_figure_package.py`：核对能力、图表路线、回执、嵌图和视觉状态。
- `verify_formula_rendering.py`：核对公式源稿、OMML、PDF残留和摘要。
- `verify_manuscript_delivery.py`：核对正文长度、文件名、目录、表格、DOCX/PDF和哈希。
- `adjudicate_status.py`：读取底层报告并计算唯一权威状态。
- `verify_quality_package.py`：核对方向评分卡、主张证据、图文语义和文档视觉覆盖。
- `capture_provenance.py`：登记真实原始文件、官方下载和实际计算/仿真命令；生产脚本不得自行伪造观察或执行回执。

检查器不决定论文观点、公式含义或证据取舍，也不生成论文内容。

方向90分标准来自 [评分卡](references/quality/direction-rubrics.json)，方法能否支撑题目与结论依据 [方向方法门](references/quality/direction-method-gates.json)，强模型发布回归使用 [57任务基准](references/benchmarks/strong-model-benchmark.json)。评分卡只规定关注点和Critical，不规定正文句式。
初稿完成后调用同方向 `references/reviewers/<DIRECTION_ID>.md` 进行第一次隔离审稿。全部图片、DOCX、PDF和视觉回执完成后必须再次调用同方向审稿提示词，生成绑定终稿SHA-256的 `09-final-peer-review.json`；最终评分卡只能采用这次终稿审稿分数。

按 [模式×检查器矩阵](references/mode-checker-matrix.json) 运行检查。FULL_BUILD和AUDIT_ONLY运行四个底层检查器；其他模式只运行适用项，对不适用或未变化项使用标准SKIPPED报告。完整论文另运行 `verify_quality_package.py`，质量目标依据当前方向内嵌90分评分卡。最后运行裁决器。

文献或数据失败时回到证据阶段；图表失败时回到配图；公式失败时回到公式或导出；文档失败时回到排版。任何失败都不能被模型自述覆盖。最终回复只读取 `14-adjudicated-status.json.authoritative_status`。

图片工具已经成功生成某图时，正文、DOCX和PDF必须插入该生成图或由它合成的最终PNG；同名SVG只能作为备用或修正源。最终嵌入路径以图表清单中的 `final_embed_file` 为唯一依据，不能按文件名或扩展名自行改选SVG。

最终答复只报告真实完成内容、论文题目、实际正文长度、文献/图片/表格数量、按“安全论文题目_YYYYMMDD-HHMMSS”生成且共用同一时间戳的DOCX/PDF路径、QA路径、能力缺口以及权威 `RESEARCH_STATUS`、`DELIVERY_STATUS`、`FINAL_STATUS`。三个状态必须来自 `14-adjudicated-status.json`；Manifest声明与权威值冲突时报告冲突并采用权威值。任何硬目标未满足时不得标记 `PASS`。
