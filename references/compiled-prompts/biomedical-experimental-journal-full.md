<!--
本文件已由Skill维护流程预先合成为单一完整提示词；运行时请完整读取，不要继续加载其他规则。
公共来源（固定顺序）：
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
方向来源：
- references/directions/biomedical-experimental-journal.md
来源清单结束。
-->

# biomedical-experimental-journal 完整论文生成提示词

## 合并说明

本文件由公共规则与当前方向规则合并生成，执行时应整体读取。

<!-- task-module:capability-and-runtime -->
<!-- 公共来源：references/common/capability-and-runtime.md -->

# 公共规则一：运行契约

只执行本次模式。已有题目的FULL_BUILD持续到真实交付；FIGURES_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY和DEFENSE_ONLY不得扩展范围。除权限、伦理、付费、凭证或硬阻塞外不重复等待确认。能力只按当前执行器、父代理、客户端和插件的真实观察填写；`available:null`表示未知，不得当成不可用，模型品牌不能替代工具检查。
paper-request.json是一次性语义输入，paper.py派生参数、能力、Profile、模块与唯一执行MD。模型负责方向、方法和材料判断；脚本只拼接、转换和核验。run-params.md保存用户题目、模式、语言、层次、篇幅、文献/图表目标和停止条件。字数按用户明确值、模板、论文层次和默认值排序；中文THESIS层次未知兜底25,000。

能力为image_generation、visual_inspection、docx_export、pdf_export四项三态值。已知可用时可补tool、caller和evidence；父/客户端代调只记录一个真实caller。能力后来变化时使用安全amend形成新提示词，不静默改旧报告。MODEL_LABEL写模型与客户端，RUN_LABEL只区分测试目录，不进入论文署名。
<!-- /task-module -->

<!-- task-module:integrity-and-evidence -->
<!-- 公共来源：references/common/integrity-and-evidence.md -->

# 公共规则二：真实性与证据

不得编造文献、DOI、法源、标准、实验、数据、访谈、问卷、病例、性能、提升比例、伦理审批、项目或个人信息。重要主张标为OBSERVED、VERIFIED_EXTERNAL、INFERRED、PROPOSED或UNSUPPORTED；UNSUPPORTED不得进入定稿。没有真实实验/实施材料时降级为设计、协议、公开数据分析或综述，不能用随机数和模型生成CSV补结果。DESIGN_ONLY/PROTOCOL_ONLY不得出现“本研究实测、p<0.05、满意度提升、测试通过”等结果型断言。
工程区分实现、验证、设计与未来工作；定量结果回到原始数据与计算；人体研究说明伦理、同意、样本和匿名化。范文不是事实来源。

FULL_BUILD建立data/data-provenance.json。真实数据项记录dataset_id、文件、SHA-256、origin、claim_role、supports_claims。origin只用USER_PROVIDED、AUTHOR_OBSERVED、OFFICIAL_DOWNLOAD、FORMAL_SIMULATION、CALCULATED、SYNTHETIC_DEMO、MODEL_SYNTHETIC或MANUSCRIPT_CONTEXT；后四类不得冒充观察结果。正式结果只能由RESULT、SIMULATION_RESULT或DESIGN_CALCULATION角色支撑。

下载、计算、仿真用capture_provenance.py捕获输入、命令、输出、退出码和摘要。AUTHOR_OBSERVED绑定运行前原始文件；OFFICIAL_DOWNLOAD留下载字节与最终URL；FORMAL_SIMULATION留引擎、模型和原始输出；CALCULATED留输入与脚本。结果脚本不得手写验证回执。

research_claim_level为OBSERVED_STUDY、DESIGN_ONLY、PROTOCOL_ONLY或REVIEW_SYNTHESIS。材料语义决定真实性；脚本成功、披露局限均不证明题目已回答。证据不足先补材料，仍不足则降低主张、报告研究与篇幅缺口，不重复填充。
<!-- /task-module -->

<!-- task-module:literature-and-citation -->
<!-- 公共来源：references/common/literature-and-citation.md -->

# 公共规则三：文献检索与引用

