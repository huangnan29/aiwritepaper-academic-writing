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
- references/common/quality-90.md
- references/common/svg-layout.md
方向来源：
- references/directions/geography-environmental-empirical.md
来源清单结束。
-->

# geography-environmental-empirical 完整论文生成提示词

## 合并说明

本文件由公共规则与当前方向规则合并生成，执行时应整体读取。

<!-- task-module:capability-and-runtime -->
<!-- 公共来源：references/common/capability-and-runtime.md -->

# 公共规则一：运行契约

只执行参数中选定的任务。FULL_BUILD完成论文；FIGURES_ONLY只改图；EXPORT_ONLY只导出；AUDIT_ONLY只读检查；PROPOSAL_ONLY写开题；DEFENSE_ONLY重组已有论文。RESUME用已冻结提示词续跑，REVISE_ONLY用修改意见和影响清单，不重新生产整篇。

用户已给题目并要求开始时使用AUTO_COMPLETE；AUTO_BENCHMARK是兼容名。除权限、伦理、凭证、付费及无法继续的硬阻塞外持续完成，不重复询问题目或大纲。用户指定的目录和材料边界优先。

## 参数唯一来源

paper-request.json是模型一次填写的任务记录；paper.py prepare已生成run-params.md、能力/Profile/模块记录和Manifest骨架，不再重复准备。run-params.md是本次题目、方向、模式、语言、层次、篇幅、文献/图表数量、模板和停止条件的执行来源。字数按用户、模板、明确层次默认、25,000兜底排序，由准备入口调用统一解析器生成TARGET_LENGTH/MIN_LENGTH/MAX_LENGTH；THESIS层次未知仍25,000。用户明确值不可被默认值覆盖。

准备时真实检查当前执行器、父代理、客户端和插件的检索、文件、运行、生图、视觉与文档能力；已完成的观察不在写作阶段反复探测。00-capability-report.json由入口保留available、callers、tools与实际依据，不按品牌推断能力。任一层可生图即按可用处理；工具状态后来变化时更新真实记录，不虚构调用或静默改写旧报告。

MODEL_LABEL写真实模型与客户端，未知时写UNKNOWN；RUN_LABEL另记目录标签，不进入论文署名。模型负责选择方向和方法，工具只拼接、转换、计算与核验。
<!-- /task-module -->

<!-- task-module:integrity-and-evidence -->
<!-- 公共来源：references/common/integrity-and-evidence.md -->

# 公共规则二：真实性与证据

不得编造文献、DOI、作者、期刊、政策、标准、法条、网页、实验、数据、访谈、问卷、病例、用户数量、性能、提升比例、伦理审批、项目、个人信息或致谢对象。

在研究契约、证据矩阵或审计记录中，将重要主张标记为以下状态之一：

- `OBSERVED`：由用户材料、原始数据、代码运行或日志直接观察；
- `VERIFIED_EXTERNAL`：由已核验的权威外部来源支持；
- `INFERRED`：基于证据的推论，必须降低语气并说明限制；
- `PROPOSED`：设计方案、测试计划或预期标准；
- `UNSUPPORTED`：不得进入最终正文。

工程论文必须区分已实现、已验证、设计方案和未来扩展。实证论文的每个定量结果必须追溯到数据文件与计算过程。临床、问卷、访谈和人体研究必须说明伦理、同意、样本和匿名化边界。没有真实材料时，降级为研究方案、公开数据分析、验证协议、概念设计或文献综述。

AIWritePaper 范文仅提供结构观察，不是事实来源。不得复制范文正文、引用其未核验数字，或继承其“已完成”表述。

凡涉及定量结果或“系统已实现/已运行”的主张，必须能够回到用户材料、数据文件、源码版本、执行命令、原始日志、公开数据集或已核验来源。`FULL_BUILD` 必须建立 `data/data-provenance.json`，根对象记录 `schema_version: 1.0`、与Manifest一致的 `research_claim_level` 和 `datasets[]`。每个真实数据集记录 `dataset_id`、文件、SHA-256、`origin`、`claim_role` 与 `supports_claims`。

`origin` 只能为 `USER_PROVIDED`、`AUTHOR_OBSERVED`、`OFFICIAL_DOWNLOAD`、`FORMAL_SIMULATION`、`CALCULATED`、`SYNTHETIC_DEMO`、兼容旧名 `MODEL_SYNTHETIC` 或 `MANUSCRIPT_CONTEXT`；`claim_role` 只能为 `RESULT`、`SIMULATION_RESULT`、`DESIGN_CALCULATION`、`ILLUSTRATION` 或 `CONTEXT_ONLY`。每个登记数据集必须有真实文件和SHA-256。合成/演示数据不能支撑结果、仿真结果或正式设计计算；`CALCULATED` 不能冒充观察结果。Python局部变量、随机休眠、手写JSON、自写“下载成功/ERP已核验/GDC已读取”文本或模拟请求不是真实数据库、Web服务、GPU、课堂、问卷或硬件实验。

所有数据回执使用Skill的 `scripts/capture_provenance.py` 生成，不能由生产数据的同一个项目脚本手写：

