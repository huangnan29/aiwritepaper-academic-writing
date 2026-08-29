# 公共规则十一：90分质量上限与方向审稿

当前方向的90分标准来自 `references/quality/direction-rubrics.json`。评分维度固定为证据25、内容20、结构15、配图15、文档15、自审10。高分不要求研究状态为PASS；设计稿、方案或综述可在诚实PARTIAL状态下获得高交付质量分。

正文完成后建立 `claim-evidence-map.json`：列出重要主张、章节定位、主张状态、证据source_id、页码/章节、反例/限制和是否进入结论。重要主张没有证据或限制时必须修改，不能用多篇段尾引文掩盖。

依据当前方向评分卡进行独立同行评审。初稿审稿可以写入 `09-peer-review.md`，但不能直接作为最终评分。全部图片、DOCX、PDF和视觉审计完成后必须重新隔离审稿，写入 `09-final-peer-review.json`，绑定最终正文、Figure Manifest、视觉审计、DOCX和PDF的SHA-256；审稿输入不包含作者自评分。最终 `15-quality-scorecard.json` 的分项与总分必须与该审稿报告一致，并记录审稿报告路径和SHA-256。不得先给高分再补理由，也不得在旧审稿后由作者自行抬分。

任何Critical未清零、Important仍为OPEN/ACCEPTED/NOTED、任一维度低于该维度80%、总分低于90时不能标记“90+质量目标达成”。已修复Important可以保留审计记录，但状态必须是 `RESOLVED`、`FIXED`、`CLOSED` 或 `ADDRESSED`。

配图另建 `figures/figure-semantic-audit.json`：每张图记录图题主张、遮住图题后的盲读摘要、正文定位、节点/箭头/数据来源一致性和PASS/PARTIAL/FAIL。可换标题复用的模板图、与正文无关曲线、错误箭头或ImageGen虚构关系不得PASS。

文档另建 `16-document-visual-audit.json`，抽查封面、中文摘要、英文摘要、目录、复杂表格、复杂公式、代表性配图、参考文献及末页；每个检查点绑定实际页码、由最终PDF渲染的PNG/JPEG/WebP页面图、页面图SHA-256、视觉回执、问题、修复和状态。整份PDF不能冒充某一页的视觉检查文件；页码不能写“约12页”一类字符串。只解析文件不等于视觉通过。

正文质量审查关注重复句式、列表占比、无证据强化词、摘要—结论机械复述和边界声明密度。只报告位置和修订建议，不输出AI率，不自动重写正文。
