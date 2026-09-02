# 更新记录

## 2.1.0-dev - 2026-08-29

### 2026-08-30：执行流程收敛

- 默认入口改为准备、生产、检查、定点修复四阶段。新增paper.py prepare/check/resume，将机械准备和多检查器编排隐藏在确定性入口中，不生成研究内容。
- 模型一次填写paper-request.json；自动生成参数、能力/Profile/模块记录与Manifest，不再重复维护多份准备文件。
- 新Manifest使用DERIVED_ONLY，取消三层作者自报状态的必填要求；真实性和实际裁决仍由原检查器处理。
- check登记真实输出及摘要，保存当次日志与旧报告，返回实际FAIL/PARTIAL/PASS，不以退出码或旧PASS代替当前结果。
- AUDIT_ONLY在新副本检查，原稿不修改；FIGURES_ONLY只在明确重导时检查公式和文档；旧CLI保留兼容。
- 本轮仍未运行论文生产A/B，不宣称弱模型或90分目标已改善，不发布或分发。

- 本地剪枝候选，未发布、未分发，尚无真实论文A/B质量结论。
- 公共规则合并去重，full/compact同源；新增显式task-selection按模式和所需功能确定性抽取模块，保留唯一执行MD和旧CLI兼容。
- FULL_BUILD、开题、答辩、局部配图、导出、审计相互隔离；RESUME不得重建，局部任务不附整篇阶段卡。
- Profile仅用明确同模型同客户端执行失败作辅助信号，不把缺材料、缺工具或诚实PARTIAL误作弱模型。
- 新增可选qa-review.json统一实际审查输入，由工具派生兼容视图与摘要，不生成语义PASS、独立身份或数字分数。
- PDF目录核验实际条目/页码；图下重复alt题注被拦截，正文图号引用保持合法；计数剔除多行表格与TeX控制命令。
- 结论比例与词频改为建议，方向方法门按所用方法启用；保留真假数据、公式、实际嵌图及文件硬检查。
- README收敛为使用、边界、安装和维护，历史版本留在本文件。体积和测试记录在实施计划中独立报告，不宣称稳定90分。

## 2.0.0 - 2026-08-29

- 19方向新增独立方法完成门，明确核心方法成立条件以及证据不足时的改题、降级和禁止外推路线。
- 新增终稿编辑阶段：冻结事实、数据、引文、公式和图片，仅处理重复、过程旁白、强化词、章节比例和摘要—结论一致性。
- 质量检查新增结论占比、真实性边界密度、运行过程语言、宣传词和重复句监测；正文低于目标中心时QUALITY封顶PARTIAL。
- 终稿隔离审稿新增题目、研究问题、方法结果和摘要结论四项一致性门，评分卡不得脱离终稿审稿抬分。
- 图片检查阻止有生图能力时把语义结构图批量标记为`imagegen_eligible=false`；合成演示数据不得进入主张型数据图。
- 默认THESIS排版要求独立封面，摘要、Abstract与目录分别新页开始；PDF目录出现在第一页时交付失败。
- README记录Grok Build 19方向与Antigravity六篇v1.9.1回归结论，区分表面完成度与可信学术质量。

## 1.9.2 - 2026-08-29

- 新增 `capture_provenance.py`，以统一机器回执登记用户/作者原始文件、HTTP下载与真实计算/仿真命令。
- 数据验收增加19方向ID白名单、原始来源链、官方下载字节、领域引擎输入输出、退出码和未声明随机结果检查。
- 禁止本次项目脚本生成的CSV/JSON冒充 `AUTHOR_OBSERVED`，禁止手写成功文本冒充获取、观察和仿真回执。
- 修复作者—年份制参考文献被交付检查器统计为零篇的问题。
- 文档视觉检查强制使用页面级PNG/JPEG/WebP和正整数页码，不再接受整份PDF作为检查点文件。
- 最终质量评分绑定 `09-final-peer-review.json`；终稿审稿必须覆盖最终正文、图表清单、视觉审计、DOCX和PDF，未关闭Important阻止QUALITY_OK。

## 1.9.1 - 2026-08-29

