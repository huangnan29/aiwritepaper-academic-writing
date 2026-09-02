<!--
本文件从完整版同一源的CORE段确定性生成；真实性底线不降低。
公共来源：
- references/common/capability-and-runtime.md
- references/common/integrity-and-evidence.md
- references/common/literature-and-citation.md
- references/common/output-contract.md
- references/common/academic-figures.md
- references/common/statistical-figures-and-trace.md
- references/common/academic-prose-quality.md
- references/common/autonomous-completion.md
- references/common/final-quality-gates.md
- references/common/mathematical-formulas.md
- references/common/svg-layout.md
方向来源：references/directions/electronic-circuit-design.md
-->

# electronic-circuit-design 紧凑论文生成提示词

## 合并说明

当前文件只保留执行与方向核心；每次只做阶段卡要求的工作。

<!-- task-module:capability-and-runtime -->
<!-- 公共CORE来源：references/common/capability-and-runtime.md -->

只执行本次模式。已有题目的FULL_BUILD持续到真实交付；FIGURES_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY和DEFENSE_ONLY不得扩展范围。除权限、伦理、付费、凭证或硬阻塞外不重复等待确认。能力只按当前执行器、父代理、客户端和插件的真实观察填写；`available:null`表示未知，不得当成不可用，模型品牌不能替代工具检查。
<!-- /task-module -->

<!-- task-module:integrity-and-evidence -->
<!-- 公共CORE来源：references/common/integrity-and-evidence.md -->

不得编造文献、DOI、法源、标准、实验、数据、访谈、问卷、病例、性能、提升比例、伦理审批、项目或个人信息。重要主张标为OBSERVED、VERIFIED_EXTERNAL、INFERRED、PROPOSED或UNSUPPORTED；UNSUPPORTED不得进入定稿。没有真实实验/实施材料时降级为设计、协议、公开数据分析或综述，不能用随机数和模型生成CSV补结果。DESIGN_ONLY/PROTOCOL_ONLY不得出现“本研究实测、p<0.05、满意度提升、测试通过”等结果型断言。
<!-- /task-module -->

<!-- task-module:literature-and-citation -->
<!-- 公共CORE来源：references/common/literature-and-citation.md -->

先写检索式和纳排标准，再写正文。发现层用于找候选，证据层读取全文/法源/标准/官方数据，核验层核对题名、作者、年份、版本与DOI；发现记录不能冒充全文。文献状态仅为VERIFIED_FULLTEXT、VERIFIED_METADATA、UNVERIFIED、REJECTED。核心主张须由有页/节定位的VERIFIED_FULLTEXT支撑；只核元数据不能转述样本、方法、数字或引语。正文引用、文末文献、references.bib和证据矩阵必须闭合。
<!-- /task-module -->

<!-- task-module:output-contract -->
<!-- 公共CORE来源：references/common/output-contract.md -->

DOCX与PDF来自同一份07-paper-full.md和同一图表清单。导出时固定一个本地时间戳，文件名为“安全论文题目_YYYYMMDD-HHMMSS.docx/pdf”，不覆盖旧稿。无模板采用A4中文学术草稿：正文12pt、首行2字符、1.5倍行距；真实Heading样式生成左侧导航；图题仅一次且图下，表题表上；表格单元格零首行/悬挂缩进；公式为可编辑OMML；中文THESIS含中英文摘要和关键词；目录有真实条目与页码。
<!-- /task-module -->

<!-- task-module:academic-figures -->
<!-- 公共CORE来源：references/common/academic-figures.md -->

每图先写目的、正文位置、事实节点/边、逐字标签、禁止项和精确性。生图能力真实可用时，普通流程、架构、组织和概念图必须用IMAGE_GENERATION，并逐图给出详细Prompt；统计图用DATA_CODE；引脚、电路、化学结构和尺度图用DOMAIN_EXACT；真实影像用EVIDENCE_FILE。只有无生图工具、用户要求矢量或出版限制时才SVG_FALLBACK。成功生图及其中文覆盖PNG必须成为final_embed_file并实际进入Word/PDF，不能被同号SVG替换。
<!-- /task-module -->

<!-- task-module:statistical-figures-and-trace -->
<!-- 公共CORE来源：references/common/statistical-figures-and-trace.md -->