先写检索式和纳排标准，再写正文。发现层用于找候选，证据层读取全文/法源/标准/官方数据，核验层核对题名、作者、年份、版本与DOI；发现记录不能冒充全文。文献状态仅为VERIFIED_FULLTEXT、VERIFIED_METADATA、UNVERIFIED、REJECTED。核心主张须由有页/节定位的VERIFIED_FULLTEXT支撑；只核元数据不能转述样本、方法、数字或引语。正文引用、文末文献、references.bib和证据矩阵必须闭合。
02-search-log.md记录真实数据库、访问路径、检索式、日期、筛选和限制。访问模式为OPEN_API、OPEN_WEB、LOGIN_REQUIRED、INSTITUTION_REQUIRED或MANUAL_ONLY；知道库名不等于已经访问。订阅库不可用时记录CAPABILITY_GAP，转OpenAlex、Crossref、PubMed/PMC/Europe PMC、arXiv、DOAJ及官方网站。

03-evidence-matrix.csv至少含source_id、题名、作者、年份、类型、来源、卷期页、DOI/URL、访问日期、核验来源、支持主张、章节、状态、evidence_role、access_mode、publication_status、fulltext_locator、page_locator、备注；本地全文另记文件与SHA。evidence_role用DISCOVERY/EVIDENCE/VERIFICATION，publication_status区分正式、预印本、工作论文、标准、官方文件和数据集。

预印本与正式版按工作身份去重，核心因果、疗效和性能优先正式版。中文核心标注CSSCI、CSCD、北大核心或科技核心及目录版本。系统综述至少双库并保留完整流程。Crossref未收录不自动等于虚构；DOI解析后题名明确错配为Critical。法条、标准、案例、手册和数据集按各自版本、条款、页码、许可与下载日期核验。

NUMERIC正文和文末使用同一编号；AUTHOR_YEAR不得保留编号列表，并为每条来源记录唯一citation_token。达不到最低文献目标时先扩展同义词、英文词、标准和官方文档；仍不足则报告PARTIAL，不能凑假文献。
<!-- /task-module -->

<!-- task-module:output-contract -->
<!-- 公共来源：references/common/output-contract.md -->

# 公共规则四：文档交付

DOCX与PDF来自同一份07-paper-full.md和同一图表清单。导出时固定一个本地时间戳，文件名为“安全论文题目_YYYYMMDD-HHMMSS.docx/pdf”，不覆盖旧稿。无模板采用A4中文学术草稿：正文12pt、首行2字符、1.5倍行距；真实Heading样式生成左侧导航；图题仅一次且图下，表题表上；表格单元格零首行/悬挂缩进；公式为可编辑OMML；中文THESIS含中英文摘要和关键词；目录有真实条目与页码。
默认页边距上下2.54cm、左3.0cm、右2.5cm；中文宋体或可用CJK字体，英文数字Times New Roman。Title居中22pt，Heading 1/2/3为16/14/12pt。参考文献10.5pt悬挂缩进，页码页脚居中。学校或期刊模板优先。

Word正文缩进不能继承到表格、题注、目录和公式；清除表格段落firstLine、firstLineChars、hanging、hangingChars。图号由display_number和正式题注统一产生，Markdown图片替代文字不得再次变成可见图题。final_embed_file是唯一嵌图入口。

Word目录域存在不等于已更新；PDF目录必须能对应章节和页码。原生目录更新不可用时可生成准确静态PDF目录，同时保留Word导航并说明限制。核对空白页、孤行、超版心表格、标题落页尾、图题分离、图片变形和公式溢出。

正文长度排除摘要、目录、参考文献、附录、表格、图题和TeX控制命令。文件存在和可解析只是机械前提，不代表内容正确。
<!-- /task-module -->

<!-- task-module:academic-figures -->
<!-- 公共来源：references/common/academic-figures.md -->

# 公共规则五：学术配图

每图先写目的、正文位置、事实节点/边、逐字标签、禁止项和精确性。生图能力真实可用时，普通流程、架构、组织和概念图必须用IMAGE_GENERATION，并逐图给出详细Prompt；统计图用DATA_CODE；引脚、电路、化学结构和尺度图用DOMAIN_EXACT；真实影像用EVIDENCE_FILE。只有无生图工具、用户要求矢量或出版限制时才SVG_FALLBACK。成功生图及其中文覆盖PNG必须成为final_embed_file并实际进入Word/PDF，不能被同号SVG替换。
先从最终图复述关系再对照正文；流程检查正常与异常分支，核对年份、数值及端点。错图局部修复，不以回执或“示意图”免责。
图中文字默认简体中文，保留型号、协议、单位和化学式；Prompt列exact_labels和allowed_foreign_tokens。文字失败用DETERMINISTIC_OVERLAY覆盖中文并保留构图，不整图改英文或改插纯SVG。

