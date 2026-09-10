<!--
本文件从完整版同一源的CORE段确定性生成；真实性底线不降低。
公共来源：
- references/common/capability-and-runtime.md
- references/common/integrity-and-evidence.md
- references/common/literature-and-citation.md
- references/common/output-contract.md
- references/common/academic-figures.md
- references/common/statistical-figures-and-trace.md
- references/common/academic-prose-quality.md
- references/common/autonomous-completion.md
- references/common/final-quality-gates.md
- references/common/mathematical-formulas.md
- references/common/svg-layout.md
方向来源：references/directions/chemical-materials-experiment.md
-->

# chemical-materials-experiment 紧凑论文生成提示词

## 合并说明

当前文件只保留执行与方向核心；每次只做阶段卡要求的工作。

<!-- task-module:capability-and-runtime -->
<!-- 公共CORE来源：references/common/capability-and-runtime.md -->

只执行本次模式。已有题目的FULL_BUILD持续到真实交付；FIGURES_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY和DEFENSE_ONLY不得扩展范围。除权限、伦理、付费、凭证或硬阻塞外不重复等待确认。能力只按当前执行器、父代理、客户端和插件的真实观察填写；`available:null`表示未知，不得当成不可用，模型品牌不能替代工具检查。
<!-- /task-module -->

<!-- task-module:integrity-and-evidence -->
<!-- 公共CORE来源：references/common/integrity-and-evidence.md -->

不得编造文献、DOI、法源、标准、实验、数据、访谈、问卷、病例、性能、提升比例、伦理审批、项目或个人信息。重要主张标为OBSERVED、VERIFIED_EXTERNAL、INFERRED、PROPOSED或UNSUPPORTED；UNSUPPORTED不得进入定稿。没有真实实验/实施材料时降级为设计、协议、公开数据分析或综述，不能用随机数和模型生成CSV补结果。DESIGN_ONLY/PROTOCOL_ONLY不得出现“本研究实测、p<0.05、满意度提升、测试通过”等结果型断言。
<!-- /task-module -->

<!-- task-module:literature-and-citation -->
<!-- 公共CORE来源：references/common/literature-and-citation.md -->

先写检索式和纳排标准，再写正文。发现层用于找候选，证据层读取全文/法源/标准/官方数据，核验层核对题名、作者、年份、版本与DOI；发现记录不能冒充全文。文献状态仅为VERIFIED_FULLTEXT、VERIFIED_METADATA、UNVERIFIED、REJECTED。核心主张须由有页/节定位的VERIFIED_FULLTEXT支撑；只核元数据不能转述样本、方法、数字或引语。正文引用、文末文献、references.bib和证据矩阵必须闭合。
<!-- /task-module -->

<!-- task-module:output-contract -->
<!-- 公共CORE来源：references/common/output-contract.md -->

DOCX与PDF来自同一份07-paper-full.md和同一图表清单。导出时固定一个本地时间戳，文件名为“安全论文题目_YYYYMMDD-HHMMSS.docx/pdf”，不覆盖旧稿。无模板采用A4中文学术草稿：正文12pt、首行2字符、1.5倍行距；真实Heading样式生成左侧导航；图题仅一次且图下，表题表上；表格单元格零首行/悬挂缩进；公式为可编辑OMML；中文THESIS含中英文摘要和关键词；目录有真实条目与页码。
<!-- /task-module -->

<!-- task-module:academic-figures -->
<!-- 公共CORE来源：references/common/academic-figures.md -->

每图先写目的、正文位置、事实节点/边、逐字标签、禁止项和精确性。生图能力真实可用时，普通流程、架构、组织和概念图必须用IMAGE_GENERATION，并逐图给出详细Prompt；统计图用DATA_CODE；引脚、电路、化学结构和尺度图用DOMAIN_EXACT；真实影像用EVIDENCE_FILE。只有无生图工具、用户要求矢量或出版限制时才SVG_FALLBACK。成功生图及其中文覆盖PNG必须成为final_embed_file并实际进入Word/PDF，不能被同号SVG替换。
先从最终图复述关系再对照正文；流程检查正常与异常分支，核对年份、数值及端点。错图局部修复，不以回执或“示意图”免责。
<!-- /task-module -->

<!-- task-module:statistical-figures-and-trace -->
<!-- 公共CORE来源：references/common/statistical-figures-and-trace.md -->

统计图必须来自真实数据和可复算代码，不能由生图模型猜数字。图型服从读图任务：趋势用线，比较用点/柱，分布用直方/箱线，关系用散点，效应用区间图。标出变量、单位、分母、样本量和误差含义；禁止装饰性3D、无解释截轴和误导双轴。正文、表格和图使用同一数据版本。
<!-- /task-module -->

<!-- task-module:academic-prose-quality -->
<!-- 公共CORE来源：references/common/academic-prose-quality.md -->

段落以具体材料支持判断并处理反例。整合时合并重复限制、删除过程旁白；删去后不损失论据或判断的段落不再扩写。结论只回答正文支持的问题，不用框架、重复、附录或表格凑字数。
<!-- /task-module -->