- 修正v1.9.0只完成质量框架却过早宣称路线闭环的问题。
- QUALITY成为第五个底层报告：FAIL强制最终FAIL，PARTIAL封顶交付PARTIAL，不能旁路权威裁决。
- 图文语义与文档视觉PASS必须绑定被检查文件、页面图、视觉工具回执及SHA-256。
- 从19方向评分卡生成19份隔离审稿Prompt，审稿输入禁止包含作者自评分，先定位问题再给分。
- 新增57任务运行与汇总器；只有57份真实质量报告和权威裁决均存在并达到门槛时，`release_pass`才可能为true。
- 明确基准配置、运行器完成不等于57篇模型任务已实际执行。

## 1.9.0 - 2026-08-29

- 合并v1.7—v1.9路线，新增19方向90分评分卡、专业关注点与方向级Critical规则。
- 新增 `claim-evidence-map.json`、`15-quality-scorecard.json`、`figures/figure-semantic-audit.json`、`16-document-visual-audit.json` 和 `verify_quality_package.py`。
- 90+声明要求Critical为0、总分≥90且六维均达到满分80%；研究状态PARTIAL不阻止高质量方案获得90分。
- 图表语义审计使用遮住图题后的盲读摘要，阻止换标题复用模板图、无关曲线和错误关系。
- 文档视觉审计覆盖封面、双语摘要、目录、复杂表格、复杂公式、代表图、参考文献与末页。
- 新增57任务强模型基准矩阵和非退化发布门。

## 1.6.0 - 2026-08-29

- 新增 `RESUME` 与 `prepare_resume.py`，验证原提示词、Manifest、阶段状态及SHA-256后从首个未完成阶段继续。
- 新增 `REVISE_ONLY`、修改稿规则、影响清单Schema与确定性修改提示词合成器；未受影响证据和图表保持冻结。
- 新增机器可读模式×检查器矩阵及 `write_skipped_report.py`；SKIPPED状态绑定模式、原因、输入和上游报告，FULL_BUILD禁止跳过。
- 状态裁决器支持模式化RUN/UNCHANGED/NOT_APPLICABLE，并拒绝手写跳过、跨模式跳过和链式跳过。
- 中文THESIS及无模板中文JOURNAL默认要求中英文摘要与关键词；DOCX和Markdown同时检查。
- 默认字数按用户值、模板、论文层次和25,000兜底分层；新增 `resolve_default_length.py`，英文论文使用独立词数默认值。
- Python入口补充 `python3`、`python`、Windows `py -3` 回退。
- `AUTO_COMPLETE`替代面向用户的AUTO_BENCHMARK名称，旧名称保留兼容；适配器增加工具拓扑判断。
- SKILL长段落改为检查器职责列表；README版本信息开始向CHANGELOG收敛，后续继续精简历史评测长文。

## 1.5.0 - 2026-08-29

- 新增 `FULL_AUTONOMY`、`GUIDED`、`WEAK_MODEL` 三档执行Profile；公共真实性和交付标准不变，只调整任务组织与上下文负载。
- 新增 `select_execution_profile.py` 与Profile Selection Schema；用户覆盖优先，同模型历史PARTIAL进入GUIDED、历史FAIL进入WEAK_MODEL，默认保持强模型自主路径。
- FULL_AUTONOMY的最终提示词字节与旧合成方式完全一致，不附加Profile任务卡，防止强模型退化。
- 新增弱模型紧凑公共核心，并从同一19方向源确定性生成19份 `*-compact.md`；实际体积约11.6—13.0KB，对比完整版约84KB。
- 真实电子电路方向前向合成验证：Cursor FULL_AUTONOMY为86,561字节且与旧路径逐字节一致；Antigravity同模型历史FAIL自动选择WEAK_MODEL，最终输入16,344字节，减少81.1%。
- GUIDED使用完整提示词加阶段检查；WEAK_MODEL使用唯一compact提示词加弱模型任务卡，不同时加载完整版。
- 新增 `00-execution-checkpoints.json` 与Schema，六阶段产物绑定路径和SHA-256；未关闭任务卡、文件缺失或后续改写时最终裁决失败。
- `compose_prompt.py` 新增Profile校验，阻止WEAK_MODEL误用full、GUIDED漏任务卡或FULL_AUTONOMY被附加弱模型模板。
- `run-manifest.json` 新增 `execution_profile`、`profile_selection_report` 与条件化 `execution_checkpoints`；权威状态报告记录实际模型、Skill版本和Profile。
- 新增15项Profile选择、合成、身份绑定与阶段裁决测试，并把compact同步、体积上限和关键契约接入CI。