figures/figure-manifest.json是唯一图片清单。每图记录figure_id、display_number、title、figure_type、exactness_class、claim_bearing、imagegen_eligible、generation_route、route_exemption、source_locator/source_data、caption_claim、supported_manuscript_claims、limitations、language_contract、text_render_strategy、final_embed_file、generated_file、prompt_file、generation_receipt、vlm_verification。未使用字段为null，不编造。

route_exemption仅为USER_REQUESTED_VECTOR、PUBLICATION_RESTRICTION、IMAGE_TOOL_UNAVAILABLE、DOMAIN_EXACTNESS、EVIDENCE_REQUIRED或null。generation_receipt绑定真实工具结果、时间、Prompt与生成文件摘要；模型自述只能DECLARED_ONLY。vlm_verification绑定实际查看文件与回执，不以生成成功代替审图。

不采信生成者通过说明；查悬空、重复、反向、错误汇合，领域图对照源表。覆盖后复看合成图与文稿，观察写回qa-observations。

图内不写外部图号或整段题注。两轮无效修复后记NEEDS_REVIEW及缺陷，不删必要边过检。缺视觉能力记CAPABILITY_GAP；高质量图仅局部修复。
<!-- /task-module -->

<!-- task-module:statistical-figures-and-trace -->
<!-- 公共来源：references/common/statistical-figures-and-trace.md -->

# 公共规则六：统计图与计算

统计图必须来自真实数据和可复算代码，不能由生图模型猜数字。图型服从读图任务：趋势用线，比较用点/柱，分布用直方/箱线，关系用散点，效应用区间图。标出变量、单位、分母、样本量和误差含义；禁止装饰性3D、无解释截轴和误导双轴。正文、表格和图使用同一数据版本。
每图绑定dataset_id、源文件、SHA-256、origin、数据状态和真实采集来源。transformation记录脚本、摘要、命令回执、输入和输出摘要；随机过程记录目的、种子和分布。合成或演示数据不能支撑正式结果。

分类统计不只核计数，还要检查研究对象、任务和方法。对随机项、边界项、异常项及高影响项留抽查记录；更正分类后重算图表。预印本与正式版去重。VLM只检查视觉，不能证明计算或分类正确。

最终字号通常不低于8pt，PNG在插入尺寸至少300DPI；配色兼顾灰度和色觉差异。caption_claim、正文主张和limitations与实际数据一致。
<!-- /task-module -->

<!-- task-module:academic-prose-quality -->
<!-- 公共来源：references/common/academic-prose-quality.md -->

# 公共规则七：正文编辑

段落以具体材料支持判断并处理反例。整合时合并重复限制、删除过程旁白；删去后不损失论据或判断的段落不再扩写。结论只回答正文支持的问题，不用框架、重复、附录或表格凑字数。
证据核查在前，语言编辑在后，不改数值、引文、公式或图中关系。方法集中说明限制，讨论保留影响解释的条件；反复“仅为方案、仍需验证”合并为具体失效条件和验证指标。不删不利结果，篇幅不足补材料与分析。列表不替代论证，不统一段长或结论比例，不输出“AI率”。
<!-- /task-module -->

<!-- task-module:autonomous-completion -->
<!-- 公共来源：references/common/autonomous-completion.md -->

# 公共规则八：执行与续跑

FULL_BUILD按契约、检索、分析、分章写作、图表、导出和局部修复持续执行；局部模式不扩围。在原契约核对题目与实际材料，分析后选本题2—3个关键反例核查；设计矛盾不能只写未来验证。下一章用计划、证据和前章摘要。缺材料不编结果凑字数或默改题目。RESUME验证旧提示词后继续，REVISE_ONLY另存修订。
01-research-contract.md合写问题、最低/已有材料、方法、可支持答案、章节预算和图表，不复制大纲。替换信源不等于替换研究对象或分析单位；改题遵守TITLE_POLICY。保留本任务有效分析和阴性结果；反例核查只记录发现的问题，不另建清单。总篇幅按用户要求，不足如实报告。

FULL_AUTONOMY无阶段卡；GUIDED/WEAK_MODEL按执行困难增加检查点，不因材料或工具缺口降档。上下文将满时存状态、产物、问题与下一动作。amend只重做失效阶段。
<!-- /task-module -->