- `USER_PROVIDED` 与 `AUTHOR_OBSERVED` 必须先登记不可变原始文件，并在数据项的 `source_artifacts[]` 记录原始文件路径、SHA-256与来源；本次运行脚本创建的CSV/JSON不能登记为作者观察。
- `OFFICIAL_DOWNLOAD` 必须保留实际下载字节，回执记录原始URL、最终URL、HTTP状态、时间、内容类型、文件大小与SHA-256；只有平台名称和`SUCCESS`的文本无效。
- `FORMAL_SIMULATION` 必须捕获领域引擎、版本/类别、真实命令、退出码、输入模型、原始输出、stdout/stderr与SHA-256；Python手工数组、插值曲线或绘图脚本不能冒充SPICE、FEA、CFD或实验结果。
- 承担正式设计计算的 `CALCULATED` 必须捕获输入、脚本、命令和输出。结果脚本使用随机数时必须记录用途、种子和分布；未声明随机生成的正式结果直接失败。
- `OBSERVED_STUDY` 至少有一个能够回到用户/作者真实原始文件或官方真实下载字节的结果数据集；只有题录、回执文本或模型生成数据时必须降级。

`run-manifest.json` 的 `research_claim_level` 只能为：

- `OBSERVED_STUDY`：存在可核验的本研究原始数据与观察回执；
- `DESIGN_ONLY`：系统、电路、管理或教学设计，未实施验证；
- `PROTOCOL_ONLY`：实验或研究方案，尚未产生本研究结果；
- `REVIEW_SYNTHESIS`：以已核验外部证据完成综述综合。

设计或方案论文出现“本系统实测”“实验班提升”“p<0.05”“满意度达到”“通过某项测试”等本研究结果表述，而数据清单没有真实观察材料时，属于Critical错误，不得进入最终正文。

真实性判断由模型结合材料语义完成，不以某个脚本返回码代替。发现证据不足时，应降低表述强度、改写为设计方案或验证协议，并继续完成能够诚实交付的章节；不得用“材料不足”作为把整篇论文缩短到目标一半的理由。
<!-- /task-module -->

<!-- task-module:literature-and-citation -->
<!-- 公共来源：references/common/literature-and-citation.md -->

# 公共规则三：文献检索与引用

先设计检索式和纳入排除标准，再写正文。来源优先级为同行评议论文、学位论文、政府或标准机构、出版社页面、官方技术文档。聚合页、采集站、营销页和匿名内容只能作为线索。

## 信源三层分工

- 发现层：Web of Science、Scopus、Engineering Village（Ei Compendex、Inspec）、DBLP、CNKI检索结果页等索引与引文库，用于查找候选文献和引文追踪；索引记录本身不是全文证据。
- 证据层：出版社全文、机构知识库或作者合法存档版本、正式法源、标准原文、官方指南、官方数据集和监管披露，用于实际阅读并支撑论文主张；出版平台上的文章是否适合作核心证据仍需逐篇判断。
- 核验层：Crossref、DOI解析、出版社官方页、PubMed或SinoMed记录，用于核对题名、作者、年份、卷期页、DOI和版本；元数据核验不能代替全文阅读。

当前方向提示词内置“文献信源”清单，按其顺序开库。信源跟随证据形态和方向路由，不跟随专业名称。

## 访问方式与真实检索

信源访问方式标记为 `OPEN_API`、`OPEN_WEB`、`LOGIN_REQUIRED`、`INSTITUTION_REQUIRED` 或 `MANUAL_ONLY`。方向清单中的标记描述典型访问条件，不代表本次运行已经具备权限；同一来源存在多种路径时用 `|` 连接。纸质教材与手册、授权内部材料、无法自动读取的馆藏或标准原文标记为 `MANUAL_ONLY`。知道数据库名称不等于具备访问权限：`02-search-log.md` 的每条检索必须记录实际使用的数据库和访问路径，未实际访问的库不得出现在检索记录中，不得虚构“已在Web of Science、Scopus、SciFinder中检索”之类的过程。

首选库需要机构订阅且当前环境不可访问时，记录 `CAPABILITY_GAP` 并转入开放路线继续检索：OpenAlex、Crossref、PubMed、PMC、Europe PMC、arXiv、DOAJ、Semantic Scholar以及官方政府、标准、统计和法源网站。开放路线是无订阅环境下的正当检索方式，不是质量缺陷，但应在检索日志中说明库覆盖面的限制。

## 中文题录入口

中文学位论文和国内期刊题录，多数方向都要开中文库：CNKI及海外镜像 `oversea.cnki.net` 为 `OPEN_WEB` 题录入口，多数全文属于 `LOGIN_REQUIRED|INSTITUTION_REQUIRED`；万方、维普按实际访问条件标记，用于与CNKI交叉去重补漏；医学与护理方向优先使用中国生物医学文献服务系统SinoMed中的中国生物医学文献数据库CBM做主题词检索，并按本次访问记录 `OPEN_WEB|LOGIN_REQUIRED|INSTITUTION_REQUIRED`。表述“CNKI核心刊”时必须区分CSSCI、CSCD、北大核心或中国科技核心，并记录所依据的目录版本。

