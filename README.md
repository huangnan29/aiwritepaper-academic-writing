# AIWritePaper Agentic Skill

这是一个面向 AIWritePaper 论文生产准备流程的 Agent Skill。它遵循 [agentskills.io](https://agentskills.io/) 的开放 `SKILL.md` 规范，可供支持 Agent Skills 的编码助手按需发现和调用。

仓库根目录的 `SKILL.md` 是核心入口，`references/` 和 `scripts/` 是配套的完整内容。`agents/openai.yaml` 仅是 OpenAI/Codex 的可选 UI 元数据，其他 agent 可以忽略它，不影响安装和使用。

## 核心能力

- 覆盖 19 个论文方向提示词，并根据题目、研究动作和证据形式只加载一个匹配方向。
- 强制执行研究契约、文献核验、证据矩阵、真实性边界和最终质量门。
- 没有真实数据、源码、实验、问卷、访谈、病例或日志时，自动降级为方案、协议或综述，不生成虚构结果。
- 在图表生产前区分语言模型、SVG 渲染器和专用图片生成工具，不把“能写 SVG”误判为“能生成图片”。
- 按图类路由流程图、架构图、ER 图、UML、统计图、科研原始图像与生成式机制示意。

## 学术配图能力

根 Skill 已内置统一的学术配图规则：

- `references/common/academic-figures.md`：证据边界、图类路由和通用质量门；
- `references/figure-skills/academic-figure-routing.md`：生成式学术插画的事实契约与禁止项；
- `references/figure-skills/academic-svg-quality.md`：流程图、架构图、ER 图、UML 和研究框架的确定性 SVG 规则。

仓库还提供两个可独立安装的配套 Skill：

- `skills/academic-figure-router/`：判断应使用图片模型、SVG、数据绘图、领域工具还是原始科研图像；
- `skills/academic-svg-enhancer/`：设计、重绘和验收出版级 SVG，并附带 `scripts/audit_svg.py` 静态审计器。

关键边界：流程、关系、数值、公式、连接、坐标或数据库基数必须逐项准确的图，默认走确定性路径；只有自然形态确实是主要信息、事实契约完整且当前环境实际具备图片工具时，才允许生成明确标记的概念示意。生成式图片不得冒充显微图、医学影像、实验照片或统计结果。

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

安装器支持以下 agent 参数：`codex`、`claude`、`cursor`、`gemini`、`antigravity`、`copilot`、`opencode`、`universal`。

`user` 是用户级安装，`project` 是当前工作目录下的项目级安装。执行 `project` 安装时，请先切换到项目根目录。默认情况下，目标目录已存在就会拒绝覆盖；确认要替换已有版本时才使用 `force`。

macOS、Linux 或其他 POSIX shell：

```bash
# 项目级通用安装到 .agents/skills/aiwritepaper-agentic-skill
./install.sh --agent universal --scope project

# 用户级 Codex 安装
./install.sh --agent codex --scope user

# 全局安装到 Antigravity 的 ~/.gemini/config/skills
./install.sh --agent antigravity --scope user

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

mkdir -p .agents/skills
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git .agents/skills/aiwritepaper-agentic-skill
```

用户级安装时，把上面命令中的目标路径分别替换为以下路径：

```text
~/.claude/skills/aiwritepaper-agentic-skill
~/.codex/skills/aiwritepaper-agentic-skill
~/.cursor/skills/aiwritepaper-agentic-skill
~/.config/opencode/skills/aiwritepaper-agentic-skill
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

For a local install, the POSIX installer clones the fixed repository into a temporary directory and copies the complete `aiwritepaper-agentic-skill` folder. It supports `--agent codex|claude|cursor|gemini|antigravity|copilot|opencode|universal`, `--scope user|project`, and `--force`. The PowerShell 5.1 installer provides the same options as `-Agent`, `-Scope`, and `-Force`.

## License

MIT License. See [LICENSE](LICENSE).
