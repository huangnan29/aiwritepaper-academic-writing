#!/usr/bin/env python3
"""从方向评分卡生成19份隔离的专业审稿Prompt。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=json.loads((ROOT/"references/quality/direction-rubrics.json").read_text(encoding="utf-8"));out=ROOT/"references/reviewers";out.mkdir(exist_ok=True)
 for key,r in d["directions"].items():
  focus="\n".join(f"- {x}" for x in r["focus"]);crit="\n".join(f"- {x}" for x in r["critical"])
  text=f"# 独立方向审稿：{key}\n\n你是与写作模型隔离的专业审稿人。只读取研究契约、证据矩阵、最终正文、图表Manifest和本评分卡；不得读取作者自评分。先列Critical/Important/Minor及精确定位，再按证据25、内容20、结构15、配图15、文档15、自审10评分。没有证据不得给高分。\n\n## 专业关注点\n{focus}\n\n## Critical\n{crit}\n\n## 输出\n写入 `15-quality-scorecard.json`，每个问题包含location、evidence、fix与status。Critical未清零或任一维度低于80%时不得给90分。\n"
  (out/f"{key}.md").write_text(text,encoding="utf-8")
 print(len(d["directions"]));return 0
if __name__=="__main__":raise SystemExit(main())