<!-- task-module:final-quality-gates -->
<!-- 公共来源：references/common/final-quality-gates.md -->

# 公共规则九：统一核验

核对核心主张、最终图中关系及导出页面后写qa-observations.json，再运行`paper.py check`。入口仅作证据、图片、公式、交付四类机械检查，不给语义PASS或分数。Critical/Important修复后重检，无法修复报PARTIAL/FAIL；哈希不证明专业正确。
qa-observations.json记录主张、逐图和页面问题，视觉判断绑定所看文件、页码和真实回执。学术评分交给写作流外的另一会话、模型或人工。

机械检查覆盖引用、数据、生图与嵌图、OMML、目录、题注、表格、篇幅、文档及SHA。旧报告须匹配当前输入才能复用。AUDIT_ONLY另存；FIGURES_ONLY无重导不改正文文档。

实际查看摘要、目录、章首、代表表格、最长公式和图片页；排除页眉重复再判章序，PDF不得留“Word更新目录”占位。局部修复后重导并复看，缺视觉能力如实报告，不能以解析代替目验。

修复后重跑check，最终只据14-adjudicated-status.json报告RESEARCH_STATUS、DELIVERY_STATUS、FINAL_STATUS和缺口；报告缺失、陈旧或命令失败不得报PASS。
<!-- /task-module -->

<!-- task-module:mathematical-formulas -->
<!-- 公共来源：references/common/mathematical-formulas.md -->

# 公共规则十：公式

先核对公式含义、符号、单位、前提、边界和代入，再处理渲染。Markdown统一使用`$...$`与`$$...$$`；代码中安全处理反斜杠。DOCX公式必须是可编辑OMML，PDF不得显示TeX源码，不能用生图模型重画精确公式。重要公式分配稳定ID并记录源定位；不能只比较Markdown公式数与OMML节点数。
先用本稿实际需要的分式、上下标、根式、希腊字母、矩阵和中文说明做最小导出测试，再复用同一路径。不可通过python-docx读取整段后重新赋值破坏数学对象。长公式按数学结构分行，编号右对齐，检查溢出、缺字和上下标。

equations/formula-audit.md记录重要公式ID、位置、含义检查和问题，不复制全文。verify_formula_rendering.py绑定Markdown、DOCX和PDF摘要。无公式记录真实零项；缺视觉或转换能力记CAPABILITY_GAP。
<!-- /task-module -->

<!-- task-module:svg-layout -->
<!-- 公共来源：references/common/svg-layout.md -->

# 可选模块：SVG与精确矢量图

SVG只用于无生图工具、用户/出版要求矢量或DOMAIN_EXACT骨架。先列节点、边、逐字标签和禁止关系，再排坐标。优先整数网格、正交折线、端点落在正确边界/引脚；并行边独占通道，检查交叉、穿节点和共线重叠。中文使用真实可用CJK字体并按论文物理尺寸检查字号。最终SVG转PNG后实际查看，不能让几何PASS代替语义核对。
流程图按主方向分层，决策边写条件；组织图按真实隶属；ER/UML保留基数、主外键和关系；电路/引脚读取连接表或网表；机制图区分因果、关联和假设；时间线按真实先后。统计数值由数据代码生成。

简单节点边图可把无坐标spec交给render_svg_layout.mjs；失败、稠密或领域符号不合适时转原生/领域工具，不删必要边。标签使用独立空白带；长跨域边绕外缘或拆图，电气汇合点明确标结点。

COMPILED模式记录spec、报告和renderer摘要；报告PASS后才能使用。复杂path、文本遮挡和专业语义仍需视觉检查。DOMAIN_EXACT必须核对网表、引脚表或领域输入。成功ImageGen不得被SVG覆盖。
<!-- /task-module -->

<!-- task-module:direction -->
<!-- 方向来源：references/directions/biomedical-experimental-journal.md -->

# 方向提示词：生物医学实验型期刊论文

PROMPT_ID: `biomedical-experimental-journal`

## 范文结构依据

- 公开示例：期刊范文《青蒿素衍生物ART-1对HepG2细胞凋亡的诱导作用》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=1965588401834950656
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

细胞、分子、药理、基础医学和实验生物学的短篇期刊论文。

## 不适用或高风险情形