统计图必须来自真实数据和可复算代码，不能由生图模型猜数字。图型服从读图任务：趋势用线，比较用点/柱，分布用直方/箱线，关系用散点，效应用区间图。标出变量、单位、分母、样本量和误差含义；禁止装饰性3D、无解释截轴和误导双轴。正文、表格和图使用同一数据版本。
<!-- /task-module -->

<!-- task-module:academic-prose-quality -->
<!-- 公共CORE来源：references/common/academic-prose-quality.md -->

段落提出具体判断，说明材料如何支持、反例和边界。相邻段落必须增加信息；列表只用于真实并列关系，不能替代论证。避免连续制造“几层、几维、几阶段”框架、无证据强化、过程旁白和摘要—结论机械复述。结论只回答正文已支持的问题，不能靠重复、附录和表格凑字数。
<!-- /task-module -->

<!-- task-module:autonomous-completion -->
<!-- 公共CORE来源：references/common/autonomous-completion.md -->

FULL_BUILD按研究契约、检索、证据、大纲、分章正文、图表、整合、导出、检查和定点修复持续执行；局部模式只做用户指定部分。下一章使用计划、证据和前章摘要，不反复加载全文。缺材料时完成诚实的设计/协议/综述，不编结果补字数。发现错误只返回受影响阶段；RESUME验证旧提示词和摘要后继续，REVISE_ONLY保留原稿并另存。
<!-- /task-module -->

<!-- task-module:final-quality-gates -->
<!-- 公共CORE来源：references/common/final-quality-gates.md -->

完成专业、图形和页面观察后写qa-observations.json，再运行一次`paper.py check`。入口只执行证据、图片、公式和交付四类机械检查并计算权威状态，不生成论文、语义PASS或数字评分。Critical/Important必须修复；无法修复时明确PARTIAL/FAIL。哈希只绑定文件，检查器成功不证明专业正确。
<!-- /task-module -->

<!-- task-module:mathematical-formulas -->
<!-- 公共CORE来源：references/common/mathematical-formulas.md -->

先核对公式含义、符号、单位、前提、边界和代入，再处理渲染。Markdown统一使用`$...$`与`$$...$$`；代码中安全处理反斜杠。DOCX公式必须是可编辑OMML，PDF不得显示TeX源码，不能用生图模型重画精确公式。重要公式分配稳定ID并记录源定位；不能只比较Markdown公式数与OMML节点数。
<!-- /task-module -->

<!-- task-module:svg-layout -->
<!-- 公共CORE来源：references/common/svg-layout.md -->

SVG只用于无生图工具、用户/出版要求矢量或DOMAIN_EXACT骨架。先列节点、边、逐字标签和禁止关系，再排坐标。优先整数网格、正交折线、端点落在正确边界/引脚；并行边独占通道，检查交叉、穿节点和共线重叠。中文使用真实可用CJK字体并按论文物理尺寸检查字号。最终SVG转PNG后实际查看，不能让几何PASS代替语义核对。
<!-- /task-module -->

<!-- task-module:direction -->
<!-- 方向CORE来源：references/directions/electronic-circuit-design.md -->

PROMPT_ID: `electronic-circuit-design`

## 范文结构依据

- 公开示例：电路设计范文《基于CAD的电动车充电接口电路设计》
- 来源：https://www.aiwritepaper.com/paper_editor?orderNumber=2038336519713857536
- 使用边界：只学习章节组织与交付形态，不把范文正文和其中数字作为证据。

## 适用范围

模拟/数字电路、接口、电源、嵌入式硬件、PCB和电气控制设计。

## 不适用或高风险情形

没有原理图、器件数据手册、仿真或测量记录却宣称指标达成。

## 方向专属输入

在研究契约中补充：研究对象、核心变量或工程指标、真实材料清单、研究方法、伦理或安全要求、目标学校/期刊模板。输入不足时先记录缺口，不自行补造。

## 推荐结构

1. 问题与技术指标
2. 原理和方案比较
3. 器件选型与参数计算
4. 总体原理图与子电路
5. 仿真、PCB与安全设计
6. 测试环境和用例
7. 结果、误差与故障分析
8. 结论与改进

结构应按题目和材料调整，不机械保留空章节。每个三级标题都要说明问题、主张、证据、计划字数、图表和完成标准。

## 必需证据

- 原理图、网表和BOM
- 器件官方数据手册
- 仿真工程
- PCB文件
- 示波器或逻辑分析仪记录
- 测试工装和日志

