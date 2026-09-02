# 公共规则一：运行契约

<!-- compact-core:start -->
只执行本次模式。已有题目的FULL_BUILD持续到真实交付；FIGURES_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY和DEFENSE_ONLY不得扩展范围。除权限、伦理、付费、凭证或硬阻塞外不重复等待确认。能力只按当前执行器、父代理、客户端和插件的真实观察填写；`available:null`表示未知，不得当成不可用，模型品牌不能替代工具检查。
<!-- compact-core:end -->

paper-request.json是一次性语义输入，paper.py派生参数、能力、Profile、模块与唯一执行MD。模型负责方向、方法和材料判断；脚本只拼接、转换和核验。run-params.md保存用户题目、模式、语言、层次、篇幅、文献/图表目标和停止条件。字数按用户明确值、模板、论文层次和默认值排序；中文THESIS层次未知兜底25,000。

能力为image_generation、visual_inspection、docx_export、pdf_export四项三态值。已知可用时可补tool、caller和evidence；父/客户端代调只记录一个真实caller。能力后来变化时使用安全amend形成新提示词，不静默改旧报告。MODEL_LABEL写模型与客户端，RUN_LABEL只区分测试目录，不进入论文署名。
