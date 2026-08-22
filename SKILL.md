---
name: aiwritepaper-agentic-skill
description: 根据论文题目和可用材料选择一个方向专属完整提示词，将本次参数与该提示词合成为单一最终执行MD，并持续完成中文论文、配图、DOCX、PDF或验收。没有题目时可推荐10个可行题目；不用于编造研究、数据、文献或规避检测。
license: MIT
metadata:
  author: huangnan29
  version: "0.4.2"
  repository: https://github.com/huangnan29/aiwritepaper-agentic-skill
---

# AIWritePaper 单提示词执行入口

本Skill只负责两件事：选择一个论文方向；让执行阶段完整读取一份自包含提示词。不要在论文生产过程中继续跳转公共规则、配图子Skill或Skill自带脚本。

## 一、先确定请求类型

- 用户已有完整题目：直接判断方向，不重复询问题目，不等待确认。
- 用户要求完整论文：使用 `FULL_BUILD`。
- 用户已有正文，只要求配图：使用 `FIGURES_ONLY`。
- 用户已有定稿，只要求DOCX/PDF：使用 `EXPORT_ONLY`。
- 用户只要求检查：使用 `AUDIT_ONLY`。
- 用户没有题目：一次询问专业、细分方向、论文层次、可用材料和方法偏好；信息足够时直接推荐10个题目。每个题目给出核心问题、方向、方法、证据需求、可行性、风险和材料不足时的降级题目。选题阶段不生成论文。

已有题目且用户要求开始执行时，默认 `AUTO_BENCHMARK`：除权限、伦理、凭证、付费或无法继续的硬阻塞外，不停下来等待用户确认。

已有完整题目并触发 `FULL_BUILD` 时，用户没有明确指定正文长度则固定使用 `TARGET_LENGTH: 25000`，允许误差±10%，正文下限为22,500。用户明确给出的字数目标始终优先，不得被默认值覆盖。

## 二、选择唯一方向

不要只看专业名称，要同时判断研究对象、研究动作、证据形式和成果形态。选择一个首选完整提示词：

| 题目信号 | 唯一完整提示词 |
|---|---|
| SpringBoot、管理系统、平台、数据库、软件架构、设计与实现 | `references/compiled-prompts/software-system-engineering-full.md` |
| 机械零件、材料选型、热处理、工艺路线、强度校核 | `references/compiled-prompts/mechanical-material-process-full.md` |
| 电路、接口、PCB、器件选型、仿真、信号测试 | `references/compiled-prompts/electronic-circuit-design-full.md` |
| 物理材料、能带、光电性能、物性测量、数值模拟 | `references/compiled-prompts/physical-materials-experiment-full.md` |
| 合成、复合材料、表征、电化学、反应机理 | `references/compiled-prompts/chemical-materials-experiment-full.md` |
| 企业运营、商业模式、组织管理、案例分析 | `references/compiled-prompts/management-case-analysis-full.md` |
| 区域、坡面、土壤、水文、遥感、GIS、空间分布 | `references/compiled-prompts/geography-environmental-empirical-full.md` |
| 细胞、分子通路、药物处理、实验型医学期刊 | `references/compiled-prompts/biomedical-experimental-journal-full.md` |
| 机器学习、分类预测、特征工程、模型评估、可解释性 | `references/compiled-prompts/machine-learning-applied-empirical-full.md` |
| 教学、课程、学习者、教育技术、教学干预 | `references/compiled-prompts/education-applied-research-full.md` |
| 文旅产品、视觉、交互、空间、服务设计、设计实践 | `references/compiled-prompts/art-design-practice-full.md` |
| 贸易、产业、宏观政策、计量模型、经济影响 | `references/compiled-prompts/economics-policy-empirical-full.md` |
| 著作权、侵权、法律规制、法条、判例、规范分析 | `references/compiled-prompts/legal-normative-analysis-full.md` |
| 患者护理、护理干预、临床观察、病例资料 | `references/compiled-prompts/clinical-nursing-research-full.md` |
| 数学思想、数学教学、题型、课堂策略 | `references/compiled-prompts/mathematics-education-full.md` |
| 作家、作品、意象、叙事、修辞、文本细读 | `references/compiled-prompts/literature-textual-analysis-full.md` |
| 明确要求期刊IMRaD且研究方法已确定 | `references/compiled-prompts/general-journal-imrad-full.md` |
| 研究进展、现状与展望、系统综述、范围综述 | `references/compiled-prompts/literature-review-synthesis-full.md` |
| 在职、MBA实践、岗位改进、组织问题与行动方案 | `references/compiled-prompts/professional-work-report-full.md` |

“系统”要根据源码、图纸或电路证据区分软件、机械和电子；“影响因素”要根据数据、问卷或访谈区分方法；“期刊论文”只是成果格式，先判断研究方法。没有源码、图纸、实验、病例或数据时，选择相同学科方向，但在最终提示词中诚实降级为设计方案、验证协议、公开数据研究、规范分析或综述。

## 三、建立单一最终执行提示词

确定方向后必须完整读取所选 `*-full.md`，从文件开头读到结尾。该文件已经包含通用主提示词、近期配图规则、弱模型持续完成机制和方向增量；不要再读取 `references/common/`、`references/directions/`、`references/figure-skills/`、嵌套Skills或Skill脚本来补充执行规则。

在用户输出目录创建 `final-execution-prompt.md`，内容按以下顺序组成：

1. 本次真实运行参数：模式、输出目录、模型标签、题目、论文类型、学科、研究对象、核心问题、语言、目标正文长度、引用格式、最低文献数、图片数、表格数、模板和用户材料；
2. 用户明确的目录、工具、真实性、格式和停止条件；
3. 所选 `*-full.md` 的完整原文。

用户没有另行指定 `OUTPUT_DIR` 时使用当前工作目录；没有指定 `MODEL_LABEL` 时使用当前工作目录名称。目录边界明确时，除读取Skill与用户授权材料外，只在该输出目录写入，不访问其他模型结果目录。

直接给题目且未提供字数时，写入 `TARGET_LENGTH: 25000`，不得留空、不得改成模型自行估计值。正文统计范围为第一章至结论的主体论述，不含摘要、目录、参考文献、致谢、附录、代码和图表题注。

不得概括、删减或改写所选完整提示词。写入后重新从头到尾读取 `final-execution-prompt.md`，后续只把它作为论文生产指令。若无法完整读取或写入该文件，明确报告硬阻塞；不得用当前 `SKILL.md` 的简短说明替代正式提示词。

## 四、持续执行

按照 `final-execution-prompt.md` 直接执行。已有题目的 `FULL_BUILD` 不输出路由方案后停顿，不要求用户再次批准大纲，不把论文正文只留在聊天窗口。

执行模型自主选择当前可用工具。只有数据统计图、DOCX/PDF导出或其他当前任务确实需要时，才在本次输出目录创建项目专用代码；不得调用Skill目录中的固定Python流水线决定章节、内容、状态或PASS。

图片工具已经成功生成某图时，正文、DOCX和PDF必须插入该生成图或由它合成的最终PNG；同名SVG只能作为备用或修正源。最终嵌入路径以图表清单中的 `final_embed_file` 为唯一依据，不能按文件名或扩展名自行改选SVG。

最终答复只报告真实完成内容、论文题目、实际正文长度、文献/图片/表格数量、DOCX/PDF/QA路径、能力缺口和最终状态。任何硬目标未满足时不得标记 `PASS`。
