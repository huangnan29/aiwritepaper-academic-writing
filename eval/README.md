# 独立评测

本目录不进入论文写作提示词。论文生产结束后先冻结评审包，再由另一会话、另一模型或人工评分；写作进程不得创建数字评分或把SELF改名为ISOLATED。

## 当前精简测试

当前只保留Grok标杆和Gemini 3.8 Flash弱模型观察。已完成结果直接复用，只新增Grok两篇与Gemini两篇。四篇使用同一个`v2.1.0-rc.2`快照，但在四个完全独立的项目目录中并行执行，不需要切换仓库版本。

```bash
LAB="/Users/anan/Desktop/paper-test/aiwritepaper-ab-2.1.0-rc.2"

uv run python eval/ab_runner.py --lab "$LAB" run \
  --agent antigravity --agent grok \
  --version v2.1.0-rc.2 \
  --topic circuit --topic apos --topic review \
  --parallel 4
```

已完成的Gemini APOS和Grok综述会自动跳过，因此实际只启动4篇。每篇独立写`case-manifest.json`与运行日志；总Manifest的写入经过同步保护。任一任务失败不会修改其他任务的论文文件。

动态进度页：

```bash
uv run python eval/ab_dashboard.py --lab "$LAB" --port 8766
```

浏览器打开`http://127.0.0.1:8766`。页面每2秒从各任务的真实文件和独立状态读取进度，展示6个精简样本；页面只读。

## 控制器边界

`ab_runner.py`仍保留旧实验目录的兼容能力，但当前协议不要求重跑v1.9.1，也不要求完成18/30任务矩阵。Antigravity使用真实`agy`与`gemini-3.8-flash-high`，Grok Build使用Grok 4.6。所有命令使用参数数组，不拼接Shell。

运行结束后可冻结匿名材料：

```bash
uv run python eval/ab_runner.py --lab "$LAB" blind
# 独立审阅者把评分写入 "$LAB/reviews/"
uv run python eval/ab_runner.py --lab "$LAB" summarize
```

`blind-map.private.json`权限为600，不交给审阅者。匿名副本去除Skill、Prompt、模型与版本路径。数字评分不能改变`14-adjudicated-status.json`。

单篇冻结也可使用：

```bash
uv run python eval/build_review_package.py --root <论文目录> --output <独立评测目录>/review-package.json
```
