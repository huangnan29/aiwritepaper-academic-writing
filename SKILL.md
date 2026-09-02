---
name: aiwritepaper-academic-writing
description: 根据题目和真实材料完成毕业论文、学位论文、期刊论文、开题、答辩、学术配图及DOCX/PDF；一次准备合成唯一执行MD，支持续跑、定点改稿和独立验收。不用于编造研究、文献、数据或规避检测。
license: MIT
metadata:
  author: huangnan29
  version: "2.1.0-rc.2"
  repository: https://github.com/huangnan29/aiwritepaper-academic-writing
---

# AIWritePaper｜AI自动学术写作

本Skill采用MD-first：模型只做一次语义判断，工具把参数、唯一方向、所需模块和当前Agent适配器确定性合成一份执行MD；生产阶段只执行这份文件。脚本不写正文、不选择研究方法，也不产生学术分数。

## 1. 判断任务

- 已有题目并要求完整论文：FULL_BUILD；默认持续完成，不再等待大纲确认。
- 继续已有任务：RESUME；读取原提示词和检查点，不重新prepare。
- 按意见修改：REVISE_ONLY；保留原稿并定点修订。
- 只改图、只导出、只检查、开题、答辩：分别使用FIGURES_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY、DEFENSE_ONLY。
- 只判断方向：ROUTE_ONLY；到路由结果停止。
- 没有题目：完整读取[选题规则](references/topic-selection.md)，一次收集必要信息并推荐10个可行题目。

## 2. 准备一次

完整读取[方向路由](references/routing.md)，选择一个且仅一个direction_id。按当前实际工具选择一个适配器：Codex用`codex`，Grok用`grok`，Gemini/Antigravity用`gemini-antigravity`，Claude/Cursor用`claude-cursor`，Kimi/WorkBuddy/MiniMax用`kimi-workbuddy`，其他终端Agent用`universal-terminal`。

根据[准备说明](references/preparation.md)创建paper-request.json。能力只填写image_generation、visual_inspection、docx_export、pdf_export四项，值为true、false或null；null表示未确认，不能当成不可用。方向已有默认features，模型仅在必要时填写feature_overrides。

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" prepare --root "<OUTPUT_DIR>" --request paper-request.json
```

中文THESIS未指定层次和字数时默认25,000。用户值和模板优先。TITLE_POLICY默认为ASK；用户明确要求不中断完成时可用SAFE_DOWNGRADE，只允许“影响→关联”“实现→设计”“实证→综述”等预定义降级，并在最终答复公开。

准备入口生成唯一final-execution-prompt.md、Manifest和派生记录。FULL_AUTONOMY读取同方向full；明确历史执行失败或用户指定WEAK_MODEL时读取同源compact。不要再分别填写Profile、模块或合成文件；不要在执行时返回公共规则目录。

## 3. 安全补模块

执行后发现确需统计、公式、SVG或文档模块时，创建prompt-amendment.json并运行：

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" prepare --amend --root "<OUTPUT_DIR>" --request prompt-amendment.json
```

amend生成版本化的新参数、任务选择和执行MD，保留旧文件。已有产物的模块不能移除；正文开始后相关图片、文档和验收阶段会失效并须重检。不得借amend改方向、数据性质或未授权题目。

## 4. 执行唯一MD

从头到尾读取活动执行提示词并持续生产。除Skill规则和用户授权材料外，只在OUTPUT_DIR写入，不读取其他模型目录。缺真实材料时诚实降级主张，不能编实验、文献、数据、案例或性能。

图表严格区分：统计图由真实数据和代码生成；精确电路/引脚/结构图读取领域源表；普通流程、架构和概念图在真实生图工具可用时必须逐张生图。成功生图或其中文覆盖PNG必须作为final_embed_file进入DOCX/PDF，不能被同号SVG替换。中文论文图中文字默认中文。

GUIDED/WEAK_MODEL使用同一[阶段辅助](references/profiles/staged-assistance.md)。接近上下文上限先保存检查点；错误只返回受影响阶段，不全面重写。

## 5. 四类机械检查

完成实际专业、图形和页面观察后，按[观察模板](references/qa-observations.example.json)写qa-observations.json。它记录具体问题和文件回执，不含作者分数或“独立审稿”身份。

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" check --root "<OUTPUT_DIR>" \
  --docx "<题目_时间戳.docx>" --pdf "<题目_时间戳.pdf>"
```

入口只运行证据、图片、公式和交付四类检查，再生成14-adjudicated-status.json。哈希、退出码和文件齐全不能证明专业结论正确；Critical/Important不能由模型自述覆盖。最终答复只采用权威RESEARCH_STATUS、DELIVERY_STATUS和FINAL_STATUS。

需要数字评分时，在写作流程结束后使用`eval/build_review_package.py`冻结交付包，交给另一会话、另一模型或人工盲评。写作模型不得给自己的论文打分或用自述冒充独立结果。

## 6. 续跑与局部模式

RESUME使用prepare_resume.py验证活动提示词、Manifest和阶段摘要；REVISE_ONLY使用compose_revision.py和修改影响清单。AUDIT_ONLY必须输出到原稿目录之外。FIGURES_ONLY只处理授权图片；需要重导时才连带检查公式与文档。

若最终DOCX/PDF、正文、文献、图表或检查报告缺失，必须报告PARTIAL/FAIL和具体能力缺口，不能虚报PASS。
