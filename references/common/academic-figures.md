# 公共规则五：学术配图路由与证据边界

先确定图要表达或证明什么，再选择绘图后端。能力报告必须分开记录：语言模型原生输出、客户端提供的图片工具、本次运行实际成功调用。图片输入或理解、编写 SVG、把 SVG 渲染为 PNG、同一供应商另有图片模型，都不等于当前运行已具备 `IMAGE_GENERATOR`。

## 路由

- 流程图、组织架构、软件架构、部署图、ER 图、UML、研究框架、因果图、时间线和关系必须准确的信息图：当前客户端有图片生成能力时，读取 `references/figure-skills/academic-figure-routing.md`，先从上下文建立精确结构契约和详细生图 Prompt，再逐图调用图片工具；生成后逐项核对节点、箭头、方向和中文标签，必要时使用确定性文字/箭头修正层。只有当前客户端没有图片生成能力时，才读取 `references/figure-skills/academic-svg-quality.md` 走纯 SVG。
- 柱状图、折线图、散点图、热图、森林图和模型诊断图：读取真实数据并用 Python、R 或等价统计工具生成；保留数据、单位、样本量、计算和脚本。
- 数学、几何、化学结构、电路和地图：使用对应领域工具，不使用生成式图片猜测公式、连接、结构或边界。
- 显微图、医学影像、实验照片、遥感图和仪器截图：使用原始科研文件并保留采集与处理记录；不得生成、补画或无披露增强证据区域。
- 生物机制、材料机理、复杂实验装置剖面、教育插画、应用场景和空间过程：当前客户端有图片生成能力时，读取 `references/figure-skills/academic-figure-routing.md`，逐张生成明确标注的概念示意；关键文字、箭头、比例和图例可使用确定性后处理。只有没有图片生成能力时才使用抽象 SVG 代替。

## 混合配图硬门

`FULL_BUILD` 或 `FIGURES_ONLY` 必须先建立完整图表组合，而不是逐图临时决定。当前客户端若暴露内置图片生成工具，将 `image_generation_policy.client_tool_exposed` 和 `required` 设为 `true`，并把所有流程、架构、框架、组织、ER/UML、机制、装置、应用场景、用户交互、服务生态和空间过程图列入 `eligible_figure_ids`，逐张真实调用图片工具。每个图号必须同时出现在 `prompt_by_figure` 与 `generated_by_figure`，分别映射到独立详细 Prompt 文件和独立位图产物；少任一项即为 `FAIL`。关键标签、箭头和数值可使用确定性后处理，但底图或主体视觉必须来自真实图片调用。

不能用 SVG、HTML 渲染、截图、占位 PNG 或图片输入能力冒充 image-gen 调用。只有用户明确退出或目标期刊明确禁止 AI 图片时可以豁免，并在 `figures/figure-manifest.json` 记录 `explicit_user_opt_out` 或 `venue_prohibits_ai_images` 及原因。数据统计图不列入 `eligible_figure_ids`，必须从真实数据使用 Python、R 或等价代码生成；显微、医学、遥感、实验照片等使用原始科研文件；公式、化学结构、电路和地图使用领域工具。除此之外，有图片能力时不得使用纯 SVG 作为主交付。

## 通用质量门

每张图必须有图形规格、图号、图题、正文首次引用位置、来源、生成方式、模型或工具、可编辑源或提示词、限制和人工核对状态。路由状态使用 `READY`、`INPUT_REQUIRED`、`CAPABILITY_GAP`、`VISUAL_QA_BLOCKED`、`PASS` 或 `FAIL`；缺少关键来源时不得生成终稿。PNG 记录最终物理宽度、像素宽高和有效 DPI，不能只写“300 DPI”。先引用、再展示、后解释。结构或事实未经核对、未实际渲染、文字溢出、页面缩放后不可读、存在裁切或远程资源时不得进入最终论文。

含中文的 SVG 必须声明至少一个明确支持中文的本地字体候选和 `sans-serif` 回退；禁止只写 `Helvetica`、`Arial`、`Times New Roman`、`Roboto` 或 generic family。推荐栈为 `"Noto Sans CJK SC", "Source Han Sans SC", "Source Han Sans CN", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "WenQuanYi Micro Hei", "SimHei", sans-serif`。生成后必须运行 `skills/academic-svg-enhancer/scripts/audit_svg.py`；出现 `CJK_FONT_FAMILY_MISSING` 或 `CJK_FONT_FALLBACK_UNSAFE` 时不得导出。使用最终导出所用的同一渲染器检查中文探针，并分别抽查 PNG、DOCX 与 PDF；只看 SVG 源码或浏览器预览不得标记 `PASS`。