所有结果必须能回溯到原始文件、计算过程或已核验来源。

## 文献信源

- 发现与筛选：IEEE Xplore、IET Inspec（INSTITUTION_REQUIRED）；CNKI电子与仪器类核心刊（注明目录版本）。
- 证据与全文：TI、ADI、Infineon等器件厂商官方数据手册（OPEN_WEB）；IEC、JEDEC、USB-IF等接口标准原文；出版社全文或作者合法存档版本。
- 开放路线：厂商datasheet官网（OPEN_WEB）；JEDEC注册后可免费下载的标准（LOGIN_REQUIRED）；OpenAlex（OPEN_API）；arXiv eess类目（预印本，须核正式版）。
- 不宜作核心引文：论坛抄录的datasheet、电商模块说明书。
- 信源核验门槛：器件参数必须追溯到官方数据手册的具体版本号或日期；接口时序与电气特性以标准原文为准。

## 图表与表格

系统框图、原理图、关键波形、PCB布局和测试连接；表格包括器件选型、指标预算和测试结果。

## 无材料时的降级规则

无实物与测量时只报告仿真或设计目标，并明确不能证明实机性能。

## 方向质量门槛

- 研究问题与方法匹配；
- 核心主张有对应证据；
- 图表来源、单位、样本和口径可追溯；
- 结果与讨论不混淆；
- 局限真实且不以未来工作掩盖当前缺口；
- 方向专属伦理、安全、标准或版权要求已处理；
- 与公共规则共同执行后才允许进入最终验收。

## 电气闭合规则

任何电源链都要同时闭合输入范围、输出目标、压差或占空比、峰值电流、纹波、热耗散、启动浪涌和最低工作电压。不能只比较典型值。线性稳压至少校核`Vin_min - dropout >= Vout`与最坏功耗；开关电源说明开关频率、磁性器件、补偿、效率假设和布局敏感回路。负载预算按峰值而非平均值，传感器加热、无线发射、继电器吸合等瞬态单列。

数字接口逐项核对供电域、VIH/VIL、VOH/VOL、上拉电压、总线电容、速率、地址和时序。不同电压域不得因“逻辑兼容”省略电平转换依据。断电状态检查I/O钳位、反向供电、默认上拉、启动配置脚、热插拔和掉电顺序。模拟链说明输入共模范围、输出摆幅、源阻抗、偏置、带宽、噪声、采样建立时间和保护；每个公式必须能回到器件条件。

## 精确连接合同

原理图、引脚图、接线图和PCB网络属于DOMAIN_EXACT。制作前建立`figures/connection-table.csv`或真实网表，每条连接至少含`from_component,from_pin,to_component,to_pin,net,voltage_domain,source`。器件型号、封装、引脚号、信号方向、复用功能和数据手册页码另成引脚映射表。图中每一条线都必须在连接表出现，连接表中的每条必需网络也必须出现在图中；不能凭语言模型记忆猜脚位。

精确图先由EDA、网表或确定性矢量工具产生可核对骨架，生图只用于背景、材质和不改变拓扑的视觉增强。系统框图、工作流程等语义结构图在生图工具可用时仍执行IMAGE_GENERATION。任何成功生图必须通过`final_embed_file`进入DOCX/PDF，不能被同号SVG替换。

## 证据分层

- 设计计算：输入来自数据手册、标准和明确假设，只能证明参数选择自洽。
- 仿真结果：必须保存真实网表、模型版本、求解器、命令、原始输出和收敛信息；不能写成实测。
- 样机实测：必须保存仪器型号、校准状态、测试点、工况、波形或原始日志；不能由仿真图替代。

三类证据在标题、摘要、结果和结论中使用一致措辞。未制板时不写“系统运行稳定”；未做正式仿真时不写“仿真验证通过”。
<!-- /task-module -->

<!-- task-module:method -->
<!-- 方法门来源：references/quality/direction-method-gates.json -->

## 当前方向方法完成门

只检查本稿实际采用的方法与主张；不为通过清单添加无关实验。事实错误不能以材料不足豁免。

- 器件参数回到对应版本数据手册
- 电源、电平、引脚和时序逐项校核
- 仿真结果具有真实网表、引擎命令和原始输出

### 数据不足时的题目与主张处理

未实际运行SPICE或制板时保持设计与验证方案，不报告仿真通过、样机指标或认证。
<!-- /task-module -->
