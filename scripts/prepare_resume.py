#!/usr/bin/env python3
"""验证已有运行状态并生成只读续跑计划，不重建已冻结产物。"""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

STAGES = ["EVIDENCE","OUTLINE","DRAFT","FIGURES","DOCUMENTS","VALIDATION"]
def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()
def main() -> int:
    ap=argparse.ArgumentParser(description="生成AIWritePaper RESUME续跑计划");ap.add_argument("--root",type=Path,default=Path.cwd());ap.add_argument("--output",type=Path,default=Path("00-resume-plan.json"));a=ap.parse_args();root=a.root.resolve();errors=[];warnings=[];frozen=[];invalid=[]
    manifest_path=root/"run-manifest.json"; prompt=root/"final-execution-prompt.md"; composition=root/"00-prompt-composition.json"
    try:m=json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as e:m={};errors.append(f"RUN_MANIFEST_INVALID: {e}")
    try:c=json.loads(composition.read_text(encoding="utf-8"))
    except Exception as e:c={};errors.append(f"PROMPT_COMPOSITION_INVALID: {e}")
    if not prompt.is_file() or not c or c.get("sha256")!=sha256(prompt): errors.append("FINAL_PROMPT_HASH_MISMATCH")
    checkpoints=root/str(m.get("execution_checkpoints") or "00-execution-checkpoints.json")
    resume_from=None
    if checkpoints.is_file():
        try: cp=json.loads(checkpoints.read_text(encoding="utf-8")); stages=cp.get("stages",{})
        except Exception as e: stages={};errors.append(f"CHECKPOINTS_INVALID: {e}")
        for stage in STAGES:
            info=stages.get(stage,{})
            valid=info.get("status")=="PASS" and bool(info.get("outputs"))
            for item in info.get("outputs",[]):
                p=(root/str(item.get("file"))).resolve()
                try:p.relative_to(root)
                except ValueError:valid=False;continue
                if not p.is_file() or item.get("sha256")!=sha256(p):valid=False
            if valid and resume_from is None:frozen.append(stage)
            elif resume_from is None:resume_from=stage;invalid.append(stage)
            else:invalid.append(stage)
    else:
        warnings.append("CHECKPOINTS_MISSING_INFER_FROM_REPORTS")
        report_rules=[("EVIDENCE","04-evidence-verification.json",{"EVIDENCE_OK","EVIDENCE_PARTIAL"}),("FIGURES","figures/figure-verification.json",{"STRUCTURE_OK"}),("DOCUMENTS","equations/formula-verification.json",{"FORMULA_OK"}),("DOCUMENTS","13-delivery-verification.json",{"DELIVERY_OK"})]
        resume_from="VALIDATION"
        for stage,path,ok in report_rules:
            p=root/path
            try:status=json.loads(p.read_text(encoding="utf-8")).get("status")
            except Exception:status=None
            if status not in ok:resume_from=stage;break
    if resume_from is None: resume_from="VALIDATION"
    payload={"schema_version":"1.0","run_mode":"RESUME","resume_from":resume_from,"frozen_stages":frozen,"invalidated_stages":invalid,"errors":errors,"warnings":warnings,"prompt_sha256":sha256(prompt) if prompt.is_file() else None,"manifest_sha256":sha256(manifest_path) if manifest_path.is_file() else None}
    out=a.output if a.output.is_absolute() else root/a.output;out.resolve().relative_to(root);out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(payload,ensure_ascii=False,indent=2));return 1 if errors else 0
if __name__=="__main__": raise SystemExit(main())
