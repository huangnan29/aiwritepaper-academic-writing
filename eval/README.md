# 独立评测

本目录不进入论文写作提示词。论文生产结束后，先冻结评审包，再由另一会话、另一模型或人工盲评。写作进程不得创建数字评分或把SELF改名为ISOLATED。

## 自动A/B控制器

不需要切换仓库版本。控制器把v1.9.1与v2.1.0-rc.2分别提取到18个独立项目目录，固定随机顺序，并直接调用Codex、Grok Build与Antigravity CLI。默认模型分别为GPT-5.6-Sol、Grok 4.6和Gemini 3.8 Flash High。

```bash
LAB="/Users/anan/Desktop/paper-test/aiwritepaper-ab-2.1.0-rc.2"

uv run python eval/ab_runner.py --lab "$LAB" init
uv run python eval/ab_runner.py --lab "$LAB" doctor
uv run python eval/ab_runner.py --lab "$LAB" run --dry-run
uv run python eval/ab_runner.py --lab "$LAB" run
uv run python eval/ab_runner.py --lab "$LAB" status
```

动态查看首批进度：

```bash
uv run python eval/ab_dashboard.py --lab "$LAB" --port 8766
```

浏览器打开`http://127.0.0.1:8766`。页面每2秒读取真实文件并更新总体进度、当前Agent、当前阶段、耗时和每篇完成度；只读，不改变实验状态。

`run`按固定随机序列逐个执行，已完成任务自动跳过；可以用`--agent`、`--version`、`--topic`和`--limit`先跑小批次。所有命令使用参数数组，不拼接shell。Antigravity通过真实`agy`命令运行，以独立项目作为工作区并自动批准工具；不启用其OS终端沙箱，因为该沙箱会阻断`uv`运行目录和项目`.venv`。论文Prompt与Skill仍限制只写当前运行目录。Grok和Codex使用各自无交互模式。

完成后匿名和汇总：

```bash
uv run python eval/ab_runner.py --lab "$LAB" blind
# 独立审阅者把R001.json等结果写入 "$LAB/reviews/"
uv run python eval/ab_runner.py --lab "$LAB" summarize
```

`blind-map.private.json`权限为600，不交给审阅者；匿名副本去除Skill、Prompt、模型与版本路径。控制器不会修改用户级全局Skill。

```bash
uv run python eval/build_review_package.py --root <论文目录> --output <独立评测目录>/review-package.json
```

评审包只登记真实文件及SHA-256，不运行外部命令。`references/reviewers/`、`references/quality/direction-rubrics.json`与`references/benchmarks/`仅供独立评测和维护，不由`paper.py prepare/check`加载。数字分数写入独立评测目录，不能改变`14-adjudicated-status.json`。
