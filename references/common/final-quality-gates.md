# 公共规则九：统一核验

<!-- compact-core:start -->
核对核心主张、最终图中关系及导出页面后写qa-observations.json，再运行`paper.py check`。入口仅作证据、图片、公式、交付四类机械检查，不给语义PASS或分数。Critical/Important修复后重检，无法修复报PARTIAL/FAIL；哈希不证明专业正确。
<!-- compact-core:end -->

qa-observations.json记录主张、逐图和页面问题，视觉判断绑定所看文件、页码和真实回执。学术评分交给写作流外的另一会话、模型或人工。

机械检查覆盖引用、数据、生图与嵌图、OMML、目录、题注、表格、篇幅、文档及SHA。旧报告须匹配当前输入才能复用。AUDIT_ONLY另存；FIGURES_ONLY无重导不改正文文档。

实际查看摘要、目录、章首、代表表格、最长公式和图片页；排除页眉重复再判章序，PDF不得留“Word更新目录”占位。局部修复后重导并复看，缺视觉能力如实报告，不能以解析代替目验。

修复后重跑check，最终只据14-adjudicated-status.json报告RESEARCH_STATUS、DELIVERY_STATUS、FINAL_STATUS和缺口；报告缺失、陈旧或命令失败不得报PASS。
