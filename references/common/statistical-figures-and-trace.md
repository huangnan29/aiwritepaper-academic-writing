# 公共规则六：统计图、图表规划与证据追踪

本规则补充“学术配图路由”，只强化统计图与所有图表的证据链，不改变结构图的ImageGen优先级。架构、流程、ER、UML、机制、装置和研究框架仍按图片能力路由；统计图必须读取真实数据并由代码生成。

## 图表规划契约

详细大纲必须先建立 `figure_plan[]`，再进入制图。每项至少记录：

```yaml
figure_plan:
  - figure_id: "fig-4-1"
    purpose: "该图回答的具体问题"
    figure_type: "ARCHITECTURE|PROCESS|ER_UML|STATISTICAL|NETWORK_DATA|DOMAIN|EVIDENCE_IMAGE"
    claim_bearing: true
    source_kind: "MANUSCRIPT_CONTEXT|DATASET|SOURCE_FILE"
    source_locator: "正文、schema、数据文件或原始科研文件"
    route: "IMAGE_GENERATION|DATA_CODE|DOMAIN_TOOL|EVIDENCE_FILE|SVG_FALLBACK"
    svg_layout_mode: "NATIVE|COMPILED|null"
    placement: "第4章4.1节"
    final_format: "PNG"
    risks: []
```

计划只决定目的、来源、路线、位置和风险，不得提前生成实验结果或任意数字。没有真实数据时，统计图候选必须改为测试指标体系、数据采集方案、待测表结构或纯文字说明。

## 统计图选择

先写一句分析问题与一句预期读图任务，再选择最简单、可辩护的图形：

| 数据关系 | 首选图形 | 关键条件 |
|---|---|---|
| 时间或有序趋势 | 折线图 | 通常至少8个有意义时间点；点太少改用斜率图、柱状图或表格 |
| 类别比较与排序 | 柱状图、点图或棒棒糖图 | 长标签用横向；无语义顺序时排序 |
| 分布 | 直方图、箱线图或小提琴图 | 说明样本量、分组和异常值规则 |
| 两变量关系 | 散点图与回归/平滑线 | 通常至少12个同粒度观测；保留样本量或分母 |
| 多变量关系 | 相关性热图 | 报告相关口径与缺失值处理 |
| 效应量 | 森林图 | 效应量、区间和权重可追溯 |
| 发表偏倚 | 漏斗图 | 仅用于适用的系统综述或Meta分析 |
| 数据驱动网络 | 网络图 | 必须有真实节点边表或邻接矩阵 |

以下情况不强行画统计图：少于3个数据点、单个百分比或均值、只有一个类别、所有值相同、图形与现有表格完全重复、数据无法解释坐标含义。精确查数优先表格，比较形状优先图形。

禁止使用3D图、彩虹色图、无说明的截断坐标轴、用双Y轴制造相关性、仅为装饰的图形和无法解释的数据编码。饼图不是默认路线，确需使用时限制少量类别并明确分母。

## 数据真实性与可复现性

- 正式统计图必须有真实数据文件、字段说明、单位、样本量或观测粒度、处理脚本和脚本SHA-256。
- `data_status` 只能为 `OBSERVED`、`VERIFIED_EXTERNAL`、`SIMULATED_RESEARCH` 或 `NOT_APPLICABLE`。`SIMULATED_RESEARCH` 只适用于研究方法本身就是仿真且存在可执行模型、参数、种子和输出数据文件的情况。
- `PROPOSED`、`HARDCODED_EXAMPLE`、任意手写数组、`np.random`、`rnorm`、`runif`或演示模板输出不得作为论文结果图。随机重采样、Bootstrap或正式仿真可以使用随机数，但必须读取真实输入或记录研究模型、固定种子与输出文件。
- 绘图脚本出现随机函数时，Manifest增加 `randomness: {"purpose": "bootstrap|simulation|other", "seed": 42, "output_file": "..."}`；没有用途和种子声明时机械校验失败。
- 示例代码必须失败关闭：数据占位未替换时主动报错，不得渲染看似完整的示例图片。
- 图中数值、正文数值和表格数值必须来自同一数据版本与计算口径；不能靠视觉模型验证统计计算。

## 出版与可访问性质量

