#!/usr/bin/env python3
"""确定性合成单一修改稿执行提示词，不参与修改决策。"""
from __future__ import annotations
import argparse, hashlib, json, os, tempfile
from pathlib import Path
def read(p:Path)->bytes:
    b=p.read_bytes();b.decode("utf-8")
    if not b.strip():raise ValueError(f"输入为空: {p}")
    return b.rstrip(b"\r\n")
def write(p:Path,b:bytes):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="wb",dir=p.parent,delete=False) as f:t=Path(f.name);f.write(b);f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--base-prompt",type=Path,required=True);p.add_argument("--request",type=Path,required=True);p.add_argument("--rules",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--report",type=Path,required=True);a=p.parse_args();paths=[x.expanduser().resolve() for x in [a.base_prompt,a.request,a.rules]];out=a.output.expanduser().resolve();data=b"\n\n".join(read(x) for x in paths)+b"\n";write(out,data);payload={"schema_version":"1.0","run_mode":"REVISE_ONLY","output":str(out),"sha256":hashlib.sha256(data).hexdigest(),"inputs":[{"file":str(x),"sha256":hashlib.sha256(x.read_bytes()).hexdigest()} for x in paths]};write(a.report.expanduser().resolve(),(json.dumps(payload,ensure_ascii=False,indent=2)+"\n").encode());print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
