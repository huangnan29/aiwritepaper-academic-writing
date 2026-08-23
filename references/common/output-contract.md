# 公共规则四：生产流程与文件契约

按“研究契约 → 检索 → 证据矩阵 → 大纲 → 论证地图 → 分章写作 → 图表 → 全文整合 → 引用审计 → 同行评审 → 修订 → DOCX/PDF → 最终验收”执行。

运行开始时保留 `run-params.md`，并通过文件级确定性拼接生成 `final-execution-prompt.md`；不得由模型重新生成完整方向提示词。

`FULL_BUILD` 输出：`run-params.md`、`final-execution-prompt.md`、`00-capability-report.md`、`01-research-contract.md`、`02-search-log.md`、`03-evidence-matrix.csv`、`04-reference-audit.md`、`references.bib`、`05-outline.md`、`06-argument-map.md`、`chapters/`、`figures/figure-manifest.json`、`figures/figure-manifest.md`、`tables/table-data-and-sources.md`、`07-paper-full.md`、`08-claim-citation-audit.md`、`09-peer-review.md`、`10-revision-log.md`、`final-paper.docx`、可选 `final-paper.tex`、`final-paper.pdf`、`11-format-validation.md`、`12-final-qa-report.md` 和 `run-manifest.json`。没有真实生成的文件不得列入完成清单。

`PROPOSAL_ONLY` 输出 `run-params.md`、`final-execution-prompt.md`、研究契约、检索与文献核验文件、`proposal-report.md` 及可用工具允许的DOCX/PDF。`DEFENSE_ONLY` 输出 `run-params.md`、`final-execution-prompt.md`、答辩大纲、逐页内容及可用工具允许的PPTX/PDF。两种模式都不得虚构结果。

大纲必须给每章和主要三级标题分配字数，分配总和落在目标正文长度允许区间内，并按 `statistical-figures-and-trace.md` 建立 `figure_plan[]`。逐章写作，每章读取契约、大纲、论证地图和前章摘要；每章完成后立即核算该章与累计正文长度。章节低于计划的90%时，在进入下一章前扩充已有小节的论证、证据、设计细节、反例、限制或验证方案。不得在结论、附录、致谢或参考文献之后追加“扩展章节”补字数。

每段围绕一个中心命题。摘要、正文、结果和结论必须保持一致，结论不得引入新证据。图表必须服务论证并有来源，表格在Word中保持原生可编辑。

全文整合时只允许一个摘要、一套连续正文、一份参考文献和一份致谢。章节顺序必须与批准的大纲一致，不能因为文件名排序把补写内容放到附录或参考文献之后。章节、图表或引用修改后重新整合并导出。

全文整合时，`07-paper-full.md`中的每个图片链接必须逐项等于权威 `figures/figure-manifest.json` 对应图号的 `final_embed_file`。`figure-manifest.md` 只供人阅读。禁止使用目录通配、同名文件优先级或“优先SVG”逻辑自动选图。图片工具已成功生成位图时，Markdown不得继续引用其旧SVG版本。

提供学校模板时模板优先。没有模板时只能标记为通用草稿格式。DOCX与PDF从同一份定稿生成，图片实际嵌入，标题使用真实样式，目录、页码、题注和交叉引用可更新。根据当前环境自主选择文档工具；只有确实需要时才在本次输出目录创建项目专用脚本。Skill内 `compose_prompt.py` 只允许用于确定性合成最终提示词；`verify_figure_package.py` 只允许验证Manifest、文件、哈希、Markdown和DOCX嵌入一致性；维护脚本与其他Skill脚本不得参与论文内容、证据或最终状态判断。

## 默认学术论文排版

用户或学校没有提供模板时，使用以下通用中文学术论文格式；一旦提供模板，以模板为最高优先级：

- 页面为A4；上、下页边距2.54cm，左3.0cm，右2.5cm；
- 论文主标题居中、黑体或等价中文无衬线字体、22pt、加粗；
- 中文正文使用宋体、SimSun或Songti SC，12pt；英文与数字使用Times New Roman，12pt；两端对齐，首行缩进2字符，1.5倍行距，段前段后0；
- 一级标题使用内置 `Heading 1`，16pt黑体；二级标题使用 `Heading 2`，14pt黑体；三级标题使用 `Heading 3`，12pt黑体；标题与下一段保持同页，不用普通加粗段落冒充标题；
- 图题位于图下方、表题位于表上方，居中、10.5pt；表格使用可编辑原生表格，优先三线表，不使用图片表格；
- 参考文献10.5pt，按引用格式设置悬挂缩进；页码置于页脚居中；目录由真实标题样式生成并设置为可更新字段；
- 避免孤行、标题单独落在页尾、图题与图片分页分离、表格超出页边距和图片拉伸变形。图片与图题应作为连续整体保留在正文版心内，并与页脚页码保持明显距离；剩余空间不足时整体缩放或移到下一页，不能让图题与页码位于同一水平区域或发生视觉粘连。

## Word图题唯一性

图号与图题只有一个可见来源。生成图片画布内部不得再写外部题注形式的“图X-X 标题”；Word中每张图片下方只保留一个题注段落。不得同时保留Markdown图片替代文字形成的可见题注、普通文本题注和Word `Caption`题注，也不得在插图后再次复制相同图号。无论使用自动 `SEQ` 域还是普通文本，每个图号在Word可见段落中必须恰好出现一次。

图片的替代文本用于无障碍说明，不应作为可见图题重复输出。导出后按图表清单逐个检查Word可见段落：相同图号出现0次或超过1次均需修复。表号同样只能保留一个可见题注。

Word插图程序必须逐项读取权威JSON中的 `final_embed_file`，默认嵌入最终PNG，不得通过查找同名 `.svg`、读取Markdown摘要、沿用旧链接或按扩展名排序选择图片。导出后解包DOCX检查 `word/media/`，确认每个图号实际嵌入的是对应最终位图；必要时比较文件摘要、像素尺寸或可识别视觉内容。PDF中再抽查同一页，确保显示内容与 `final_embed_file` 一致。

## Word左侧导航目录

Word左侧导航窗格依赖真实标题样式，不等同于正文中的手工目录。论文标题可使用 `Title`，章标题必须使用内置 `Heading 1`，二级标题使用 `Heading 2`，三级标题使用 `Heading 3`；样式ID应保持 `Heading1`、`Heading2`、`Heading3`，并分别具有0、1、2级大纲级别。可以修改这些内置样式的字体和段落格式，但不能把标题转换成普通段落或只设置字号、加粗。

从Markdown转换时，必须显式映射章节层级到上述Word样式。自动目录与导航窗格使用同一组标题；导出后检查DOCX中存在分层标题样式，章、节、小节均能出现在Word导航窗格中。`11-format-validation.md`记录Heading 1/2/3数量、目录字段状态、可更新性以及图题/表题重复检查结果。

用户额外要求开题报告时，依据同一研究契约、大纲和证据边界输出 `proposal-report.md`；用户要求答辩材料时，依据最终论文输出答辩大纲、逐页内容和可用工具允许的PPTX/PDF。附加交付不能反向改变论文证据或把计划写成已完成结果。
