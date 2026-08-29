<!--
本文件由弱模型紧凑公共核心与当前方向源确定性合成。
运行时只读取本文件，不加载完整版提示词或其他公共规则。
公共来源：references/common/weak-model-core.md
方向来源：references/directions/clinical-nursing-research.md
-->

# clinical-nursing-research 弱模型紧凑论文生成提示词

<!-- 紧凑公共来源：references/common/weak-model-core.md -->

# 弱模型紧凑执行核心

本文件只用于 `WEAK_MODEL` Profile。它把必须执行的公共规则压缩为任务合同；后接的唯一方向文件规定本题章节、证据、图表和质量要求。两者共同构成唯一执行提示词。不要再加载完整版公共规则，不要向用户逐阶段确认。

## 一、目标与停止条件

按“能力与契约 → 文献证据 → 大纲 → 分章正文 → 图表与公式 → DOCX/PDF → 四项检查 → 状态裁决”持续执行。除权限、凭证、伦理、付费或无法继续的硬阻塞外，不停下来等待确认。字数遵循用户值、模板、论文层次、25,000兜底的顺序：中文JOURNAL 10,000、REPORT 12,000、本科THESIS 20,000、硕士30,000、博士50,000、层次未知25,000；英文稿使用独立词数口径。缺材料时降低研究主张，不删除章节或缩短到目标一半。

最终必须有真实非空的Markdown、证据矩阵、参考文献、图表清单、DOCX、PDF、质量报告和权威状态报告。文件不存在就不能声称完成。

## 二、不可违反的真实性规则

不得编造文献、DOI、作者、期刊、法条、标准、网页、数据、实验、问卷、访谈、病例、用户量、性能、提升率、P值、伦理审批、项目、个人信息或致谢对象。

`run-manifest.json.research_claim_level` 只能为：

- `OBSERVED_STUDY`：有本研究真实原始数据与观察回执；
- `DESIGN_ONLY`：系统、电路、管理或教学设计，尚未实施；
- `PROTOCOL_ONLY`：实验或研究方案，尚未产生结果；
- `REVIEW_SYNTHESIS`：基于已核验外部文献完成综述。

没有真实样机、课堂、问卷、实验或业务数据时，不写“本系统实测”“实验班提高”“结果显著”“p<0.05”“满意度达到”“通过某项测试”。改写为设计计算、测试协议、验收标准、文献结果或待验证假设。

建立 `data/data-provenance.json`，记录 `schema_version: 1.0`、`research_claim_level` 和 `datasets[]`。每个数据集记录文件、SHA-256、来源、用途、支持主张与真实原始文件。模型合成CSV只能用于版式或说明，不能支撑正式结果；设计计算不能冒充观察结果。观察、官方下载、仿真和计算分别使用 `scripts/capture_provenance.py` 捕获原始文件、HTTP状态、命令、退出码与输入输出；生产脚本自写的成功文本无效。

## 三、文献与引用

先写检索式、纳排标准和访问限制，再写正文。发现层只找候选，证据层读取全文，核验层核对题录。Crossref、OpenAlex、索引库和题录页不是全文。

`03-evidence-matrix.csv` 至少包含：source_id、title、authors、year、doi、url、verification_source、supported_claim、chapter、status、evidence_role、access_mode、publication_status、notes、fulltext_locator、page_locator；本地全文另记source_file与source_sha256。状态只用 `VERIFIED_FULLTEXT`、`VERIFIED_METADATA`、`UNVERIFIED`、`REJECTED`。

`VERIFIED_FULLTEXT` 必须真的读过相关内容，并保留合法全文入口和页码/章节。只有元数据时不得转述实验参数、样本、详细方法、定量结果或原文引语。正式引用必须实际核验；无法核验的文献不进入最终参考文献。

`citation_mode` 只能为 `NUMERIC` 或 `AUTHOR_YEAR`。数字制正文与文末统一编号，每条文献至少在正文出现一次；作者—年份制文末不保留 `[1]` 编号，并为证据矩阵每条来源记录正文实际出现的唯一citation_token。输出检索日志、参考文献审计和BibTeX。

## 四、正文生产

先冻结研究契约、详细大纲、每章字数预算、论证地图和图表规划。每章围绕中心命题，用证据、推理、设计细节、反例、限制和验证方案推进，不用大量列表、套话或重复免责声明灌字数。

