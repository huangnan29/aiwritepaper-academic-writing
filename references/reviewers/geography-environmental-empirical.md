# 方向专业审查：geography-environmental-empirical

只在论文写作流程结束后使用。先读取冻结的review-package.json，再按其中SHA-256核对实际稿件、证据矩阵、图表清单、DOCX/PDF与QA。目录名、Skill版本和作者期望分数不得作为评分依据；文件哈希只证明评审对象固定，不证明结论正确。

## 专业关注点
- 空间尺度与数据版本
- 空间方法和不确定性
- 地图、机制与外推边界

## 适用方法检查
只使用当前研究实际采用的方法，不强制添加无关实验。
- 保存原始栅格/矢量、版本、许可和下载回执
- 空间单元、投影、分辨率和面积口径一致
- 地图与统计使用同一处理结果

材料不足时：无法处理原始空间数据时改用明确的已发布统计产品，不手绘面积、坐标和变化率。

## 不能忽略的专业错误
- 虚构坐标/遥感数据
- 空间尺度错配

## 审查输出
在独立评测目录写review-result.json，不修改论文目录和14-adjudicated-status.json。结果包含review_id、reviewer_identity、reviewed_package_sha256、六维分数、total、逐项issues、Critical/Important数量和证据定位。权重为证据25、内容20、结构15、配图15、文档15、学术诚信10。

每个问题写severity、location、evidence、why_it_matters与recommended_fix。分别核对题目支持、研究问题回答、方法结果、摘要结论和图文语义。无法实际查看图片或文档页面时，对应维度写NOT_REVIEWED并说明能力缺口，不能猜分。先列问题再评分；终稿变化后旧结果自动失效。
