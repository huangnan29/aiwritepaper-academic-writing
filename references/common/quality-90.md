# 公共规则十一：具体审查与独立评分

90分是独立评测目标，不是作者必须填写的结果。当前方向专业检查卡用于找到真实问题；不因文件齐全、回执存在或模型自报高分宣布达标。

## 一份审查输入

在qa-review.json（schema_version:1.1）集中记录实际审查；模型先完成观察，工具prepare_audit_views.py只投影为旧格式并计算摘要。保留原始资料、检索日志、图片调用、视觉回执和最终文件，不用汇总替代证据。

- claims：重要主张的location、importance、evidence_ids、来源页/章节、反例与边界。CORE/CONCLUSION不得缺少证据指向。
- figures：每张figure_id、与权威清单相同的final_embed_file、status、blind_summary、checked_file和visual_receipt。遮住图题核对节点、边、数值与正文，实际文件和观察缺一不可。
- document_checks：checkpoint、正整数page、status、checked_file（最终PDF的实际页面图）、visual_receipt、发现问题。检查cover、primary_abstract、toc、complex_table、complex_formula、representative_figure、references、last_page等适用位置；确实无对应内容时写status:NOT_APPLICABLE及reason，不造图或公式。检查器从真实DOCX确认零公式/表格/媒体；只有明确JOURNAL或REPORT可免封面/目录，未知模板不自动豁免。
- review：reviewer_mode为SELF或ISOLATED，真实status、issues（critical_open、important_open、显式items），alignment四项：title_supported、research_question_answered、method_result_consistent、abstract_conclusion_consistent。每个问题写level、location、evidence、fix、status；未解决问题不能写成RESOLVED。

有真实隔离审稿时reviewer_source绑定实际审稿来源文件；不能只改ISOLATED字符串伪装独立性。scores和total仅在实际执行数字评分时填写，按证据25、内容20、结构15、配图15、文档15、自审10；无评分就省略，不默认给0或90。

统一检查入口会自动进行审计视图投影，无需另开一个生产步骤：
```bash
python3 "<SKILL_DIR>/scripts/paper.py" check --root "<OUTPUT_DIR>"
```

工具生成claim-evidence-map.json、figures/figure-semantic-audit.json、16-document-visual-audit.json、09-final-peer-review.json及兼容15-quality-scorecard.json；有能力JSON和权威图片JSON时派生其Markdown视图。没有实际观察或文件不一致时不能生成成功材料。关键文件和回执摘要由工具绑定；输入变化后旧审查失效，不自动续签。

## 判定与返修

Critical和Important必须处理；缺原始材料、缺视觉工具或无法完成修复时明确交付缺口，不能以提高评分逃避。纯语言比例、常用词密度作建议，真实性、数学和专业错误仍为实质问题。

SELF或未评分只说明已做自审，不是90分已验证，质量保持PARTIAL。有实际独立评分时仍须总分≥90、各维≥80%、无未解决重要问题、来源和检查覆盖有效，才可报告对应评测结果。每张图的节点/箭头和最终目录必须实际查看；工具绑定证据不证明审稿结论正确。
