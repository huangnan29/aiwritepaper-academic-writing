#!/usr/bin/env python3
"""验证90分评分卡、主张证据、图文语义和文档视觉审计的覆盖一致性。"""
import argparse,hashlib,json
from pathlib import Path
WEIGHTS={"evidence":25,"content":20,"structure":15,"figures":15,"documents":15,"integrity":10}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    x=json.loads(p.read_text(encoding="utf-8"));
    if not isinstance(x,(dict,list)):raise ValueError(p)
    return x
def main():
    a=argparse.ArgumentParser();a.add_argument("--root",type=Path,default=Path.cwd());a.add_argument("--report",type=Path,default=Path("17-quality-verification.json"));x=a.parse_args();r=x.root.resolve();errors=[];warnings=[]
    m=load(r/"run-manifest.json");direction=m.get("direction_id");score=load(r/"15-quality-scorecard.json");claims=load(r/"claim-evidence-map.json");semantic=load(r/"figures/figure-semantic-audit.json");visual=load(r/"16-document-visual-audit.json");manifest=load(r/"figures/figure-manifest.json")
    if score.get("direction_id")!=direction:errors.append("DIRECTION_RUBRIC_MISMATCH")
    scores=score.get("scores",{});calc=sum(float(scores.get(k,-999)) for k in WEIGHTS)
    if abs(calc-float(score.get("total",-1)))>.01:errors.append("SCORE_TOTAL_MISMATCH")
    if score.get("critical"):errors.append("CRITICAL_NOT_ZERO")
    for k,w in WEIGHTS.items():
        if float(scores.get(k,-1))<w*.8:warnings.append(f"DIMENSION_BELOW_80_PERCENT:{k}")
    rows=claims.get("claims",[]) if isinstance(claims,dict) else []
    if not rows or any(not q.get("location") or (q.get("importance") in {"CORE","CONCLUSION"} and not q.get("evidence_ids")) for q in rows):errors.append("CLAIM_EVIDENCE_COVERAGE")
    figs=manifest.get("figures",[]);expected={q.get("figure_id") for q in figs};audits=semantic.get("figures",[]) if isinstance(semantic,dict) else [];actual={q.get("figure_id") for q in audits}
    if expected!=actual or any(q.get("status")!="PASS" for q in audits):errors.append("FIGURE_SEMANTIC_NOT_PASS")
    required={"cover","primary_abstract","toc","complex_table","complex_formula","representative_figure","references","last_page"};checks=visual.get("checks",[]) if isinstance(visual,dict) else []
    if not required.issubset({q.get("checkpoint") for q in checks}) or any(q.get("status")!="PASS" for q in checks):errors.append("DOCUMENT_VISUAL_NOT_PASS")
    status="QUALITY_FAIL" if errors else ("QUALITY_PARTIAL" if warnings or calc<90 else "QUALITY_OK");inputs={str(p.relative_to(r)):sha(p) for p in [r/"run-manifest.json",r/"15-quality-scorecard.json",r/"claim-evidence-map.json",r/"figures/figure-semantic-audit.json",r/"16-document-visual-audit.json",r/"figures/figure-manifest.json"]};script=Path(__file__).resolve();payload={"schema_version":"1.0","status":status,"total":calc,"errors":errors,"warnings":warnings,"input_sha256":inputs,"verifier":{"name":script.name,"version":"1.9.0","sha256":sha(script)}};out=x.report if x.report.is_absolute() else r/x.report;out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(payload,ensure_ascii=False,indent=2));return 1 if status=="QUALITY_FAIL" else 0
if __name__=="__main__":raise SystemExit(main())