## 预印本与工作论文

arXiv、bioRxiv、ChemRxiv、SSRN、NBER工作论文可以收录，但必须在证据矩阵中标注 `publication_status` 为预印本或工作论文，并检查是否已有正式发表版本；两者去重后优先引用正式版。核心因果、疗效或性能主张优先使用正式发表来源，仅有预印本支持时降低表述强度。系统综述中预印本单独报告，除非检索协议明确允许，不混入正式纳入集。

## 检索与证据记录

在 `02-search-log.md` 记录数据库、实际访问路径、检索式、日期、筛选步骤和访问限制。在 `03-evidence-matrix.csv` 记录 source_id、题名、作者、年份、类型、来源、卷期页、DOI、URL、访问日期、核验来源、支持主张、章节、状态、evidence_role、access_mode、publication_status、备注、`fulltext_locator` 与 `page_locator`；使用本地来源文件时另记 `source_file` 与 `source_sha256`。作者—年份制另加唯一 `citation_token`。

上述字段是最低证据契约，不是可选示例。只包含 `source_id,DOI,status` 或缺少题名、作者、年份、支持主张、章节和访问/发表状态的极简表不属于完整证据矩阵，不能通过最终交付验收。

新增字段使用受控值：`evidence_role` 只能为 `DISCOVERY`、`EVIDENCE`、`VERIFICATION`，兼具多种角色时用 `|` 连接；`access_mode` 只能使用上述五种访问标记，实际路径与典型条件不一致时以本次观察为准；`publication_status` 使用 `PUBLISHED`、`PREPRINT`、`WORKING_PAPER`、`STANDARD`、`OFFICIAL_DOCUMENT`、`DATASET` 或 `OTHER`。空值必须解释，不能自行创造近义状态。

状态只能为：

- `VERIFIED_FULLTEXT`：元数据与相关全文内容已核验；
- `VERIFIED_METADATA`：只核验元数据，只能支持存在性和书目信息；
- `UNVERIFIED`：不得进入正式引用；
- `REJECTED`：重复、低质量或不匹配。

核心论点只能由已阅读且匹配的来源支持。每条文内引用必须匹配参考文献，每条参考文献必须在正文出现。无法访问全文时降低表述强度，不得假装读过。输出 `references.bib` 与 `04-reference-audit.md`。

`run-manifest.json` 必须显式记录 `citation_mode` 为 `NUMERIC` 或 `AUTHOR_YEAR`。`NUMERIC` 的正文和文末都使用同一套编号；`AUTHOR_YEAR` 的文末不得继续保留编号列表，证据矩阵的每条可用来源必须给出正文实际出现的唯一 `citation_token`。不得让正文使用作者—年份、文末却使用 `[1]` 编号列表。

正式验收使用 `scripts/verify_evidence_integrity.py` 解析DOI与题名、全文核验来源、定位信息、引用覆盖和数据来源。Crossref未收录不自动等于虚构，但DOI解析后题名明确对应另一篇文献时为Critical错误。网络无法执行DOI核验时记录 `CAPABILITY_GAP` 并将证据状态降为 `PARTIAL`，不能虚报完全通过。

`VERIFIED_METADATA` 不得用于转述全文实验参数、样本、定量结果、详细方法或原文引语；正式摘要能够直接确认的研究范围须明确写成摘要层。支撑全文级主张时使用 `VERIFIED_FULLTEXT` 并保留定位。法条、标准、案例数字和技术手册参数分别记录法源版本/条款、标准号/范围页、来源文件/页码/期间/计算和手册版本/页码。

最低参考文献数量是生产目标，不是最后才检查的备注。检索和核验应持续到达到 `MIN_REFERENCES`，或已经穷尽当前可用来源与工具。未达到最低数量时不得标记 `PASS`；但应先扩大同义词、英文关键词、相关方法、标准和官方文档检索，不得只用少量来源反复支撑全文。
<!-- /task-module -->

<!-- task-module:output-contract -->
<!-- 公共来源：references/common/output-contract.md -->

# 公共规则四：文档交付契约

本模块只用于要求导出文档的任务。用户/学校/期刊模板优先；无模板时说明采用通用草稿格式。DOCX与PDF来自同一份07-paper-full.md、图表清单和结构映射，不能分别改写后独立输出。

## 文件与身份

run-manifest.json记录run_mode、model_label、skill_version、direction_id、execution_profile、profile_selection_report、paper_level、manuscript_language、abstract_contract、citation_mode、research_claim_level、document_profile、契约目标和最终文件路径。GUIDED/WEAK使用execution_checkpoints；RESUME记录00-resume-plan.json，REVISE_ONLY记录revision-impact.json。00-prompt-composition.json绑定实际执行提示词。

开始最终导出时固定GENERATED_AT_LOCAL，使用“安全论文题目_YYYYMMDD-HHMMSS.docx”与同名PDF。清理路径分隔符和控制字符，保留中文，不覆盖原正式稿。final-paper.docx/.pdf仅为内部临时名。实际文件摘要由工具计算；打包不能移除时间戳或替换清单路径。

## 默认中文学术版式