没有实验记录、伦理/生物安全条件或统计数据却报告疗效、表达差异和显著性。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 结构式摘要
2. 引言与假设
3. 材料与方法
4. 伦理/生物安全和统计
5. 结果
6. 讨论
7. 局限
8. 结论与数据可用性

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 细胞系来源与鉴定
- 试剂批次
- 实验方案
- 原始图像和仪器文件
- 生物重复
- 统计脚本
- 伦理或生物安全材料

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：PubMed/MEDLINE（OPEN_WEB与OPEN_API）；Web of Science、Embase（INSTITUTION_REQUIRED，若可访问）；SinoMed中的CBM或CNKI医学核心刊（注明目录版本）。
- 证据与全文：PMC与Europe PMC全文（OPEN_WEB）；出版社全文或作者合法存档版本；Cochrane Library方法与系统评价。
- 开放路线：PubMed、PMC、Europe PMC（OPEN_API）；ClinicalTrials.gov与中国临床试验注册中心（OPEN_WEB）；bioRxiv（预印本，主张须降级）。
- 不宜作核心引文：预印本当阳性结果终证、未核细胞系STR的二次引用。
- 信源核验门槛：临床或动物试验主张核对注册号与伦理信息；预印本与正式发表版本去重。

## 图表与表格

实验流程、剂量反应、流式/显微图、蛋白表达和误差条；表格报告样本量、重复和统计方法。

## 无材料时的降级规则

无真实实验时改为预注册式实验方案或系统综述，不生成P值、蛋白表达量或疗效。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 实验逻辑闭合

先定义生物模型来源、种属/细胞系、处理、对照、重复层级、主要终点和排除规则。技术重复不能冒充生物学重复；同一动物或样本的多次测量不得当独立样本。细胞系说明鉴定和污染状态，动物与人体材料说明伦理、同意和登记。

机制主张至少区分相关、必要性和充分性。抑制剂单一结果不能证明通路特异；需要阳性/阴性、载体、溶剂、救援或正交检测等与主张相称的对照。抗体、引物、试剂、仪器和分析软件记录型号/货号/版本。图像定量保留原始视野、盲法、阈值和归一化。

统计单位与实验单位一致；预先定义主要比较、多重性、效应量和不确定性。只有模拟数据时写实验协议，不生成柱状图、p值或“机制得到验证”。
## 扩展专业攻略

结果按研究问题组织，先报告质量控制与样本流，再报告主要终点、机制和稳健性。Western blot、显微图和流式图保留未裁切原图及门控；组学分析说明批次、质控、归一化、差异阈值和验证集。临床可转化表述受模型外推限制。常见错误包括种属标志物错配、样本数按孔数计算、只用单一抑制剂证明机制、挑选代表图和虚构伦理编号。

剂量与时间设计说明生物学依据和毒性窗口。蛋白、转录与功能读出不应互相替代；时间顺序必须支持所提机制。组学发现与验证分开，富集分析是候选机制线索，不是通路激活的直接证明。涉及生存、重复测量或层级数据时使用匹配模型并检查假设。图版标出比例尺、样本单位、重复和统计方法，不能裁切掉反例或把多个批次拼成一张“代表图”。

讨论区分模型内结论、跨模型一致性和临床外推。阳性结果处理替代通路，阴性结果讨论检测能力。若关键对照缺失，结论必须退回关联或候选机制，不能在摘要保持确定性措辞。

样本量说明主要终点、效应假设、方差、检验水准、把握度和失访；探索性研究则明确估计不稳定。批次效应在设计阶段随机化或平衡，在分析阶段显示而非删除。动物实验报告随机、盲法、性别、福利终点与排除；人体样本说明临床特征、前分析过程和去标识。数据与代码共享声明只写真实可提供内容。

每个关键结论至少能从正文定位到原始图表、实验批次和统计单位。若不同检测方法给出矛盾结果，应报告矛盾并检查灵敏度、特异性和取样时间，而不是挑选支持假设的一项。重复失败、异常值和排除样本均保留理由；排除规则不能在看见组别结果后调整。

原始记录不可替代。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 队列原始文件与下载回执真实存在
- 特征选择与评价分离并报告乐观偏差
- 外部验证缺失时不得称临床标志物已验证

### 数据不足时的题目与主张处理

模拟、随机数据不能冒充病例结果；真实队列内部再分析可以保留，筛选与评价重用时报告乐观偏差并修订评价，不能据此宣称独立验证。
<!-- /task-module -->
