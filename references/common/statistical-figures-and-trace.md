# 公共规则六：统计图与计算来源

统计图由真实数据和可复算代码生成，不由生图模型猜数字。先写分析问题、变量与读图任务：趋势用有序点/线，类别比较用点/柱，分布用直方/箱线，关系用散点，效应量用区间图；选择取决于数据含义而非统一最低点数。没有有效比较或与表格完全重复时不强画图。

坐标写变量、单位、变换、分母和样本量；误差棒说明SD/SE/CI及计算方法。类别保留合理顺序；长标签用横向布局。避免无解释截轴、装饰性3D、制造相关性的双轴。配色兼顾灰度与色觉差异，可采用viridis/cividis及直接标签；最终实际字号通常不低于8pt，PNG在插入尺寸至少300DPI。

## 数据与版本

每个源文件记录dataset_id、file、sha256、origin（data_origin）和真实采集来源；来源遵循数据真实性模块。data_status为OBSERVED、VERIFIED_EXTERNAL或SIMULATED_RESEARCH，研究仿真必须有模型、参数、种子及输出；NOT_APPLICABLE不能用于主张型统计图。PROPOSED、HARDCODED_EXAMPLE、MODEL_SYNTHETIC/SYNTHETIC_DEMO不能支撑真实结果。

transformation记录script、sha256、execution_receipt（command、receipt_file、receipt_sha256、script_sha256、inputs及output_sha256）。通过capture_provenance.py捕获实际命令、日志与输入输出，不能自写“运行成功”。Bootstrap、重采样和正式随机模拟可使用随机数，但randomness须说明purpose、seed、output_file和适用假设；不是看到随机函数就判造假。

所有正文、表格、图用同一数据版本；汇总图能回到逐条记录和处理逻辑。数据网络需真实节点边表。分类映射不能只验证计数：模型须核对实际研究对象、任务和方法，不能把摘要背景词当作研究内容；抽查边界项与异常项，误分类修复后重算图表。预印本和正式版核对工作身份，不能重复计入。

用代码复算数字、样本与不确定性，再用视觉检查系列遗漏、轴标签、尺度和图题是否越过证据。VLM不能证明计算正确，数字能复算也不能证明分类正确。caption_claim与supported_manuscript_claims须与正文实际用图一致，limitations记录真实不可比与缺失问题。