- A4；上下2.54cm、左3.0cm、右2.5cm；中文宋体/SimSun/Songti SC，英文数字Times New Roman；正文12pt，两端对齐、首行2字符、1.5倍行距、段前后0。
- THESIS封面独页，中文摘要、Abstract、目录分别新页。中文THESIS和无模板中文JOURNAL要求双语摘要及Keywords/关键词，研究对象、结果性质与限制一致；其他类型按模板。
- Title居中22pt；Heading 1/2/3分别16/14/12pt，使用真实内置样式与正确outlineLvl。按实际大纲保留需要的层级，不为填满三级标题而造章节；标题与下一段同页。
- 图题置图下、表题置表上，10.5pt；原生可编辑表格优先三线表。图和图题不分离、不侵入页脚，图片不变形，实际显示文字清晰。
- 独立公式居中、编号右对齐；公式保留可编辑OMML，修改字体与段落时不得重建为纯文本。
- 参考文献10.5pt，按引用格式悬挂缩进；页码页脚居中。避免孤行、空白页、超版心表格及标题落页尾。

## Word表格单元格缩进

正文首行缩进不适用于表格、题注、目录、公式。非空单元格首行与悬挂缩进均为0，表头居中、文字表体左对齐、数值按需要对齐。清除firstLine、firstLineChars、hanging、hangingChars。Pandoc的Compact/Table样式可能继承Normal；核验顺序是直接格式→当前样式→basedOn父样式→缺失样式时默认样式。不得只凭“看起来居中”判断通过。

## 题注、插图和目录

每图只有一个正式题注，图号由display_number给出；不要把Markdown图片替代文字另输出成可见图题。正文引用“见图2-1”合法，不得因正文提及图号而误判题注重复。插图采用图表模块规定的唯一最终路径，导出后核对实际媒体，而非按同名扩展名重新选图。

Word导航依赖真实Heading样式；目录域存在不等于最终目录生成。更新目录后再导出PDF；PDF必须有可对应章节的实际条目与页码，空标题、“更新域”提示或无页码列表都不算完成。原生更新工具不可用时可生成准确的静态PDF目录，同时保留Word标题与导航，并说明静态目录限制。

正文长度按统一口径复核，表格（含Pandoc多行表格）、图注、摘要、目录、参考文献、附录及TeX控制命令不用于凑字数。文件存在、能打开，不代表语义与排版通过。
<!-- /task-module -->

<!-- task-module:academic-figures -->
<!-- 公共来源：references/common/academic-figures.md -->

# 公共规则五：学术配图

图服务正文的具体主张。先确定事实，再选择路线和布局；配图成功后必须核对最终文档中的实际图片。

## 事实、路线与语言

每图在figure_plan中记录目的、正文位置、类型、来源、节点/关系/标签、禁止项与精确性要求。复杂图的事实清单可单列figures/<FIGURE_ID>-facts.md。普通流程、架构、组织、ER/UML和概念图必须从上下文写详细生图Prompt，包含准确标签、边的起终点、分组、方向、风格与禁止项，不能只给论文题目。

实际生图能力可用时，SEMANTIC_STRUCTURE走IMAGE_GENERATION，包括需要精确关系的流程图；不得批量把imagegen_eligible设为false以绕过。数据统计图走DATA_CODE；电路引脚、化学结构、尺度等DOMAIN_EXACT先用可核对的领域工具/确定性底图，生图只处理不改变事实核心的视觉部分；真实科研影像走EVIDENCE_FILE，不能生成证据区域。真正无生图工具、用户明确要求矢量或出版格式禁止时才走SVG_FALLBACK，不以省时为理由降级。

中文论文图中说明默认简体中文，型号、协议、单位、化学式等允许保留。Prompt写出逐字标签。直接文字失败可用DETERMINISTIC_OVERLAY覆盖中文，保留原始生图与覆盖过程，不能换成纯SVG替代成功图片。禁止无授权把全图改成英文；标记允许的外文技术词，检查中文缺字、伪字及非白名单英文长句。

## 唯一图片清单

figures/figure-manifest.json是唯一真源（schema_version:1.5，figures数组），每图记录：
- figure_id、display_number、title、figure_type、exactness_class、claim_bearing、imagegen_eligible、generation_route、route_exemption；
- source_locator或source_data，caption_claim、supported_manuscript_claims（含正文locator）与limitations；
- language_contract（manuscript_language、label_language、exact_labels、allowed_foreign_tokens），text_render_strategy；
- 最终文件final_embed_file；原始generated_file、prompt_file、generation_receipt；没有使用的路线字段为null，不能编造填满；
- canvas_contains_figure_number_or_caption:false；以及实际vlm_verification。

route_exemption只接受USER_REQUESTED_VECTOR、PUBLICATION_RESTRICTION、IMAGE_TOOL_UNAVAILABLE、DOMAIN_EXACTNESS、EVIDENCE_REQUIRED或null；工具可用却使用IMAGE_TOOL_UNAVAILABLE无效。图片工具成功后，final_embed_file指向该生图或其修正PNG，旧SVG只作备用。Markdown、Word媒体和PDF显示必须使用这一文件；不能按同名扩展名另选。figure-manifest.md只是工具派生的一行摘要，不另写路由。

