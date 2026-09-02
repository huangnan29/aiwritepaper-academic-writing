<div align="center">

# AIWritePaper｜AI学术写作全流程

从题目与材料，到单一执行MD、正文、配图和可核验的DOCX/PDF。

![候选版本](https://img.shields.io/badge/version-2.1.0--dev-2563EB)
![架构](https://img.shields.io/badge/architecture-MD--first-7C3AED)
![方向](https://img.shields.io/badge/directions-19-16A34A)

</div>

> 当前为本地剪枝候选版，尚未发布、未分发，也未完成真实论文A/B测试。单元测试和提示词体积下降不代表已达到90分。

## 快速使用

正常使用只需给出题目和必要材料：

```text
使用 aiwritepaper-academic-writing，完成《你的论文题目》。
没有真实实验数据时不要编造，交付正文、配图、Word、PDF和实际检查结果。
```

没有题目时先选题；直接给题目时持续执行，不逐阶段向用户确认。用户明确字数优先；中文THESIS层次未知默认25,000，明确论文类型/层次及模板按统一解析器计算，不再由多份规则分别设默认值。

单独配图仍然可用：

```text
使用 aiwritepaper-academic-writing 的 FIGURES_ONLY 模式，优化当前论文配图，保留正文与研究结论。
```

需要重导Word/PDF时明确提出；否则只改图片与图表清单。也保留RESUME、REVISE_ONLY、EXPORT_ONLY、AUDIT_ONLY、PROPOSAL_ONLY和DEFENSE_ONLY。

## 这一轮剪了什么

- 公共规则去重；full与compact来自同一规则源，不维护两套真实性标准。
- 合成前由模型选择模式、方向和所需features，工具只按字节提取模块。执行期仍只读一份最终MD。
- 只导出不携带检索、生图和研究生产模块；只配图默认不携带全文结构、参考文献生产和导出模块。
- 研究计划可合并契约、大纲与论证安排；实际审查集中记录，旧格式报告由工具派生，不重复填写事实。
- 历史PARTIAL/FAIL不自动意味着弱模型；只有明确执行失败才增加阶段辅助。研究材料、配额与工具缺口单独说明。
- 结论比例和词频作审稿提示，不代替专业判断；方法门按实际研究设计适用，不把DID步骤套给所有政策论文。
- 目录要有实际条目与页码；重复题注按图片附近的题注结构检查，正文引用图号不会被当作重复题注。
- 90分保留为独立评测目标；作者可以不填数字分数，SELF不能冒充独立评估。

详细实现与未完成的真实测试分别见[实施计划](implementation_plan.md)、[任务状态](task.md)。历史版本说明只保留在[CHANGELOG](CHANGELOG.md)，不把旧成果重复写成新版本承诺。

## 执行结构

```text
一次准备 → 完整生产 → 统一检查 → 定点修复与交付
```

模块不是新的一层执行路由。选择发生在合成前；开始论文后不反复翻读公共目录。必要模块遗漏时明确记录变化并重新合成，不能静默改变已冻结提示词。

注意：compact现在是同源模块目录的兼容文件名，不再表示旧版约15KB的独立短提示词。全量compact文件比旧版大；新入口必须按task-selection提取实际模块。弱模型的最终输入和真实完成率尚未做对照，不把“同源”说成已经验证的弱模型提升，也不自动替换其已安装版本。

### 模型现在需要管理什么

准备时只填写一份paper-request.json，工具一次生成运行参数、能力/Profile记录、模块选择、Manifest骨架和唯一执行MD。完整生产后，模型记录真实专业/视觉观察；一个check入口派生兼容视图、按模式运行检查并汇总问题。无需逐个调用五个检查器，也不再维护三套自报PASS。

底层检查仍在，不是删除真实性与格式验证来缩短流程。准备工具不替模型选择方向、推断工具能力、写正文或评分；检查工具不替代专业审查。读取到原始检查器返回码0也可能汇总为PARTIAL，不会自动显示成功。

### 新入口

使用[任务记录模板](references/paper-request.example.json)，填写真实任务和能力观察；不能直接运行占位示例。

```bash
uv run python scripts/paper.py prepare --root /path/to/paper --request paper-request.json

# 读取唯一MD，完成真实研究、正文、图片与文档后，再检查。
uv run python scripts/paper.py check --root /path/to/paper --docx "论文_时间戳.docx" --pdf "论文_时间戳.pdf"
```

字段和特殊模式见[准备说明](references/preparation.md)。features包含figures、statistics、svg、formulas、documents；选择svg不等于获准绕过生图。prepare的--preview和check的--plan均只读预览，不代表任务完成。旧compose_prompt.py等CLI保留兼容，不再作为默认生产步骤。

## 保留的能力与底线

| 能力 | 不变的要求 |
|---|---|
| 19方向与信源路由 | 按研究动作和证据选择方向，保留开放数据库备用路线 |
| 文献与数据 | 元数据不冒充全文，真实输入/计算/日志不能被模型生成记录替代 |
| 原生生图 | 有工具时语义图调用生图，中文论文默认中文标签 |
| 精确图与统计图 | 数字可复算，领域图核对原始引脚/结构；科研影像不能生成证据区域 |
| SVG | 只在合法降级/领域场景启用；事实、字形、连线及最终PNG均检查 |
| 最终嵌图 | 只认final_embed_file；成功生图不能被备用SVG覆盖 |
| Word/PDF | 同一份定稿，OMML公式，真实标题导航、实际目录、零表格首行缩进、唯一题注 |
| 文件名 | 安全论文题目_YYYYMMDD-HHMMSS，Word与PDF同一时间戳 |
| 续跑与改稿 | 保留原稿及未受影响的证据，不全面重写 |
| 状态 | 机械通过不等于学术正确，自审分数不等于独立90分 |

## 检查与报告

文献、图表、公式和文档检查器继续存在；不因为脚本数量减少而放弃已验证的硬检查。Python只用于确定性工作，不负责决定论文观点、研究方法或替代审稿。

qa-review.json可以汇总具体主张、逐图观察、文档页面检查和实际审稿结论。prepare_audit_views.py只生成兼容视图并绑定文件摘要；不能创造观察、PASS、独立身份或分数。无评分时numeric_score为null、ninety_plus_verified为false。

新入口自动调用投影器。Manifest使用state_contract:DERIVED_ONLY，不要求作者先填research_status/delivery_status/final_status再证明自己；当次裁决从实际报告计算。正式路径和SHA-256可由check登记，研究性质则由模型明确给出，不猜测已实施研究。

只读审计必须提供源目录之外的新--audit-dir；源稿只读。旧检查报告留在.audit-logs/<本次运行>/upstream，崩溃或失败不得回退到旧PASS。输入变化后，不能把旧报告标成未变化；导出和改图重导允许重新核验实际图片、公式和文档，不重新生成研究内容。

原始数据、下载字节、实际工具调用、计算/仿真日志及旧正式文档继续保留。哈希只证明文件绑定，不证明来源真实或结论正确。最终状态由adjudicate_status.py汇总真实报告；仍有重要问题就明确报告，不调高分数逃避返修。

## 真实评测的边界

v2.0.0近期六篇审查中，Sol一篇APOS为89分，Grok Build五篇均分78.6分；主要缺陷包括目录未展开、电路图错误、综述分类误判和题目与方法未对齐。不同样本与审查深度不能直接当作版本升降幅度。

本候选只提供剪枝实现。下一步应固定题目、材料、模型/客户端和盲评口径，与v2.0.0对照，并加入此前表现好的题目检查非退化。57任务基准是维护期测试计划，不是57篇已通过；CI代码测试也不是论文效果验证。

## 安装与适配

发布安装器从GitHub远端克隆，不复制当前未提交工作树。需要测试本地候选时明确让Agent读取本地仓库SKILL.md；不要假称运行了尚未安装的候选版本。

已发布版本安装方式：

```bash
git clone https://github.com/huangnan29/aiwritepaper-academic-writing.git
cd aiwritepaper-academic-writing
./install.sh --agent grok --scope user
./install.sh --agent antigravity --scope user
```

Windows使用：

```powershell
.\install.ps1 -Agent codex -Scope user
```

可选codex、claude、cursor、kimi、gemini、antigravity、copilot、opencode、workbuddy、grok、zcode/zai、deepseek-tui/deepseek和universal。更新/旧名称迁移使用--force --migrate-legacy（PowerShell为-Force -MigrateLegacy），执行前确认目标安装。

| Agent | 用户级技能根目录 |
|---|---|
| Codex | ~/.codex/skills |
| Claude Code | ~/.claude/skills |
| Cursor | ~/.cursor/skills |
| Kimi Code | $KIMI_CODE_HOME/skills，默认~/.kimi-code/skills |
| Gemini CLI | ~/.gemini/skills |
| Antigravity | ~/.gemini/config/skills |
| Grok Build | ~/.grok/skills |
| WorkBuddy | ~/.workbuddy/skills |
| Z.ai / ZCode | ~/.zcode/skills |
| DeepSeek-tui | ~/.codewhale/skills |
| Copilot | ~/.copilot/skills |
| OpenCode | ~/.config/opencode/skills |
| 通用Agent | ~/.agents/skills |

每个根目录下的注册名称均为aiwritepaper-academic-writing。--scope project使用安装器相应项目路径；不改变模型或客户端配置，不自动安装额外付费服务。

## 维护

当前版本：`2.1.0-dev`。没有本轮发布标签或GitHub推送。

CI已配置使用[官方setup-uv](https://github.com/astral-sh/setup-uv)和PDF测试依赖，但本地候选尚未触发远端CI；本地测试通过不能写成GitHub CI已通过。

```bash
uv run python scripts/build_compiled.py
uv run python scripts/build_direction_reviewers.py
uv run python scripts/verify_compiled.py
uv run python -m unittest discover -s tests -p 'test_*.py'
node --test tests/test_render_svg_layout.mjs
```

构建仅生成受版本管理的提示词和审稿参考，不执行论文。release候选必须另外提供真实产物评测证据，不能以文件体积、测试数量或自评分代替。