- 默认输出最终PNG并保留可编辑源；期刊要求时同时提供PDF/EPS。最终PNG有效分辨率至少300 DPI。
- 参考尺寸：单栏约84 mm、1.5栏约127 mm、双栏约175 mm；在实际插入尺寸检查字号和裁切。
- 连续色使用viridis或cividis等感知均匀方案；分类色同时提供形状、线型、纹理或直接标签，不能只依赖红绿差异。
- 坐标轴写清变量、单位与变换；多系列有图例或直接标签；均值比较按研究设计报告SD、SE或置信区间，不能用无定义误差棒。
- 最终显示文字通常不小于8 pt；中文使用跨平台CJK字体并在PNG、DOCX、PDF中检查缺字。
- 图片画布内部不得写论文外部题注形式的“图X-X + 完整图题”；轴标题和面板标题可以保留，正式图号与图题只在文档题注中出现一次。

## 权威Figure Manifest

`figures/figure-manifest.json` 是机器可读的唯一插图路由真源；`figures/figure-manifest.md` 是供人阅读的摘要，不能被导出程序用于重新选图。JSON根对象包含 `schema_version` 与 `figures[]`，当前版本为 `1.2`。每张图至少记录：

```json
{
  "figure_id": "fig-4-1",
  "title": "图题文字",
  "figure_type": "STATISTICAL",
  "claim_bearing": true,
  "generation_route": "DATA_CODE",
  "data_status": "OBSERVED",
  "prompt_file": null,
  "generated_file": null,
  "generation_receipt": null,
  "svg_layout_mode": null,
  "svg_layout": null,
  "fallback_file": null,
  "source_data": [{"dataset_id": "bench-v1", "file": "data/bench.csv", "sha256": "..."}],
  "transformation": {
    "script": "figures/plot_bench.py",
    "sha256": "...",
    "execution_receipt": {
      "command": "实际执行命令",
      "receipt_file": "figures/receipts/fig-4-1-data-run.log",
      "receipt_sha256": "...",
      "script_sha256": "...",
      "inputs": [{"file": "data/bench.csv", "sha256": "..."}],
      "output_sha256": "..."
    }
  },
  "caption_claim": "图题或图注表达的可检验主张",
  "supported_manuscript_claims": [{"claim": "正文主张", "locator": "第7章7.2节"}],
  "limitations": [],
  "canvas_contains_figure_number_or_caption": false,
  "final_embed_file": "figures/fig-4-1-final.png",
  "vlm_verification": {
    "status": "PASS",
    "iterations": 1,
    "remaining_issues": [],
    "evidence_level": "VISUAL_TOOL_RESULT",
    "tool": "实际视觉工具",
    "checked_at": "2026-08-23T09:05:00-07:00",
    "checked_file_sha256": "...",
    "receipt_file": "figures/receipts/fig-4-1-vlm.txt",
    "receipt_sha256": "..."
  }
}
```

条件字段规则：

- `IMAGE_GENERATION`：必须有独立 `prompt_file` 与真实 `generated_file`；最终文件若不同，必须记录文字、箭头或格式合成过程，不能改用纯SVG重画。
- `DATA_CODE`：必须有 `source_data`、每个输入文件SHA-256、脚本、脚本SHA-256、实际执行回执和非空最终文件；执行回执记录实际命令、输入摘要、脚本摘要、输出摘要及原始日志，主张型统计图不能使用 `NOT_APPLICABLE`。
- `DOMAIN_TOOL`：记录领域工具、输入文件与导出过程。
- `EVIDENCE_FILE`：记录原始科研文件、采集或处理来源；不得生成证据区域。
- `SVG_FALLBACK`：只在图片工具不可用、用户退出或格式禁止时使用，记录 `CAPABILITY_GAP`；`svg_layout_mode` 为 `NATIVE` 或 `COMPILED`。`COMPILED` 必须记录语义Spec、布局报告、渲染器标识及各自SHA-256；SVG保留为fallback，最终文档默认嵌入经过核对的PNG。
- `canvas_contains_figure_number_or_caption` 必须为 `false`，避免与Word/LaTeX题注重复。

`COMPILED` 的 `svg_layout` 使用固定字段：