## 调用与视觉证据

generation_receipt保存实际工具结果或客户端片段，记录evidence_level（NATIVE_TOOL_RESULT或CLIENT_TRANSCRIPT）、tool、真实调用时间、call_id（未暴露时NOT_EXPOSED）、receipt_file、receipt_sha256、prompt_sha256、generated_sha256。只有自述时标DECLARED_ONLY，不能证明调用。SHA-256只能绑定文件，不能证明内容正确或服务商背书。

vlm_verification记录实际status、remaining_issues、iterations、tool、checked_at、checked_file_sha256、receipt_file、receipt_sha256及language_check（status、target_language、observed_language、unintended_foreign_text、allowed_foreign_tokens_verified、exact_labels_verified）。保存真实观察，不由脚本默认填PASS。检查器返回IMAGEGEN_BYPASSED时回到工具能力和路线核对，不能改能力声明绕过。

检查最终PNG在论文实际尺寸的字体、裁切、遮挡、色彩、连接与题注。更重要的是逐边核对起终点、分支条件和正文事实；“好看”或“节点齐全”不足以通过。不能用文字解释错误图片来代替修正。图内不写外部图号/整段图题，正式题注由文档层生成一次。

原始生成图、Prompt与调用结果保留；overlay另记base_image/source_file等实际输入与执行回执。统计图的数据及计算规则见本次选择的统计模块；SVG降级的字体和布局规则见本次选择的SVG模块。若本次唯一MD未含某个必要模块，先补全任务选择并形成有记录的新版提示词；不得悄悄猜规则或宣称旧提示词未改变。

## 修复边界

先解决事实关系，再优化布局。最多两轮无效修复后记录NEEDS_REVIEW和具体缺陷，不能将其改为PASS。缺视觉能力时诚实记CAPABILITY_GAP；原生SVG已通过时不套模板重绘，成功生图不被SVG覆盖。高质量图应保持，只有受影响图和导出需要重检。
<!-- /task-module -->

<!-- task-module:statistical-figures-and-trace -->
<!-- 公共来源：references/common/statistical-figures-and-trace.md -->

# 公共规则六：统计图与计算来源

统计图由真实数据和可复算代码生成，不由生图模型猜数字。先写分析问题、变量与读图任务：趋势用有序点/线，类别比较用点/柱，分布用直方/箱线，关系用散点，效应量用区间图；选择取决于数据含义而非统一最低点数。没有有效比较或与表格完全重复时不强画图。

坐标写变量、单位、变换、分母和样本量；误差棒说明SD/SE/CI及计算方法。类别保留合理顺序；长标签用横向布局。避免无解释截轴、装饰性3D、制造相关性的双轴。配色兼顾灰度与色觉差异，可采用viridis/cividis及直接标签；最终实际字号通常不低于8pt，PNG在插入尺寸至少300DPI。

## 数据与版本

每个源文件记录dataset_id、file、sha256、origin（data_origin）和真实采集来源；来源遵循数据真实性模块。data_status为OBSERVED、VERIFIED_EXTERNAL或SIMULATED_RESEARCH，研究仿真必须有模型、参数、种子及输出；NOT_APPLICABLE不能用于主张型统计图。PROPOSED、HARDCODED_EXAMPLE、MODEL_SYNTHETIC/SYNTHETIC_DEMO不能支撑真实结果。

transformation记录script、sha256、execution_receipt（command、receipt_file、receipt_sha256、script_sha256、inputs及output_sha256）。通过capture_provenance.py捕获实际命令、日志与输入输出，不能自写“运行成功”。Bootstrap、重采样和正式随机模拟可使用随机数，但randomness须说明purpose、seed、output_file和适用假设；不是看到随机函数就判造假。

所有正文、表格、图用同一数据版本；汇总图能回到逐条记录和处理逻辑。数据网络需真实节点边表。分类映射不能只验证计数：模型须核对实际研究对象、任务和方法，不能把摘要背景词当作研究内容；抽查边界项与异常项，误分类修复后重算图表。预印本和正式版核对工作身份，不能重复计入。

用代码复算数字、样本与不确定性，再用视觉检查系列遗漏、轴标签、尺度和图题是否越过证据。VLM不能证明计算正确，数字能复算也不能证明分类正确。caption_claim与supported_manuscript_claims须与正文实际用图一致，limitations记录真实不可比与缺失问题。
<!-- /task-module -->

<!-- task-module:academic-prose-quality -->
<!-- 公共来源：references/common/academic-prose-quality.md -->

# 公共规则七：正文与终稿编辑

## 材料推动段落

段落应提出具体判断，说明材料如何支持它、有哪些相反证据或适用边界。只核验题录的文献不能被转述成全文实验、引语或细节；没有本次实验与运行证据时不写成已验证成果。

## 控制框架和清单

围绕研究问题组织章节，不连续制造多套“几层、几维、几阶段”框架。分类只有在理论、编码或后文逐项分析支持时才保留。列表用于确有并列关系的内容，不替代论证。全文只保留一份连续参考文献；摘要、章末与结论不重复整套分类。