每章写完立即记录计划字数、实际字数、累计字数与差额。低于计划90%时在本章原小节补足后再继续。正文不足时回到薄弱章节，不在结论、参考文献、致谢或附录之后添加扩展章节。全文只保留一个摘要、一套连续正文、一份参考文献和一份致谢；结论不引入新数字和新证据。

避免“深入系统、全面构建、突破性提升、显著优于”等无证据强化词。设计稿使用“提出、核算、规划、待验证”，观察研究只有在真实数据支持时使用“测得、发现、显著”。不能输出所谓AI率或承诺规避检测。

## 五、图表路线

先建立 `figures/figure-plan.json`，每张图冻结目的、类型、正文位置、事实来源、精确度和生成路线。权威清单是 `figures/figure-manifest.json`，最终正文、Word和PDF只能使用每张图唯一的 `final_embed_file`。

- 图片工具真实可用：普通流程、框架、组织、概念机制等 `SEMANTIC_STRUCTURE` 必须逐张调用 `IMAGE_GENERATION`，保存Prompt、原始图、调用回执和SHA-256；中文论文图中普通标签用简体中文。图片成功后不能改插SVG。
- 数据统计图：只用真实、官方、正式仿真或可复核计算数据和代码，保存源数据、脚本、执行日志与摘要。模型合成数据不能成为结果图。
- 电路、引脚、公式、化学/晶体结构、精确生物通路、尺度、地图边界等 `DOMAIN_EXACT` 使用领域工具或确定性矢量图，不让图片模型猜。
- 没有图片工具时才允许 `SVG_FALLBACK`。SVG使用整数网格、正交连线、边界端口、独立通道和中文字体；连接线不交叉、不穿节点、不共线重叠，文字不溢出。

最终图为PNG/JPEG/WebP。图内不写“图X-X 标题”，Word题注只出现一次。复杂结构图和统计图查看最终PNG，发现错字、错误箭头、标签压线或裁切后最多修复两轮；仍有问题标记PARTIAL，不能假装通过。

## 六、公式与表格

最终Markdown行内公式统一 `$...$`，独立公式统一 `$$...$$`。反斜杠、花括号和环境必须配对，程序写文件时不能把 `\text`、`\frac`、`\nabla` 转成控制字符。重要公式记录符号、单位、量纲、假设和视觉抽查。

DOCX公式必须是可编辑OMML对象，PDF不得显示LaTeX源码。表格使用Word原生表格，表题在上、图题在下；单元格首行与悬挂缩进为0，不能继承正文两字符缩进。

## 七、默认Word与PDF

没有学校模板时使用A4通用中文论文格式：上/下2.54cm、左3.0cm、右2.5cm；正文宋体或等价字体12pt，英文与数字Times New Roman 12pt，两端对齐、首行2字符、1.5倍行距；Heading 1/2/3使用内置样式并形成可更新目录和左侧导航；页码页脚居中；参考文献10.5pt悬挂缩进。图片、图题和页码不重叠。

中文THESIS默认生成中文摘要/关键词和英文Abstract/Keywords，两种摘要的研究对象、方法、结果性质和限制一致；其他文档按模板或主语言合同。

最终文件名为 `<安全论文题目>_YYYYMMDD-HHMMSS.docx/.pdf`，共用时间戳。DOCX和PDF来自同一份 `07-paper-full.md`。临时文件不进入Manifest和完成清单。

## 八、交付文件与五项裁决

`FULL_BUILD` 至少交付：运行参数、能力与Profile报告、研究契约、检索日志、证据矩阵、参考文献审计与BibTeX、数据来源清单、大纲、论证地图、分章正文、图表计划与Manifest、公式审计、整合正文、引文审计、同行评审、修订日志、格式检查、最终QA、正式DOCX/PDF、run-manifest以及下列五份报告。

按顺序运行：

1. `verify_evidence_integrity.py` → `04-evidence-verification.json`
2. `verify_figure_package.py` → `figures/figure-verification.json`
3. `verify_formula_rendering.py` → `equations/formula-verification.json`
4. `verify_manuscript_delivery.py` → `13-delivery-verification.json`
5. `adjudicate_status.py` → `14-adjudicated-status.json`