```json
{
  "spec_file": "figures/fig-2-1-spec.json",
  "spec_sha256": "...",
  "report_file": "figures/fig-2-1-layout-report.json",
  "report_sha256": "...",
  "renderer": "aiwritepaper-agentic-skill@0.8.2/render_svg_layout.mjs",
  "renderer_sha256": "..."
}
```

### 图片工具调用回执

`IMAGE_GENERATION` 不能只靠模型声称“已经调用”。每次调用后立即把客户端实际返回的工具结果或终端调用片段原样保存到当前输出目录，例如 `figures/receipts/fig-2-1-imagegen.json`；不得事后根据记忆补写或伪造。Manifest中的 `generation_receipt` 至少记录：

```json
{
  "evidence_level": "NATIVE_TOOL_RESULT",
  "tool": "imagegen",
  "provider": "OpenAI",
  "model": "gpt-image",
  "invoked_at": "2026-08-23T09:00:00-07:00",
  "call_id": "服务实际返回的调用ID",
  "receipt_file": "figures/receipts/fig-2-1-imagegen.json",
  "receipt_sha256": "...",
  "prompt_sha256": "...",
  "generated_sha256": "..."
}
```

- `NATIVE_TOOL_RESULT`：客户端提供原生工具结果和真实调用ID；
- `CLIENT_TRANSCRIPT`：客户端不暴露原生ID，但可保存含调用时间、工具名和输出定位的实际调用片段；`call_id` 写 `NOT_EXPOSED`；
- `DECLARED_ONLY`：只有模型自述，不能证明发生过图片调用，机械校验失败且最终状态不得为 `PASS`。

回执只能证明本地保存的Prompt、工具结果与生成文件摘要相互一致，不能冒充服务商签名证明。客户端既不暴露调用结果也无法保存调用片段时，如实使用 `DECLARED_ONLY` 或记录 `CAPABILITY_GAP`，不能编造ID。

机器可读结构同时由 `references/schemas/figure-manifest.schema.json` 定义。`figure-manifest.md` 每张图只保留一行摘要，且必须恰好出现一次 `figure_id` 和一次对应的 `final_embed_file`；它不能列出另一个“推荐插图”路径。机械校验同时读取两份清单，摘要缺失或路由不一致时失败。

## VLM渲染核验

当前Agent具备视觉能力时，对主张型统计图和复杂结构图执行渲染核验。最多修复两轮，第三次仍有问题则标记 `NEEDS_REVIEW`，不能假装通过。

`PASS`与`PASS_WITH_NOTES`必须保存视觉工具实际返回结果或客户端调用片段，并记录被检查的 `final_embed_file` SHA-256、工具、检查时间、回执文件及其SHA-256。`DECLARED_ONLY`表示只有模型自述，机械校验失败。没有视觉工具时使用 `SKIPPED` 并填写具体 `reason`，不得伪造视觉检查；需要视觉检查的复杂图因此保持能力缺口。

所有图片检查：裁切、文字重叠、最小字号、中文缺字、颜色区分、外部题注重复、实际论文尺寸可读性。

统计图增加检查：数据系列是否遗漏、图中数值与数据是否一致、误差棒尺度、坐标轴单位、分母与样本量、图题主张是否超出数据。VLM只能发现可见异常，数值仍由代码复算。

流程、架构、ER/UML增加检查：节点数量和逐字标签、分组层级、每条箭头的起点终点、分支条件、连接线交叉与穿越、连接点位置、主次路径和图例。不能只检查“好看”。

## 图表—主张追踪

主张型图表必须能追溯到数据或上下文、转换过程、图题主张、正文使用位置和已知限制。每条 `supported_manuscript_claims` 必须在正文真实引用该图；正文所有实质性用图主张也必须反向出现在Manifest中。空 `limitations: []` 只表示未声明限制，不等于系统确认没有限制。

机械校验只能验证字段、文件、哈希和路由一致性，不能证明图表在学术上正确。最终状态仍由模型结合真实数据、渲染结果、DOCX/PDF和用户要求判断。

SVG降级图的机械校验额外检查可解析的直线、折线与矩形节点：非共享端点交叉或连线横穿节点时失败。复杂贝塞尔 `path`、曲线箭头、文字边界和视觉拥挤仍必须通过VLM或人工检查，静态几何检查不得宣称覆盖全部SVG布局。
