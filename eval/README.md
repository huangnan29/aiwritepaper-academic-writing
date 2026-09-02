# 独立评测

本目录不进入论文写作提示词。论文生产结束后，先冻结评审包，再由另一会话、另一模型或人工盲评。写作进程不得创建数字评分或把SELF改名为ISOLATED。

```bash
uv run python eval/build_review_package.py --root <论文目录> --output <独立评测目录>/review-package.json
```

评审包只登记真实文件及SHA-256，不运行外部命令。`references/reviewers/`、`references/quality/direction-rubrics.json`与`references/benchmarks/`仅供独立评测和维护，不由`paper.py prepare/check`加载。数字分数写入独立评测目录，不能改变`14-adjudicated-status.json`。
