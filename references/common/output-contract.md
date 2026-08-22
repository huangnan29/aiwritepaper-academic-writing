# 公共规则四：生产流程与文件契约

按“研究契约 → 检索 → 证据矩阵 → 大纲 → 论证地图 → 分章写作 → 图表 → 全文整合 → 引用审计 → 同行评审 → 修订 → DOCX/PDF → 最终验收”执行。

建议输出：`00-capability-report.md`、`01-research-contract.md`、`02-search-log.md`、`03-evidence-matrix.csv`、`04-reference-audit.md`、`references.bib`、`05-outline.md`、`06-argument-map.md`、`chapters/`、`figures/figure-manifest.json`、`tables/table-data-and-sources.md`、`07-paper-full.md`、`08-claim-citation-audit.md`、`09-peer-review.md`、`10-revision-log.md`、`final-paper.docx`、`final-paper.tex`、`final-paper.pdf`、`11-format-validation.md`、`12-final-qa-report.md` 和 `run-manifest.json`。

逐章写作，每章读取契约、大纲、论证地图和前章摘要。每段围绕一个中心命题。摘要、结果和结论保持一致；结论不得引入新证据。

图表必须服务论证并有来源。概念图用自包含 HTML/CSS/SVG、Mermaid 或 Graphviz；真实数据图从明确数据文件生成。没有数据不得绘制虚构数值图。表格在 Word 中保持原生可编辑，图片同时保留 SVG 与至少 300 DPI PNG。

提供学校模板时模板优先。没有模板时只能标记为通用草稿格式。DOCX 与 PDF 必须来自同一份定稿，图片嵌入文件，标题使用真实样式，目录、页码、题注和交叉引用可更新。