## 1.4.0 - 2026-08-29

- 新增 `verify_evidence_integrity.py`，机械核对DOI题名、全文状态来源、定位信息、引用覆盖和数据来源。
- 证据矩阵新增 `fulltext_locator`、`page_locator`，本地全文可绑定 `source_file/source_sha256`；作者—年份制新增唯一 `citation_token`。
- `run-manifest.json` 新增真实 `model_label`、`skill_version`、`citation_mode` 与 `research_claim_level`，禁止用目录名代替模型身份。
- 新增Data Provenance Schema与 `data/data-provenance.json`，模型合成数据不得支撑结果、仿真结果或正式设计计算。
- 设计稿和实验方案没有观察数据却声称实测、显著提升、P值、满意度或通过测试时返回Critical错误。
- 图表、公式、文献和总交付四份报告新增当前检查器名称、版本、检查器SHA-256与输入文件SHA-256，旧报告、检查后修改或模型手写报告不能通过最终裁决。
- 新增 `adjudicate_status.py` 与 `14-adjudicated-status.json`；最终权威状态由报告计算，Manifest声明冲突被保留但不能覆盖结果。
- `DESIGN_ONLY` 与 `PROTOCOL_ONLY` 的研究状态自动封顶为PARTIAL，不影响交付质量评分；底层报告FAIL时最终状态强制FAIL。

## 1.3.1 - 2026-08-28

- 修复正文首行缩进被Pandoc `Compact` 或表格段落样式继承到Word单元格的问题。
- 表格单元格普通段落强制取消首行与悬挂缩进，表头、文字型表体和数值型表体按内容分别对齐。
- `verify_manuscript_delivery.py` 新增有效样式继承解析，沿直接格式、当前样式、`basedOn` 父样式以及无效样式ID向默认Normal回退，检查 `firstLine/firstLineChars/hanging/hangingChars`。
- 新增继承异常与显式清零两项回归测试；对Grok Build v1.3.0九篇结果前向检查，检出3篇共424个真实异常单元格，6篇无误报。

## 1.3.0 - 2026-08-28

- 新增数学公式公共规则，统一Markdown公式源稿、符号与量纲审计、Word可编辑公式和PDF可见结果要求。
- 最终Markdown统一使用 `$...$` 与 `$$...$$`；兼容识别并阻止HY4常见的 `\(...\)`、`\[...\]` 未归一化后直接导出。
- 新增公式控制字符检查，阻止程序写文件时把 `\text`、`\frac`、`\nabla` 误解释为制表、换页或换行并静默破坏公式。
- DOCX公式必须为OMML `m:oMath`/`m:oMathPara`对象，普通正文残留TeX分隔符或命令时机械验收失败。
- 新增 `verify_formula_rendering.py`，检查四类分隔符、花括号、环境配对、Word公式对象数、DOCX/PDF可见TeX残留和最终文件摘要。
- `FULL_BUILD` 新增 `equations/formula-audit.md` 与 `equations/formula-verification.json`，总交付检查强制读取公式报告并核对Markdown、DOCX和PDF SHA-256。
- 新增Antigravity `$$...$$` 与HY4 `\[...\]` 原样进入Word的回归测试，避免只修复单一模型或单一分隔符。

## 1.2.0 - 2026-08-28

- 中文论文配图默认使用简体中文说明，芯片型号、协议、化学式、蛋白/基因名、单位和标准缩写按白名单保留。
- Figure Manifest升级到Schema 1.5，新增 `language_contract`、`text_render_strategy`、`text_overlay` 与VLM `language_check`。
- 图片Prompt强制包含逐字目标语言标签；中文论文整体改用英文标签时机械验收失败。
- 新增 `DIRECT_IMAGE_TEXT`、`DETERMINISTIC_OVERLAY`、`DOMAIN_VECTOR_TEXT` 和 `NO_CANVAS_TEXT` 四种文字渲染策略。
- 确定性覆盖路线保留原始GenerateImage底图，绑定覆盖源、执行回执以及底图/最终PNG摘要，避免中文修正退化成纯SVG替图。
- Cursor适配明确GenerateImage中文失败时使用确定性中文覆盖，不以英文渲染稳定性覆盖论文语言要求。

