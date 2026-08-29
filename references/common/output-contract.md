# 公共规则四：生产流程与文件契约

按“研究契约 → 检索 → 证据矩阵 → 大纲 → 论证地图 → 分章写作 → 图表 → 全文整合 → 引用审计 → 同行评审 → 修订 → DOCX/PDF → 最终验收”执行。

运行开始时保留 `run-params.md`，并通过文件级确定性拼接生成 `final-execution-prompt.md`；不得由模型重新生成完整方向提示词。

`FULL_BUILD` 输出：`run-params.md`、`final-execution-prompt.md`、`00-prompt-composition.json`、`00-capability-report.md`、`00-capability-report.json`、`00-profile-selection.json`、GUIDED/WEAK模型使用的 `00-execution-checkpoints.json`、`01-research-contract.md`、`02-search-log.md`、`03-evidence-matrix.csv`、`04-reference-audit.md`、`04-evidence-verification.json`、`references.bib`、`data/data-provenance.json`、`05-outline.md`、`06-argument-map.md`、`chapters/`、`figures/figure-plan.json`、`figures/figure-manifest.json`、`figures/figure-manifest.md`、`figures/figure-verification.json`、`tables/table-data-and-sources.md`、`equations/formula-audit.md`、`equations/formula-verification.json`、`07-paper-full.md`、`08-claim-citation-audit.md`、`09-peer-review.md`、`10-revision-log.md`、按下述规则命名的DOCX与PDF、可选同名TEX、`11-format-validation.md`、`12-final-qa-report.md`、`13-delivery-verification.json`、`14-adjudicated-status.json` 和 `run-manifest.json`。FULL_AUTONOMY不强制创建阶段任务卡；没有真实生成的文件不得列入完成清单。

`RESUME` 额外输出 `00-resume-plan.json`，不覆盖原提示词和冻结产物。`REVISE_ONLY` 输出 `revision-request.md`、`revision-impact.json`、`revision-execution-prompt.md`、`revision-prompt-composition.json`、`revision-log.md` 以及新时间戳DOCX/PDF，并保留修改前摘要。

`run-manifest.json` 必须记录真实 `run_mode`、`model_label`、`skill_version`、`execution_profile`、`profile_selection_report`、GUIDED/WEAK使用的 `execution_checkpoints`、`paper_level`、`manuscript_language`、`abstract_contract`、`citation_mode`、`research_claim_level`、`document_profile`（`THESIS`、`JOURNAL`、`REPORT` 或 `CUSTOM`）、目标长度和容差、模型声明的三层状态、五份报告路径以及正式文档路径与摘要。Profile必须与选择报告一致；检查器运行/跳过必须符合模式矩阵。模型声明只供冲突审计，最终状态以 `14-adjudicated-status.json` 为唯一真源。

## 最终文档文件名

开始最终导出时冻结一次本地生成时间 `GENERATED_AT_LOCAL`，格式为 `YYYYMMDD-HHMMSS`。把论文题目转换为安全文件名：保留中文、字母、数字、空格、短横线和下划线；将 `/\\:*?"<>|`、控制字符和连续空白替换或折叠为单个下划线；去除首尾空格、点与下划线；题目过长时在不破坏字符的前提下截断，使文件名主体不超过120个字符。最终文件名固定为：

```text
<安全论文题目>_<GENERATED_AT_LOCAL>.docx
<安全论文题目>_<GENERATED_AT_LOCAL>.pdf
```

DOCX与PDF必须使用同一文件名主体和同一时间戳。`final-paper.docx`、`final-paper.pdf`只能作为本次运行内部临时文件名，不能进入最终完成清单、最终回复或 `run-manifest.json`；成功导出后将本次创建的临时文件原子重命名为正式文件。不得覆盖同名既有文件，发生冲突时重新冻结更晚的时间戳。`run-manifest.json`必须记录ISO 8601本地时间、时区、正式DOCX/PDF相对路径与SHA-256。任何打包、上传或展示层都不得再次重命名正式文件；打包完成后重新验证Manifest路径和摘要。

