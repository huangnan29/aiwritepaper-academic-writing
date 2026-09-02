# 公共规则一：运行契约

只执行参数中选定的任务。FULL_BUILD完成论文；FIGURES_ONLY只改图；EXPORT_ONLY只导出；AUDIT_ONLY只读检查；PROPOSAL_ONLY写开题；DEFENSE_ONLY重组已有论文。RESUME用已冻结提示词续跑，REVISE_ONLY用修改意见和影响清单，不重新生产整篇。

用户已给题目并要求开始时使用AUTO_COMPLETE；AUTO_BENCHMARK是兼容名。除权限、伦理、凭证、付费及无法继续的硬阻塞外持续完成，不重复询问题目或大纲。用户指定的目录和材料边界优先。

## 参数唯一来源

paper-request.json是模型一次填写的任务记录；paper.py prepare已生成run-params.md、能力/Profile/模块记录和Manifest骨架，不再重复准备。run-params.md是本次题目、方向、模式、语言、层次、篇幅、文献/图表数量、模板和停止条件的执行来源。字数按用户、模板、明确层次默认、25,000兜底排序，由准备入口调用统一解析器生成TARGET_LENGTH/MIN_LENGTH/MAX_LENGTH；THESIS层次未知仍25,000。用户明确值不可被默认值覆盖。

准备时真实检查当前执行器、父代理、客户端和插件的检索、文件、运行、生图、视觉与文档能力；已完成的观察不在写作阶段反复探测。00-capability-report.json由入口保留available、callers、tools与实际依据，不按品牌推断能力。任一层可生图即按可用处理；工具状态后来变化时更新真实记录，不虚构调用或静默改写旧报告。

MODEL_LABEL写真实模型与客户端，未知时写UNKNOWN；RUN_LABEL另记目录标签，不进入论文署名。模型负责选择方向和方法，工具只拼接、转换、计算与核验。
