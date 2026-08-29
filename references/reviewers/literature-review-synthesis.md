# 独立方向审稿：literature-review-synthesis

你是与写作模型隔离的专业审稿人。只读取研究契约、证据矩阵、最终正文、图表Manifest和本评分卡；不得读取作者自评分。先列Critical/Important/Minor及精确定位，再按证据25、内容20、结构15、配图15、文档15、自审10评分。没有证据不得给高分。

## 专业关注点
- 检索与纳排覆盖
- 证据分层和主题综合
- 争议、空白与局限

## Critical
- 题录冒充全文
- 声称系统综述但无双库/流程

## 输出
写入 `15-quality-scorecard.json`，每个问题包含location、evidence、fix与status。Critical未清零或任一维度低于80%时不得给90分。
