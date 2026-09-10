# 公共规则二：真实性与证据

<!-- compact-core:start -->
不得编造文献、DOI、法源、标准、实验、数据、访谈、问卷、病例、性能、提升比例、伦理审批、项目或个人信息。重要主张标为OBSERVED、VERIFIED_EXTERNAL、INFERRED、PROPOSED或UNSUPPORTED；UNSUPPORTED不得进入定稿。没有真实实验/实施材料时降级为设计、协议、公开数据分析或综述，不能用随机数和模型生成CSV补结果。DESIGN_ONLY/PROTOCOL_ONLY不得出现“本研究实测、p<0.05、满意度提升、测试通过”等结果型断言。
<!-- compact-core:end -->

工程区分实现、验证、设计与未来工作；定量结果回到原始数据与计算；人体研究说明伦理、同意、样本和匿名化。范文不是事实来源。

FULL_BUILD建立data/data-provenance.json。真实数据项记录dataset_id、文件、SHA-256、origin、claim_role、supports_claims。origin只用USER_PROVIDED、AUTHOR_OBSERVED、OFFICIAL_DOWNLOAD、FORMAL_SIMULATION、CALCULATED、SYNTHETIC_DEMO、MODEL_SYNTHETIC或MANUSCRIPT_CONTEXT；后四类不得冒充观察结果。正式结果只能由RESULT、SIMULATION_RESULT或DESIGN_CALCULATION角色支撑。

下载、计算、仿真用capture_provenance.py捕获输入、命令、输出、退出码和摘要。AUTHOR_OBSERVED绑定运行前原始文件；OFFICIAL_DOWNLOAD留下载字节与最终URL；FORMAL_SIMULATION留引擎、模型和原始输出；CALCULATED留输入与脚本。结果脚本不得手写验证回执。

research_claim_level为OBSERVED_STUDY、DESIGN_ONLY、PROTOCOL_ONLY或REVIEW_SYNTHESIS。材料语义决定真实性；脚本成功、披露局限均不证明题目已回答。证据不足先补材料，仍不足则降低主张、报告研究与篇幅缺口，不重复填充。
