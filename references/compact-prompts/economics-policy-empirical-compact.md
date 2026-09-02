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
方向来源：references/directions/economics-policy-empirical.md
-->

# economics-policy-empirical 紧凑论文生成提示词

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
<!-- 方向CORE来源：references/directions/economics-policy-empirical.md -->

PROMPT_ID: `economics-policy-empirical`

## 范文结构依据

- 公开示例：经济学范文《中美贸易战对中国经济的影响分析》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=1949493723062599680
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

宏观经济、产业经济、贸易、金融、区域经济和政策评估。

## 不适用或高风险情形

没有数据和识别策略却声称政策造成某个经济结果。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 问题、制度背景与贡献
2. 文献与理论机制
3. 研究假设
4. 数据、变量和描述统计
5. 模型与识别策略
6. 基准结果
7. 稳健性、机制和异质性
8. 政策含义与限制

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 官方或授权数据集
- 变量字典
- 清洗脚本
- 模型代码
- 识别假设
- 稳健性检验和可复现输出

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：EconLit、JSTOR、Web of Science SSCI（INSTITUTION_REQUIRED）；CNKI经济学核心刊（注明CSSCI目录版本）。
- 证据与全文：世界银行、IMF、WTO开放数据（OPEN_API或OPEN_WEB）；国家统计局、海关总署官网；中国人民银行、发改委政策原文；CSMAR、Wind、CEIC（INSTITUTION_REQUIRED，注明授权）。
- 开放路线：世行与IMF开放数据、统计局官网、NBER工作论文（OPEN_WEB，标注工作论文状态）、OpenAlex（OPEN_API）；SSRN未审稿只作线索并降级表述。
- 不宜作核心引文：财经自媒体解读、SSRN未审稿当已发表因果证据。
- 信源核验门槛：数据记录表号、期次与下载日期；工作论文与正式发表版本去重；政策引用注明文号与发布机构。

## 图表与表格

制度时间线、理论机制、趋势和平行趋势、真实估计图；表格包括变量、描述统计、回归和稳健性。

## 无材料时的降级规则

无可用数据时改为政策史、理论机制或证据综述，不写因果效应。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 识别策略闭合

先定义政策/冲击、处理单位、时点、暴露强度、结果变量、样本窗口和反事实。描述性差异只能支持关联。DID需解释平行趋势、处理时点和溢出；分期处理考虑异质处理效应。断点需证明阈值规则与操纵检验；工具变量需论证相关性、排除限制和单调性；面板固定效应不能自动消除时变混杂。

变量口径、价格基期、行政区划、缺失、缩尾、权重和聚类层级可复查。主结果、稳健性、机制和异质性预先分层，不能在看到结果后把探索性分析改写成主假设。机制变量若本身受处理影响，不应当作普通控制项。

没有真实数据、代码和回归输出时写识别方案或政策综述，不填系数、标准误、显著性和经济效应。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 政策效应主张须明确政策时点、暴露定义、样本和实际识别策略；关联研究只解释关联
- 采用DID或事件研究时检查前趋势与平行趋势假设，并在适用时做安慰剂检验；这些不是所有政策研究的统一必做项
- 采用多时点处理DID时检查异质效应偏差；采用其他设计时检查该设计自己的识别假设

### 数据不足时的题目与主张处理

识别假设不成立或只有横截面关联时删除因果措辞，建议收窄题目为关联、差异或识别限制；实质改题须符合用户授权，不能默改。
<!-- /task-module -->
