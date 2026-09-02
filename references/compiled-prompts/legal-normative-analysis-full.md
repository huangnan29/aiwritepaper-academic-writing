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
- references/directions/legal-normative-analysis.md
来源清单结束。
-->

# legal-normative-analysis 完整论文生成提示词

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
工程论文区分已实现、已验证、设计方案和未来扩展；实证论文的定量结果回到原始数据与计算；人体研究说明伦理、同意、样本和匿名化。范文只供结构观察，不是事实来源。

FULL_BUILD建立data/data-provenance.json。真实数据项记录dataset_id、文件、SHA-256、origin、claim_role、supports_claims。origin只用USER_PROVIDED、AUTHOR_OBSERVED、OFFICIAL_DOWNLOAD、FORMAL_SIMULATION、CALCULATED、SYNTHETIC_DEMO、MODEL_SYNTHETIC或MANUSCRIPT_CONTEXT；后四类不得冒充观察结果。正式结果只能由RESULT、SIMULATION_RESULT或DESIGN_CALCULATION角色支撑。

所有下载、计算和仿真用capture_provenance.py捕获真实输入、命令、输出、退出码和摘要。AUTHOR_OBSERVED须绑定运行前存在的原始文件；OFFICIAL_DOWNLOAD保留实际下载字节和最终URL；FORMAL_SIMULATION保留领域引擎、模型、命令和原始输出；CALCULATED保留输入与计算脚本。生产结果的脚本不能同时手写“已验证”回执。

research_claim_level只能为OBSERVED_STUDY、DESIGN_ONLY、PROTOCOL_ONLY或REVIEW_SYNTHESIS。真实性判断由材料语义决定；脚本成功不等于研究结论成立。证据不足时降低主张并完成仍可诚实交付的部分，不把正文缩短到目标一半。
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
中文论文图中文字默认简体中文，型号、协议、单位和化学式可保留。Prompt列出exact_labels和allowed_foreign_tokens。生图中文字失败时保留原始构图，用DETERMINISTIC_OVERLAY覆盖中文，不把整图改英文，也不改插纯SVG。

figures/figure-manifest.json是唯一图片清单。每图记录figure_id、display_number、title、figure_type、exactness_class、claim_bearing、imagegen_eligible、generation_route、route_exemption、source_locator/source_data、caption_claim、supported_manuscript_claims、limitations、language_contract、text_render_strategy、final_embed_file、generated_file、prompt_file、generation_receipt、vlm_verification。未使用字段为null，不编造。

route_exemption仅为USER_REQUESTED_VECTOR、PUBLICATION_RESTRICTION、IMAGE_TOOL_UNAVAILABLE、DOMAIN_EXACTNESS、EVIDENCE_REQUIRED或null。generation_receipt绑定真实工具结果、时间、Prompt与生成文件摘要；模型自述只能DECLARED_ONLY。vlm_verification绑定实际查看文件与回执，检查节点、箭头、文字、裁切和正文一致性。

图内不写外部图号和整段题注。最多两轮无效修复后记NEEDS_REVIEW和具体缺陷；不能为了过检删必要边。缺视觉能力记CAPABILITY_GAP。高质量原图只做受影响区域修复。
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

段落提出具体判断，说明材料如何支持、反例和边界。相邻段落必须增加信息；列表只用于真实并列关系，不能替代论证。避免连续制造“几层、几维、几阶段”框架、无证据强化、过程旁白和摘要—结论机械复述。结论只回答正文已支持的问题，不能靠重复、附录和表格凑字数。
研究与证据核查在前，语言编辑在后。编辑不得改数值、引文、公式或图片关系；发现实质错误回到对应环节。段落长短服从论证，不按统一模板排布。词频、长句、结论比例和边界词密度只作定位提示，不输出“AI率”或保证检测结果。
<!-- /task-module -->

<!-- task-module:autonomous-completion -->
<!-- 公共来源：references/common/autonomous-completion.md -->

# 公共规则八：执行与续跑

FULL_BUILD按研究契约、检索、证据、大纲、分章正文、图表、整合、导出、检查和定点修复持续执行；局部模式只做用户指定部分。下一章使用计划、证据和前章摘要，不反复加载全文。缺材料时完成诚实的设计/协议/综述，不编结果补字数。发现错误只返回受影响阶段；RESUME验证旧提示词和摘要后继续，REVISE_ONLY保留原稿并另存。
研究问题、材料边界、方法、章节目标、预算、图表和完成标准可合写入01-research-contract.md，避免为文件数量复制05-outline或06-argument-map。章节预算可有理由重分配，但总篇幅遵守用户硬下限。

FULL_AUTONOMY不加载阶段卡；GUIDED/WEAK_MODEL仅在明确执行困难时增加检查点，材料或工具缺口不等于模型弱。接近上下文上限时保存阶段状态、产物、未解决问题和下一动作。amend后只重做被声明失效的阶段。
<!-- /task-module -->

<!-- task-module:final-quality-gates -->
<!-- 公共来源：references/common/final-quality-gates.md -->

# 公共规则九：统一核验