## 1.1.0 - 2026-08-27

- 从GLM-5.3 Flash高质量电路SVG实践中提炼跨方向方法，新增逐图事实清单、禁止项、路线切换和失败证据保留规则。
- 为流程、软件架构、组织架构、ER/UML、电路与设备连接、机制概念图、统计图和科研影像规定不同布局语法。
- 原生SVG新增整数网格、正交端口、通道分配、外缘绕行、标签空白带、物理字号反推、CJK字体和高风险字形检查。
- Python图表验收器与Node布局编译器新增不同边共线重叠检测，补齐仅检查严格交叉时的几何盲区。
- 视觉验收明确执行“最终PNG渲染—缺陷清单—修改—几何复检—再次视觉检查”闭环并保留回执。
- 以5张ESP32参考SVG前向测试，3张通过，2张检出真实共线重叠并返回具体线段坐标。

## 1.0.0 - 2026-08-26

- 项目中文展示名更改为“AIWritePaper｜AI学术写作全流程”。
- Skill注册名、安装目录与GitHub仓库名统一更改为 `aiwritepaper-academic-writing`。
- Codex、Claude、Cursor、Kimi Code、Gemini、Antigravity、Grok Build、WorkBuddy、OpenCode、Copilot、Z.ai、DeepSeek-tui与通用Agent安装文档同步新名称。
- POSIX与PowerShell安装器新增旧名称迁移开关；新名称成功安装后才删除 `aiwritepaper-agentic-skill` 旧目录。
- 19个论文方向、MD-first执行架构、文献信源、配图与三级验收规则保持兼容。

## 0.9.1 - 2026-08-25

- 新增条件化四级验收：真实性和机械损坏继续阻断；缺少视觉核验降为PARTIAL；字数贴线与重复免责声明只作警告。
- Figure Manifest升级到Schema 1.4，新增 `exactness_class` 与数据 `origin/data_origin`；精确领域图禁止直接使用纯ImageGen，模型合成CSV禁止支撑正式结果。
- 图表验收报告新增 `mechanical_status` 与 `visual_status`；ImageGen图片全部跳过视觉检查时不能声明完整交付PASS。
- 交付验收强制读取并留存 `figures/figure-verification.json`，修复38篇回归中33篇未保存图表验收回执仍通过的问题。
- 新增 `document_profile`：THESIS检查DOCX正文实际字号与PDF可见目录，JOURNAL/REPORT不套用毕业论文目录，CUSTOM读取用户格式契约。
- 证据矩阵验收扩展为完整题录、主张、章节、访问和发表状态字段，阻止极简 `source_id,DOI,status` 空壳矩阵。
- 新增 `FINAL_STATUS` 一致性门，允许 `DELIVERY_STATUS=PARTIAL`；研究或交付FAIL时最终FAIL，只有两者均PASS才最终PASS。
- 正文低于目标95%产生贴线交付警告；重复真实性免责声明产生自然表达修订提示，两者均不覆盖用户明确字数容差。
- Antigravity适配新增429图片配额回执、模型合成数据标记与外部验收报告留存要求。

## 0.9.0 - 2026-08-24

