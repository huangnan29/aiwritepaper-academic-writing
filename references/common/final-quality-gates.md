# 公共规则九：审计与最终验收

全文整合后检查标题编号、摘要一致性、方法与技术栈、术语、数字来源、图表引用、引文匹配、参考文献覆盖、重复章节、个人信息和未来计划误写为结果。

同行评审按 Critical、Important、Minor 分级。Critical 和 Important 必须修复并在 `10-revision-log.md` 记录修改位置、内容、验证和状态。

最终由模型读取研究契约、正文和真实文件后逐项验收，并验证：

- 要求文件存在且非空；
- DOCX 可解包和解析；
- PDF 可解析、页数大于零且无异常空白页；
- 标题、摘要、各章、参考文献和致谢均存在；
- 全文只有一份连续参考文献，各章没有重复插入局部书目；摘要、章节首尾与结论没有机械复述同一套多层分类；
- 主体段落由具体材料、推理和边界推动，不以大量加粗列表、空泛框架词或无证据的“显著、全面、有效”代替论证；
- 实际字数、图、表和文献达到合同要求；
- `00-capability-report.json` 可解析，且图片生成能力覆盖当前执行器、父代理、客户端与MCP/插件；
- 证据矩阵包含完整题录、主张与章节映射字段；只有元数据的文献没有被用于全文级实验、参数、结果或引语主张；
- 图表不裁切、不越界，表格宽度合理；
- 详细大纲包含 `figure_plan[]`，每张实际图片均能回到计划中的目的、来源、路线和位置；
- 权威 `figures/figure-manifest.json` 可解析、图号唯一、条件字段完整，Markdown摘要没有覆盖JSON路由；
- 图片能力Agent应生图的每张图均有独立Prompt和真实位图；数据统计图有数据与代码；SVG降级图在PNG、DOCX、PDF中没有字体替换、方框、乱码、缺字、溢出或裁切；
- 图片生成能力可用时，任何 `imagegen_eligible=true` 的图都没有进入SVG降级；父代理代调时完整图片任务单已逐张执行，不是只补第一张概念图；
- `IMAGE_GENERATION` 每次调用均保存原生工具结果或客户端调用片段，Manifest记录Prompt、回执和原始生成文件SHA-256；只有模型自述、回执缺失或摘要不匹配时不得标记通过；
- 主张型统计图的 `data_status` 不是 `PROPOSED` 或 `HARDCODED_EXAMPLE`，真实数据、脚本与脚本SHA-256均存在；研究仿真只有在方法本身为仿真且保留参数、种子和输出数据时才允许；
- `DATA_CODE` 的每个源数据文件均有SHA-256，实际执行回执绑定命令、运行日志、输入、脚本和最终输出摘要；只有脚本文件而没有执行证据时不得通过；
- 每个图号只有一个 `final_embed_file`；图片工具成功生成后，该字段指向生成位图或以其为底图合成的最终PNG，不能指向SVG备用源；
- `07-paper-full.md`、DOCX的 `word/media/` 和PDF实际显示内容均与 `final_embed_file` 一致，不存在Imagine已生成但最终插入旧SVG的情况；
- SVG连接线尽量不交叉、不穿越节点或文字，转折整齐，箭头与连接点位置合理；
- SVG中可解析的直线和折线不存在非共享端点交叉或横穿矩形节点；复杂贝塞尔路径保留VLM或人工核验，不以静态检查冒充完整几何证明；
- SVG只执行单向降级：图片生成成功时未被SVG覆盖；原生SVG通过时未被模板重绘；`COMPILED`模式的语义Spec不含坐标，布局报告、输入、输出和渲染器SHA-256一致且状态为 `PASS`；
- 当前Agent具备视觉能力时，主张型统计图和复杂结构图已完成VLM渲染核验；两轮修复后仍有问题则为 `NEEDS_REVIEW`，不得标记通过；
- `IMAGE_GENERATION` 产物没有独立视觉或人工核验时，机械状态可以通过但视觉状态为 `PARTIAL`，最终交付不得写成完全 `PASS`；
- VLM的 `PASS` 或 `PASS_WITH_NOTES` 绑定实际视觉工具回执、检查时间和被检查文件SHA-256；只有模型自述的VLM状态无效；
- 图表的 `caption_claim`、正文实质性用图主张、源数据/上下文、转换过程和limitations双向可追溯；空limitations只表示未声明，不等于确认没有限制；
- Word中每个图号和表号只有一个可见题注，不存在图片内题注与Word题注重复；
- Word图片和图题不侵入页脚，与页码保持清晰间距，不形成“图题后多出页码”的视觉假重复；
- Word章、节、小节使用内置Heading 1/2/3及正确大纲级别，自动目录可更新且左侧导航窗格能够形成分层目录；
- 未提供学校模板时，A4、页边距、字体字号、行距、缩进、标题、题注、表格、参考文献和页码符合默认学术格式；
- 没有远程图片、临时路径、调试文字和模型自述；
- 文献、数字、图表、伦理和个人信息审计通过；
- 所有最终文件计算 SHA-256。
- 最终DOCX与PDF文件名均为“安全论文题目_YYYYMMDD-HHMMSS”，共用同一时间戳；`run-manifest.json`记录生成时间、时区、正式路径和SHA-256，不能把 `final-paper.docx/.pdf` 列为最终交付。
- `THESIS`文档的DOCX正文样式满足默认或学校模板的字号与行距，PDF中存在实际可见目录；`JOURNAL`、`REPORT`和`CUSTOM`按各自格式契约验收，不套用毕业论文目录门。
- `figures/figure-verification.json` 与 `13-delivery-verification.json` 已真实写入交付包；只在终端显示通过但未保存报告不算闭环。

