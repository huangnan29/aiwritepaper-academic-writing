# AIWritePaper Agentic Skill

这是一个遵循 [agentskills.io](https://agentskills.io/) 规范的中文论文生产Skill。`0.4.x`采用MD-first结构：先根据题目选择一个方向，再让模型完整读取一份独立提示词并持续执行，不再由Skill内Python脚本控制论文流程。

## 为什么重构

旧版本把运行规则拆分到大量公共引用、配图子Skill和Python验收器中。不同Agent对递归加载和长任务状态保持能力不同，容易出现脚本通过但正文、文献、图表或字数明显不足的情况。

`0.4.x`的原则：

- `SKILL.md`只负责请求判断和方向选择；
- 19个 `references/compiled-prompts/*-full.md` 都是完整、自包含的最终提示词；
- 正式执行前把本次参数与所选完整提示词写入 `final-execution-prompt.md`；
- 后续只按照这一份MD执行；
- 不再调用Skill内预置Python流水线；
- 最终状态由模型对照用户目标和真实产物判断。

直接给出题目触发 `FULL_BUILD` 且没有指定字数时，默认正文目标为25,000字，允许误差±10%，低于22,500不能标记 `PASS`。

## 保留的论文能力

- 19个论文方向；
- 没有题目时推荐10个可行题目；
- 能力检查、研究契约、文献检索、证据矩阵、详细大纲和论证地图；
- 按章写作、累计字数检查和弱模型持续完成机制；
- 全文整合、引用审计、同行评审和修订；
- DOCX、PDF、格式检查、QA和运行清单；
- `FULL_BUILD`、`FIGURES_ONLY`、`EXPORT_ONLY`、`AUDIT_ONLY`、`ROUTE_ONLY`。

## 配图规则

- Agent具备图片生成能力时，流程、架构、框架、组织、ER/UML、机制、装置和场景类图逐张调用图片工具；
- Codex优先使用 `imagegen`/`image_gen`，Grok使用Imagine，Gemini使用Nano Banana或当前实际图片工具；
- 精确流程图先从上下文提取节点总数、逐字标签、箭头起止、分支、层级和禁止项，再保存独立详细Prompt并生成图片；
- 生成图片存在局部文字或箭头问题时先编辑图片，必要时增加确定性覆盖层；
- 数据统计图读取真实数据，通过Python、R或等价代码生成；
- 原始科研影像使用原文件，公式、化学、电路和地图使用领域工具；
- 没有图片生成能力时才降级SVG；中文SVG使用明确的跨平台中文字体栈，并在PNG、DOCX和PDF中检查。
- SVG降级图还要检查连接线整齐度、非必要交叉、穿越、转折、箭头和连接点位置。
- Imagine或其他图片工具成功生成后，正文、Word和PDF必须插入该位图或以其为底图合成的最终PNG；同名SVG只能作为备用源。每张图通过 `final_embed_file` 指定唯一最终插图，导出程序不得重新选择SVG。

未提供学校模板时使用通用学术格式：A4、中文正文12pt、1.5倍行距、首行缩进2字符、分级Heading样式、图题在下、表题在上、可编辑表格和可更新目录。Word中每个图号只保留一个可见题注，章、节、小节使用Heading 1/2/3与正确大纲级别，以支持左侧导航窗格。

## 目录结构

```text
aiwritepaper-agentic-skill/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── compiled-prompts/    # 运行时只读取其中一个完整提示词
│   ├── directions/          # 19个方向增量源，供维护
│   ├── common/              # 通用规则源，供维护
│   └── deliverables/        # 开题与答辩附加要求
├── install.sh
└── install.ps1
```

正式论文执行阶段不得继续加载 `common/` 或 `directions/`。它们只用于维护已经预合成的完整提示词。

## 快速安装

通用Agent Skills环境：

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill
```

Codex全局安装：

```bash
./install.sh --agent codex --scope user
```

Grok Build全局安装：

```bash
./install.sh --agent grok --scope user
```

WorkBuddy全局安装：

```bash
./install.sh --agent workbuddy --scope user
```

Antigravity全局安装：

```bash
./install.sh --agent antigravity --scope user
```

Windows PowerShell：

```powershell
.\install.ps1 -Agent codex -Scope user
.\install.ps1 -Agent grok -Scope user
.\install.ps1 -Agent workbuddy -Scope user
.\install.ps1 -Agent antigravity -Scope user
```

## 安装路径

| agent | 项目级 | 用户级 |
|---|---|---|
| Claude | `.claude/skills/aiwritepaper-agentic-skill` | `~/.claude/skills/aiwritepaper-agentic-skill` |
| Codex | `.codex/skills/aiwritepaper-agentic-skill` | `~/.codex/skills/aiwritepaper-agentic-skill` |
| Cursor | `.cursor/skills/aiwritepaper-agentic-skill` | `~/.cursor/skills/aiwritepaper-agentic-skill` |
| Gemini | `.gemini/skills/aiwritepaper-agentic-skill` | `~/.gemini/skills/aiwritepaper-agentic-skill` |
| Antigravity | `.agents/skills/aiwritepaper-agentic-skill` | `~/.gemini/config/skills/aiwritepaper-agentic-skill` |
| Grok Build | `.grok/skills/aiwritepaper-agentic-skill` | `~/.grok/skills/aiwritepaper-agentic-skill` |
| Copilot | `.github/skills/aiwritepaper-agentic-skill` | `~/.copilot/skills/aiwritepaper-agentic-skill` |
| OpenCode | `.opencode/skills/aiwritepaper-agentic-skill` | `~/.config/opencode/skills/aiwritepaper-agentic-skill` |
| WorkBuddy | `.workbuddy/skills/aiwritepaper-agentic-skill` | `~/.workbuddy/skills/aiwritepaper-agentic-skill` |
| 通用 | `.agents/skills/aiwritepaper-agentic-skill` | `~/.agents/skills/aiwritepaper-agentic-skill` |

默认情况下目标目录已存在时安装器拒绝覆盖。确认更新已有版本时追加 `--force` 或 `-Force`。

## 使用方式

提供题目、输出目录和目标参数，然后要求调用Skill执行。例如：

```text
使用 $aiwritepaper-agentic-skill 完成论文生产。
题目：基于SpringBoot的助农服务平台系统设计与实现
运行模式：FULL_BUILD
目标正文：28000
最低文献：30
目标图片：10-14
目标表格：8-12
不要停留在计划阶段，持续执行到DOCX、PDF和最终QA。
```

Skill会先选择一个 `*-full.md`，再在输出目录创建 `final-execution-prompt.md`。已有题目时不需要再次确认方向。

## 维护边界

更新公共规则或方向增量时，需要重新生成19份完整提示词并逐份检查。合并过程只能做机械拼接，不能决定章节、内容、证据或最终状态。维护工具不随运行版Skill分发；当前历史版本可以通过Git标签 `v0.3.1-runtime-gates` 恢复。

## License

MIT License。参见 [LICENSE](LICENSE)。