- 新增六组Agent适配文件，覆盖Codex、Grok、Gemini/Antigravity、Claude/Cursor、Kimi/WorkBuddy与通用终端Agent；适配规则与唯一方向提示词确定性合并，继续保持MD-first单提示词执行。
- 新增机器可读 `00-capability-report.json` 与Schema，能力检查覆盖当前执行器、父代理、客户端和MCP/插件，阻止把“子执行器无工具”误报为整个任务无图片能力。
- Figure Manifest升级到Schema 1.3，新增 `display_number`、`imagegen_eligible` 和 `route_exemption`；图片工具可用却让结构图走SVG时返回 `IMAGEGEN_BYPASSED`。
- 新增父子代理完整图片任务交接：论文执行器先提交全部 `figure-plan.json` 与逐图Prompt，拥有Imagine、Nano Banana或imagegen的调用层必须逐张执行，不能只补第一张概念图。
- 新增 `verify_manuscript_delivery.py`，统一统计正文有效单位，检查证据矩阵列数与状态、BibTeX/最终书目数量、时间戳文件名、Manifest路径与SHA-256、Word目录/Heading/表格和PDF基础状态。
- 最终状态拆分为 `RESEARCH_STATUS` 与 `DELIVERY_STATUS`，区分诚实降级的研究材料缺口与损坏的文档交付；任一机械验收失败时交付状态必须为FAIL。
- DOCX与PDF要求来自同一份定稿和结构映射；Manifest显式图号成为Word题注唯一来源，打包与上传层不得再次移除正式文件时间戳。
- SVG降级增加论文实际栏宽、最小打印字号、宽高比与留白约束；正文规则减少重复免责声明，在不降低真实性边界的前提下改善合规说明书式表达。
- README新增0.9.0闭环架构、Agent映射及2026-08-24 Grok Bot十二题回归审计摘要。

## 0.8.2 - 2026-08-23

- README补充同题实测的文献信源执行审计，区分发现、证据和核验层，公开四组结果的状态错用、全文证据、访问诚实性和案例页码缺口。
- 新增学术正文质量规则：材料推动段落、中心框架控制、摘要克制、章节局部书目去重、句段节奏和无证据强结论降级；明确不输出AI率或承诺规避检测。
- 新增SVG单向降级：图片生成成功时不进入SVG；高质量原生SVG直接保留；只有原生布局失败时才进入 `COMPILED`。
- 新增无远程依赖的 `render_svg_layout.mjs`，弱模型只提交无坐标语义Spec，布局器负责中文换行、节点尺寸、分层位置、正交连线、端口和画布。
- Figure Manifest升级到Schema 1.2，新增 `svg_layout_mode` 与编译Spec、报告和渲染器摘要记录；新增 `svg-layout-spec.schema.json`。
- 新增9项Node隔离测试并接入CI；22项Python图表验收同步验证编译布局输入、输出、报告和渲染器SHA-256。

## 0.8.0 - 2026-08-23

- 最终DOCX/PDF改为“安全论文题目_YYYYMMDD-HHMMSS”命名，两种格式共用同一时间戳；Manifest记录时间、时区、路径和SHA-256。
- README新增2026-08-23同题实测快照，明确单次未校准审计边界，并记录Grok、Kimi→K3、Gemini 3.7 Flash与MiniMax M3的实际优缺点。
- 安装器新增ZCode（Z.ai）与DeepSeek-tui（Codewhale）的用户级和项目级Skill路径。
- Figure Manifest升级到Schema 1.1，新增标准 `references/schemas/figure-manifest.schema.json`。
- `IMAGE_GENERATION` 新增真实调用回执契约，绑定工具、模型、时间、调用ID以及Prompt、回执、生成文件SHA-256；只有模型自述时机械校验失败。
- VLM的 `PASS`/`PASS_WITH_NOTES` 新增视觉工具回执、检查时间和被检查最终图片SHA-256；无视觉能力时必须明确 `SKIPPED` 原因。
- 图表Markdown摘要与权威JSON新增一致性校验，每个 `figure_id` 和 `final_embed_file` 必须恰好对应一次。
- DOCX验收新增Heading 1/2/3、TOC字段、图题缺失/重复和媒体摘要检查。
- PDF验收由文件头检查升级为真实解析、页数、疑似空白页和图像对象数量检查；缺少解析依赖时明确警告。
- `DATA_CODE` 新增数据执行回执，绑定实际命令、运行日志、源数据、脚本与最终输出SHA-256。
- SVG静态几何检查新增直线/折线交叉与横穿矩形节点检测；复杂贝塞尔路径明确保留VLM核验。
- 图表隔离测试从10项增加到20项，覆盖调用回执、VLM回执、数据执行血缘、摘要漂移、Word目录、重复图题和SVG直线交叉。

## 0.7.0 - 2026-08-23