存在Python能力时依次运行 `scripts/verify_figure_package.py` 与 `scripts/verify_manuscript_delivery.py`，分别把结果写入 `figures/figure-verification.json` 和 `13-delivery-verification.json`。前者检查能力与路由、DOCX图片/图题和PDF基础状态；后者统一统计正文、检查证据矩阵、正式文件名、路径、哈希、Word表格/目录和PDF。任一脚本失败时 `DELIVERY_STATUS=FAIL`，返回对应阶段修复后重新运行；脚本通过不证明学术结论正确，也不能替代视觉与学术判断。

```bash
python3 "<SKILL_DIR>/scripts/verify_figure_package.py" \
  --root "<OUTPUT_DIR>" \
  --report "figures/figure-verification.json"

python3 "<SKILL_DIR>/scripts/verify_manuscript_delivery.py" \
  --root "<OUTPUT_DIR>" \
  --target "<TARGET_LENGTH>" \
  --minimum "<MIN_LENGTH>" \
  --maximum "<MAX_LENGTH>" \
  --report "13-delivery-verification.json"
```

`FIGURES_ONLY` 且用户没有要求重新导出文档时，第一个命令增加 `--skip-documents`；`FULL_BUILD` 不得跳过文档检查。检查器默认从 `run-manifest.json` 读取正式DOCX/PDF路径，避免模型传入另一个临时文件规避验收。

把实际值和目标值写入 `12-final-qa-report.md` 与 `run-manifest.json`：正文长度及目标区间、文献数、图片数、表格数、DOCX/PDF状态、Critical/Important数量、能力缺口、`RESEARCH_STATUS`、`DELIVERY_STATUS`、`FINAL_STATUS`和两份验收报告路径。总状态只能为：

- `PASS`：所有用户硬目标和真实性边界均满足；
- `PARTIAL`：核心初稿可用，但存在明确能力、材料、模板、数量或格式缺口；
- `FAIL`：缺核心正文或必需终稿、正文不足目标下限、伪造文献/数据/结果、文件损坏、结构错乱或仍有Critical/Important问题。

用户明确字数目标时按用户目标及允许误差验收。直接题目自动完成且用户未指定字数时，默认目标25,000，可接受区间22,500—27,500；低于22,500不得标记 `PASS`。同理，文献、图片和表格低于用户明确下限时不得标记 `PASS`。不得承诺“保证通过”“绝对原创”或虚报检测结果。