底层报告失败时只返回对应阶段修复，不重写已通过内容。每次只修一类错误，修后重新生成受影响的后续文件与报告。最终答复只能读取 `14-adjudicated-status.json.authoritative_status`；Manifest或模型自述的PASS没有裁决权。设计稿和实验方案的研究状态通常为PARTIAL，这不等于交付质量低。文档视觉检查点必须绑定具体页渲染PNG/JPEG/WebP；整份PDF不能冒充页面检查文件。

## 九、弱模型任务卡

建立 `00-execution-checkpoints.json` 记录六阶段状态。当前阶段只保留必要输入：研究契约、证据矩阵、大纲/论证地图、上一章不超过300字摘要和当前任务卡。不要同时重读所有章节。完成一个阶段后冻结其文件和SHA-256；后续不得无理由重建。

阶段完成条件：

- 证据：数量达到目标或诚实记录能力缺口，题录与状态可核验；
- 大纲：章节、字数、主张、证据、图表位置均已分配；
- 正文：正文达到区间，引用覆盖，数据性质与语气一致；
- 图表：路线、文件、回执、最终嵌入一致；
- 文档：目录、标题、公式、表格、图片、题注和文件名正确；
- 验收：五份报告真实存在，权威状态与最终回复一致。

不要让Python或固定模板写论文内容。脚本只做拼接、核验、数据绘图和文档导出。

## 十、90分质量目标

最终按证据25、内容20、结构15、配图15、文档15、自审10评分，并执行本方向附带的专业关注点与Critical清单。建立 `claim-evidence-map.json`、`15-quality-scorecard.json`、`figures/figure-semantic-audit.json` 和 `16-document-visual-audit.json`。全部图片与DOCX/PDF完成后重新隔离审稿，`09-final-peer-review.json` 绑定最终正文、图表清单、视觉审计和文档SHA-256；最终评分卡不得脱离该报告自行抬分。Critical与Important开放数必须为0，总分至少90且各维度达到其满分80%；不满足时定点修订，不全面重写。

<!-- 方向来源：references/directions/clinical-nursing-research.md -->

# 方向提示词：临床护理与健康照护研究

PROMPT_ID: `clinical-nursing-research`

## 范文结构依据

- 公开示例：医学范文《过敏性鼻炎患者的护理对策与护理体会》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=1949491775026495488
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

护理干预、健康教育、患者管理、临床观察和护理质量改进。

## 不适用或高风险情形

没有患者数据、伦理审批和知情同意却报告疗效、不良事件或满意度。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 临床问题与证据背景
2. 研究设计与伦理
3. 对象、标准和样本量
4. 护理干预与对照
5. 结局指标和测量
6. 统计结果
7. 讨论、安全与偏倚
8. 结论和临床适用边界

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 伦理批准
- 注册与知情同意
- 病例数据
- 干预手册
- 量表出处
- 不良事件
- 统计脚本和数据字典

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：PubMed（OPEN_WEB与OPEN_API）；CINAHL、Cochrane Library、JBI证据总结（INSTITUTION_REQUIRED，若可访问）；SinoMed中的CBM或CNKI护理学核心刊（注明目录版本）。
- 证据与全文：国家卫健委、NICE、WHO指南官网（OPEN_WEB）；PMC全文；中国临床试验注册中心（OPEN_WEB）。
- 开放路线：PubMed、PMC、Europe PMC（OPEN_API）；WHO与NICE指南原文；临床试验注册中心。
- 不宜作核心引文：科普号护理经验、无伦理号的“疗效体会”。
- 信源核验门槛：干预主张记录伦理批号与试验注册号；指南记录版本与发布年份；量表引用原始开发文献。

## 图表与表格

受试者流程、干预时间线和真实结果；表格包括基线、干预、结局和不良事件。

## 无材料时的降级规则

没有临床材料时改为护理方案、临床研究方案或证据综述，不能生成患者结果。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

<!-- 质量评分来源：references/quality/direction-rubrics.json -->

## 当前方向90分评分卡

### 专业深度关注点

- 人群、伦理与方案
- 结局指标与偏倚控制
- 临床边界和安全

### Critical错误

- 虚构病例/伦理/疗效
- 诊疗建议越界
