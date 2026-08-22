# AIWritePaper Agentic Skill

一个遵循 [Agent Skills 开放规范](https://agentskills.io/specification) 的可移植论文选题路由与可审计论文生产 Skill。

它会先判断用户是否已有选题。有题目时，根据学科、研究对象、研究方法和证据类型选择一个方向提示词；没有题目时，询问专业、细分方向和可用材料，再推荐 10 个可行选题。

## 核心能力

- 覆盖 19 个论文方向提示词。
- 基于 25 个 AIWritePaper 公开范文入口进行结构分析。
- 区分系统设计、工程实验、机器学习、实证研究、法学、人文、医学、综述与工作报告。
- 强制执行文献核验、证据矩阵、真实性边界和最终质量门槛。
- 没有真实数据、源码、实验、问卷、访谈或病例时，自动降级为方案、协议或综述，不生成虚构结果。

## 推荐安装方式

使用 [Vercel Skills CLI](https://github.com/vercel-labs/skills)，可以自动识别并安装到多数支持 Agent Skills 的客户端：

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill
```

全局安装到常用客户端：

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill -g \
  -a codex \
  -a claude-code \
  -a cursor \
  -a gemini-cli \
  -a github-copilot \
  -a opencode \
  -y
```

安装到所有已支持的 agent：

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill --all
```

仅临时使用，不安装：

```bash
npx skills use huangnan29/aiwritepaper-agentic-skill@aiwritepaper-agentic-skill
```

## 原生安装命令

### Gemini CLI

```bash
gemini skills install https://github.com/huangnan29/aiwritepaper-agentic-skill
```

工作区安装：

```bash
gemini skills install https://github.com/huangnan29/aiwritepaper-agentic-skill --scope workspace
```

### GitHub Copilot CLI

先克隆仓库，再把完整目录注册为技能来源，避免只安装 `SKILL.md` 而遗漏 `references/`：

```bash
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git
copilot plugins install --skill ./aiwritepaper-agentic-skill
```

### Claude Code

```bash
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.claude/skills/aiwritepaper-agentic-skill
```

安装后可输入：

```text
/aiwritepaper-agentic-skill
```

### Codex

```bash
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.codex/skills/aiwritepaper-agentic-skill
```

### Cursor

```bash
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.cursor/skills/aiwritepaper-agentic-skill
```

Cursor 也支持在 Customize 中使用 GitHub 仓库地址导入 Remote Rule/Skill。

### OpenCode

```bash
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.config/opencode/skills/aiwritepaper-agentic-skill
```

### 通用 `.agents` 路径

Cursor、Gemini CLI、GitHub Copilot、OpenCode、Kimi Code CLI、Cline 等客户端支持 `.agents/skills` 兼容路径：

```bash
git clone https://github.com/huangnan29/aiwritepaper-agentic-skill.git \
  ~/.agents/skills/aiwritepaper-agentic-skill
```

## 自带安装脚本

macOS/Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/huangnan29/aiwritepaper-agentic-skill/main/install.sh \
  | bash -s -- codex user
```

可用 agent 参数：`codex`、`claude`、`cursor`、`gemini`、`copilot`、`opencode`、`universal`。

项目级安装示例：

```bash
./install.sh cursor project
```

目标已存在时不会覆盖。需要更新且保留旧版本备份时使用：

```bash
./install.sh cursor user --force
```

Windows PowerShell：

```powershell
./install.ps1 -Agent codex -Scope user
```

## 项目级与用户级

| 范围 | 用途 |
|---|---|
| 用户级 | 所有项目可用，适合个人长期安装 |
| 项目级 | 只在当前项目使用，适合团队随仓库共享 |

不同客户端的具体路径存在差异，推荐优先使用 `npx skills` 或本仓库安装脚本自动选择。

## `agents/openai.yaml` 是什么

`agents/openai.yaml` 是 OpenAI/Codex 界面的可选元数据，负责提供显示名称、简短说明、默认提示词和调用策略。它不是 Agent Skills 开放规范的必需文件，也不是 Skill 的执行入口。

其他 agent 不认识这个文件时会直接忽略。Skill 的跨平台入口始终是根目录的 `SKILL.md`，所有核心流程、方向提示词和参考资料均不依赖 `agents/openai.yaml`。

## 更新与卸载

使用 Skills CLI：

```bash
npx skills update aiwritepaper-agentic-skill
npx skills remove aiwritepaper-agentic-skill
```

使用 Git 克隆安装时：

```bash
git -C ~/.codex/skills/aiwritepaper-agentic-skill pull --ff-only
```

卸载时删除对应 agent 的技能目录即可。

## 安全与学术边界

- 安装第三方 Skill 前先检查 `SKILL.md`、`scripts/` 和权限要求。
- 本 Skill 不包含 API Key、账号、登录态或远程执行配置。
- 公开范文只用于结构研究，不复制范文全文，也不把其中数字当作真实证据。
- 本 Skill 不承诺论文通过、原创率、AIGC 检测结果或学术认可。
- 用户仍需对研究数据、伦理、引用、结论和最终提交负责。

## English Quick Start

This repository follows the open [Agent Skills specification](https://agentskills.io/specification). The portable entry point is `SKILL.md`; `agents/openai.yaml` is optional OpenAI/Codex UI metadata and is ignored by other agents.

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill
```

Install globally for selected agents:

```bash
npx skills add huangnan29/aiwritepaper-agentic-skill -g \
  -a codex -a claude-code -a cursor -a gemini-cli \
  -a github-copilot -a opencode -y
```

## 参考资料

- [Agent Skills Specification](https://agentskills.io/specification)
- [Claude Code Skills](https://code.claude.com/docs/en/skills)
- [Cursor Agent Skills](https://cursor.com/docs/skills)
- [Gemini CLI Skills](https://geminicli.com/docs/cli/using-agent-skills/)
- [GitHub Copilot Agent Skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [OpenCode Skills](https://opencode.ai/docs/skills)

## License

MIT
