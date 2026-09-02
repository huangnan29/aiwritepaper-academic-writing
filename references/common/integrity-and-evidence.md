# 公共规则二：真实性与证据

<!-- compact-core:start -->
不得编造文献、DOI、法源、标准、实验、数据、访谈、问卷、病例、性能、提升比例、伦理审批、项目或个人信息。重要主张标为OBSERVED、VERIFIED_EXTERNAL、INFERRED、PROPOSED或UNSUPPORTED；UNSUPPORTED不得进入定稿。没有真实实验/实施材料时降级为设计、协议、公开数据分析或综述，不能用随机数和模型生成CSV补结果。DESIGN_ONLY/PROTOCOL_ONLY不得出现“本研究实测、p<0.05、满意度提升、测试通过”等结果型断言。
<!-- compact-core:end -->

工程论文区分已实现、已验证、设计方案和未来扩展；实证论文的定量结果回到原始数据与计算；人体研究说明伦理、同意、样本和匿名化。范文只供结构观察，不是事实来源。

FULL_BUILD建立data/data-provenance.json。真实数据项记录dataset_id、文件、SHA-256、origin、claim_role、supports_claims。origin只用USER_PROVIDED、AUTHOR_OBSERVED、OFFICIAL_DOWNLOAD、FORMAL_SIMULATION、CALCULATED、SYNTHETIC_DEMO、MODEL_SYNTHETIC或MANUSCRIPT_CONTEXT；后四类不得冒充观察结果。正式结果只能由RESULT、SIMULATION_RESULT或DESIGN_CALCULATION角色支撑。

所有下载、计算和仿真用capture_provenance.py捕获真实输入、命令、输出、退出码和摘要。AUTHOR_OBSERVED须绑定运行前存在的原始文件；OFFICIAL_DOWNLOAD保留实际下载字节和最终URL；FORMAL_SIMULATION保留领域引擎、模型、命令和原始输出；CALCULATED保留输入与计算脚本。生产结果的脚本不能同时手写“已验证”回执。

research_claim_level只能为OBSERVED_STUDY、DESIGN_ONLY、PROTOCOL_ONLY或REVIEW_SYNTHESIS。真实性判断由材料语义决定；脚本成功不等于研究结论成立。证据不足时降低主张并完成仍可诚实交付的部分，不把正文缩短到目标一半。
