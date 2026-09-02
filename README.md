<div align="center">

# AIWritePaper｜AI自动学术写作

从题目和真实材料出发，完成方向路由、文献、正文、学术配图、DOCX/PDF与可核验交付。

![版本](https://img.shields.io/badge/version-2.1.0--rc.1-DB2777)
![架构](https://img.shields.io/badge/architecture-MD--first-7C3AED)
![方向](https://img.shields.io/badge/directions-19-16A34A)
![弱模型预算](https://img.shields.io/badge/compact-%E2%89%A415KB-0284C7)

</div>

> `2.1.0-rc.1` 是候选版本。工程回归通过不等于论文稳定达到90分；正式版仍需完成同题、同材料、同客户端的跨Agent盲评A/B。

## 一句话使用

```text
使用 aiwritepaper-academic-writing 完成《论文题目》。只使用真实可核材料；完成正文、配图、DOCX、PDF和实际验收，不要停在计划。
```

已有题目默认持续执行。用户未给字数时，中文THESIS且层次未知默认正文25,000；用户或学校模板优先。没有题目时先推荐10个可行题目。

单独改图：

```text
使用 aiwritepaper-academic-writing 的 FIGURES_ONLY 模式优化当前论文配图，保留正文主张；如需重新导出Word/PDF一并完成。
```

## 2.1做了什么

这一版解决的不是“再加规则”，而是上一轮审查指出的四个结构问题：

- 写作流程不再给自己打分，也不能用`SELF/ISOLATED`字符串制造独立评审。
- 19个方向全部扩充专业方法、证据边界、常见错误和主张条件；构建门要求方向内容占最终专业提示词至少30%。
- Full与Compact由同一源的CORE/扩展段生成；19方向弱模型最终输入按保守参数估算均不超过15KB。
- 准备入口采用方向默认模块，能力允许true/false/null；漏模块可安全amend，不覆盖旧提示词。

三类高风险图表增加源表合同：

- 电子电路：`connection-table.csv`绑定器件、引脚、网络、电压域与数据手册来源。
- 数学教育：`concept-edge-table.csv`绑定理论概念、关系和箭头方向。
- 文献综述：`screening-audit.csv`区分发现、全文、纳入和引用集合，并保留分类抽查。

## 核心架构

```text
题目、材料与真实能力
        ↓
模型一次判断：方向、方法、模式、必要覆盖
        ↓
paper.py prepare：确定性合成唯一执行MD
        ↓
模型完成研究、正文、图表与文档
        ↓
paper.py check：证据 / 图片 / 公式 / 交付四类机械检查
        ↓
定点修复并重新检查 → 冻结交付包
        ═════════ 写作与评分边界 ═════════
        ↓
另一会话、另一模型或人工独立评分
```

脚本只做重复且可机械验证的工作，不选择研究方法、不生成正文、不判断专业结论。数字评分位于`eval/`，不会进入最终执行提示词，也不会影响权威交付状态。

## 快速准备

模型根据[准备说明](references/preparation.md)创建paper-request.json。方向已有默认features，通常无需列出全部模块。能力为四项三态：

```json
{
  "schema_version": "1.0",
  "paper_title": "你的题目",
  "direction_id": "software-system-engineering",
  "model_label": "实际模型 @ 实际客户端",
  "agent_adapter": "universal-terminal",
  "run_mode": "FULL_BUILD",
  "capabilities": {
    "image_generation": null,
    "visual_inspection": true,
    "docx_export": true,
    "pdf_export": true
  },
  "constraints": "只使用用户材料与实际核验来源。"
}
```

`null`表示尚未确认，不是“没有能力”。若图片工具可用，建议在`capability_details`补充真实tool与caller。

```bash
uv run python scripts/paper.py prepare --root /path/to/paper --request paper-request.json
```

准备只生成任务契约、能力记录和唯一执行MD，不生成论文，也不写PASS。

## 安全amend

执行后发现确需增加统计、公式、SVG或文档模块：

```bash
uv run python scripts/paper.py prepare --amend --root /path/to/paper --request prompt-amendment.json
```

amend生成`final-execution-prompt.v2.md`等版本化文件，原提示词保持不变。已有产物的模块不能移除；正文开始后受影响阶段自动标记失效。题目降级受STRICT、ASK、SAFE_DOWNGRADE三种策略约束。

## 图片、公式与文档

| 类型 | 首选路线 |
|---|---|
| 普通流程、架构、组织、概念图 | 当前或父层有生图能力时必须IMAGE_GENERATION |
| 数据统计图 | 真实数据＋可复算代码 |
| 电路、引脚、化学结构、尺度图 | 领域工具或可核对的确定性骨架 |
| 真实科研影像 | 原始证据文件 |
| SVG | 无生图工具、用户/出版矢量要求或DOMAIN_EXACT骨架 |

成功生图或其中文覆盖PNG必须成为`final_embed_file`并实际进入DOCX/PDF；同号SVG只能备用。中文论文图中文字默认中文，型号、协议、单位和公式可保留。

Markdown公式统一使用`$...$`与`$$...$$`；DOCX使用可编辑OMML，PDF不得显示TeX源码。Word默认具有真实Heading导航、有效目录、唯一题注和零表格单元格首行缩进。DOCX/PDF按“安全题目_YYYYMMDD-HHMMSS”共用时间戳。

## 统一检查

完成逐图和页面实际观察后，按[观察模板](references/qa-observations.example.json)记录具体问题与回执：

```bash
uv run python scripts/paper.py check --root /path/to/paper \
  --docx "论文题目_YYYYMMDD-HHMMSS.docx" \
  --pdf "论文题目_YYYYMMDD-HHMMSS.pdf"
```

底层只有四类权威机械检查：

1. 文献、引用、全文定位和数据来源；
2. 图片路线、回执、语言、源表与实际嵌图；
3. 公式源、OMML与PDF残留；
4. 正文长度、目录、题注、表格和DOCX/PDF。

最终状态读取`14-adjudicated-status.json`。机械PASS不代表专业正确；缺视觉能力、真实数据或独立审阅时会如实出现PARTIAL/待评审。

## 独立评测

写作结束后冻结评审包：

```bash
uv run python eval/build_review_package.py \
  --root /path/to/paper \
  --output /path/to/evaluation/review-package.json
```

再由独立会话、另一模型或人工盲评。写作进程不会创建数字评分，也不会用评分覆盖机械失败。历史评分器与57任务矩阵仅作为维护资料，不代表已经跑完。

## 历史Agent观察

既有批次的题目、版本和审查严格度不同，不能作为绝对模型排行榜。相对稳定的现象是：Grok Build/Grok 4.6通常具有较高完整度和较好的原生生图执行；Kimi正文配合WorkBuddy K3完成最终Word的历史样本完成度较高，但必须标记为模型接力，不能并成单一K3成绩；Gemini 3.7 Flash/Antigravity曾出现内容、排版、SVG和证据可靠性问题；MiniMax M3/Claude Code历史批次还出现过内容、引用和Word结构严重缺失。Z.ai与DeepSeek-tui有过较好单篇结果，但样本量不足。

2.1.0-rc.1针对这些共性失败增加Compact预算、三态能力、默认模块、专业源表和四类硬检查；尚未用新版本完成同题复测，因此README不宣称任何Agent已经提升。

## 模式

支持FULL_BUILD、RESUME、REVISE_ONLY、FIGURES_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY、DEFENSE_ONLY和ROUTE_ONLY。AUDIT_ONLY必须输出到原稿目录外；RESUME读取活动版本提示词；REVISE_ONLY保留原稿并另存。

## 安装

```bash
git clone https://github.com/huangnan29/aiwritepaper-academic-writing.git
cd aiwritepaper-academic-writing
./install.sh --agent codex --scope user
```

支持codex、claude、cursor、kimi、gemini、antigravity、copilot、opencode、workbuddy、grok、zcode/zai、deepseek/deepseek-tui和universal。覆盖更新使用`--force`；Windows使用`install.ps1 -Force`。

| Agent | 用户级目录 |
|---|---|
| Codex | `~/.codex/skills` |
| Claude Code | `~/.claude/skills` |
| Cursor | `~/.cursor/skills` |
| Kimi Code | `~/.kimi-code/skills` |
| Gemini CLI | `~/.gemini/skills` |
| Antigravity | `~/.gemini/config/skills` |
| Grok Build | `~/.grok/skills` |
| WorkBuddy | `~/.workbuddy/skills` |
| Z.ai / ZCode | `~/.zcode/skills` |
| DeepSeek-tui | `~/.codewhale/skills` |

## 维护与候选限制

当前版本：`2.1.0-rc.1`。

```bash
uv run python scripts/build_compiled.py
uv run python scripts/verify_compiled.py
uv run python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_render_svg_layout.mjs
```

只有跨Agent真实论文A/B达到[实施计划](implementation_plan.md)的非劣与零伪造门槛，才会把RC升级为正式2.1.0并覆盖稳定安装。详细历史见[CHANGELOG](CHANGELOG.md)。
