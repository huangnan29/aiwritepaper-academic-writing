# 公共规则四：生产流程与文件契约

按“研究契约 → 检索 → 证据矩阵 → 大纲 → 论证地图 → 分章写作 → 图表 → 全文整合 → 引用审计 → 同行评审 → 修订 → DOCX/PDF → 最终验收”执行。

`FULL_BUILD` 输出：`final-execution-prompt.md`、`00-capability-report.md`、`01-research-contract.md`、`02-search-log.md`、`03-evidence-matrix.csv`、`04-reference-audit.md`、`references.bib`、`05-outline.md`、`06-argument-map.md`、`chapters/`、`figures/figure-manifest.md`、`tables/table-data-and-sources.md`、`07-paper-full.md`、`08-claim-citation-audit.md`、`09-peer-review.md`、`10-revision-log.md`、`final-paper.docx`、可选 `final-paper.tex`、`final-paper.pdf`、`11-format-validation.md`、`12-final-qa-report.md` 和 `run-manifest.json`。没有真实生成的文件不得列入完成清单。

大纲必须给每章和主要三级标题分配字数，分配总和落在目标正文长度允许区间内。逐章写作，每章读取契约、大纲、论证地图和前章摘要；每章完成后立即核算该章与累计正文长度。章节低于计划的90%时，在进入下一章前扩充已有小节的论证、证据、设计细节、反例、限制或验证方案。不得在结论、附录、致谢或参考文献之后追加“扩展章节”补字数。

每段围绕一个中心命题。摘要、正文、结果和结论必须保持一致，结论不得引入新证据。图表必须服务论证并有来源，表格在Word中保持原生可编辑。

全文整合时只允许一个摘要、一套连续正文、一份参考文献和一份致谢。章节顺序必须与批准的大纲一致，不能因为文件名排序把补写内容放到附录或参考文献之后。章节、图表或引用修改后重新整合并导出。

提供学校模板时模板优先。没有模板时只能标记为通用草稿格式。DOCX与PDF从同一份定稿生成，图片实际嵌入，标题使用真实样式，目录、页码、题注和交叉引用可更新。根据当前环境自主选择文档工具；只有确实需要时才在本次输出目录创建项目专用脚本，不调用Skill内预置Python流水线。

用户额外要求开题报告时，依据同一研究契约、大纲和证据边界输出 `proposal-report.md`；用户要求答辩材料时，依据最终论文输出答辩大纲、逐页内容和可用工具允许的PPTX/PDF。附加交付不能反向改变论文证据或把计划写成已完成结果。
