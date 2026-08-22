# 公共规则七：审计与最终验收

全文整合后检查标题编号、摘要一致性、方法与技术栈、术语、数字来源、图表引用、引文匹配、参考文献覆盖、重复章节、个人信息和未来计划误写为结果。

同行评审按 Critical、Important、Minor 分级。Critical 和 Important 必须修复并在 `10-revision-log.md` 记录修改位置、内容、验证和状态。

最终必须先运行 `scripts/validate_delivery.py --phase preqa`，写入相同状态的 manifest 与 QA 后再运行 `--phase final`，并验证：

- 要求文件存在且非空；
- DOCX 可解包和解析；
- PDF 可解析、页数大于零且无异常空白页；
- 标题、摘要、各章、参考文献和致谢均存在；
- 实际字数、图、表和文献达到合同要求；
- 图表不裁切、不越界，表格宽度合理；
- 含中文的 SVG 已通过字体静态门，且 PNG、DOCX、PDF 未出现字体替换、方框、乱码、缺字或因字宽变化导致的溢出；
- `figures/figure-manifest.json` 已声明 `image_generation_policy`；当前客户端暴露图片工具且未获明确豁免时，所有 `eligible_figure_ids` 都被 `prompt_by_figure` 和 `generated_by_figure` 逐项覆盖，独立详细 Prompt 文件与真实 image-gen 生成的 PNG/JPEG/WebP 均存在且非空，图号、工具、提示词、路径、限制和人工核对记录一一对应；任一适合生图的流程、架构或框架图只交付 SVG，或用截图冒充生成式图片，均为 `FAIL`；
- 没有远程图片、临时路径、调试文字和模型自述；
- 文献、数字、图表、伦理和个人信息审计通过；
- 所有最终文件计算 SHA-256。

状态只能为 `PASS`、`PARTIAL` 或 `FAIL`，以验收器输出为准。缺少必要工具或材料为 `PARTIAL`；缺少 `FULL_BUILD` 必需终稿、manifest 与文件矛盾、伪造文献或结果、损坏文件、未关闭 Critical/Important 为 `FAIL`。不得承诺“保证通过”“绝对原创”或虚报检测结果。模型不得在验收器之后手工提升状态。
