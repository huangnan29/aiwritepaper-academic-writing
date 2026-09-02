# 方向专业审查：education-applied-research

只在论文写作流程结束后使用。先读取冻结的review-package.json，再按其中SHA-256核对实际稿件、证据矩阵、图表清单、DOCX/PDF与QA。目录名、Skill版本和作者期望分数不得作为评分依据；文件哈希只证明评审对象固定，不证明结论正确。

## 专业关注点
- 课标与真实学情材料
- 任务、预期反应和理答
- 量规、实施保真度与边界

## 适用方法检查
只使用当前研究实际采用的方法，不强制添加无关实验。
- 真实课堂数据具有伦理、样本和工具
- 设计任务与预期反应逐项对齐
- 量规和实施保真度能够被观察

材料不足时：无课堂原始材料时保持教学设计，不生成班级成绩、问卷或满意度。

## 不能忽略的专业错误
- 虚构班级成绩/问卷
- 素养只作标签

## 审查输出
在独立评测目录写review-result.json，不修改论文目录和14-adjudicated-status.json。结果包含review_id、reviewer_identity、reviewed_package_sha256、六维分数、total、逐项issues、Critical/Important数量和证据定位。权重为证据25、内容20、结构15、配图15、文档15、学术诚信10。

每个问题写severity、location、evidence、why_it_matters与recommended_fix。分别核对题目支持、研究问题回答、方法结果、摘要结论和图文语义。无法实际查看图片或文档页面时，对应维度写NOT_REVIEWED并说明能力缺口，不能猜分。先列问题再评分；终稿变化后旧结果自动失效。
