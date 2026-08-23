# 更新记录

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
