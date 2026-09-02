# 方向专业审查：software-system-engineering

只在论文写作流程结束后使用。先读取冻结的review-package.json，再按其中SHA-256核对实际稿件、证据矩阵、图表清单、DOCX/PDF与QA。目录名、Skill版本和作者期望分数不得作为评分依据；文件哈希只证明评审对象固定，不证明结论正确。

## 专业关注点
- 需求与角色闭环
- 架构/数据库/API/权限决策
- 测试、部署和限制

## 适用方法检查
只使用当前研究实际采用的方法，不强制添加无关实验。
- 需求角色、权限、数据模型和接口互相追踪
- 实现声明具有源码版本与构建记录
- 性能和测试结论具有环境、用例和日志

材料不足时：无源码、部署和测试日志时保持架构设计与验证方案，不报告已上线、并发性能和用户量。

## 不能忽略的专业错误
- 虚构上线/性能/用户量
- 数据模型或权限闭环缺失

## 审查输出
在独立评测目录写review-result.json，不修改论文目录和14-adjudicated-status.json。结果包含review_id、reviewer_identity、reviewed_package_sha256、六维分数、total、逐项issues、Critical/Important数量和证据定位。权重为证据25、内容20、结构15、配图15、文档15、学术诚信10。

每个问题写severity、location、evidence、why_it_matters与recommended_fix。分别核对题目支持、研究问题回答、方法结果、摘要结论和图文语义。无法实际查看图片或文档页面时，对应维度写NOT_REVIEWED并说明能力缺口，不能猜分。先列问题再评分；终稿变化后旧结果自动失效。
