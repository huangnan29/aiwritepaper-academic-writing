# 方向专业审查：general-journal-imrad

只在论文写作流程结束后使用。先读取冻结的review-package.json，再按其中SHA-256核对实际稿件、证据矩阵、图表清单、DOCX/PDF与QA。目录名、Skill版本和作者期望分数不得作为评分依据；文件哈希只证明评审对象固定，不证明结论正确。

## 专业关注点
- 研究问题与方法匹配
- 结果证据和不确定性
- 讨论与既有研究对话

## 适用方法检查
只使用当前研究实际采用的方法，不强制添加无关实验。
- 研究问题、方法、结果和讨论逐项同构
- 每个结果均有原始数据或全文证据
- 不确定性和失败结果进入讨论

材料不足时：核心结果未取得时收窄题目或改为协议/综述，不用局限段掩盖研究问题未完成。

## 不能忽略的专业错误
- 虚构样本或结果
- 方法结果不一致

## 审查输出
在独立评测目录写review-result.json，不修改论文目录和14-adjudicated-status.json。结果包含review_id、reviewer_identity、reviewed_package_sha256、六维分数、total、逐项issues、Critical/Important数量和证据定位。权重为证据25、内容20、结构15、配图15、文档15、学术诚信10。

每个问题写severity、location、evidence、why_it_matters与recommended_fix。分别核对题目支持、研究问题回答、方法结果、摘要结论和图文语义。无法实际查看图片或文档页面时，对应维度写NOT_REVIEWED并说明能力缺口，不能猜分。先列问题再评分；终稿变化后旧结果自动失效。
