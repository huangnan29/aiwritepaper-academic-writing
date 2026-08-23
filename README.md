<div align="center">

# AIWritePaper Agentic Skill

**从论文题目到一份完整执行提示词，再持续交付正文、配图、DOCX 与 PDF。**

![Version](https://img.shields.io/badge/version-0.6.0-2563EB?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-16A34A?style=flat-square)
![Architecture](https://img.shields.io/badge/architecture-MD--first-7C3AED?style=flat-square)
![Directions](https://img.shields.io/badge/paper%20directions-19-EA580C?style=flat-square)

[快速开始](#快速开始) · [工作方式](#工作方式) · [配图策略](#配图策略) · [Word交付](#word交付) · [安装路径](#安装路径)

</div>

> [!NOTE]
> 当前版本采用 **MD-first 单提示词执行**。Skill先判断论文方向，模型只写本次参数头，再通过确定性文件拼接生成 `final-execution-prompt.md`。正式执行阶段不再跳转多层规则，脚本也不控制论文内容、证据或最终状态。

## 你会得到什么

| 能力 | 默认行为 |
|---|---|
| 自动选方向 | 根据题目、研究对象、方法和证据，从19个方向中选择一个 |
| 稳定字数 | 直接给题目且未指定字数时，默认正文25,000字，允许±10% |
| 文献与证据 | 先检索、核验并建立证据矩阵，不编造文献、数据或实验 |
| 方向级信源 | 每个方向内置首选库、开放路线和不宜引用清单；无订阅时走开放路线 |
| 论文生产 | 大纲、分章、累计字数检查、全文整合、同行评审与修订 |
| 学术配图 | 有图片工具时逐张生图；统计图由真实数据和代码生成 |
| 文档交付 | 生成并检查DOCX、PDF、目录、标题层级、题注和页码 |
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
检索 → 大纲 → 分章 → 配图 → 整合 → DOCX/PDF → QA
```

每个 `references/compiled-prompts/*-full.md` 都是完整、自包含的论文生产提示词。模型选中一个方向后，不再复述这份长文本；`scripts/compose_prompt.py` 只做确定性文件拼接，并输出字节数和SHA-256。模型随后从头到尾读取一次最终MD，后续只执行这一份文件。

### 为什么改为文件级拼接

- 避免弱模型复制长提示词时截断、意译或漏段；
- compiled prompt原文字节不经过模型生成；
- 参数、完整规则和开题/答辩附加规则仍合成一份最终MD；
- 维护脚本只负责拼接与同步校验，不参与论文决策。

## 默认规则

### 直接题目自动完成

用户直接给出完整题目并触发 `FULL_BUILD` 时：

- 不重复询问题目；
- 不停在大纲确认阶段；
- 未给字数时使用 `TARGET_LENGTH: 25000`；
- 可接受正文区间为22,500—27,500；
- 低于22,500不得标记 `PASS`；
- 用户明确给出的字数、文献、图片和表格目标始终优先。

正文统计范围为第一章至结论的主体论述，不含摘要、目录、参考文献、致谢、附录、代码和图表题注。

### 弱模型持续完成

- 大纲先分配章节字数，合计必须落入目标区间；
- 每章完成后检查计划字数、实际字数和累计字数；
- 章节不足时先补足原小节，再进入下一章；
- 禁止在附录、致谢或参考文献后增加“扩展章节”补字数；
- 文献、图片和表格未达标时，不提前进入排版；
- 文件存在或PDF可打开，不等于论文已经完成。

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

### 精确流程图

生图Prompt必须明确：

- 画布比例与阅读方向；
- 节点总数、逐字标签和节点形状；
- 分组、层级和主次路径；
- 每条箭头的起点、终点和分支条件；
- 禁止新增、遗漏、合并或改写的内容；
- 输出后的逐项验收清单。

### 最终插图优先级

每张图只有一个最终入口：`final_embed_file`。

- Imagine、`imagegen`、`image_gen`或Nano Banana成功生成后，最终Markdown、DOCX和PDF必须使用该位图；
- 如果增加文字或箭头覆盖层，先合成为最终PNG，再设置为 `final_embed_file`；
- 同名SVG只能保留为`source_file`、`fallback_file`或`overlay_source`；
- 整合和导出阶段不得扫描同名文件并重新选择SVG；
- DOCX导出后检查`word/media/`，PDF再做视觉核对。

### SVG降级质量

- 中文使用明确的跨平台字体栈；
- 连接线尽量不交叉、不重叠、不穿越节点或文字；
- 转折位置整齐，连接点位于合理的节点边界；
- 箭头准确落在目标边界，不悬空、不伸入文字；
- 无法避免交叉时优先绕行、拆图或使用跨线桥；
- 在论文实际显示尺寸检查PNG、DOCX与PDF。

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
├── 01-research-contract.md
├── 02-search-log.md
├── 03-evidence-matrix.csv
├── 04-reference-audit.md
├── references.bib
├── 05-outline.md
├── 06-argument-map.md
├── chapters/
├── figures/
│   └── figure-manifest.md
├── tables/
├── 07-paper-full.md
├── 08-claim-citation-audit.md
├── 09-peer-review.md
├── 10-revision-log.md
├── final-paper.docx
├── final-paper.pdf
├── 11-format-validation.md
├── 12-final-qa-report.md
└── run-manifest.json
```

## 快速开始

### 通用安装

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill
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
```

更新已有安装时追加`--force`。

### Windows PowerShell

```powershell
.\install.ps1 -Agent codex -Scope user
.\install.ps1 -Agent claude -Scope user
.\install.ps1 -Agent cursor -Scope user
.\install.ps1 -Agent kimi -Scope user
.\install.ps1 -Agent grok -Scope user
.\install.ps1 -Agent workbuddy -Scope user
.\install.ps1 -Agent antigravity -Scope user
```

更新已有安装时追加`-Force`。

## 安装路径

| Agent | 项目级 | 用户级 |
|---|---|---|
| Claude | `.claude/skills/aiwritepaper-agentic-skill` | `~/.claude/skills/aiwritepaper-agentic-skill` |
| Codex | `.codex/skills/aiwritepaper-agentic-skill` | `~/.codex/skills/aiwritepaper-agentic-skill` |
| Cursor | `.cursor/skills/aiwritepaper-agentic-skill` | `~/.cursor/skills/aiwritepaper-agentic-skill` |
| Kimi Code | `.kimi-code/skills/aiwritepaper-agentic-skill` | `$KIMI_CODE_HOME/skills/aiwritepaper-agentic-skill`（默认`~/.kimi-code/skills`） |
| Gemini CLI | `.gemini/skills/aiwritepaper-agentic-skill` | `~/.gemini/skills/aiwritepaper-agentic-skill` |
| Antigravity | `.agents/skills/aiwritepaper-agentic-skill` | `~/.gemini/config/skills/aiwritepaper-agentic-skill` |
| Grok Build | `.grok/skills/aiwritepaper-agentic-skill` | `~/.grok/skills/aiwritepaper-agentic-skill` |
| GitHub Copilot | `.github/skills/aiwritepaper-agentic-skill` | `~/.copilot/skills/aiwritepaper-agentic-skill` |
| OpenCode | `.opencode/skills/aiwritepaper-agentic-skill` | `~/.config/opencode/skills/aiwritepaper-agentic-skill` |
| WorkBuddy | `.workbuddy/skills/aiwritepaper-agentic-skill` | `~/.workbuddy/skills/aiwritepaper-agentic-skill` |
| 通用Agent | `.agents/skills/aiwritepaper-agentic-skill` | `~/.agents/skills/aiwritepaper-agentic-skill` |

## 使用示例

### 完整论文

```text
使用 $aiwritepaper-agentic-skill 完成论文生产。

题目：基于SpringBoot的助农服务平台系统设计与实现
运行模式：FULL_BUILD
最低文献：30
目标图片：10-14
目标表格：8-12

未指定字数，使用默认25,000字。不要停留在计划阶段，持续执行到DOCX、PDF和最终QA。
```

### 单独优化图片

```text
使用 $aiwritepaper-agentic-skill，运行FIGURES_ONLY。

读取当前论文和figures目录。有图片工具时逐张调用；统计图使用真实数据和代码。
更新figure-manifest.md和final_embed_file，不改写正文主张。
```

## 项目结构

```text
aiwritepaper-agentic-skill/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
│   ├── compose_prompt.py   # 运行时只做确定性文件拼接
│   ├── build_compiled.py   # 维护时重建19份完整提示词
│   └── verify_compiled.py  # 只读校验源文件、路由和版本同步
├── references/
│   ├── compiled-prompts/    # 运行时只读取其中一个完整提示词
│   ├── directions/          # 19个方向增量源
│   ├── common/              # 通用规则源
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

- 当前版本：`0.6.0`
- 更新记录：[CHANGELOG.md](CHANGELOG.md)
- Skill入口：[SKILL.md](SKILL.md)
- 历史复杂流水线版可通过Git标签`v0.3.1-runtime-gates`恢复

## License

[MIT License](LICENSE)
