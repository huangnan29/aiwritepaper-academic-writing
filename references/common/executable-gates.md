# 公共规则六：可执行生产门禁

文字声明不能替代实际工具调用。涉及完整生产、导出或验收时，按以下顺序运行 Skill 自带脚本，并保存机器可读结果。

## 1. 能力探测

在创建研究结果或最终文件前运行 `scripts/probe_capabilities.py`。`00-capability-report.md` 必须由探测结果生成或逐项引用其证据。客户端内置图片工具无法从本地探测时保持 `UNVERIFIED`，只有实际调用并保存产物后才能升级状态。

## 2. 证据门

出现性能、准确率、实验、问卷、病例、用户量或系统运行结果时，先读取 `references/evidence-manifest.md`。真实系统命令必须通过 `scripts/run_evidence.py` 执行并生成日志与 `execution_record`；不得在清单中手写一个从未运行的命令。随后创建 `evidence-manifest.json` 并运行 `scripts/validate_evidence.py`。证据等级必须明确区分真实系统观测、模拟、合成数据、硬编码示例、外部核验和计划。模拟、合成或硬编码结果只能用于方法演示，不得进入摘要、结果或结论并表述为实测。

## 3. 全文整合与导出

`FULL_BUILD` 和 `EXPORT_ONLY` 使用 `scripts/assemble_and_export.py --mode FULL_BUILD|EXPORT_ONLY` 按确定顺序整合章节。`FULL_BUILD` 或 `EXPORT_ONLY` 跳过 DOCX/PDF 时只能返回 `PARTIAL`，不能返回 `PASS`。`07-paper-full.md` 必须包含正文内容，不能用“详见分章文件”、文件链接或占位段落代替。只有脚本真实生成并验证非空后，才能记录 DOCX/PDF 已完成；缺少导出工具时标记 `CAPABILITY_GAP` 或 `PARTIAL`。

## 4. 最终交付验收

所有写作、图表、整合和导出完成后，先运行 `scripts/validate_delivery.py --mode FULL_BUILD --phase preqa` 计算预验收状态。随后把该状态写入 `run-manifest.json` 与 `12-final-qa-report.md`，确保 QA 晚于全部被验收产物，再运行 `scripts/validate_delivery.py --mode AUDIT_ONLY --phase final`。终验收要求 manifest 与 QA 声明严格等于脚本计算状态。`run-manifest.json` 必须记录 `run_mode: FULL_BUILD`；任何一次验收返回 `FAIL` 时不得改写为 `PASS`。

## 顺序约束

阶段顺序固定为：`PROBE → RESEARCH → DRAFT → EVIDENCE → FIGURES → ASSEMBLE → EXPORT → VALIDATE → QA`。QA 文件必须晚于所有被验收产物。任何阶段修改正文、图或最终文件后，后续整合、导出和验收全部失效，必须重新运行。
