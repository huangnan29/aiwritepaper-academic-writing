#!/usr/bin/env python3
"""准备57任务目录并汇总真实质量报告；不伪造或代替模型运行。"""
import argparse,json
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--matrix",type=Path,default=Path(__file__).resolve().parents[1]/"references/benchmarks/strong-model-benchmark.json");p.add_argument("--prepare",action="store_true");p.add_argument("--collect",action="store_true");a=p.parse_args();root=a.root.resolve();matrix=json.loads(a.matrix.read_text());tasks=matrix["tasks"]
 if a.prepare:
  root.mkdir(parents=True,exist_ok=True)
  for t in tasks:
   d=root/t["task_id"];d.mkdir(exist_ok=True);(d/"benchmark-task.json").write_text(json.dumps(t,ensure_ascii=False,indent=2)+"\n")
 if a.collect:
  rows=[]
  for t in tasks:
   d=root/t["task_id"];q=d/"17-quality-verification.json";s=d/"15-quality-scorecard.json";adj=d/"14-adjudicated-status.json"
   if not(q.is_file() and s.is_file() and adj.is_file()):rows.append({**t,"status":"MISSING"});continue
   quality=json.loads(q.read_text());score=json.loads(s.read_text());ad=json.loads(adj.read_text());rows.append({**t,"status":"COMPLETE","score":score.get("total"),"critical":len(score.get("critical",[])),"quality_status":quality.get("status"),"final_status":ad.get("authoritative_status",{}).get("final_status")})
  completed=[x for x in rows if x["status"]=="COMPLETE"];means={}
  for d in {x["direction_id"] for x in completed}:
   vals=[float(x["score"]) for x in completed if x["direction_id"]==d];means[d]=sum(vals)/len(vals)
  scores=[float(x["score"]) for x in completed];gate=matrix["release_gate"];passed=len(completed)==len(tasks) and sum(scores)/len(scores)>=gate["mean_min"] and min(scores)>=gate["single_min"] and min(means.values())>=gate["direction_mean_min"] and all(x["critical"]<=gate["critical_max"] and x["quality_status"]=="QUALITY_OK" for x in completed)
  summary={"schema_version":"1.0","total":len(tasks),"completed":len(completed),"mean":sum(scores)/len(scores) if scores else None,"direction_means":means,"release_pass":passed,"rows":rows};(root/"benchmark-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n");print(json.dumps({k:summary[k] for k in ["total","completed","mean","release_pass"]},ensure_ascii=False));return 0 if passed else 1
 return 0
if __name__=="__main__":raise SystemExit(main())
