---
name: aiwritepaper-academic-writing
description: 根据题目和材料完成论文、开题、答辩、学术配图或DOCX/PDF；一次准备合成唯一执行MD，模型自主生产，统一检查后定点修复。不用于编造研究、数据、文献或规避检测。
license: MIT
metadata:
  author: huangnan29
  version: "2.1.0-dev"
  repository: https://github.com/huangnan29/aiwritepaper-academic-writing
---

# AIWritePaper｜AI学术写作全流程

本地开发候选，尚未验证跨模型90分。模型负责方向、研究方法和内容；脚本只做确定性准备、转换和核验，不生成观点、语义PASS或分数。

普通任务只有四个阶段：**准备 → 完整生产 → 统一检查 → 定点修复与交付**。不要把底层兼容文件当作需要逐一手填的新任务。

## 一、准备一次

没有题目时按[选题规则](references/topic-selection.md)一次收集必要信息、推荐10个可行题目；已有题目不要重新询问或等待大纲批准。完整读取[方向路由](references/routing.md)，只选择一个方向。材料不足不能编造，实质改题需要用户授权。

确定模式：完整论文FULL_BUILD；只改图FIGURES_ONLY；只导出EXPORT_ONLY；只检查AUDIT_ONLY；开题PROPOSAL_ONLY；答辩DEFENSE_ONLY。ROUTE_ONLY只给方向，不生产。

根据实际工具观察和用户要求填写一份paper-request.json，字段见[准备记录说明](references/preparation.md)及[模板](references/paper-request.example.json)。不要把示例能力当成真实能力。默认自主执行，字数由统一解析器按用户、模板、层次和兜底计算；中文THESIS层次未知仍为25,000。用户明确值优先。

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" prepare --root "<OUTPUT_DIR>" --request paper-request.json
```

这个入口一次生成参数、能力记录、Profile、模块选择、Manifest骨架和final-execution-prompt.md。不再分别运行默认字数、Profile选择、合成命令，也不手抄它们的派生文件。PREPARED_NOT_EXECUTED只表示完成准备，不表示论文已生成。

现有目录已准备过时禁止覆盖。继续原运行使用paper.py resume --root <OUTPUT_DIR>；读取续跑计划，从未完成处继续，不能重新路由或重建提示词。按意见改稿使用[REVISE_ONLY规则](references/deliverables/revision.md)和原compose_revision.py，不全面重写或覆盖旧定稿。

## 二、完整生产

从头到尾读取一次final-execution-prompt.md，只按这一份MD执行当前模式，不继续翻读多个公共规则。研究计划可把契约、大纲和论证安排合写；模型主要维护正文、真实证据、图表与必要研究文件，而非相同事实的多份状态表。

已有题目时AUTO_COMPLETE（兼容AUTO_BENCHMARK）持续完成；除权限、伦理、凭证、付费或无法继续的硬阻塞外不等待确认。强模型保持自主性；只有明确执行困难才附加阶段卡，不能因为缺材料、配额或诚实设计稿而降档。

有实际生图能力时，语义图使用图片生成；数据图用真实数据代码，领域精确图核对原始结构。中文标签、SVG字体/走线、公式、题注、目录和默认版式按合入模块执行。成功图片不得被备用SVG覆盖，最终嵌图只认final_embed_file。

输出正文与真实DOCX/PDF，文件以“安全论文题目_YYYYMMDD-HHMMSS”命名。模型/用户必须判断的研究性质和引用方式在契约中明确；研究实际变化时更新一次，不让工具猜研究是否完成。

## 三、统一检查

完成实际专业审查与最终页面/图形观察后，集中记录qa-review.json；没有独立审稿来源时写SELF，未评分就不填写数字。不能用“已看过”或一串PASS替代具体证据。

```bash
uv run python "<SKILL_DIR>/scripts/paper.py" check --root "<OUTPUT_DIR>" --docx "<正式Word文件>" --pdf "<正式PDF文件>"
```

已由导出工具正确填写最终路径时可省略--docx/--pdf；它们只登记真实文件并计算摘要。研究性质未确定时用--claim-level显式给出OBSERVED_STUDY、DESIGN_ONLY、PROTOCOL_ONLY或REVIEW_SYNTHESIS，不填三套自报PASS。

检查入口自动派生兼容审计视图、运行模式适用的文献/图表/公式/文档/质量检查、最后裁决，并汇总到12-final-qa-report.md。旧报告保留在.audit-logs中，失败不能读旧PASS；退出码0也可能表示PARTIAL。--plan只显示计划，不写文件或宣称通过。

AUDIT_ONLY必须指定源目录之外的新--audit-dir，检查在副本进行，原稿及旧报告只读。FIGURES_ONLY未要求重导时不运行文档生产；要求重导时同时检查公式和文档。导出不重新生图或写正文，但仍核对已有材料与最终文件，不能把过期报告当成未变化。

## 四、定点修复与交付

只修报告定位的实际问题，再用同一check入口复查；不反复重写整篇，不通过改分数解决错误。报告未解决问题、真实文件及当次状态，不能用作者自评、哈希或单元测试声称论文稳定90分。

底层工具与旧CLI继续兼容，细节见[准备说明](references/preparation.md)、[模式矩阵](references/mode-checker-matrix.json)和[原生拼接回退](references/prompt-composition.md)。Python不可用时如实记录能力缺口，不能假装已经运行统一检查。维护构建与[57任务基准](references/benchmarks/strong-model-benchmark.json)不属于论文生产步骤；真实论文A/B仍是发布前的独立工作。