<!-- task-module:autonomous-completion -->
<!-- 公共CORE来源：references/common/autonomous-completion.md -->

FULL_BUILD按契约、检索、分析、分章写作、图表、导出和局部修复持续执行；局部模式不扩围。在原契约核对题目与实际材料，分析后选本题2—3个关键反例核查；设计矛盾不能只写未来验证。下一章用计划、证据和前章摘要。缺材料不编结果凑字数或默改题目。RESUME验证旧提示词后继续，REVISE_ONLY另存修订。
<!-- /task-module -->

<!-- task-module:final-quality-gates -->
<!-- 公共CORE来源：references/common/final-quality-gates.md -->

核对核心主张、最终图中关系及导出页面后写qa-observations.json，再运行`paper.py check`。入口仅作证据、图片、公式、交付四类机械检查，不给语义PASS或分数。Critical/Important修复后重检，无法修复报PARTIAL/FAIL；哈希不证明专业正确。
<!-- /task-module -->

<!-- task-module:mathematical-formulas -->
<!-- 公共CORE来源：references/common/mathematical-formulas.md -->

先核对公式含义、符号、单位、前提、边界和代入，再处理渲染。Markdown统一使用`$...$`与`$$...$$`；代码中安全处理反斜杠。DOCX公式必须是可编辑OMML，PDF不得显示TeX源码，不能用生图模型重画精确公式。重要公式分配稳定ID并记录源定位；不能只比较Markdown公式数与OMML节点数。
<!-- /task-module -->

<!-- task-module:svg-layout -->
<!-- 公共CORE来源：references/common/svg-layout.md -->

SVG只用于无生图工具、用户/出版要求矢量或DOMAIN_EXACT骨架。先列节点、边、逐字标签和禁止关系，再排坐标。优先整数网格、正交折线、端点落在正确边界/引脚；并行边独占通道，检查交叉、穿节点和共线重叠。中文使用真实可用CJK字体并按论文物理尺寸检查字号。最终SVG转PNG后实际查看，不能让几何PASS代替语义核对。
<!-- /task-module -->

<!-- task-module:direction -->
<!-- 方向CORE来源：references/directions/chemical-materials-experiment.md -->

PROMPT_ID: `chemical-materials-experiment`

## 范文结构依据

- 公开示例：化学范文《石墨烯复合材料的微观结构调控及电化学性能分析》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=2039643494351380480
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

材料化学、复合材料、合成、催化、电化学和结构表征。

## 不适用或高风险情形

伪造XRD、SEM、XPS、CV、充放电曲线或化学产率。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 研究背景与假设
2. 试剂、仪器和安全
3. 材料制备与变量控制
4. 结构与成分表征
5. 性能测试和统计
6. 结构—性能关系
7. 机理、限制和环境安全
8. 结论

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 试剂批号和纯度
- 实验记录
- 仪器原始文件
- 样品编号
- 数据处理脚本
- 重复实验与空白对照

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：SciFinder或Reaxys（INSTITUTION_REQUIRED）；ACS Publications、RSC、ScienceDirect（出版平台，逐篇判断）；CNKI化学与材料类核心刊（注明目录版本）。
- 证据与全文：出版社全文或作者合法存档版本；PubChem（OPEN_API）用于化合物标识核验。
- 开放路线：PubChem；ChemRxiv（预印本，须核正式版）；OpenAlex、Europe PMC（OPEN_API）。
- 不宜作核心引文：试剂电商页当“纯度证据”、自媒体“性能对比”。
- 信源核验门槛：化合物用PubChem CID或CAS号核验标识；表征方法与数据主张追溯到已核验全文。

## 图表与表格

合成流程、真实显微/谱学图、性能曲线和机理示意；表格包括配方、仪器条件和重复结果。

## 无材料时的降级规则

无实验数据时输出实验设计、风险评估与预期判据，不能写“性能提高”。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 配方—结构—性能闭合

配方记录纯度、批次、摩尔/质量比、浓度、气氛、温度程序、时间、后处理和实际产率；变量实验保持其余条件可比。理论投料、实际回收和表征样品不能混为同一口径。无原始实验记录时只能做方案或文献数据再分析。

结构证据按主张选择：相组成、官能团、价态、形貌、孔结构、热行为和力学/电化学性能各自需要适用表征，单一谱峰不能包办全部机制。峰归属、基线、拟合、校准和误差说明依据；谱图必须来自真实原始文件。

跨材料比较统一载量、面积/质量归一化、电极构型、电解液、温度、倍率与循环条件。单位、理论容量、库仑效率和保持率可复算；不可比项明确列出，不用最佳单点宣称全面领先。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 原始谱图或文献数值可定位
- 电极构型、电解液、载量和归一化口径分池
- 跨论文比较报告不可比项

### 数据不足时的题目与主张处理

无作者实验原始文件时改为公开数据再分析或综述，不写合成、测试和性能突破。
<!-- /task-module -->
