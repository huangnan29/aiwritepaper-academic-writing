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
