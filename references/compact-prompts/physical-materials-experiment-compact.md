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
方向来源：references/directions/physical-materials-experiment.md
-->

# physical-materials-experiment 紧凑论文生成提示词

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
<!-- /task-module -->

<!-- task-module:statistical-figures-and-trace -->
<!-- 公共CORE来源：references/common/statistical-figures-and-trace.md -->

统计图必须来自真实数据和可复算代码，不能由生图模型猜数字。图型服从读图任务：趋势用线，比较用点/柱，分布用直方/箱线，关系用散点，效应用区间图。标出变量、单位、分母、样本量和误差含义；禁止装饰性3D、无解释截轴和误导双轴。正文、表格和图使用同一数据版本。
<!-- /task-module -->

<!-- task-module:academic-prose-quality -->
<!-- 公共CORE来源：references/common/academic-prose-quality.md -->

段落提出具体判断，说明材料如何支持、反例和边界。相邻段落必须增加信息；列表只用于真实并列关系，不能替代论证。避免连续制造“几层、几维、几阶段”框架、无证据强化、过程旁白和摘要—结论机械复述。结论只回答正文已支持的问题，不能靠重复、附录和表格凑字数。
<!-- /task-module -->

<!-- task-module:autonomous-completion -->
<!-- 公共CORE来源：references/common/autonomous-completion.md -->

FULL_BUILD按研究契约、检索、证据、大纲、分章正文、图表、整合、导出、检查和定点修复持续执行；局部模式只做用户指定部分。下一章使用计划、证据和前章摘要，不反复加载全文。缺材料时完成诚实的设计/协议/综述，不编结果补字数。发现错误只返回受影响阶段；RESUME验证旧提示词和摘要后继续，REVISE_ONLY保留原稿并另存。
<!-- /task-module -->

<!-- task-module:final-quality-gates -->
<!-- 公共CORE来源：references/common/final-quality-gates.md -->

完成专业、图形和页面观察后写qa-observations.json，再运行一次`paper.py check`。入口只执行证据、图片、公式和交付四类机械检查并计算权威状态，不生成论文、语义PASS或数字评分。Critical/Important必须修复；无法修复时明确PARTIAL/FAIL。哈希只绑定文件，检查器成功不证明专业正确。
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
<!-- 方向CORE来源：references/directions/physical-materials-experiment.md -->

PROMPT_ID: `physical-materials-experiment`

## 范文结构依据

- 公开示例：物理范文《二维半导体材料能带结构调控及光电性能研究》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=2039643711029125120
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

凝聚态、半导体、光电、材料物性、计算物理和实验物理。

## 不适用或高风险情形

没有样品、计算输入或仪器数据却绘制能带、光谱或物性曲线。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 研究问题与理论背景
2. 材料体系与调控变量
3. 样品制备或计算方法
4. 表征和测量方法
5. 结果及不确定度
6. 机理讨论与文献比较
7. 局限与可重复性
8. 结论

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 样品批次和制备记录
- 仪器型号与校准
- 原始谱图或计算输入输出
- 数据处理脚本
- 误差和重复测量

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：Web of Science（INSTITUTION_REQUIRED，引文索引非全文）；APS、AIP、ACS等出版社库；CNKI物理与材料类核心刊（注明目录版本）。
- 证据与全文：出版社全文或作者合法存档版本；Materials Project（OPEN_API）、ICSD（INSTITUTION_REQUIRED）等晶体与物性库只作数据来源，不作论文替代。
- 开放路线：arXiv cond-mat（预印本，主张须降级或核正式版）；OpenAlex、Crossref（OPEN_API）；Materials Project。
- 不宜作核心引文：个人主页未发表图、无法回溯仪器文件的二次绘图。
- 信源核验门槛：晶体与物性数据记录数据库名称、版本和条目ID；预印本与正式发表版本去重。

## 图表与表格

实验装置、晶体/能带示意、真实谱图、拟合残差和误差条；表格包括样品、参数和重复性。

## 无材料时的降级规则

没有原始数据时改为理论框架、实验方案或可复现计算协议，不生成结果曲线。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 机制—样品—可观测量闭合

先定义物理机制、可观测量、样品组成/结构、制备历史、环境和测量几何。理论量、计算量和实验量分开；直接带隙、间接带隙、光学边、激子峰和输运激活能不能混为同一“带隙”。

测量记录仪器、校准、分辨率、扫描范围、背景/暗电流、重复与不确定性。谱线拟合说明模型、基线、约束和残差；器件性能统一面积、厚度、扫描方向、稳态/瞬态和环境。数据库材料ID、计算层级与原始下载字节可核。

没有真实计算或实验文件时改为文献数据再分析，不生成光谱、I-V和相图并称为观测。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 数据库原始下载字节与材料ID可核
- 计算层级、实验口径和激子/带隙定义分开
- 光谱、相图和I-V来自真实输出

### 数据不足时的题目与主张处理

无原始计算或实验文件时降为文献数据再分析；模型曲线不得称数据库下载或实验观测。
<!-- /task-module -->