完成专业、图形和页面观察后写qa-observations.json，再运行一次`paper.py check`。入口只执行证据、图片、公式和交付四类机械检查并计算权威状态，不生成论文、语义PASS或数字评分。Critical/Important必须修复；无法修复时明确PARTIAL/FAIL。哈希只绑定文件，检查器成功不证明专业正确。
qa-observations.json只记录主张证据、逐图盲检、实际页面检查和问题清单；每个视觉判断绑定被查看文件与真实回执。需要学术评价时，在写作流程结束后把冻结交付包交给另一会话、另一模型或人工审阅。

检查覆盖题录与引用、数据来源、生图路线与实际嵌图、公式/OMML、目录、题注、表格、篇幅、DOCX/PDF和SHA。旧报告只有输入摘要与当前文件完全一致时才能复用。AUDIT_ONLY输出到源目录之外；FIGURES_ONLY无重导时不改正文和文档。

修复后重新check。最终答复只读取14-adjudicated-status.json，报告RESEARCH_STATUS、DELIVERY_STATUS、FINAL_STATUS及真实缺口；任何报告缺失、陈旧或命令失败都不能报PASS。
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
<!-- 方向来源：references/directions/legal-normative-analysis.md -->

# 方向提示词：法学规范与案例分析

PROMPT_ID: `legal-normative-analysis`

## 范文结构依据

- 公开示例：法学范文《短视频著作权侵权问题研究》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=1949492578290237440
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

部门法、知识产权、数字治理、司法案例、比较法和法律制度完善。

## 不适用或高风险情形

引用失效法条、虚构判例、混淆现行法与草案，或用数量很少的案例代表总体。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 问题界定与概念
2. 现行法源与制度背景
3. 学说与争议
4. 案例选择和裁判规则
5. 规范漏洞与利益衡量
6. 域外比较的可比性
7. 完善建议
8. 结论

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 现行法律法规
- 司法解释
- 官方案例文书
- 权威释义
- 生效日期
- 裁判文书定位和比较法原文

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：国家法律法规数据库 flk.npc.gov.cn（OPEN_WEB）；中国裁判文书网（OPEN_WEB，部分功能LOGIN_REQUIRED）；CNKI法学核心刊（注明CSSCI目录版本）。
- 证据与全文：法源正文与司法解释官方文本；最高人民法院公报；全国人大常委会官网；北大法宝、威科先行（INSTITUTION_REQUIRED，须核到官方文本）；Westlaw、Lexis用于比较法（INSTITUTION_REQUIRED）。
- 开放路线：flk.npc.gov.cn、政府与法院官网（OPEN_WEB）；裁判文书网按实际功能记录 `OPEN_WEB|LOGIN_REQUIRED|MANUAL_ONLY`。
- 不宜作核心引文：自媒体“判例解读”、失效法规或草案当现行法。
- 信源核验门槛：每条法源记录版本、施行日期与现行有效状态；判例记录案号与审理法院；商业库文本与官方文本核对一致。

## 图表与表格

规范关系、权利义务和裁判路径图；表格包括法源层级、案例要素和制度比较。

## 无材料时的降级规则

无法取得判例全文时仅做法条与文献分析，不能描述具体裁判理由。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 规范论证闭合

先冻结法域、时点、法源版本、效力层级和争点。按构成要件、请求权基础或规范冲突路径展开，区分现行法、司法解释、指导性/参考性案例、学说和比较法。新闻、律所文章和数据库摘要只能作为线索。

案例事实、裁判理由和研究者评价分开，定位到案号、法院、日期和具体段落。类案比较先建立同一筛选口径，不能从少数著名案件推出普遍裁判规则。比较法说明制度背景与移植限制。

无法取得法条或裁判原文时降级为学说综述；不得生成案号、法条、判决引语和生效状态。
## 扩展专业攻略

论证同时处理支持解释、反对解释、体系后果和权利影响。时间线图只画可核事件，规范关系图标明效力与适用条件。常见错误是引用失效条文、混淆部门规章与法律、将个案结果写成统一规则、只列观点不完成涵摄、比较法直接移植以及用政策建议替代法律论证。

请求权或构成要件分析要逐项列明规范依据、事实前提、举证责任和法律效果。规范冲突说明特别法、上位法、时间和目的解释路径。案例样本若来自公开裁判库，记录检索日期、关键词、法院层级和公开偏差；裁判数量变化不能直接推断真实案件发生率。

价值衡量需在具体规范和事实中展开，不能以“平衡利益”结束。建议修改法律时区分解释论与立法论，并评估执行主体、程序和副作用。引用境外制度时核对法域与现行版本，避免把学术概述当成条文原文。

结论回答既定争点，并明确解释适用的事实条件、程序位置与例外。

引用法源应保留官方公布或权威数据库定位，避免只给二手链接。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 法源版本、效力层级和生效状态可核
- 案例主张定位到裁判文书具体理由
- 比较法只作说理来源

### 数据不足时的题目与主张处理

无法取得裁判或法条原文时降低为学说综述，不把新闻转述写成裁判规则。
<!-- /task-module -->
