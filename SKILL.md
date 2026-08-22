---
name: aiwritepaper-agentic-skill
description: 根据已有选题、专业细分方向和可用研究材料，为中文论文选择与 AIWritePaper 公开范文结构相匹配的可审计提示词；也可在用户没有确定选题时推荐 10 个可行题目。适用于毕业论文、期刊论文、文献综述、工程设计、实证研究、法学、人文和工作报告的选题路由与完整论文生产准备，不用于代替真实研究、编造数据或规避检测。
license: MIT
compatibility: 遵循 Agent Skills 开放规范；基础路由只需读取 Markdown，完整论文生产还需要当前 agent 具备网络检索、文件写入和相应文档工具。
metadata:
  author: huangnan29
  version: "0.1.0"
  repository: https://github.com/huangnan29/aiwritepaper-agentic-skill
---

# AIWritePaper Agentic Skill

本 Skill 负责两件事：先把题目收敛为可回答、可取证的研究问题，再只加载一个最匹配的方向提示词。不要默认加载全部方向文件。

## 启动判断

1. 如果当前请求已经给出完整题目，直接视为“已有选题”，不要重复询问是否有题目。
2. 如果当前请求没有完整题目，先询问：“你是否已经有确定的论文题目？”
3. 用户有题目时，读取 [references/routing.md](references/routing.md)，判断学科、研究对象、研究动作、证据形式和成果形态。
4. 用户没有题目时，读取 [references/topic-selection.md](references/topic-selection.md)，一次询问专业、细分方向、论文层次、已有材料和方法偏好，然后推荐 10 个题目。
5. 用户只给出大概方向时，先分析可能的研究路径；仅当歧义会改变提示词类型时提出一个消歧问题，再推荐或确认题目。

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
