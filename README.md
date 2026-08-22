# AIWritePaper Agentic Skill

这是一个面向 AIWritePaper 论文生产准备流程的 Agent Skill。它遵循 [agentskills.io](https://agentskills.io/) 的开放 `SKILL.md` 规范，可供支持 Agent Skills 的编码助手按需发现和调用。

仓库根目录的 `SKILL.md` 是核心入口，`references/` 和 `scripts/` 是配套的完整内容。`agents/openai.yaml` 仅是 OpenAI/Codex 的可选 UI 元数据，其他 agent 可以忽略它，不影响安装和使用。

## 核心能力

- 覆盖 19 个论文方向提示词，并根据题目、研究动作和证据形式只加载一个匹配方向。
- 强制执行研究契约、文献核验、证据矩阵、真实性边界和最终质量门。
- 没有真实数据、源码、实验、问卷、访谈、病例或日志时，自动降级为方案、协议或综述，不生成虚构结果。
- 在图表生产前区分语言模型、SVG 渲染器和专用图片生成工具，不把“能写 SVG”误判为“能生成图片”。
- 按图类路由流程图、架构图、ER 图、UML、统计图、科研原始图像与生成式机制示意。

## 0.3.0 可执行门禁

`0.3.0` 将关键质量要求从文字提示升级为确定性脚本：

| 脚本 | 作用 |
| --- | --- |
| `scripts/probe_capabilities.py` | 实际探测文件、代码、渲染、DOCX、PDF 和检查工具，不能由模型凭空声明能力 |
| `scripts/run_evidence.py` | 以 `shell=False` 运行真实证据命令，保存受限日志、时间、返回码和 SHA-256 执行记录 |
| `scripts/validate_evidence.py` | 校验真实系统观测、模拟、合成数据、硬编码示例、外部核验和计划之间的证据等级 |
| `scripts/assemble_and_export.py` | 按确定顺序合并章节，并在工具可用时生成 DOCX/PDF |
| `scripts/validate_delivery.py` | 核对必需文件、manifest、全文整合、DOCX/PDF、图形、体量和 QA 时间顺序，并计算最终状态 |

典型 `FULL_BUILD` 调用顺序：

```bash
uv run python /path/to/skill/scripts/probe_capabilities.py \
  --root /path/to/paper --json --output /path/to/paper/00-capability-report.json

uv run python /path/to/skill/scripts/run_evidence.py \
  --root /path/to/paper --id EXP-01 --claim "真实系统测试主张" \
  --output-log evidence/exp-01.log \
  --record-output evidence/exp-01-execution.json \
  -- python tests/run_real_experiment.py

uv run python /path/to/skill/scripts/validate_evidence.py \
  --root /path/to/paper --json

uv run python /path/to/skill/scripts/assemble_and_export.py \
  --root /path/to/paper --mode FULL_BUILD --json

uv run python /path/to/skill/scripts/validate_delivery.py \
  --root /path/to/paper --mode FULL_BUILD --phase preqa --json \
  --output /path/to/paper/delivery-validation.json

# 将预验收状态写入 run-manifest.json 与 12-final-qa-report.md 后执行终验收
uv run python /path/to/skill/scripts/validate_delivery.py \
  --root /path/to/paper --mode AUDIT_ONLY --phase final --json \
  --output /path/to/paper/delivery-validation.json
```

完整论文生产阶段固定为：

```text
PROBE → RESEARCH → DRAFT → EVIDENCE → FIGURES → ASSEMBLE → EXPORT → VALIDATE → QA
```

模型不能自行把状态写成 `PASS`。`FULL_BUILD` 缺少 DOCX/PDF、全文仍是分章链接、manifest 与文件不一致、QA 早于被验收文件或证据清单失败时，最终状态必须由验收脚本降级。

支持五种运行模式：

- `ROUTE_ONLY`：只做选题和方向路由；
- `FULL_BUILD`：完整研究、写作、配图、导出和验收；
- `FIGURES_ONLY`：只优化配图；
- `EXPORT_ONLY`：只从现有定稿导出 DOCX/PDF；
- `AUDIT_ONLY`：只读核验现有产物。

## 学术配图能力

根 Skill 已内置统一的学术配图规则：

- `references/common/academic-figures.md`：证据边界、图类路由和通用质量门；
- `references/figure-skills/academic-figure-routing.md`：生成式学术插画的事实契约与禁止项；
- `references/figure-skills/academic-svg-quality.md`：流程图、架构图、ER 图、UML 和研究框架的确定性 SVG 规则。

仓库还提供两个可独立安装的配套 Skill：

- `skills/academic-figure-router/`：判断应使用图片模型、SVG、数据绘图、领域工具还是原始科研图像；
- `skills/academic-svg-enhancer/`：设计、重绘和验收出版级 SVG，并附带 `scripts/audit_svg.py` 静态审计器。

关键边界：具备图片生成能力的 Agent 对流程、架构、框架、组织、ER/UML、机制、装置和场景类图逐张调用图片工具，并用详细 Prompt 与逐项验收保证准确；数据统计图从真实数据用代码生成。原始科研影像和公式、化学、电路、地图等领域图不交给图片模型猜测。生成式图片不得冒充显微图、医学影像、实验照片或统计结果。

### 中文 SVG 字体门

`0.3.1` 会把含中文但没有 `font-family`、或只声明 `Helvetica`、`Arial`、`Times New Roman` 等拉丁字体的 SVG 判为失败。可编辑 SVG 应声明跨平台中文回退栈，并使用最终导出所用的同一渲染器检查“中文字体测试 0123 Aa”探针。PNG、DOCX 和 PDF 必须分别抽查，不能以浏览器预览正常代替最终文档验收。需要跨环境保持绝对一致时，可额外交付文字转路径版本，但必须保留可编辑源并确认字体许可。

### image-gen 强制调用门

在 `FULL_BUILD` 或 `FIGURES_ONLY` 中，只要当前客户端暴露内置图片生成工具，所有非数据统计、非原始科研影像、非公式/化学/电路/地图领域图都必须逐张真实调用图片工具生成，并把详细 Prompt、工具、产物路径和人工核对结果写入 `figures/figure-manifest.json`。Codex 环境优先调用内置 `imagegen`/`image_gen`。精确流程图、架构图、研究框架、组织图、ER/UML 等也先从上下文提取完整节点、连线、方向、层级和中文标签，形成逐项可核对的生图 Prompt，再生成精美位图；SVG 只能用于无图片能力环境或生成图后的局部文字/箭头修正，不能替代真实调用。数据统计图必须从真实数据用 Python、R 等代码生成。只有用户明确退出或目标期刊明确禁止 AI 图片时才能豁免。

## 快速安装

### 通用安装

适用于支持 Agent Skills 的环境：

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill
```

### Antigravity 全局安装

Antigravity 在所有项目中共享的 Skill 目录为 `~/.gemini/config/skills/`。首次安装：

```bash
mkdir -p ~/.gemini/config/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.gemini/config/skills/aiwritepaper-agentic-skill
```

安装后重新扫描 Skills 或新建会话。实际入口应为：

```text
~/.gemini/config/skills/aiwritepaper-agentic-skill/SKILL.md
```

更新已有全局安装：

```bash
git -C ~/.gemini/config/skills/aiwritepaper-agentic-skill pull --ff-only
```

如果只需要独立配图能力，可将仓库中的 `skills/academic-figure-router/` 和 `skills/academic-svg-enhancer/` 分别复制到 `~/.gemini/config/skills/`，保持各自目录下的 `SKILL.md`、`references/`、`scripts/` 和 `tests/` 完整。

### WorkBuddy 全局安装

WorkBuddy 在所有项目中共享的 Skill 目录为 `~/.workbuddy/skills/`。首次安装：

```bash
mkdir -p ~/.workbuddy/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.workbuddy/skills/aiwritepaper-agentic-skill
```

Windows PowerShell 5.1：

```powershell
$WorkBuddySkills = Join-Path $HOME '.workbuddy\skills'
New-Item -ItemType Directory -Path $WorkBuddySkills -Force | Out-Null
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git (Join-Path $WorkBuddySkills 'aiwritepaper-agentic-skill')
```

安装后请重启 WorkBuddy，或在设置中重新扫描 Skills。扫描完成后，在“我安装的”中应能看到根 Skill `aiwritepaper-agentic-skill`，以及仓库内的两个嵌套配图 Skill：`academic-figure-router` 和 `academic-svg-enhancer`。请保持仓库的完整目录层级，不要只复制根目录下的 `SKILL.md`。

### 指定 agent 的全局安装

下面的 `--global` 表示用户级安装，对该用户的多个项目生效：

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill --agent codex --global
npx skills add huangnan29/aiwritepaper-agentic-skill --agent claude-code --global
npx skills add huangnan29/aiwritepaper-agentic-skill --agent cursor --global
npx skills add huangnan29/aiwritepaper-agentic-skill --agent gemini-cli --global
npx skills add huangnan29/aiwritepaper-agentic-skill --agent github-copilot --global
npx skills add huangnan29/aiwritepaper-agentic-skill --agent opencode --global
```

### Gemini CLI 原生命令

Gemini CLI 默认安装到用户级目录；项目级安装使用它自己的 `workspace` 术语：

```bash
gemini skills install https://github.com/huangnan29/aiwritepaper-agentic-skill.git
gemini skills install https://github.com/huangnan29/aiwritepaper-agentic-skill.git --scope workspace
```

### GitHub Copilot CLI 原生命令

Copilot CLI 默认安装到用户级目录；项目级安装使用 `--scope project`：

```bash
copilot plugins install --skill https://github.com/huangnan29/aiwritepaper-agentic-skill.git
copilot plugins install --skill --scope project https://github.com/huangnan29/aiwritepaper-agentic-skill.git
```

交互式 Copilot CLI 也可以使用：

```text
/plugins install --skill https://github.com/huangnan29/aiwritepaper-agentic-skill.git
/plugins install --skill --project https://github.com/huangnan29/aiwritepaper-agentic-skill.git
```

## 本地安装器

安装器支持以下 agent 参数：`codex`、`claude`、`cursor`、`gemini`、`antigravity`、`copilot`、`opencode`、`workbuddy`、`universal`。

`user` 是用户级安装，`project` 是当前工作目录下的项目级安装。执行 `project` 安装时，请先切换到项目根目录。默认情况下，目标目录已存在就会拒绝覆盖；确认要替换已有版本时才使用 `force`。

macOS、Linux 或其他 POSIX shell：

```bash
# 项目级通用安装到 .agents/skills/aiwritepaper-agentic-skill
./install.sh --agent universal --scope project

# 用户级 Codex 安装
./install.sh --agent codex --scope user

# 全局安装到 Antigravity 的 ~/.gemini/config/skills
./install.sh --agent antigravity --scope user

# 全局安装到 WorkBuddy 的 ~/.workbuddy/skills
./install.sh --agent workbuddy --scope user

# 强制更新项目级 Copilot 安装
./install.sh --agent copilot --scope project --force
```

Windows PowerShell 5.1：

```powershell
# 项目级通用安装到 .agents\skills\aiwritepaper-agentic-skill
.\install.ps1 -Agent universal -Scope project

# 用户级 Codex 安装
.\install.ps1 -Agent codex -Scope user

# 全局安装到 Antigravity 的 .gemini\config\skills
.\install.ps1 -Agent antigravity -Scope user

# 全局安装到 WorkBuddy 的 .workbuddy\skills
.\install.ps1 -Agent workbuddy -Scope user

# 强制更新项目级 Copilot 安装
.\install.ps1 -Agent copilot -Scope project -Force
```

两个安装器都会从固定来源
`https://github.com/huangnan29/aiwritepaper-agentic-skill.git`
克隆到临时目录，再复制完整的 `aiwritepaper-agentic-skill` 目录。它们不会执行远程脚本，也不会只复制 `SKILL.md`。安装后的目录始终保留完整目录名 `aiwritepaper-agentic-skill`，不会把文件散落在 `.agents` 或其他 skills 根目录中。

### 安装路径

| agent 参数 | 项目级路径 | 用户级路径 |
| --- | --- | --- |
| `claude` | `.claude/skills/aiwritepaper-agentic-skill` | `~/.claude/skills/aiwritepaper-agentic-skill` |
| `codex` | `.codex/skills/aiwritepaper-agentic-skill` | `~/.codex/skills/aiwritepaper-agentic-skill` |
| `cursor` | `.cursor/skills/aiwritepaper-agentic-skill` | `~/.cursor/skills/aiwritepaper-agentic-skill` |
| `gemini` | `.gemini/skills/aiwritepaper-agentic-skill` | `~/.gemini/skills/aiwritepaper-agentic-skill` |
| `antigravity` | `.agents/skills/aiwritepaper-agentic-skill` | `~/.gemini/config/skills/aiwritepaper-agentic-skill` |
| `copilot` | `.github/skills/aiwritepaper-agentic-skill` | `~/.copilot/skills/aiwritepaper-agentic-skill` |
| `opencode` | `.opencode/skills/aiwritepaper-agentic-skill` | `~/.config/opencode/skills/aiwritepaper-agentic-skill` |
| `workbuddy` | `.workbuddy/skills/aiwritepaper-agentic-skill` | `~/.workbuddy/skills/aiwritepaper-agentic-skill` |
| `universal` | `.agents/skills/aiwritepaper-agentic-skill` | `~/.agents/skills/aiwritepaper-agentic-skill` |

### 手动 git clone 安装

以下命令只复制完整目录，不要把仓库内容直接克隆到 `.agents`、`.claude` 或其他 skills 根目录。

项目级安装，在项目根目录执行并选择一个目标路径：

```bash
mkdir -p .claude/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .claude/skills/aiwritepaper-agentic-skill

mkdir -p .codex/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .codex/skills/aiwritepaper-agentic-skill

mkdir -p .cursor/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .cursor/skills/aiwritepaper-agentic-skill

mkdir -p .opencode/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .opencode/skills/aiwritepaper-agentic-skill

mkdir -p .workbuddy/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .workbuddy/skills/aiwritepaper-agentic-skill

mkdir -p .agents/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .agents/skills/aiwritepaper-agentic-skill
```

用户级安装时，把上面命令中的目标路径分别替换为以下路径：

```text
~/.claude/skills/aiwritepaper-agentic-skill
~/.codex/skills/aiwritepaper-agentic-skill
~/.cursor/skills/aiwritepaper-agentic-skill
~/.config/opencode/skills/aiwritepaper-agentic-skill
~/.workbuddy/skills/aiwritepaper-agentic-skill
~/.agents/skills/aiwritepaper-agentic-skill
```

例如 Codex 用户级安装：

```bash
mkdir -p "$HOME/.codex/skills"
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git "$HOME/.codex/skills/aiwritepaper-agentic-skill"
```

## 项目级与用户级

- 项目级只对当前项目生效，适合把 Skill 与项目配置一起提交或固定版本。
- 用户级对该用户的多个项目生效，适合个人常用工作流；它可能被项目级同名 Skill 覆盖，具体优先级由 agent 决定。
- `universal` 使用 `.agents/skills/` 或 `~/.agents/skills/`，适合遵循开放规范的通用 agent。若某个 agent 有明确的专用目录，优先使用对应的 agent 参数。
- `antigravity` 的用户级安装使用 Antigravity 桌面端当前的全局目录 `~/.gemini/config/skills/`；项目级安装使用 `.agents/skills/`。
- 安装器的 `--scope project` 和 `-Scope project` 指当前目录；Gemini 原生命令使用 `--scope workspace`，这是两个 CLI 的参数名称差异，含义都是项目级。

## 安全审查

安装前请审阅 `SKILL.md`、`references/`、`scripts/` 及其依赖。Skill 可能在被 agent 激活时读取文件、访问网络或执行配套脚本，应只从可信来源安装，并避免在敏感项目中无审查启用。

本仓库的两个本地安装器只会克隆固定仓库并复制完整目录，不执行远程脚本。使用 `npx`、Gemini CLI 或 Copilot CLI 的原生命令时，仍应遵循对应 CLI 的确认和信任提示。

## 更新

更新前先审阅远程变更。使用本地安装器时，在同一 agent 和 scope 下追加 `--force` 或 `-Force`：

```bash
./install.sh --agent codex --scope user --force
```

```powershell
.\install.ps1 -Agent codex -Scope user -Force
```

通用 CLI、Gemini CLI 和 Copilot CLI 请使用其对应的更新命令，或按其文档重新执行安装命令；如果目标目录由本地安装器管理，重复安装时必须明确使用 force 覆盖。

## 卸载

只删除对应的完整 Skill 目录，不要删除整个 `.agents`、`.codex` 或其他 agent 配置目录。例如：

```bash
rm -rf .agents/skills/aiwritepaper-agentic-skill
rm -rf "$HOME/.codex/skills/aiwritepaper-agentic-skill"
```

PowerShell 5.1：

```powershell
Remove-Item -LiteralPath .agents\skills\aiwritepaper-agentic-skill -Recurse -Force
Remove-Item -LiteralPath (Join-Path $HOME '.codex\skills\aiwritepaper-agentic-skill') -Recurse -Force
```

通过 Gemini CLI 或 Copilot CLI 原生安装的版本，分别使用 `gemini skills uninstall aiwritepaper-agentic-skill` 或 Copilot 的 `/plugins remove --skill aiwritepaper-agentic-skill`。

## 维护约定

`skills/` 保存可独立安装的完整配图 Skill，`references/figure-skills/` 保存根 Skill 编译提示词时使用的集成规则。修改配图逻辑时必须同步检查两处，并重新运行提示词编译、根 Skill 校验、两个独立 Skill 校验和 SVG 审计器测试。

## English Quick Start

This repository follows the open agentskills.io `SKILL.md` standard. Install it with:

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill
```

For a local install, the POSIX installer clones the fixed repository into a temporary directory and copies the complete `aiwritepaper-agentic-skill` folder. It supports `--agent codex|claude|cursor|gemini|antigravity|copilot|opencode|workbuddy|universal`, `--scope user|project`, and `--force`. The PowerShell 5.1 installer provides the same options as `-Agent`, `-Scope`, and `-Force`.

## License

MIT License. See [LICENSE](LICENSE).
