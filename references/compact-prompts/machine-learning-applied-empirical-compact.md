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
方向来源：references/directions/machine-learning-applied-empirical.md
-->

# machine-learning-applied-empirical 紧凑论文生成提示词

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
<!-- 方向CORE来源：references/directions/machine-learning-applied-empirical.md -->

PROMPT_ID: `machine-learning-applied-empirical`

## 范文结构依据

- 公开示例：互动范文《基于机器学习的银行信贷评分模型研究》
- 来源：https://www.aiwritepaper.com/paper_preview?pic=bank
- 使用边界：只学习章节组织与交付形态，不把范文页面中的模型效果和业务结论作为证据。

## 适用范围

分类、回归、预测、风险评分、推荐、异常检测及机器学习在金融、管理、医疗、工业等场景的应用研究。

## 不适用或高风险情形

没有合法可用的数据集、数据字典、训练环境和评估记录，却报告准确率、AUC、F1、提升比例或业务价值。

## 方向专属输入

在研究契约中冻结任务定义、预测时点、标签、数据来源、样本划分、基线、评价指标、随机种子、软件与硬件环境、伦理与隐私要求。明确训练集、验证集和测试集之间的隔离规则。

## 推荐结构

1. 问题背景、任务定义与研究问题
2. 相关工作、理论和应用约束
3. 数据来源、样本、标签与质量控制
4. 特征工程、基线与模型方法
5. 训练协议、超参数和复现环境
6. 独立评估、消融、稳健性与误差分析
7. 可解释性、公平性、隐私和部署边界
8. 结论、局限与后续验证

结构应按题目和材料调整。每个三级标题说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 数据集许可、版本、样本选择和字段字典；
- 去重、缺失处理、异常处理和防止数据泄漏的脚本；
- 基线模型和选择依据；
- 训练配置、随机种子、依赖版本和日志；
- 独立测试结果、置信区间或重复实验；
- 误差案例、子群体表现和适用边界；
- 涉及个人或敏感数据时的伦理、隐私和安全材料。

## 文献信源

- 发现与筛选：IEEE Xplore、ACM Digital Library（INSTITUTION_REQUIRED）；NeurIPS、ICML、ICLR等会议官方论文集（OPEN_WEB）；DBLP（OPEN_WEB，纯题录）；CNKI计算机类核心刊（注明目录版本）。
- 证据与全文：会议官方论文集与OpenReview全文（OPEN_WEB）；UCI、OpenML、Hugging Face Datasets官方数据卡（OPEN_WEB，记录许可证）。
- 开放路线：arXiv cs.LG/cs.AI/stat.ML（预印本，须核是否已正式发表）；Semantic Scholar、OpenAlex（OPEN_API）；Papers with Code仅作线索。
- 不宜作核心引文：Kaggle讨论区数字、无代码与数据划分的博客“SOTA复现”。
- 信源核验门槛：基线数字追溯到论文表格或官方排行榜；数据集记录名称、版本、划分与许可证；预印本与正式版去重。

## 图表与表格

可使用数据流程、样本划分、模型结构、学习曲线、ROC/PR、校准、混淆矩阵、特征解释和误差分布。每张性能图必须来自真实运行输出，并标明数据划分、样本量和指标定义。

## 无材料时的降级规则

没有数据和运行日志时，只能输出数据需求、基线设计、实验协议和预期验收标准，或降级为文献综述；不得生成任何模型性能数字。

## 方向质量门槛

- 任务定义没有标签泄漏或时间穿越；
- 基线、数据划分和指标选择合理；
- 结果来自独立测试而非训练集；
- 超参数调优没有污染最终测试集；
- 报告不确定性、误差、公平性和外推边界；
- 代码、环境和数据处理能够复现；
- 与公共规则共同执行后才允许进入最终验收。

## 建模证据闭合

冻结任务、预测时点、目标定义、分析单位、数据版本和划分原则。按主体/时间/机构分组避免同源样本跨训练测试；预处理、特征选择、调参与阈值选择只在训练折内完成。独立测试集只能在最终模型冻结后使用。

基线包括简单规则、传统模型和与任务相称的强基线；消融一次改变一个关键因素。分类报告混淆矩阵、区分度、校准和阈值后指标；回归报告误差分布与基线；生成任务说明人工/自动评价的盲法和一致性。子群、公平性和部署测试只在适用时进行。

没有真实数据、许可、代码运行和日志时写建模协议，不生成准确率、AUC、损失曲线和部署收益。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 原始数据与许可真实存在
- 监督学习中的预处理和模型选择仅在训练折内完成，其他任务使用对应的无泄漏设计
- 按任务报告独立或嵌套评价及误差；概率预测需要校准检查，有适用子群时检查差异，不强行套给所有任务

### 数据不足时的题目与主张处理

随机或演示数据只能用于教程；无真实运行日志时降为建模协议，不报告AUC、准确率和部署价值。
<!-- /task-module -->