`PROPOSAL_ONLY` 输出 `run-params.md`、`final-execution-prompt.md`、研究契约、检索与文献核验文件、`proposal-report.md` 及可用工具允许的DOCX/PDF。`DEFENSE_ONLY` 输出 `run-params.md`、`final-execution-prompt.md`、答辩大纲、逐页内容及可用工具允许的PPTX/PDF。两种模式都不得虚构结果。

大纲必须给每章和主要三级标题分配字数，分配总和落在目标正文长度允许区间内，并按 `statistical-figures-and-trace.md` 建立 `figure_plan[]`。逐章写作，每章读取契约、大纲、论证地图和前章摘要；每章完成后立即核算该章与累计正文长度。章节低于计划的90%时，在进入下一章前扩充已有小节的论证、证据、设计细节、反例、限制或验证方案。不得在结论、附录、致谢或参考文献之后追加“扩展章节”补字数。

每段围绕一个中心命题。摘要、正文、结果和结论必须保持一致，结论不得引入新证据。图表必须服务论证并有来源，表格在Word中保持原生可编辑。

全文整合时只允许一个摘要、一套连续正文、一份参考文献和一份致谢。章节顺序必须与批准的大纲一致，不能因为文件名排序把补写内容放到附录或参考文献之后。章节、图表或引用修改后重新整合并导出。

全文整合时，`07-paper-full.md`中的每个图片链接必须逐项等于权威 `figures/figure-manifest.json` 对应图号的 `final_embed_file`。`figure-manifest.md` 只供人阅读。禁止使用目录通配、同名文件优先级或“优先SVG”逻辑自动选图。图片工具已成功生成位图时，Markdown不得继续引用其旧SVG版本。

提供学校模板时模板优先。没有模板时只能标记为通用草稿格式。DOCX与PDF必须来自同一份 `07-paper-full.md` 和同一结构映射；优先先生成并验证DOCX，再由该定稿转换PDF。图片实际嵌入，公式转换为可编辑OMML对象，标题使用真实样式，目录、页码、题注和交叉引用可更新。不得分别从互不一致的Markdown和HTML版本生成Word与PDF。自定义Word排版程序不得以读取整段纯文本再重建段落的方式破坏既有公式对象。根据当前环境自主选择文档工具；只有确实需要时才在本次输出目录创建项目专用脚本。Skill内 `compose_prompt.py` 只允许用于确定性合成最终提示词；四个底层检查器和状态裁决器只做核验与状态计算；维护脚本与其他Skill脚本不得参与论文内容和证据决策。

## 默认学术论文排版

用户或学校没有提供模板时，使用以下通用中文学术论文格式；一旦提供模板，以模板为最高优先级：

- 中文THESIS默认包含中文摘要、中文关键词、英文 `Abstract` 与英文 `Keywords`；两种摘要的研究对象、方法、结果性质与限制必须一致。中文JOURNAL无模板时同样使用双语摘要；REPORT、PROPOSAL和DEFENSE默认按主语言单语，学校或期刊模板优先；

- 页面为A4；上、下页边距2.54cm，左3.0cm，右2.5cm；
- 论文主标题居中、黑体或等价中文无衬线字体、22pt、加粗；
- 中文正文使用宋体、SimSun或Songti SC，12pt；英文与数字使用Times New Roman，12pt；两端对齐，首行缩进2字符，1.5倍行距，段前段后0；该首行缩进只适用于表格外的普通正文段落，不能继承到表格单元格、题注、目录或公式段落；
- 一级标题使用内置 `Heading 1`，16pt黑体；二级标题使用 `Heading 2`，14pt黑体；三级标题使用 `Heading 3`，12pt黑体；标题与下一段保持同页，不用普通加粗段落冒充标题；
- 图题位于图下方、表题位于表上方，居中、10.5pt；表格使用可编辑原生表格，优先三线表，不使用图片表格；
- 独立公式居中，公式编号右对齐并按章节连续；Word中使用可编辑公式对象，不显示 `$`、`\[` 或 TeX 命令；
- 参考文献10.5pt，按引用格式设置悬挂缩进；页码置于页脚居中；目录由真实标题样式生成并设置为可更新字段；
- 避免孤行、标题单独落在页尾、图题与图片分页分离、表格超出页边距和图片拉伸变形。图片与图题应作为连续整体保留在正文版心内，并与页脚页码保持明显距离；剩余空间不足时整体缩放或移到下一页，不能让图题与页码位于同一水平区域或发生视觉粘连。