- 吸收ARS的统计可视化优点，新增图表类型决策、色盲安全、坐标轴与单位、误差棒、出版尺寸、300 DPI和“不应画图”规则。
- 新增统计图反虚构门：随机模板、手写演示数组和 `PROPOSED`/`HARDCODED_EXAMPLE` 不能进入正式结果图；研究仿真必须保留模型、参数、种子和输出数据。
- 详细大纲新增 `figure_plan[]`，制图前冻结目的、图类、数据/上下文来源、生成路线、位置和风险。
- 新增权威 `figures/figure-manifest.json`；Markdown清单降为人类可读摘要，所有导出只读取JSON中的 `final_embed_file`。
- Figure Manifest加入数据状态、脚本SHA-256、图题主张、正文用图主张、limitations、VLM状态和图片内题注禁止字段。
- 新增统计图与结构图双VLM检查表，最多两轮修复；仍有问题标记 `NEEDS_REVIEW`，不能假装通过。
- 新增 `verify_figure_package.py`，机械检查Manifest、路径、文件、脚本哈希、Markdown链接、DOCX媒体和基础PDF；结构通过不替代学术判断。
- 新增10项隔离测试，覆盖有效数据图、错误数据状态、脚本哈希、Markdown错链、随机函数未声明、ImageGen最终嵌入、回退SVG、图片内题注、CJK字体和DOCX媒体不一致。

## 0.6.0 - 2026-08-23

- 19个方向提示词各内置“文献信源”清单：发现与筛选库、证据与全文来源、开放路线、不宜作核心引文和方向核验门槛。
- 公共文献规则新增信源三层分工：发现层（索引与引文库）、证据层（全文、法源、标准、官方数据）和核验层（Crossref、DOI、PubMed/SinoMed），索引记录不作全文证据。
- 新增访问方式标记 `OPEN_API`/`OPEN_WEB`/`LOGIN_REQUIRED`/`INSTITUTION_REQUIRED`/`MANUAL_ONLY`；检索日志必须记录实际访问路径，禁止虚构未访问数据库的检索过程。
- 首选库不可访问时记录 `CAPABILITY_GAP` 并转入开放路线（OpenAlex、Crossref、PubMed/PMC/Europe PMC、arXiv、DOAJ及官方政府、标准、统计、法源网站）。
- 新增中文题录入口规则：CNKI海外镜像、万方维普交叉去重、SinoMed CBM主题词检索；“CNKI核心刊”必须区分CSSCI/CSCD/北大核心/中国科技核心并记录目录版本。
- 新增预印本与工作论文政策：标注发表状态、与正式版去重、核心主张优先正式发表来源。
- 证据矩阵新增 `evidence_role`、`access_mode`、`publication_status` 三列。
- 三个新增字段采用机器可读受控值，兼具多种角色或访问路径时用 `|` 连接，禁止自由创造近义状态。
- 方向级专项核验门槛：法源版本与生效状态、标准号与年份、数据集版本与许可、器件手册版本、系统综述至少双库交叉。
- 编译校验新增文献信源章节位置、五类条目、访问标记、规范数据库名称和侵权来源残留检查。

## 0.5.0 - 2026-08-22

- 将长提示词复制从模型生成改为文件级确定性合成：模型只写 `run-params.md`，`compose_prompt.py` 原样拼接唯一compiled prompt与条件附加规则。
- `SKILL.md` 不再维护重复的19方向表；已有题目统一读取 `routing.md`，无题目时按需读取 `topic-selection.md`。
- 接通 `PROPOSAL_ONLY` 与 `DEFENSE_ONLY`，开题和答辩规则按需合入同一 `final-execution-prompt.md`。
- 新增 `build_compiled.py` 与 `verify_compiled.py`，重建并校验19份compiled prompts、路由目标和版本同步。
- 新增GitHub Actions同步校验，防止common、directions与compiled prompts漂移。
- 补充 `MODEL_LABEL` 用途、自然触发词和跨平台原生拼接降级说明，移除空 `figure-skills` 死引用。
- 安装器新增Kimi Code用户级与项目级路径支持，默认安装到 `$KIMI_CODE_HOME/skills` 对应的 `.kimi-code/skills`。

## 0.4.2 - 2026-08-22

