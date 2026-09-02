# 方向专业审查：legal-normative-analysis

只在论文写作流程结束后使用。先读取冻结的review-package.json，再按其中SHA-256核对实际稿件、证据矩阵、图表清单、DOCX/PDF与QA。目录名、Skill版本和作者期望分数不得作为评分依据；文件哈希只证明评审对象固定，不证明结论正确。

## 专业关注点
- 法源版本与效力层级
- 构成要件/请求权/案例
- 解释路径与比较法边界

## 适用方法检查
只使用当前研究实际采用的方法，不强制添加无关实验。
- 法源版本、效力层级和生效状态可核
- 案例主张定位到裁判文书具体理由
- 比较法只作说理来源

材料不足时：无法取得裁判或法条原文时降低为学说综述，不把新闻转述写成裁判规则。

## 不能忽略的专业错误
- 失效或虚构法条案例
- 规范层级混乱

## 审查输出
在独立评测目录写review-result.json，不修改论文目录和14-adjudicated-status.json。结果包含review_id、reviewer_identity、reviewed_package_sha256、六维分数、total、逐项issues、Critical/Important数量和证据定位。权重为证据25、内容20、结构15、配图15、文档15、学术诚信10。

每个问题写severity、location、evidence、why_it_matters与recommended_fix。分别核对题目支持、研究问题回答、方法结果、摘要结论和图文语义。无法实际查看图片或文档页面时，对应维度写NOT_REVIEWED并说明能力缺口，不能猜分。先列问题再评分；终稿变化后旧结果自动失效。
