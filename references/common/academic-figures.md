# 公共规则五：学术配图

<!-- compact-core:start -->
每图先写目的、正文位置、事实节点/边、逐字标签、禁止项和精确性。生图能力真实可用时，普通流程、架构、组织和概念图必须用IMAGE_GENERATION，并逐图给出详细Prompt；统计图用DATA_CODE；引脚、电路、化学结构和尺度图用DOMAIN_EXACT；真实影像用EVIDENCE_FILE。只有无生图工具、用户要求矢量或出版限制时才SVG_FALLBACK。成功生图及其中文覆盖PNG必须成为final_embed_file并实际进入Word/PDF，不能被同号SVG替换。
先从最终图复述关系再对照正文；流程检查正常与异常分支，核对年份、数值及端点。错图局部修复，不以回执或“示意图”免责。
<!-- compact-core:end -->

图中文字默认简体中文，保留型号、协议、单位和化学式；Prompt列exact_labels和allowed_foreign_tokens。文字失败用DETERMINISTIC_OVERLAY覆盖中文并保留构图，不整图改英文或改插纯SVG。

figures/figure-manifest.json是唯一图片清单。每图记录figure_id、display_number、title、figure_type、exactness_class、claim_bearing、imagegen_eligible、generation_route、route_exemption、source_locator/source_data、caption_claim、supported_manuscript_claims、limitations、language_contract、text_render_strategy、final_embed_file、generated_file、prompt_file、generation_receipt、vlm_verification。未使用字段为null，不编造。

route_exemption仅为USER_REQUESTED_VECTOR、PUBLICATION_RESTRICTION、IMAGE_TOOL_UNAVAILABLE、DOMAIN_EXACTNESS、EVIDENCE_REQUIRED或null。generation_receipt绑定真实工具结果、时间、Prompt与生成文件摘要；模型自述只能DECLARED_ONLY。vlm_verification绑定实际查看文件与回执，不以生成成功代替审图。

不采信生成者通过说明；查悬空、重复、反向、错误汇合，领域图对照源表。覆盖后复看合成图与文稿，观察写回qa-observations。

图内不写外部图号或整段题注。两轮无效修复后记NEEDS_REVIEW及缺陷，不删必要边过检。缺视觉能力记CAPABILITY_GAP；高质量图仅局部修复。
