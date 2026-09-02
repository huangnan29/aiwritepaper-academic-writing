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
方向来源：references/directions/literature-review-synthesis.md
-->

# literature-review-synthesis 紧凑论文生成提示词

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
<!-- 方向CORE来源：references/directions/literature-review-synthesis.md -->

PROMPT_ID: `literature-review-synthesis`

## 范文结构依据

- 公开示例：AIWritePaper 公开文献综述范文
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=1891120700643606528
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

叙述性综述、系统综述、范围综述、研究进展与理论综合。

## 不适用或高风险情形

没有完整检索和筛选记录却声称“系统综述”或“穷尽全部研究”。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 综述问题与范围
2. 协议与数据库
3. 检索式和筛选标准
4. 研究特征与质量评价
5. 主题或定量综合
6. 争议、异质性与偏倚
7. 研究空白
8. 结论与更新日期

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 数据库检索记录
- 去重文件
- 纳排表
- 全文判断理由
- 质量评价表
- 数据提取表和协议

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：至少两库交叉：Web of Science或Scopus（INSTITUTION_REQUIRED）加学科库（医学加PubMed与Cochrane，中文加CNKI与CBM，计算机加IEEE与ACM）。
- 证据与全文：PRISMA声明原文；PROSPERO注册记录（OPEN_WEB）；纳入研究的出版社全文。
- 开放路线：无机构权限时改用OpenAlex加PubMed或Europe PMC等开放库完成双库交叉（OPEN_API），并在检索日志中声明库覆盖面的局限。
- 不宜作核心引文：单库“搜到什么写什么”；无检索式的“研究现状”。
- 信源核验门槛：系统综述必须至少两库、完整布尔检索式与PRISMA流程记录；预印本单独报告，除非协议允许不混入正式纳入集。

## 图表与表格

PRISMA流程、概念框架、证据地图和时间线；表格包括检索式、研究特征和质量评价。

## 无材料时的降级规则

检索范围有限时明确为叙述性或快速综述，并披露覆盖边界。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 先确定综述类型

- 系统综述：预先定义问题、至少两个互补数据库、完整检索式、去重、双阶段筛选、排除理由、质量/偏倚评价和可复算流程。
- 范围综述：回答概念、证据类型和研究空白，仍需透明检索与筛选，但不必把异质研究强行合并效应。
- 快速综述：明确删减了哪些系统步骤、由此产生何种偏倚。
- 叙述综述：围绕问题形成解释性综合，不得使用“穷尽”“系统纳入”等方法承诺。

材料只支持后一类型时，必须使用TITLE_POLICY处理标题，不能保留“系统综述”再在局限中承认只检索一个网页。

## 三个集合不得混淆

分别维护发现/映射候选集、全文评估集和正式纳入/引用集。每个集合给出定义、唯一标识、去重规则和分母。用于趋势图的映射样本可以大于全文样本，但图题必须写清口径；参考文献数量不能冒充纳入研究数量。

预印本与正式版按题名、作者、研究对象、注册号和DOI识别同一工作身份，优先保留正式版并记录版本关系。会议摘要、协议、二次综述和主研究不能在同一统计中重复计算。

## 分类与抽查合同

主题分类要读取研究对象、方法、任务和结果，不能只按摘要背景词命中。生成统计图或证据地图前建立`review/screening-audit.csv`，记录`record_id,title,set_role,classification,decision_basis,reviewer_status,notes`。至少抽查随机样本、类别边界样本、异常项和高影响主张所依赖记录；修订分类后重新计算全部图表。

像“文章背景提到AI写作”但研究实际分析一般反馈系统的记录，不得归入AI写作干预。无法取得全文时只能做题录/摘要级映射，不能提取全文方法、样本或结论。

## 综合方式

先制作研究特征表，再决定主题综合、框架综合、叙事综合或定量合并。不同研究设计、结局定义、时间窗和比较组不可比时，不计算伪精确总效应。每个主题都要说明支持研究、反例、证据质量和适用范围；研究空白不能仅由“文献少”推出，应指出现有设计无法回答的具体问题。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 系统/范围综述至少双库并保存完整检索式
- 去重、纳排和全文数量可复算
- 题录层与全文层综合严格分开

### 数据不足时的题目与主张处理

单库、分页截断或无筛选流程时不得使用系统综述名称，改为范围性梳理或叙述综述。
<!-- /task-module -->