## 句子与段落节奏

先写谁做了什么、依据是什么，减少没有对象的抽象措辞；相邻段落必须增加信息，不能只换说法。段落长度服从论证，不为了达到章节预算扩写。常用学术词不是禁词，不能靠词频判断研究质量。

## 终稿编辑阶段

研究问题与证据核查在前，语言编辑在后。编辑不能偷偷修改数值、引文、公式含义或图片关系；发现实质错误时返回对应研究/图表环节，不能以“冻结”拒绝纠错。

检查摘要、各章首尾和结论：删除重复说明、无证据强化和制作过程旁白；同一限制在影响推论的位置解释，不逐章复制。结论只回答正文已支持的问题。结论比例、模板词密度和重复句检测仅作定位提示，是否需要修改由文体与语义决定，不能单凭7%或10%比例裁定失败。用户指定的结构合同仍须满足。

编辑后重导出并核对受影响部分；保留一份具体修订清单即可。不能输出“AI率”、人类率或保证检测通过；自然表达不能以牺牲真实性为代价。
<!-- /task-module -->

<!-- task-module:autonomous-completion -->
<!-- 公共来源：references/common/autonomous-completion.md -->

# 公共规则八：执行与续跑

按当前模式执行，不因其他模式的描述扩大任务。FULL_BUILD主线是研究计划、检索核验、大纲、分章写作、图表、整合、导出、检查与定点修订。其他模式只执行用户要求的部分。

研究契约与大纲可合写在01-research-contract.md；其中保留研究问题、材料边界、方法、章节目标与预算、图表规划和完成标准。05-outline.md、06-argument-map.md仅在确有不同用途时单列，不为文件数量复制内容。研究问题需实质改题时依用户授权处理，未获授权则保留原题并报告无法支持的承诺。

每章记录实际长度和必要的连续性摘要；下一章使用计划、证据和前章摘要，不反复加载全部历史正文。章节预算是规划，不是填充指标；可以有理由地重分配，不能靠重复、结论、附录或图表凑正文。总篇幅仍按run-params.md的用户合同验收。缺少材料时完成可诚实支持的设计与论证，不能编造结果补字数。

FULL_AUTONOMY不附加阶段卡。GUIDED/WEAK_MODEL仅针对明确执行困难增加00-execution-checkpoints.json；缺数据、DESIGN_ONLY/PROTOCOL_ONLY、订阅或配额缺口不等于模型能力弱。紧凑与完整提示词共用规则源，不降低真实性标准。

发现错误只返回受影响阶段；保留已验证的证据与有效图片。修订改变了被检查文件时重检该文件及依赖它的导出，不重做无关全文。接近上下文上限时保存当前进度、产物路径、未解决问题及下一动作。RESUME先用prepare_resume.py验证原提示词与产物摘要，不能默默重建；REVISE_ONLY保留原稿并用独立时间戳导出。

run-manifest.json只记录真实身份、路径、契约与报告索引。RESEARCH_STATUS是研究证据充分性，DELIVERY_STATUS是文件交付，FINAL_STATUS取14-adjudicated-status.json，不让模型重复维护相互竞争的状态。
<!-- /task-module -->

<!-- task-module:final-quality-gates -->
<!-- 公共来源：references/common/final-quality-gates.md -->

# 公共规则九：统一核验

完成实际专业/视觉观察并记录qa-review.json后，运行一个检查入口：

```bash
python3 "<SKILL_DIR>/scripts/paper.py" check --root "<OUTPUT_DIR>" --docx "<实际Word文件>" --pdf "<实际PDF文件>"
```

路径已正确登记时省略--docx/--pdf。入口只登记已有文件并计算摘要，不生成文档；根据模式自动运行既有检查器、派生兼容视图、最后调用adjudicate_status.py，输出12-final-qa-report.md和当次问题清单。不要再次手填五份底层报告或三层自报状态。

检查涵盖文献与真实来源、图片路线和实际嵌图、公式及OMML、目录条目/页码、题注、表格、篇幅和文件。没有公式/表格时仅在真实文件支持下标不适用，不补造内容。只有已核实的旧输入和报告才能复用，不能用过期PASS掩盖本次失败。

专业审查仍须核对题目与方法、主张与证据、摘要与结论，以及图中的实际节点/箭头/数值。SHA-256只绑定输入；几何整齐不等于专业正确，脚本退出成功不等于论文通过。Critical/Important和用户硬目标不能由自评分豁免；词频与结论比例仅作建议。

FIGURES_ONLY无重导只查图片；显式要求重导时检查公式和新文档。AUDIT_ONLY用源目录外的新--audit-dir，原稿只读。其他模式按现有模式矩阵核验；兼容命令仍可用于诊断，不是模型必须逐个执行的生产阶段。

只修实际问题和依赖它的输出，重新check；不全面重写或改高分数。最终答复采用本次检查结果：RESEARCH_STATUS说明证据充分性，DELIVERY_STATUS说明交付，FINAL_STATUS为汇总。任何命令失败、报告缺失或陈旧都不能报成功；PARTIAL与具体缺口应如实交付。所有最终文件摘要由工具计算。
<!-- /task-module -->