- 新增 `final_embed_file` 唯一最终插图入口，禁止整合与导出阶段重新按同名文件或扩展名选图。
- Imagine/image-gen成功生成后，最终Markdown、DOCX和PDF必须使用生成位图或以其为底图合成的PNG。
- SVG、HTML、Mermaid与Graphviz文件降级为备用源或修正层，不能覆盖成功的图片生成产物。
- Word导出后要求检查 `word/media/` 与PDF视觉结果，确认最终插图与图表清单一致。

## 0.4.1 - 2026-08-22

- 直接题目触发完整生产且未指定字数时，默认正文目标固定为25,000字，可接受区间22,500—27,500。
- SVG降级图新增连接线整齐度、交叉、穿越、转折、箭头和连接点位置要求。
- 新增无学校模板时的A4中文学术论文默认排版格式。
- 规定Word图号与图题只有一个可见来源，阻止图片内题注、Markdown题注和Caption题注重复。
- 强制章、节、小节使用内置Heading 1/2/3与大纲级别，支持Word左侧导航窗格和可更新目录。

## 0.4.0 - 2026-08-22

- 恢复MD-first架构：方向确认后只加载一份约18KB的完整自包含提示词。
- 新增 `final-execution-prompt.md` 交接方式，将本次参数、用户边界与方向完整提示词合为单一输入。
- 移除运行版Skill中的Python流水线、确定性状态机、测试代码和会被递归发现的配图子Skill。
- 将能力检查、证据边界、字数控制、文献目标、图表目标、DOCX/PDF和最终验收重新交给模型依据材料语义自主决策。
- 加入弱模型持续完成机制：逐章核对计划与实际字数，禁止在附录或参考文献之后追加扩展章节补字数。
- 保留19个方向增量与19份预合成完整提示词。
- 将图片能力优先生图、数据统计图代码生成、精确流程图详细Prompt和中文SVG降级规则直接合入所有完整提示词。
- 增加Grok Build项目级与用户级安装参数。

## 0.3.1 - 2026-08-22

- 新增中文 SVG 字体静态门，阻止中文文本缺少字体声明或只使用拉丁字体栈。
- 固化跨 macOS、Windows、Linux 的中文字体回退栈，并要求使用最终渲染器完成中文探针、PNG、DOCX 与 PDF 抽查。
- 明确区分可编辑 SVG 与跨环境定稿版本；需要文字转路径时必须保留可编辑源并核对字体许可。
- 新增 image-gen 交付门禁：当前客户端暴露图片生成工具时，完整论文默认至少真实生成一张与正文相关、明确标注为非证据性概念示意的位图；全部回退 SVG 不得通过验收。
- 修复“图片能力未验证所以不调用、因为未调用所以永远未验证”的循环，要求先执行受控图片调用再更新能力与图表清单。

## 0.3.0 - 2026-08-22

- 新增真实能力探测、受控证据命令执行、证据清单校验、确定性章节整合与 DOCX/PDF 导出。
- 新增最终交付验收器，由脚本计算 `PASS/PARTIAL/FAIL`，阻止缺文件或旧 QA 自报成功。
- 新增 `ROUTE_ONLY`、`FULL_BUILD`、`FIGURES_ONLY`、`EXPORT_ONLY` 和 `AUDIT_ONLY` 运行模式。
- 对真实系统观测、模拟、合成数据和硬编码示例实施不同证据等级。
- 新增 WorkBuddy 项目级与用户级安装支持，并补充全局安装和技能发现说明。

## 0.2.0 - 2026-08-22

- 新增学术配图公共路由，区分生成式图片、确定性 SVG、数据绘图、领域工具和原始科研图像。
- 新增 `IMAGE_GENERATOR` 与 `SVG_RENDERER` 能力核验，禁止把图片理解、SVG 代码或渲染器误报为图片生成能力。
- 新增可独立安装的 `academic-figure-router` 与 `academic-svg-enhancer`。
- 新增 SVG 静态审计器及测试，覆盖 XML、画布、字号、远程资源和可访问性元数据。
- 重新编译 19 个论文方向提示词，并将配图证据边界和质量门写入全部方向。
- 新增 Antigravity 项目级与全局安装支持。

## 0.1.0 - 2026-08-21

- 首次发布 AIWritePaper 选题路由、19 个论文方向提示词和可审计论文生产规则。
