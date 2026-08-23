# 题目到方向提示词的路由规则

## 路由维度

不要仅靠专业名称匹配。依次判断：

1. 学科与细分方向；
2. 研究对象是系统、装置、材料、群体、企业、空间、法律规则还是文本；
3. 研究动作是设计、实验、测量、解释、比较、评价、综述还是规范论证；
4. 可用证据是源码、图纸、实验数据、空间数据、问卷、访谈、病例、公开案例、法源还是原始文本；
5. 最终成果是工程方案、实证结论、理论解释、规范建议、综述、期刊短文或工作报告。

## 方向表

| 典型信号 | 首选完整提示词 |
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

## 冲突消歧

- “系统”可能是软件系统，也可能是机械或电路系统；看核心证据是源码、图纸还是电路原理图。
- “影响因素”可能是计量实证、问卷实证或定性访谈；看是否存在结构化数据和统计模型。
- “以某企业为例”优先案例研究；若有面板数据和回归模型，可路由经济实证。
- “应用研究”不能直接决定类型；继续判断是否包含实验、教学干预、工程实现或文本分析。
- “期刊论文”是成果格式，不是研究方法。先确定学科方法，再使用通用期刊提示词补充篇幅和结构要求。
- “设计与实现”在没有源码、图纸、原型、接口或测试记录时，应建议改为“设计方案”“架构设计”或“验证方案”。

## 路由确认格式

```text
题目：
研究问题：
专业与细分方向：
研究方法类型：
唯一提示词：
证据需求：
材料缺口：
降级方案：
```
