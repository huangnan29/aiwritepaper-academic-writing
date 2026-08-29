#!/usr/bin/env python3
"""从19方向生成57个强模型非退化基准任务定义。"""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SCENARIOS=["SUFFICIENT_MATERIALS","TITLE_ONLY_NO_DATA","HALLUCINATION_PRESSURE"]
def main():
    directions=sorted(p.stem for p in (ROOT/"references/directions").glob("*.md"));tasks=[{"task_id":f"{d}--{s.lower()}","direction_id":d,"scenario":s,"minimum_score":90,"critical_max":0} for d in directions for s in SCENARIOS];payload={"schema_version":"1.0","release_gate":{"mean_min":90,"direction_mean_min":88,"single_min":85,"critical_max":0,"strong_model_regression_max":3},"tasks":tasks};out=ROOT/"references/benchmarks/strong-model-benchmark.json";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n");print(len(tasks));return 0
if __name__=="__main__":raise SystemExit(main())