### Word表格单元格缩进

表格单元格内的段落不得继承正文首行缩进。表头通常水平居中，文字型表体按内容左对齐，短代码、数值、状态和等级可居中；无论采用何种对齐方式，普通单元格段落的首行缩进与悬挂缩进均为0。只有单元格确实表达分层清单时才允许语义明确的左缩进，不能用正文的两字符首行缩进制造层级。

使用Pandoc参考DOCX时，必须单独检查 `Compact`、`Table`、`Table Text` 或实际承载表格文字的段落样式。若该样式基于带首行缩进的 `Normal`/正文样式，应在表格样式中显式覆盖首行与悬挂缩进为0；若文档引用了不存在的 `Compact` 等样式ID，Word会回退到默认段落样式，也必须按默认样式计算有效缩进。不能只在屏幕上看第一行是否“似乎居中”。使用 `python-docx`、docx-js或自定义OOXML导出时，对每个表格单元格段落显式清除 `firstLine`、`firstLineChars`、`hanging` 与 `hangingChars`，同时避免额外段前段后距。导出后按“单元格直接格式 → 当前样式 → basedOn父样式 → 不存在样式时的默认段落样式”的顺序计算有效缩进；任一非空单元格仍有首行或悬挂缩进都必须返回排版阶段修复。

## Word图题唯一性

图号与图题只有一个可见来源。每张图在Manifest中显式记录 `display_number`，例如 `2-1`；导出程序只读取该字段生成“图2-1”，不得从 `figure_id`、文件名或章节顺序猜测。生成图片画布内部不得再写外部题注形式的“图X-X 标题”；Word中每张图片下方只保留一个题注段落。不得同时保留Markdown图片替代文字形成的可见题注、普通文本题注和Word `Caption`题注，也不得在插图后再次复制相同图号。无论使用自动 `SEQ` 域还是普通文本，每个图号在Word可见段落中必须恰好出现一次。

图片的替代文本用于无障碍说明，不应作为可见图题重复输出。导出后按图表清单逐个检查Word可见段落：相同图号出现0次或超过1次均需修复。表号同样只能保留一个可见题注。

Word插图程序必须逐项读取权威JSON中的 `final_embed_file`，默认嵌入最终PNG，不得通过查找同名 `.svg`、读取Markdown摘要、沿用旧链接或按扩展名排序选择图片。导出后解包DOCX检查 `word/media/`，确认每个图号实际嵌入的是对应最终位图；必要时比较文件摘要、像素尺寸或可识别视觉内容。PDF中再抽查同一页，确保显示内容与 `final_embed_file` 一致。

## Word左侧导航目录

Word左侧导航窗格依赖真实标题样式，不等同于正文中的手工目录。论文标题可使用 `Title`，章标题必须使用内置 `Heading 1`，二级标题使用 `Heading 2`，三级标题使用 `Heading 3`；样式ID应保持 `Heading1`、`Heading2`、`Heading3`，并分别具有0、1、2级大纲级别。可以修改这些内置样式的字体和段落格式，但不能把标题转换成普通段落或只设置字号、加粗。

从Markdown转换时，必须显式映射章节层级到上述Word样式。自动目录与导航窗格使用同一组标题；导出后检查DOCX中存在分层标题样式，章、节、小节均能出现在Word导航窗格中。`11-format-validation.md`记录Heading 1/2/3数量、目录字段状态、可更新性以及图题/表题重复检查结果。

用户额外要求开题报告时，依据同一研究契约、大纲和证据边界输出 `proposal-report.md`；用户要求答辩材料时，依据最终论文输出答辩大纲、逐页内容和可用工具允许的PPTX/PDF。附加交付不能反向改变论文证据或把计划写成已完成结果。
