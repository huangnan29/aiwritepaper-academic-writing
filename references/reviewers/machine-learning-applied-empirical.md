# 方向专业审查：machine-learning-applied-empirical

只在论文写作流程结束后使用。先读取冻结的review-package.json，再按其中SHA-256核对实际稿件、证据矩阵、图表清单、DOCX/PDF与QA。目录名、Skill版本和作者期望分数不得作为评分依据；文件哈希只证明评审对象固定，不证明结论正确。

## 专业关注点
- 数据切分与泄漏防护
- 基线、消融和指标
- 复现、误差和部署边界

## 适用方法检查
只使用当前研究实际采用的方法，不强制添加无关实验。
- 原始数据与许可真实存在
- 监督学习中的预处理和模型选择仅在训练折内完成，其他任务使用对应的无泄漏设计
- 按任务报告独立或嵌套评价及误差；概率预测需要校准检查，有适用子群时检查差异，不强行套给所有任务

材料不足时：随机或演示数据只能用于教程；无真实运行日志时降为建模协议，不报告AUC、准确率和部署价值。

## 不能忽略的专业错误
- 虚构数据/性能
- 训练测试泄漏

## 审查输出
在独立评测目录写review-result.json，不修改论文目录和14-adjudicated-status.json。结果包含review_id、reviewer_identity、reviewed_package_sha256、六维分数、total、逐项issues、Critical/Important数量和证据定位。权重为证据25、内容20、结构15、配图15、文档15、学术诚信10。

每个问题写severity、location、evidence、why_it_matters与recommended_fix。分别核对题目支持、研究问题回答、方法结果、摘要结论和图文语义。无法实际查看图片或文档页面时，对应维度写NOT_REVIEWED并说明能力缺口，不能猜分。先列问题再评分；终稿变化后旧结果自动失效。