<!-- task-module:mathematical-formulas -->
<!-- 公共来源：references/common/mathematical-formulas.md -->

# 公共规则十：公式

仅在任务包含公式或需检查公式时使用。先核对数学含义：符号定义、单位/量纲、前提、边界条件、代入与结果是否一致。工具只能检查转换和计算，不能代替这一步。

Markdown统一使用行内$...$、独立$$...$$，不把\\(...\\)、\\[...\\]作为最终分隔符混用。代码字符串使用安全的原始字符串，避免\\text、\\frac、\\nabla被解释成制表、换页或换行。花括号与环境配对；价格符号、代码示例中的美元字符不能被误作公式。

使用支持tex_math_dollars的转换器或等效数学转换路径，DOCX公式必须是m:oMath/m:oMathPara原生OMML。不可通过python-docx整段读取再赋值破坏已有数学对象。PDF通过公式渲染器显示，不能直接显示TeX源代码，也不能用生图模型重画精确数学公式。

先用包含分式、上下标、根式、希腊字母、矩阵及中文说明的最小样例验证当前导出链；只测试本稿确实使用的类型。之后复用同一路径，不每章重造导出程序。默认避免公式过宽、编号碰撞，长公式按数学结构分行；渲染后检查符号缺字和上下标位置。

equations/formula-audit.md只记录重要公式的定位、含义检查与发现的问题，不重复抄写全文。verify_formula_rendering.py生成formula-verification.json并绑定Markdown、DOCX、PDF的SHA-256。无公式记录真实零项；缺转换或视觉能力记录CAPABILITY_GAP，不声称已验证。已有论文单独改图不得破坏其公式。
<!-- /task-module -->

<!-- task-module:quality-90 -->
<!-- 公共来源：references/common/quality-90.md -->

# 公共规则十一：具体审查与独立评分

90分是独立评测目标，不是作者必须填写的结果。当前方向专业检查卡用于找到真实问题；不因文件齐全、回执存在或模型自报高分宣布达标。

## 一份审查输入

在qa-review.json（schema_version:1.1）集中记录实际审查；模型先完成观察，工具prepare_audit_views.py只投影为旧格式并计算摘要。保留原始资料、检索日志、图片调用、视觉回执和最终文件，不用汇总替代证据。

- claims：重要主张的location、importance、evidence_ids、来源页/章节、反例与边界。CORE/CONCLUSION不得缺少证据指向。
- figures：每张figure_id、与权威清单相同的final_embed_file、status、blind_summary、checked_file和visual_receipt。遮住图题核对节点、边、数值与正文，实际文件和观察缺一不可。
- document_checks：checkpoint、正整数page、status、checked_file（最终PDF的实际页面图）、visual_receipt、发现问题。检查cover、primary_abstract、toc、complex_table、complex_formula、representative_figure、references、last_page等适用位置；确实无对应内容时写status:NOT_APPLICABLE及reason，不造图或公式。检查器从真实DOCX确认零公式/表格/媒体；只有明确JOURNAL或REPORT可免封面/目录，未知模板不自动豁免。
- review：reviewer_mode为SELF或ISOLATED，真实status、issues（critical_open、important_open、显式items），alignment四项：title_supported、research_question_answered、method_result_consistent、abstract_conclusion_consistent。每个问题写level、location、evidence、fix、status；未解决问题不能写成RESOLVED。

有真实隔离审稿时reviewer_source绑定实际审稿来源文件；不能只改ISOLATED字符串伪装独立性。scores和total仅在实际执行数字评分时填写，按证据25、内容20、结构15、配图15、文档15、自审10；无评分就省略，不默认给0或90。

统一检查入口会自动进行审计视图投影，无需另开一个生产步骤：
```bash
python3 "<SKILL_DIR>/scripts/paper.py" check --root "<OUTPUT_DIR>"
```

工具生成claim-evidence-map.json、figures/figure-semantic-audit.json、16-document-visual-audit.json、09-final-peer-review.json及兼容15-quality-scorecard.json；有能力JSON和权威图片JSON时派生其Markdown视图。没有实际观察或文件不一致时不能生成成功材料。关键文件和回执摘要由工具绑定；输入变化后旧审查失效，不自动续签。

## 判定与返修

Critical和Important必须处理；缺原始材料、缺视觉工具或无法完成修复时明确交付缺口，不能以提高评分逃避。纯语言比例、常用词密度作建议，真实性、数学和专业错误仍为实质问题。

SELF或未评分只说明已做自审，不是90分已验证，质量保持PARTIAL。有实际独立评分时仍须总分≥90、各维≥80%、无未解决重要问题、来源和检查覆盖有效，才可报告对应评测结果。每张图的节点/箭头和最终目录必须实际查看；工具绑定证据不证明审稿结论正确。
<!-- /task-module -->

<!-- task-module:svg-layout -->
<!-- 公共来源：references/common/svg-layout.md -->

# 可选模块：SVG降级与领域矢量布局

仅在任务选择需要SVG或DOMAIN_EXACT时使用；不改变生图优先和成功图片保留规则。先列事实清单（节点、边、逐字标签、禁止关系），再写坐标。

