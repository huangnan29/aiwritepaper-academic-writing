# 公共规则四：生产流程与文件契约

按“研究契约 → 检索 → 证据矩阵 → 大纲 → 论证地图 → 分章写作 → 图表 → 全文整合 → 引用审计 → 同行评审 → 修订 → DOCX/PDF → 最终验收”执行。

`FULL_BUILD` 建议输出：`00-capability-report.md`、能力探测 JSON、`01-research-contract.md`、`02-search-log.md`、`03-evidence-matrix.csv`、`evidence-manifest.json`、`04-reference-audit.md`、`references.bib`、`05-outline.md`、`06-argument-map.md`、`chapters/`、`figures/figure-manifest.json`、`tables/table-data-and-sources.md`、`07-paper-full.md`、`08-claim-citation-audit.md`、`09-peer-review.md`、`10-revision-log.md`、`final-paper.docx`、`final-paper.tex`、`final-paper.pdf`、`11-format-validation.md`、`delivery-validation.json`、`12-final-qa-report.md` 和 `run-manifest.json`。

逐章写作，每章读取契约、大纲、论证地图和前章摘要。每段围绕一个中心命题。摘要、结果和结论保持一致；结论不得引入新证据。

图表必须服务论证并有来源。先按 `references/common/academic-figures.md` 判断图类和证据属性。当前客户端具备图片生成能力时，流程、架构、框架、组织、ER/UML、机制、装置和场景类配图全部从上下文建立详细结构契约与生图 Prompt，并逐张真实调用图片工具；纯 SVG 不能作为这些图的主交付。数据统计图从明确数据文件和可复现的 Python、R 或等价代码生成，没有数据不得绘制虚构数值图。原始科研影像与领域符号图保持证据或专业工具路径。表格在 Word 中保持原生可编辑；生成式位图保留最终提示词、模型或工具、图号到产物的一一映射和人工核对记录；确定性修正层保留可编辑源。

提供学校模板时模板优先。没有模板时只能标记为通用草稿格式。DOCX 与 PDF 必须由确定性导出步骤从同一份定稿生成，图片嵌入文件，标题使用真实样式，目录、页码、题注和交叉引用可更新。章节、图表或引用修改后必须重新整合和导出。
