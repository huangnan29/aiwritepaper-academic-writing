#!/usr/bin/env python3
"""从方向评分卡生成19份隔离的专业审稿Prompt。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=json.loads((ROOT/"references/quality/direction-rubrics.json").read_text(encoding="utf-8"));out=ROOT/"references/reviewers";out.mkdir(exist_ok=True)
 for key,r in d["directions"].items():
  focus="\n".join(f"- {x}" for x in r["focus"]);crit="\n".join(f"- {x}" for x in r["critical"])
  text=f"# 独立方向审稿：{key}\n\n你是与写作模型隔离的专业审稿人。只读取研究契约、证据矩阵、最终正文、图表Manifest、文档视觉审计、最终DOCX/PDF和本评分卡；不得读取作者自评分。先列Critical/Important/Minor及精确定位，再按证据25、内容20、结构15、配图15、文档15、自审10评分。没有证据不得给高分。\n\n## 专业关注点\n{focus}\n\n## Critical\n{crit}\n\n## 终稿输出\n在全部图片和文档完成后写入 `09-final-peer-review.json`，记录 `schema_version: 1.0`、当前 `direction_id`、`status`、`reviewer_mode: ISOLATED`、Critical/Important开放数、六项分数、总分，以及最终正文、Figure Manifest、文档视觉审计、DOCX和PDF的逐文件SHA-256。然后把完全相同的分数写入 `15-quality-scorecard.json`，并记录终稿审稿报告路径与SHA-256。每个问题包含location、evidence、fix与status。Critical或Important未清零、任一维度低于80%或总分低于90时不得给90分。\n"
  (out/f"{key}.md").write_text(text,encoding="utf-8")
 print(len(d["directions"]));return 0
if __name__=="__main__":raise SystemExit(main())
