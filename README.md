<div align="center">

# AIWritePaper｜AI学术写作全流程

**从论文题目到一份完整执行提示词，再持续交付正文、配图、DOCX 与 PDF。**

![Version](https://img.shields.io/badge/version-1.3.1-2563EB?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-16A34A?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-MD--first-7C3AED?style=flat-square)
![Directions](https://img.shields.io/badge/paper%20directions-19-EA580C?style=flat-square)

[快速开始](#快速开始) · [工作方式](#工作方式) · [同题实测](#2026-08-23同题实测快照) · [配图策略](#配图策略) · [Word交付](#word交付) · [安装路径](#安装路径)

</div>

> [!NOTE]
> 当前版本采用 **MD-first 单提示词执行 + Agent能力适配 + 确定性交付验收**。模型继续负责方向、检索、论证、写作、公式含义和配图语义；脚本只统计字数并核对公式结构、图片路由、文件、目录、表格与哈希，不生成论文内容。

## v1.3.1表格文字缩进修复

- 正文两字符首行缩进只用于表格外普通段落，不再继承到表格单元格；
- Pandoc常用的 `Compact`、`Table`、`Table Text` 样式必须显式取消首行与悬挂缩进；
- 自定义DOCX导出器需要把单元格段落的 `firstLine`、`firstLineChars`、`hanging` 和 `hangingChars` 全部清零；
- 交付检查器按“直接格式—当前样式—basedOn父样式—无效样式ID回退Normal”计算有效缩进，避免只检查单元格XML而漏掉样式继承；
- 对Grok Build v1.3.0九篇结果回测，准确检出3篇共424个继承 `Compact firstLine=420` 的异常单元格，另外6篇保持通过。

## v1.3.0公式渲染闭环

- 最终Markdown统一使用 `$...$` 与 `$$...$$`；HY4常见的 `\(...\)`、`\[...\]` 必须在导出前等价归一化；
- 检查程序写文件时的反斜杠转义，阻止 `\text`、`\frac`、`\nabla` 被错误转换成TAB、换页或换行控制字符；
- DOCX公式必须转换为可编辑OMML对象，禁止把 `\frac`、`\sqrt`、`\text`、`\partial` 等TeX命令写进普通Word文本；
- 优先使用支持Markdown/TeX数学到OMML的成熟导出链，后续排版不得以纯文本重建段落破坏公式；
- PDF必须来自同一份已验证定稿，页面中不得显示公式分隔符或TeX源码；
- 新增 `equations/formula-audit.md`，记录重要公式的符号、单位、量纲、假设和视觉抽查；
- 新增 `verify_formula_rendering.py`，同时检查四类源稿分隔符、花括号、Word公式对象、DOCX/PDF残留源码与最终文件摘要；
- `formula-verification.json` 未达到 `FORMULA_OK`，或者未与最终DOCX/PDF摘要绑定时，总交付检查不能通过。

## v1.2.0中文论文配图语言一致性

- 图片默认跟随论文主语言；中文论文的普通节点、流程动作、分组标题与风险提示使用简体中文；
- Figure Manifest 1.5新增 `language_contract`、技术词白名单、逐字标签、文字渲染策略与语言视觉核验；
- 图片Prompt可以用英文描述风格，但 `exact_labels` 必须使用论文目标语言并逐项出现；
- Cursor GenerateImage、Imagine、imagegen等中文不稳定时保留生成底图，使用 `DETERMINISTIC_OVERLAY`确定性覆盖中文；
- 覆盖路线绑定原始生成图、覆盖源、执行回执与最终PNG摘要，不能改插纯SVG冒充生图；
- VLM发现非白名单英文长句、英文节点标题、中文错字、伪字或乱码时不能标记PASS。

## v1.1.0跨方向SVG绘制方法

- 每张SVG先生成事实与禁止项清单，再决定节点、边和坐标，防止拓扑先天画错；
- 简单节点—边图优先无坐标语义Spec和确定性编译，稠密跨域结构失败后拆图或转原生SVG；
- 为流程、架构、组织、ER/UML、电路、机制、时间线分别规定可复用布局语法；
- 原生SVG采用整数网格、正交连线、边界端口、独立通道、外缘绕行和文字空白带；
- 几何预检新增不同边共线重叠检测，与交叉、穿节点、节点重叠共同硬阻断；
- `verify_figure_package.py --preflight-svg`可在整合Manifest前单独检查原生SVG；
- 按论文实际栏宽反推字号与DPI，并对中文字体、特殊符号和实际PNG执行两轮视觉闭环。
- 使用5张ESP32参考SVG前向验证：3张直接通过，2张准确检出此前严格交叉算法遗漏的共线通道重叠。

## v1.0.0一步到位更名

- 中文展示名统一为 **AIWritePaper｜AI学术写作全流程**；
- Skill注册名与安装目录统一为 `aiwritepaper-academic-writing`；
- GitHub仓库统一为 `huangnan29/aiwritepaper-academic-writing`；
- `install.sh`与`install.ps1`支持迁移旧安装，安装成功后再清理旧目录；
- 论文生成规则、19个方向和0.9.1验收能力保持不变。

## v0.9.0解决什么

```text
统一Skill规则
    ↓
按当前客户端合入一个Agent适配文件
    ↓
模型完成论文与完整图片任务单
    ↓
当前执行器或父代理逐张调用真实图片工具
    ↓
图表验收 + 正文/文献/文档验收
    ↓
失败返回对应阶段修复，通过后才允许交付
```

- **Agent适配**：Codex、Grok、Gemini/Antigravity、Claude/Cursor、Kimi/WorkBuddy和通用终端Agent只维护短小工具映射，19个论文方向仍共用同一套规则。
- **父子代理生图交接**：只要当前执行器、父代理、客户端或MCP任一层可以生图，适合生图的结构图就不能降级为SVG；Grok父代理不得只补第一张概念图。
- **统一字数**：最终正文由确定性检查器按同一口径重新统计，模型自报和章节预算不能覆盖结果。
- **文档闭环**：正式DOCX/PDF必须带相同时间戳，Manifest路径和哈希真实存在；Word目录、Heading层级、表格和图片题注缺失会阻止交付。
- **双状态**：`RESEARCH_STATUS` 描述研究材料是否完整，`DELIVERY_STATUS` 描述文件是否合格；诚实降级的研究方案不再与损坏的Word交付混为一谈。

## v0.9.1条件化验收

v0.9.1根据Grok 38篇方向回归与Antigravity 0.8.2失败样本，增加不会一票否决正常功能的分级核验：

- 虚构/模型合成数据、缺失文件、损坏矩阵、错误路由继续硬阻断；
- 图片已机械通过但缺少VLM或人工视觉核验时，交付降为 `PARTIAL`，仍保留可用文件；
- `THESIS`检查默认/学校模板字号和PDF可见目录，`JOURNAL`、`REPORT`不强制毕业论文目录，`CUSTOM`读取用户格式契约；
- Figure Manifest 1.4新增 `exactness_class`，普通流程与框架可ImageGen，电路、晶体、化学结构、尺度、载荷和精确通路必须领域工具或确定性底图；
- 数据源新增 `origin/data_origin`，模型自行生成的CSV不能冒充实验、问卷、临床、性能或统计结果；
- 证据矩阵必须包含完整题录、支持主张、章节与访问/发表状态，不能只写 `source_id,DOI,status`；
- 强制 `RESEARCH_STATUS`、`DELIVERY_STATUS`、`FINAL_STATUS` 三层一致；
- 低于目标95%和重复免责声明只产生修订警告，不改变用户明确的±10%硬容差。

## 你会得到什么

| 能力 | 默认行为 |
|---|---|
| 自动选方向 | 根据题目、研究对象、方法和证据，从19个方向中选择一个 |
| 稳定字数 | 直接给题目且未指定字数时，默认正文25,000字，允许±10% |
| 文献与证据 | 先检索、核验并建立证据矩阵，不编造文献、数据或实验 |
| 方向级信源 | 每个方向内置首选库、开放路线和不宜引用清单；无订阅时走开放路线 |
| 论文生产 | 大纲、分章、累计字数检查、全文整合、同行评审与修订 |
| 正文质量 | 材料推动段落，限制框架堆叠、项目汇报腔、局部书目重复和无证据的强结论 |
| 学术配图 | 有图片工具时逐张生图；统计图由真实数据和代码生成 |
| 图表证据链 | 大纲先建立figure plan；图表追溯数据、脚本、图题主张、正文使用和局限 |
| 文档交付 | 生成并检查DOCX、PDF、目录、标题层级、题注和页码；最终文件按论文题目与时间戳命名 |
| 公式交付 | 统一公式源稿、可编辑Word公式、PDF可见结果、符号/量纲审计与机械验收 |
| 闭环验收 | 图表与正文/证据/文档分别机械验收，失败后返回对应阶段修复 |
| 条件模式 | 支持单独配图、只导出文档、只审计、只做方向判断、开题报告和答辩材料 |

## 工作方式

```text
题目与材料
    ↓
判断唯一论文方向
    ↓
模型写入 run-params.md
    ↓
文件级拼接唯一方向完整提示词与条件附加规则
    ↓
final-execution-prompt.md
    ↓
检索 → 大纲与figure plan → 分章 → Agent/父代理逐张配图 → 整合 → DOCX/PDF
    ↓
图表验收 → 正文/证据/文档验收 → QA
```

每个 `references/compiled-prompts/*-full.md` 都是完整、自包含的论文生产提示词。模型选中一个方向后，不再复述这份长文本；`scripts/compose_prompt.py` 只做确定性文件拼接，并输出字节数和SHA-256。模型随后从头到尾读取一次最终MD，后续只执行这一份文件。

### 为什么改为文件级拼接

- 避免弱模型复制长提示词时截断、意译或漏段；
- compiled prompt原文字节不经过模型生成；
- 参数、完整规则和开题/答辩附加规则仍合成一份最终MD；
- 维护脚本只负责拼接与同步校验，不参与论文决策。

### Agent适配文件

| 当前客户端 | 合入最终MD的适配文件 | 关键职责 |
|---|---|---|
| Codex | `integrations/codex.md` | 映射imagegen、视觉与文档工具 |
| Grok Build / Bot | `integrations/grok.md` | 父代理遍历完整Imagine任务单 |
| Gemini / Antigravity | `integrations/gemini-antigravity.md` | 只认实际暴露的Nano Banana等工具 |
| Claude Code / Cursor | `integrations/claude-cursor.md` | 区分图片读取、SVG与真实图片生成 |
| Kimi / WorkBuddy / MiniMax客户端 | `integrations/kimi-workbuddy.md` | 不按模型品牌推断终端工具权限 |
| 其他终端Agent | `integrations/universal-terminal.md` | 通用能力检查与失败关闭 |

适配文件在执行前与唯一方向提示词确定性合并，正式生产阶段仍只读取一份 `final-execution-prompt.md`。

## 默认规则

### 直接题目自动完成

用户直接给出完整题目并触发 `FULL_BUILD` 时：

- 不重复询问题目；
- 不停在大纲确认阶段；
- 未给字数时使用 `TARGET_LENGTH: 25000`；
- 可接受正文区间为22,500—27,500；
- 低于22,500不得标记 `PASS`；
- 用户明确给出的字数、文献、图片和表格目标始终优先。

正文统计范围为第一章至结论的主体论述，不含摘要、目录、参考文献、致谢、附录、代码、Markdown表格行和图表题注。最终值由 `verify_manuscript_delivery.py` 统一计算。

### 弱模型持续完成

- 大纲先分配章节字数，合计必须落入目标区间；
- 每章完成后检查计划字数、实际字数和累计字数；
- 章节不足时先补足原小节，再进入下一章；
- 禁止在附录、致谢或参考文献后增加“扩展章节”补字数；
- 文献、图片和表格未达标时，不提前进入排版；
- 文件存在或PDF可打开，不等于论文已经完成。

### 学术正文自然表达

- 正文自然度来自真实材料、明确判断和证据边界，不以规避检测为目标；
- 一个段落处理一个主张，写清主体、动作、对象、时间、口径和来源；
- 全文只保留一个中心分析框架，不连续堆叠四维、三重、五层、六类、三阶段；
- 摘要不写成项目战报，未运行的模型、实验和干预不能写成成果；
- 各章不重复插入局部参考文献清单，章节首尾不机械复述同一框架；
- “构建、赋能、机制、路径、体系、显著、全面、有效”必须对应具体动作或证据，不能代替论证。

完整规则见 `references/common/academic-prose-quality.md`。

### 最终文档命名

最终DOCX与PDF共用同一文件名主体和生成时间戳：

```text
数字化转型背景下连锁零售企业库存协同管理研究_20260823-103553.docx
数字化转型背景下连锁零售企业库存协同管理研究_20260823-103553.pdf
```

题目中的文件系统禁用字符会转换为下划线，`run-manifest.json`记录本地生成时间、时区、正式路径和SHA-256。`final-paper.docx/.pdf`只允许作为本次运行的内部临时文件名，不能作为最终交付。

## 2026-08-23同题实测快照

以下为同一题目、同一Skill v0.7.0、无用户材料条件下的单次本地审计。分数是**未校准的交付审计分**，用于暴露当前工具链问题，不是稳定模型排行榜；运行时暴露的图片、浏览器和文档工具不同，Kimi组还在后期因周限额由WorkBuddy K3接力完成。

| 执行环境 | 证据与诚信 25 | 内容论证 20 | 结构完整 15 | 配图 15 | DOCX/PDF 15 | 自审诚实 10 | 总分 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Grok Build | 23 | 18 | 14 | 14 | 12 | 9 | **90** |
| Kimi → WorkBuddy K3接力 | 20 | 17 | 14 | 12 | 13 | 8 | **84** |
| Gemini 3.7 Flash / Antigravity | 4 | 8 | 11 | 5 | 7 | 1 | **36** |
| MiniMax M3 / Claude Code | 6 | 8 | 4 | 6 | 3 | 1 | **28** |

主要观察：

- **Grok Build**：唯一实际采用图片生成路线的结果，4张生成图进入最终文档；正文能区分观察事实、推断和建议，自报 `PARTIAL` 与实际缺口基本一致。主要问题是PDF目录未展开、缺少三级标题以及v0.7尚无图片调用回执。
- **Kimi → K3接力**：正文、54条引用、6图7表和Word标题层级最完整，SVG结构图清晰。局限是后期换模型接力，且PDF目录页仍未展开，因此不能把全部成果单独归因给K3。
- **Gemini 3.7 Flash**：能力报告明确写有 `generate_image`，但6张结构/流程图全部走代码绘图；版面正文中位字号仅10pt、无TOC字段。更严重的是把未实际运行的LightGBM-LSTM、MIP和Shapley机制写成已构建并验证，并报告19%—21%、97.8%、2.3%等本地产物无法证明的结果，因此触发学术诚信失败门。
- **MiniMax M3**：当前Claude Code会话没有暴露图片生成工具，不能据此断言M3本身应直接生图；MiniMax平台另有[Image-01图片生成接口](https://platform.minimaxi.com/docs/guides/image-generation)及支持 `text_to_image` 的[官方MCP](https://platform.minimaxi.com/docs/guides/mcp-guide)，本次工具链未接通。最终正文把逐章局部参考文献列表重复插入，出现210条编号项；证据CSV错列，DOCX实际为0个表格、0个Heading 1且无TOC字段，与自报PASS不一致。

### 文献信源执行审计

同一批v0.7.0产物还按管理案例方向的信源契约进行了只读复核：发现层负责找候选，证据层必须阅读全文、正式披露或官方数据，Crossref/OpenAlex只属于发现或元数据核验层；案例数字还应定位到披露文件、页码、日期和报表口径。严格按这一标准，四组均未完全通过。

| 执行环境 | 发现层 | 证据层 | 核验与状态 | 权限声明 | 案例页码 | 结论 |
|---|---|---|---|---|---|---|
| Grok Build | 通过 | 基本通过 | 少量状态误标 | 通过 | 不完整 | **基本合规，最佳** |
| Kimi → WorkBuddy K3接力 | 通过 | 基本通过 | 通过 | 通过 | 不完整 | **基本合规** |
| MiniMax M3 / Claude Code | 基本通过 | 不通过 | CSV错列、仅元数据 | 通过 | 不通过 | **未达到要求** |
| Gemini 3.7 Flash / Antigravity | 存疑 | 不通过 | 虚报全文、错误DOI | 不通过 | 不通过 | **严重不合规** |

- **Grok Build**：50条证据记录中有38条元数据、9条全文、3条自创的 `VERIFIED_EXTERNAL`；真实保存了10个年报、政策和统计来源文件，并明确声明CNKI/WoS/CSMAR/Wind未访问。缺口是1条期刊摘要被标成全文、3条状态不在受控值中，以及年报数字没有逐项页码。
- **Kimi → K3接力**：54条记录中41条元数据、13条官方网页或披露全文；CNKI/WoS不可访问的声明真实，Crossref只用于英文题录。缺口是没有保存本地来源文件，部分案例依赖媒体转载，案例数字缺页码，检索日志49条与最终54条之间存在5条增量未解释。
- **MiniMax M3**：检索路线正确列出了OpenAlex、Crossref、交易所、统计局和CCFA，也诚实声明受限库未访问；但65条全部停在元数据层，5行CSV错列，没有保存年报全文，交易所和政府条目多为站点首页，无法支撑八家企业的精确案例结论。
- **Gemini 3.7 Flash**：46条中42条声称全文核验，却没有保存来源全文，至少14条仅以Crossref作为“全文”依据；日志还声称访问Web of Science并产生215条命中，缺少访问路径和结果证据。抽查的Cachon与Fisher条目使用了错误题名和404 DOI `10.1287/mnsc.46.8.1032.12023`，INFORMS官方记录的正确DOI为 [`10.1287/mnsc.46.8.1032.12029`](https://pubsonline.informs.org/doi/10.1287/mnsc.46.8.1032.12029)。

这次审计暴露出四个应机械化的门禁：`VERIFIED_FULLTEXT`不能只由Crossref/OpenAlex支持；管理案例关键数字必须记录 `source_file + page_locator + reporting_period + calculation`；检索日志宣称使用的数据库必须保存查询式和结果证据；证据矩阵必须先通过列数与受控状态检查。

v0.8.0据此新增图片调用与VLM回执、数据执行血缘、DOCX标题/目录/题注解析、PDF深度解析和更严格的真实性门；v0.8.2继续增加学术正文自然表达与弱模型SVG布局编译。未来实测必须注明Skill版本、运行客户端、实际工具和是否发生模型接力。

### 2026-08-24 Grok Bot十二题回归审计

十二个不同方向的v0.8.2结果证明MD-first正文与真实性边界总体稳定，但暴露了“提示词有规则、执行器仍绕过”的缺口：84张图中只有11张走图片生成、8张为真实数据代码图、65张仍为SVG；11篇只由父代理补一张概念图，库存协同一次图片生成也没有调用。按统一口径只有5篇达到22,500字正文下限，只有6篇通过当时的图表机械验收；12组实际DOCX/PDF均被打包层移除了Manifest记录的时间戳。

v0.9.0据此不再继续堆叠提示语，而是新增机器能力报告、父子代理完整图片任务交接、`IMAGEGEN_BYPASSED`硬门、统一正文/证据/文档验收和打包后路径哈希复核。该审计仍是单次本地结果，不构成模型能力排行榜。

## 文献信源

每个方向提示词内置该学科的文献信源清单，信源分三层使用：

| 层级 | 功能 | 典型来源 |
|---|---|---|
| 发现层 | 查找候选文献、引文追踪，不作全文证据 | Web of Science、Scopus、Ei Compendex、DBLP、CNKI、PubMed、ERIC |
| 证据层 | 实际阅读并支撑论文主张 | 出版社全文、法源与标准原文、官方指南、官方数据集、监管披露 |
| 核验层 | 核对题名、作者、年份、DOI和版本 | Crossref、DOI解析、出版社官方页、PubMed/SinoMed记录 |

- 信源标注访问方式（`OPEN_API`/`OPEN_WEB`/`LOGIN_REQUIRED`/`INSTITUTION_REQUIRED`/`MANUAL_ONLY`）；检索日志必须记录实际访问路径，禁止虚构未访问数据库的检索过程。
- 证据矩阵使用受控值：`evidence_role` 为 `DISCOVERY`/`EVIDENCE`/`VERIFICATION`，`access_mode` 使用上述五种访问标记，`publication_status` 区分正式发表、预印本、工作论文、标准、官方文件和数据集。
- 首选库需机构订阅且不可访问时，记录能力缺口并转入开放路线：OpenAlex、Crossref、PubMed/PMC/Europe PMC、arXiv、DOAJ及官方政府、标准、统计和法源网站。
- 预印本与工作论文须标注发表状态并与正式版去重；核心因果、疗效或性能主张优先正式发表来源。
- 方向级核验门槛：法源记录版本与生效状态、标准记录标准号与年份、数据集记录版本与许可、系统综述至少双库交叉。

## 配图策略

| 图形类型 | 首选路径 | 关键边界 |
|---|---|---|
| 流程、架构、框架、组织、ER/UML、机制、装置、场景 | 当前Agent实际暴露的图片工具 | 每张图保存独立Prompt和生成位图 |
| 柱状图、折线图、散点图、热图、森林图、模型诊断 | Python、R或等价代码 | 必须读取真实数据并保留计算过程 |
| 显微图、医学影像、实验照片、遥感、仪器截图 | 原始科研文件 | 不生成、补画或伪装成观测证据 |
| 公式、化学结构、电路、地图 | 对应领域工具 | 不让图片模型猜测符号和连接 |
| 无图片生成能力的结构图 | HTML/SVG → PNG | 检查中文字体、连线、箭头和连接点 |

### 统计图与图表证据链

- 统计图先定义分析问题和读图任务，再选择最简单、可辩护的图形；
- 少于3个数据点、单个百分比、单一类别或与表格完全重复时不强行画图；
- 禁止把 `np.random`、`rnorm`、`runif`、手写数组或演示模板输出当作论文结果；
- 正式统计图保存真实数据文件、单位、样本量或观测粒度、绘图脚本和脚本SHA-256；
- 数据文件、脚本、执行日志和最终输出分别计算SHA-256，运行回执记录实际命令与输入输出关系；
- 数据驱动网络图必须有节点边表或邻接矩阵；结构概念图仍执行ImageGen优先路线；
- 色盲安全、坐标轴单位、误差棒、300 DPI和论文实际尺寸可读性均为必查项；
- 当前Agent有视觉能力时，对统计图和复杂结构图最多进行两轮VLM修复；仍有问题标记 `NEEDS_REVIEW`。

详细规则见 `references/common/statistical-figures-and-trace.md`。

### 精确流程图

生图Prompt必须明确：

- 画布比例与阅读方向；
- 节点总数、逐字标签和节点形状；
- 分组、层级和主次路径；
- 每条箭头的起点、终点和分支条件；
- 禁止新增、遗漏、合并或改写的内容；
- 输出后的逐项验收清单。

### 最终插图优先级

每张图只有一个最终入口：权威 `figures/figure-manifest.json` 中的 `final_embed_file`。`figure-manifest.md` 只供人阅读。

- Imagine、`imagegen`、`image_gen`或Nano Banana成功生成后，最终Markdown、DOCX和PDF必须使用该位图；
- 如果增加文字或箭头覆盖层，先合成为最终PNG，再设置为 `final_embed_file`；
- 同名SVG只能保留为`source_file`、`fallback_file`或`overlay_source`；
- 整合和导出阶段不得扫描同名文件并重新选择SVG；
- DOCX导出后检查`word/media/`，PDF再做视觉核对。

### 图片调用与视觉检查回执

- `IMAGE_GENERATION` 必须保存图片工具实际返回结果或客户端调用片段，记录工具、模型、时间、调用ID以及Prompt、回执、生成文件SHA-256；
- 只有模型文字声称“已调用Imagine/ImageGen/Nano Banana”属于 `DECLARED_ONLY`，机械校验失败；
- VLM的 `PASS` 必须绑定视觉工具回执和被检查最终图片SHA-256，不能只填写状态；
- `figure-manifest.json` 当前使用Schema 1.5，在1.4精确性字段基础上新增图片语言契约、外文白名单、文字渲染策略和语言视觉核验；
- 人类摘要中的每个图号和最终插图路径必须与权威JSON恰好对应一次。

### SVG降级质量

- 中文使用明确的跨平台字体栈；
- 连接线尽量不交叉、不重叠、不穿越节点或文字；
- 转折位置整齐，连接点位于合理的节点边界；
- 箭头准确落在目标边界，不悬空、不伸入文字；
- 无法避免交叉时优先绕行、拆图或使用跨线桥；
- 静态校验可拦截直线/折线交叉和横穿矩形节点；复杂曲线仍需VLM或人工核验；
- 在论文实际显示尺寸检查PNG、DOCX与PDF。

### 弱模型SVG布局编译

SVG只执行单向降级，不影响强模型：

1. 图片工具可用时继续使用ImageGen/Imagine/Nano Banana；
2. 无图片工具时允许模型直接生成 `NATIVE` SVG，检查通过就保留；
3. 原生SVG出现重叠、溢出、穿越、交叉或端点错误时，改写语义化 `figure-spec.json`；
4. `render_svg_layout.mjs`只计算中文换行、节点尺寸、分层位置、端口、正交连线和画布；
5. 布局报告通过后再渲染最终PNG，并进行VLM或人工核验。

Spec不允许包含坐标和path，模型仍决定节点、分组与箭头语义。Schema见 `references/schemas/svg-layout-spec.schema.json`。

## Word交付

没有学校模板时，默认使用通用中文学术格式：

- A4；上、下2.54cm，左3.0cm，右2.5cm；
- 中文正文12pt，英文和数字Times New Roman 12pt；
- 两端对齐、首行缩进2字符、1.5倍行距；
- 章、节、小节使用内置Heading 1/2/3；
- 自动目录可更新，支持Word左侧导航窗格；
- 图题在图下方，表题在表上方；
- 表格保持原生可编辑，优先三线表；
- 图片、题注和页脚保持安全间距。

### 图号去重

- 图片画布内部不写“图X-X 标题”；
- Markdown替代文字不作为第二个可见图题；
- 普通文本题注与Word Caption只保留一种；
- 每个图号、表号在Word可见段落中恰好出现一次；
- `11-format-validation.md`记录Heading数量、目录状态和题注重复检查。

## 19个论文方向

<details>
<summary><strong>展开查看完整方向列表</strong></summary>

| 方向 | 完整提示词 |
|---|---|
| 软件系统工程 | `software-system-engineering-full.md` |
| 机械与材料工艺 | `mechanical-material-process-full.md` |
| 电子电路设计 | `electronic-circuit-design-full.md` |
| 物理材料实验 | `physical-materials-experiment-full.md` |
| 化学与复合材料 | `chemical-materials-experiment-full.md` |
| 管理案例分析 | `management-case-analysis-full.md` |
| 地理与环境实证 | `geography-environmental-empirical-full.md` |
| 生物医学实验期刊 | `biomedical-experimental-journal-full.md` |
| 机器学习应用实证 | `machine-learning-applied-empirical-full.md` |
| 教育应用研究 | `education-applied-research-full.md` |
| 艺术与设计实践 | `art-design-practice-full.md` |
| 经济与政策实证 | `economics-policy-empirical-full.md` |
| 法律规范分析 | `legal-normative-analysis-full.md` |
| 临床护理研究 | `clinical-nursing-research-full.md` |
| 数学教育 | `mathematics-education-full.md` |
| 文学文本分析 | `literature-textual-analysis-full.md` |
| 通用期刊IMRaD | `general-journal-imrad-full.md` |
| 文献综述与综合 | `literature-review-synthesis-full.md` |
| 专业工作报告 | `professional-work-report-full.md` |

</details>

## 运行模式

| 模式 | 用途 |
|---|---|
| `FULL_BUILD` | 完整论文、配图、DOCX、PDF和QA |
| `FIGURES_ONLY` | 读取现有正文，只新增或优化配图 |
| `EXPORT_ONLY` | 从现有定稿生成DOCX/PDF |
| `AUDIT_ONLY` | 只读检查现有论文与交付物 |
| `ROUTE_ONLY` | 只做选题或方向判断 |
| `PROPOSAL_ONLY` | 依据研究契约和已核验文献生成开题报告 |
| `DEFENSE_ONLY` | 依据现有定稿生成答辩大纲、逐页内容和可用演示文件 |

## 主要输出

```text
paper-output/
├── run-params.md
├── final-execution-prompt.md
├── 00-capability-report.md
├── 00-capability-report.json
├── 01-research-contract.md
├── 02-search-log.md
├── 03-evidence-matrix.csv
├── 04-reference-audit.md
├── references.bib
├── 05-outline.md
├── 06-argument-map.md
├── chapters/
├── figures/
│   ├── figure-plan.json      # 完整图片任务单
│   ├── figure-manifest.json  # 权威机器路由
│   ├── figure-manifest.md    # 人类可读摘要
│   ├── figure-verification.json
│   └── receipts/             # 图片调用与视觉检查原始回执
├── tables/
├── 07-paper-full.md
├── 08-claim-citation-audit.md
├── 09-peer-review.md
├── 10-revision-log.md
├── <论文题目>_<YYYYMMDD-HHMMSS>.docx
├── <论文题目>_<YYYYMMDD-HHMMSS>.pdf
├── 11-format-validation.md
├── 12-final-qa-report.md
├── 13-delivery-verification.json
└── run-manifest.json
```

## 快速开始

### 通用安装

```bash
npx skills add huangnan29/aiwritepaper-academic-writing
```

### macOS / Linux全局安装

```bash
# Codex
./install.sh --agent codex --scope user

# Claude Code
./install.sh --agent claude --scope user

# Cursor
./install.sh --agent cursor --scope user

# Kimi Code
./install.sh --agent kimi --scope user

# Grok Build
./install.sh --agent grok --scope user

# WorkBuddy
./install.sh --agent workbuddy --scope user

# Antigravity
./install.sh --agent antigravity --scope user

# ZCode（Z.ai）
./install.sh --agent zcode --scope user

# DeepSeek-tui（Codewhale）
./install.sh --agent deepseek-tui --scope user
```

从旧名称迁移或更新已有安装时追加`--force --migrate-legacy`。

### Windows PowerShell

```powershell
.\install.ps1 -Agent codex -Scope user
.\install.ps1 -Agent claude -Scope user
.\install.ps1 -Agent cursor -Scope user
.\install.ps1 -Agent kimi -Scope user
.\install.ps1 -Agent grok -Scope user
.\install.ps1 -Agent workbuddy -Scope user
.\install.ps1 -Agent antigravity -Scope user
.\install.ps1 -Agent zcode -Scope user
.\install.ps1 -Agent deepseek-tui -Scope user
```

从旧名称迁移或更新已有安装时追加`-Force -MigrateLegacy`。

## 安装路径

| Agent | 项目级 | 用户级 |
|---|---|---|
| Claude | `.claude/skills/aiwritepaper-academic-writing` | `~/.claude/skills/aiwritepaper-academic-writing` |
| Codex | `.codex/skills/aiwritepaper-academic-writing` | `~/.codex/skills/aiwritepaper-academic-writing` |
| Cursor | `.cursor/skills/aiwritepaper-academic-writing` | `~/.cursor/skills/aiwritepaper-academic-writing` |
| Kimi Code | `.kimi-code/skills/aiwritepaper-academic-writing` | `$KIMI_CODE_HOME/skills/aiwritepaper-academic-writing`（默认`~/.kimi-code/skills`） |
| Gemini CLI | `.gemini/skills/aiwritepaper-academic-writing` | `~/.gemini/skills/aiwritepaper-academic-writing` |
| Antigravity | `.agents/skills/aiwritepaper-academic-writing` | `~/.gemini/config/skills/aiwritepaper-academic-writing` |
| Grok Build | `.grok/skills/aiwritepaper-academic-writing` | `~/.grok/skills/aiwritepaper-academic-writing` |
| GitHub Copilot | `.github/skills/aiwritepaper-academic-writing` | `~/.copilot/skills/aiwritepaper-academic-writing` |
| OpenCode | `.opencode/skills/aiwritepaper-academic-writing` | `~/.config/opencode/skills/aiwritepaper-academic-writing` |
| WorkBuddy | `.workbuddy/skills/aiwritepaper-academic-writing` | `~/.workbuddy/skills/aiwritepaper-academic-writing` |
| ZCode（Z.ai） | `.zcode/skills/aiwritepaper-academic-writing` | `~/.zcode/skills/aiwritepaper-academic-writing` |
| DeepSeek-tui（Codewhale） | `.codewhale/skills/aiwritepaper-academic-writing` | `~/.codewhale/skills/aiwritepaper-academic-writing` |
| 通用Agent | `.agents/skills/aiwritepaper-academic-writing` | `~/.agents/skills/aiwritepaper-academic-writing` |

## 使用示例

### 完整论文

```text
使用 $aiwritepaper-academic-writing 完成论文生产。

题目：基于SpringBoot的助农服务平台系统设计与实现
运行模式：FULL_BUILD
最低文献：30
目标图片：10-14
目标表格：8-12

未指定字数，使用默认25,000字。不要停留在计划阶段，持续执行到DOCX、PDF和最终QA。
```

### 单独优化图片

```text
使用 $aiwritepaper-academic-writing，运行FIGURES_ONLY。

读取当前论文和figures目录。有图片工具时逐张调用；统计图使用真实数据和代码。
更新figure-manifest.json、figure-manifest.md和final_embed_file，不改写正文主张。
```

## 项目结构

```text
aiwritepaper-academic-writing/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── compose_prompt.py   # 运行时只做确定性文件拼接
│   ├── build_compiled.py   # 维护时重建19份完整提示词
│   ├── verify_compiled.py  # 只读校验源文件、路由和版本同步
│   ├── verify_figure_package.py # 机械校验图表包、哈希与嵌图路由
│   ├── verify_formula_rendering.py   # 校验公式源稿、Word OMML与PDF可见残留
│   ├── verify_manuscript_delivery.py # 统一校验字数、证据矩阵和DOCX/PDF交付
│   └── render_svg_layout.mjs # 无依赖的确定性SVG布局编译器
├── tests/
│   ├── test_verify_figure_package.py
│   ├── test_verify_formula_rendering.py
│   ├── test_verify_manuscript_delivery.py
│   └── test_render_svg_layout.mjs
├── references/
│   ├── compiled-prompts/    # 运行时只读取其中一个完整提示词
│   ├── directions/          # 19个方向增量源
│   ├── common/              # 通用规则源，含正文质量、统计图与Figure Trace
│   ├── schemas/             # Figure Manifest与SVG Layout Spec
│   ├── integrations/        # 各Agent短小能力适配文件
│   ├── routing.md            # 唯一方向路由真源
│   ├── topic-selection.md    # 无题目时按需读取
│   └── deliverables/         # 开题与答辩按需附加
├── install.sh
└── install.ps1
```

## 真实性边界

- 不编造文献、DOI、数据、实验、问卷、访谈、病例、代码运行和性能结果；
- 缺少真实材料时降级为设计方案、验证协议、公开数据研究或综述；
- 图片生成内容不得冒充显微图、医学影像、实验照片和统计结果；
- 不以规避AIGC检测或重复率检测为目标；
- 用户提供学校模板时，模板优先于默认格式。

## 维护与版本

- 当前版本：`1.3.1`
- 更新记录：[CHANGELOG.md](CHANGELOG.md)
- Skill入口：[SKILL.md](SKILL.md)
- 历史复杂流水线版可通过Git标签`v0.3.1-runtime-gates`恢复

## License

[MIT License](LICENSE)
