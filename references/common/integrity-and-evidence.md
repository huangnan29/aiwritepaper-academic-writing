# 公共规则二：真实性与证据

不得编造文献、DOI、作者、期刊、政策、标准、法条、网页、实验、数据、访谈、问卷、病例、用户数量、性能、提升比例、伦理审批、项目、个人信息或致谢对象。

在研究契约、证据矩阵或审计记录中，将重要主张标记为以下状态之一：

- `OBSERVED`：由用户材料、原始数据、代码运行或日志直接观察；
- `VERIFIED_EXTERNAL`：由已核验的权威外部来源支持；
- `INFERRED`：基于证据的推论，必须降低语气并说明限制；
- `PROPOSED`：设计方案、测试计划或预期标准；
- `UNSUPPORTED`：不得进入最终正文。

工程论文必须区分已实现、已验证、设计方案和未来扩展。实证论文的每个定量结果必须追溯到数据文件与计算过程。临床、问卷、访谈和人体研究必须说明伦理、同意、样本和匿名化边界。没有真实材料时，降级为研究方案、公开数据分析、验证协议、概念设计或文献综述。

AIWritePaper 范文仅提供结构观察，不是事实来源。不得复制范文正文、引用其未核验数字，或继承其“已完成”表述。

凡涉及定量结果或“系统已实现/已运行”的主张，必须能够回到用户材料、数据文件、源码版本、执行命令、原始日志、公开数据集或已核验来源。`FULL_BUILD` 必须建立 `data/data-provenance.json`，根对象记录 `schema_version: 1.0`、与Manifest一致的 `research_claim_level` 和 `datasets[]`。每个真实数据集记录 `dataset_id`、文件、SHA-256、`origin`、`claim_role` 与 `supports_claims`。

`origin` 只能为 `USER_PROVIDED`、`AUTHOR_OBSERVED`、`OFFICIAL_DOWNLOAD`、`FORMAL_SIMULATION`、`CALCULATED`、`SYNTHETIC_DEMO`、兼容旧名 `MODEL_SYNTHETIC` 或 `MANUSCRIPT_CONTEXT`；`claim_role` 只能为 `RESULT`、`SIMULATION_RESULT`、`DESIGN_CALCULATION`、`ILLUSTRATION` 或 `CONTEXT_ONLY`。每个登记数据集必须有真实文件和SHA-256。合成/演示数据不能支撑结果、仿真结果或正式设计计算；`CALCULATED` 不能冒充观察结果。Python局部变量、随机休眠、手写JSON、自写“下载成功/ERP已核验/GDC已读取”文本或模拟请求不是真实数据库、Web服务、GPU、课堂、问卷或硬件实验。

所有数据回执使用Skill的 `scripts/capture_provenance.py` 生成，不能由生产数据的同一个项目脚本手写：

- `USER_PROVIDED` 与 `AUTHOR_OBSERVED` 必须先登记不可变原始文件，并在数据项的 `source_artifacts[]` 记录原始文件路径、SHA-256与来源；本次运行脚本创建的CSV/JSON不能登记为作者观察。
- `OFFICIAL_DOWNLOAD` 必须保留实际下载字节，回执记录原始URL、最终URL、HTTP状态、时间、内容类型、文件大小与SHA-256；只有平台名称和`SUCCESS`的文本无效。
- `FORMAL_SIMULATION` 必须捕获领域引擎、版本/类别、真实命令、退出码、输入模型、原始输出、stdout/stderr与SHA-256；Python手工数组、插值曲线或绘图脚本不能冒充SPICE、FEA、CFD或实验结果。
- 承担正式设计计算的 `CALCULATED` 必须捕获输入、脚本、命令和输出。结果脚本使用随机数时必须记录用途、种子和分布；未声明随机生成的正式结果直接失败。
- `OBSERVED_STUDY` 至少有一个能够回到用户/作者真实原始文件或官方真实下载字节的结果数据集；只有题录、回执文本或模型生成数据时必须降级。

`run-manifest.json` 的 `research_claim_level` 只能为：

- `OBSERVED_STUDY`：存在可核验的本研究原始数据与观察回执；
- `DESIGN_ONLY`：系统、电路、管理或教学设计，未实施验证；
- `PROTOCOL_ONLY`：实验或研究方案，尚未产生本研究结果；
- `REVIEW_SYNTHESIS`：以已核验外部证据完成综述综合。

设计或方案论文出现“本系统实测”“实验班提升”“p<0.05”“满意度达到”“通过某项测试”等本研究结果表述，而数据清单没有真实观察材料时，属于Critical错误，不得进入最终正文。

真实性判断由模型结合材料语义完成，不以某个脚本返回码代替。发现证据不足时，应降低表述强度、改写为设计方案或验证协议，并继续完成能够诚实交付的章节；不得用“材料不足”作为把整篇论文缩短到目标一半的理由。
