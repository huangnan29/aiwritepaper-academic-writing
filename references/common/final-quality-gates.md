# 公共规则九：统一核验

<!-- compact-core:start -->
完成专业、图形和页面观察后写qa-observations.json，再运行一次`paper.py check`。入口只执行证据、图片、公式和交付四类机械检查并计算权威状态，不生成论文、语义PASS或数字评分。Critical/Important必须修复；无法修复时明确PARTIAL/FAIL。哈希只绑定文件，检查器成功不证明专业正确。
<!-- compact-core:end -->

qa-observations.json只记录主张证据、逐图盲检、实际页面检查和问题清单；每个视觉判断绑定被查看文件与真实回执。需要学术评价时，在写作流程结束后把冻结交付包交给另一会话、另一模型或人工审阅。

检查覆盖题录与引用、数据来源、生图路线与实际嵌图、公式/OMML、目录、题注、表格、篇幅、DOCX/PDF和SHA。旧报告只有输入摘要与当前文件完全一致时才能复用。AUDIT_ONLY输出到源目录之外；FIGURES_ONLY无重导时不改正文和文档。

修复后重新check。最终答复只读取14-adjudicated-status.json，报告RESEARCH_STATUS、DELIVERY_STATUS、FINAL_STATUS及真实缺口；任何报告缺失、陈旧或命令失败都不能报PASS。
