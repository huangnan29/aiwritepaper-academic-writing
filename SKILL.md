---
name: aiwritepaper-agentic-skill
description: 根据已有选题、专业细分方向和可用研究材料，为中文论文选择可审计提示词，并按明确模式执行完整生产、配图、导出或验收；也可在用户没有确定选题时推荐 10 个可行题目。适用于毕业论文、期刊论文、文献综述、工程设计、实证研究、法学、人文和工作报告，不用于代替真实研究、编造数据或规避检测。
license: MIT
metadata:
  author: huangnan29
  version: "0.3.1"
  repository: https://github.com/huangnan29/aiwritepaper-agentic-skill
---

# AIWritePaper Agentic Skill

本 Skill 先确定运行模式，再把题目收敛为可回答、可取证的研究问题，只加载一个最匹配的方向提示词，并通过确定性脚本完成能力探测、证据核验、全文整合、文档导出和最终验收。不要默认加载全部方向文件，也不要让模型自行宣布 `PASS`。

运行兼容性：遵循 Agent Skills 开放规范；基础路由只需读取 Markdown，完整论文生产还需要当前 agent 具备网络检索、文件写入和相应文档工具。

## 启动判断

1. 先从请求确定运行模式；无法唯一判断时只询问一个模式问题。
2. `EXPORT_ONLY`、`FIGURES_ONLY` 或 `AUDIT_ONLY` 且工作区已有研究契约或正文时，直接读取现有文件，不重复询问题目。
3. 如果当前请求已经给出完整题目，直接视为“已有选题”，不要重复询问是否有题目。
4. 如果当前请求没有完整题目，先询问：“你是否已经有确定的论文题目？”
5. 用户有题目时，读取 [references/routing.md](references/routing.md)，判断学科、研究对象、研究动作、证据形式和成果形态。
6. 用户没有题目时，读取 [references/topic-selection.md](references/topic-selection.md)，一次询问专业、细分方向、论文层次、已有材料和方法偏好，然后推荐 10 个题目。
7. 用户只给出大概方向时，先分析可能的研究路径；仅当歧义会改变提示词类型时提出一个消歧问题，再推荐或确认题目。

## 运行模式

- `ROUTE_ONLY`：只完成选题或方向提示词路由，不写论文。
- `FULL_BUILD`：执行能力探测、研究、写作、配图、整合、DOCX/PDF 导出和最终验收。
- `FIGURES_ONLY`：只规划、生成或优化配图，不改正文主张。
- `EXPORT_ONLY`：从现有定稿和图片生成 DOCX/PDF，不重新研究或改写结论。
- `AUDIT_ONLY`：只读核验现有产物，不创建实验结果，不把修复计划写成已完成。

开始工作前明确输出所选模式、输入目录、预期交付物和停止条件。

## 路由输出

在进入写作前，先向用户给出：

- 规范化题目；
- 推定专业和论文类型；
- 选中的方向提示词文件；
- 选择依据；
- 需要的原始材料；
- 材料不足时的降级方式；
- 是否需要用户确认研究问题。

如果两个方向同样合理，给出首选和备选并解释差异，不要静默猜测。

## 加载规则

- 正常执行只读取 `references/compiled-prompts/` 中一个与题目匹配的完整提示词。
- `FULL_BUILD`、`EXPORT_ONLY` 和 `AUDIT_ONLY` 必须读取 [references/common/executable-gates.md](references/common/executable-gates.md) 并运行其中对应脚本。
- 包含定量或系统运行结果时，读取 [references/evidence-manifest.md](references/evidence-manifest.md) 建立证据清单和执行记录。
- 进入图表生产时，先读取 [references/common/academic-figures.md](references/common/academic-figures.md) 判断证据属性与绘图路径。需要生成式学术插画时读取 [references/figure-skills/academic-figure-routing.md](references/figure-skills/academic-figure-routing.md)；需要流程图、架构图、ER 图、UML、研究框架或其他确定性矢量图时读取 [references/figure-skills/academic-svg-quality.md](references/figure-skills/academic-svg-quality.md)。
- 开题报告或答辩 PPT 是论文方向确定后的附加交付，分别读取 `references/deliverables/proposal-report.md` 或 `references/deliverables/defense-presentation.md`。
- [references/universal-reference-prompt.md](references/universal-reference-prompt.md) 仅用于没有方向文件可覆盖的新型论文，或用于维护方向库；不要把它作为默认提示词。
- 需要了解范文覆盖和分类依据时，读取 `references/research/coverage-report.md` 与 `references/research/taxonomy-report.md`，不要加载或复述范文全文。

## 硬性边界

- 先检索、核验和建立证据矩阵，再写正文。
- 没有真实数据、代码、实验、问卷、访谈、病例或日志时，不得生成已完成结果。
- 不以规避 AIGC 检测或重复率检测为目标。
- 不编造参考文献、DOI、政策、标准、法条、病例、伦理审批、个人信息或致谢对象。
- AIWritePaper 范文只用于学习结构和暴露风险，不作为事实来源，也不复制其正文。
- 文件生成、浏览器访问、外部数据库、DOCX/PDF 和发布操作均受当前运行环境与用户授权约束。
- 能力状态只能来自探测证据；不存在的工具不得写成 `AVAILABLE`。
- 定量结果必须通过证据清单校验；模拟、合成或硬编码示例不得表述为真实系统实验。
- `FULL_BUILD` 缺少 DOCX/PDF、全文未整合或 manifest 与文件不一致时，最终状态不得为 `PASS`。
- `12-final-qa-report.md` 只能引用确定性交付验收器计算的状态，不得由模型自行判定。
- `FULL_BUILD` 或 `FIGURES_ONLY` 中，当前客户端若暴露 `imagegen`、`image_gen`、Imagine、Nano Banana 或等价图片生成工具，所有适合图片生成的论文配图都必须逐张真实调用并保存位图。精确流程图、架构图、研究框架、组织图、ER/UML 等必须先根据上下文写出详细生图 Prompt 再生成；不得回退为纯 SVG。数据统计图从真实数据用代码生成，原始科研影像使用原文件，公式、化学、电路和地图使用领域工具。SVG 只允许用于无图片工具环境或生成图后的确定性修正层。只有用户明确退出或目标期刊明确禁止 AI 图片时可豁免并记录证据。