## 各类SVG的通用布局语法

流程图按主方向分层，决策分支写条件；组织架构按真实隶属分层；ER/UML保留基数、主外键和关系类型；电路/引脚用真实符号及引脚映射，不把方框图冒充电气原理图；机制图区分因果、关联和假设；时间线尊重真实先后和刻度。统计图由真实数据计算，不手工画数值。

先尝试适合语义的确定性布局。简单节点边图可提交不含坐标的figure-spec.json给render_svg_layout.mjs；编译失败、关系稠密或领域符号不适合时返回原生/领域工具，不能删掉必要边来通过检查。高质量原生图保留，不强制套模板。

## 几何纪律

原生图优先整数坐标网格、正交折线、统一间距；端口落在正确节点边界或引脚，不只对准某一行文字。并行边分配独立通道与入口，检查交叉、穿节点和共线重叠。长跨域边可绕外缘或分图；本来需要汇合的电气网络标结点，非连接交叉明确跨线，不为追求零交叉伪造拓扑。

标签预留空白带，检查文本边界、折行、框宽、箭头和图例；分组背景不被误当作禁止穿越的实体。虚线、曲线和斜线只在语义需要时使用，不因检查器只理解矩形与直线就禁止合法领域表示。

## 字形安全

检测当前真实可用CJK字体，字体栈可选PingFang SC、Noto Sans CJK SC、Microsoft YaHei、SimHei及sans-serif。按论文物理宽度反推字号，不能只增PNG分辨率却保留很小文字。特殊符号、上下标和单位逐项看渲染结果；优先换完整字体或合法排版，不能把μ、乘号、上下标随意替换而改变数学含义。

## 预检与视觉闭环

最终SVG→PNG→按论文尺寸看图→列具体问题→修源→重渲染→复查。SVG降级图的机械校验检查可解析线段、折线和矩形交叉/穿越/共线；复杂path、文字遮挡及语义必须另看，不声称静态几何证明覆盖全部图片。

清单svg_layout_mode为NATIVE或COMPILED；COMPILED的svg_layout记录spec_file/spec_sha256、report_file/report_sha256、renderer/renderer_sha256，报告PASS才能使用。最终嵌入PNG，源SVG与失败报告保留。DOMAIN_EXACT还须校对原始网表、引脚表或领域输入，不能把几何整齐当作专业正确。
<!-- /task-module -->

<!-- task-module:direction -->
<!-- 方向来源：references/directions/geography-environmental-empirical.md -->

# 方向提示词：地理环境与空间实证

PROMPT_ID: `geography-environmental-empirical`

## 范文结构依据

- 公开示例：地理范文《黄土丘陵区典型坡面土壤水分空间分布及剖面变化特征》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=2039642716177960960
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

自然地理、人文地理、生态、水文、土壤、遥感和GIS空间分析。

## 不适用或高风险情形

没有样点、坐标、遥感数据或公开数据集却输出空间分布和变化率。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 研究区与问题
2. 理论和相关研究
3. 数据来源与尺度
4. 采样、遥感或GIS方法
5. 空间/时间结果
6. 驱动机制与尺度效应
7. 不确定性和外推边界
8. 结论

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 研究区边界
- 投影坐标系
- 采样设计
- 数据集版本
- 遥感产品
- GIS工程和脚本
- 质量控制记录

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：Web of Science（INSTITUTION_REQUIRED）；ScienceDirect（出版平台，逐篇判断）；CNKI地理学核心刊（注明目录版本）。
- 证据与全文：NASA Earthdata、USGS、Copernicus（LOGIN_REQUIRED免费注册或OPEN_API）；地理空间数据云等官方数据集页面；OpenStreetMap仅作底图并标注许可。
- 开放路线：Earthdata、USGS、Copernicus官方产品；OpenAlex、Crossref（OPEN_API）。
- 不宜作核心引文：无版本号的网盘栅格、未注明投影与来源的地图截图。
- 信源核验门槛：遥感产品记录名称、版本、时相、分辨率与下载日期；地图注明投影、比例尺与数据来源。

## 图表与表格

研究区地图、采样点、剖面、空间分布和时间变化；地图必须含比例尺、指北针、图例和数据源。

## 无材料时的降级规则

无空间数据时仅形成采样方案、数据字典和分析流程。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。
<!-- /task-module -->

<!-- task-module:rubric -->
<!-- 质量评分来源：references/quality/direction-rubrics.json -->

## 当前方向专业检查卡

本卡用于发现问题，不要求写作模型给自己评分。

### 专业深度关注点

- 空间尺度与数据版本
- 空间方法和不确定性
- 地图、机制与外推边界

### Critical错误

- 虚构坐标/遥感数据
- 空间尺度错配
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 保存原始栅格/矢量、版本、许可和下载回执
- 空间单元、投影、分辨率和面积口径一致
- 地图与统计使用同一处理结果

### 数据不足时的题目与主张处理

无法处理原始空间数据时改用明确的已发布统计产品，不手绘面积、坐标和变化率。
<!-- /task-module -->
