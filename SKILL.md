---
name: aiwritepaper-agentic-skill
description: 根据题目和材料完成毕业论文、学位论文、期刊论文、开题报告、答辩材料、论文配图、DOCX/PDF导出或质量验收；选择唯一方向提示词并确定性合成为单一执行MD。不用于编造研究、数据、文献、实验结果或规避检测。
license: MIT
metadata:
  author: huangnan29
  version: "0.7.0"
  repository: https://github.com/huangnan29/aiwritepaper-agentic-skill
---

# AIWritePaper 单提示词执行入口

本Skill负责选择唯一论文方向，并把本次参数与一份自包含方向提示词确定性合成为 `final-execution-prompt.md`。论文生产阶段只执行这一个最终MD，不继续跳转公共规则、方向文件、配图子Skill或维护脚本。

## 一、确定请求类型

- 用户已有完整题目并要求完整论文：`FULL_BUILD`。
- 用户已有正文，只要求新增或优化配图：`FIGURES_ONLY`。
- 用户已有定稿，只要求DOCX/PDF：`EXPORT_ONLY`。
- 用户只要求检查：`AUDIT_ONLY`。
- 用户只要求方向判断：`ROUTE_ONLY`。
- 用户只要求开题报告：`PROPOSAL_ONLY`。
- 用户只要求答辩材料：`DEFENSE_ONLY`。
- 用户没有题目或只有模糊方向：完整读取 [references/topic-selection.md](references/topic-selection.md)，一次收集必要信息并推荐10个题目；用户选定后再进入方向路由，不提前生成论文。

已有题目且用户要求开始执行时，默认 `AUTO_BENCHMARK`：除权限、伦理、凭证、付费或无法继续的硬阻塞外，不停下来等待用户确认。

已有完整题目并触发 `FULL_BUILD` 时，用户没有明确指定正文长度则固定使用 `TARGET_LENGTH: 25000`，允许误差±10%，正文下限为22,500。用户明确给出的字数目标始终优先，不得被默认值覆盖。

## 二、选择唯一方向

完整读取 [references/routing.md](references/routing.md)，根据研究对象、研究动作、证据形式和成果形态选择一个且仅一个 `references/compiled-prompts/*-full.md`。不要同时加载首选与备选提示词；材料不足时仍选择同学科方向，但在本次参数中诚实降级研究主张。

`ROUTE_ONLY` 到此结束，只报告题目、研究问题、唯一方向提示词、证据需求、材料缺口和降级方案，不进入论文生产。

## 三、确定性合成最终执行提示词

除 `ROUTE_ONLY` 和尚未选题的情况外，在用户输出目录创建 `run-params.md`，只写以下本次运行内容：

1. 真实运行参数：模式、输出目录、`MODEL_LABEL`、题目、论文类型、学科、研究对象、核心问题、语言、目标正文长度、引用格式、最低文献数、图片数、表格数、模板和用户材料；
2. 用户明确的目录、工具、真实性、格式和停止条件；
3. 能力缺口与降级边界，不提前写研究结果。

`MODEL_LABEL` 只用于多模型对比测试、运行清单和结果区分；它不进入论文署名，也不改变正文内容或学术结论。用户没有指定时使用当前工作目录名称。

不要让模型重新生成、复述或复制所选 `*-full.md`。使用Skill内的确定性合成工具，把 `run-params.md`、唯一完整提示词和必要的附加交付规则按字节顺序写入 `final-execution-prompt.md`：

```bash
python3 "<SKILL_DIR>/scripts/compose_prompt.py" \
  --params "<OUTPUT_DIR>/run-params.md" \
  --compiled "<SKILL_DIR>/references/compiled-prompts/<PROMPT>-full.md" \
  --output "<OUTPUT_DIR>/final-execution-prompt.md"
```

- `PROPOSAL_ONLY` 或用户附加要求开题报告时，增加 `--addon "<SKILL_DIR>/references/deliverables/proposal-report.md"`。
- `DEFENSE_ONLY` 或用户附加要求答辩材料时，增加 `--addon "<SKILL_DIR>/references/deliverables/defense-presentation.md"`。
- `python3` 不可用时，读取 [references/prompt-composition.md](references/prompt-composition.md)，使用对应平台的原生文件拼接命令；仍不得由模型复述完整提示词。

合成工具只负责文件拼接、UTF-8校验、原文完整性和SHA-256输出，不决定方向、章节、证据、图片或最终状态。`scripts/build_compiled.py` 与 `scripts/verify_compiled.py` 仅供Skill维护，不在论文生产阶段运行。

合成成功后，从头到尾完整读取一次 `final-execution-prompt.md`。后续只把它作为生产指令，不再单独读取 `references/common/`、`references/directions/` 或其他compiled prompts。若无法合成或完整读取，报告硬阻塞；不得用当前 `SKILL.md` 的简短说明替代正式提示词。

用户没有另行指定 `OUTPUT_DIR` 时使用当前工作目录。目录边界明确时，除读取Skill与用户授权材料外，只在该输出目录写入，不访问其他模型结果目录。

## 四、持续执行

按照 `final-execution-prompt.md` 直接执行。已有题目的 `FULL_BUILD` 不输出路由方案后停顿，不要求用户再次批准大纲，不把论文正文只留在聊天窗口。

执行模型自主选择当前可用工具。只有数据统计图、DOCX/PDF导出或本次任务确实需要时，才在输出目录创建项目专用代码；不得调用Skill维护脚本决定正文、证据、章节状态或 `PASS`。

`scripts/verify_figure_package.py` 只允许检查图表Manifest、文件、哈希、Markdown链接和DOCX嵌图一致性；它的结构通过不代表图表结论正确，也不能单独决定论文 `PASS`。

图片工具已经成功生成某图时，正文、DOCX和PDF必须插入该生成图或由它合成的最终PNG；同名SVG只能作为备用或修正源。最终嵌入路径以图表清单中的 `final_embed_file` 为唯一依据，不能按文件名或扩展名自行改选SVG。

最终答复只报告真实完成内容、论文题目、实际正文长度、文献/图片/表格数量、DOCX/PDF/QA路径、能力缺口和最终状态。任何硬目标未满足时不得标记 `PASS`。
