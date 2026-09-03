#!/usr/bin/env python3
"""为AIWritePaper A/B实验提供只读动态进度页面。"""

from __future__ import annotations

import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse


HTML = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AIWritePaper 精简评测台</title>
<style>
:root{--ink:#112126;--paper:#f4f0e8;--red:#ed5b46;--lime:#c8db57;--blue:#32697a;--line:#c9c1b4;--muted:#6c746f}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:"PingFang SC","Hiragino Sans GB",sans-serif}
body:before{content:"";position:fixed;inset:0;pointer-events:none;opacity:.28;background-image:repeating-linear-gradient(0deg,transparent 0 31px,rgba(17,33,38,.055) 32px)}
.shell{max-width:1240px;margin:auto;padding:38px 34px 70px}.mast{display:grid;grid-template-columns:1fr auto;gap:24px;align-items:end;border-bottom:3px solid var(--ink);padding-bottom:20px}
.eyebrow{font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--red);font-weight:800}.title{font-family:"Iowan Old Style","Songti SC",serif;font-size:clamp(38px,6vw,76px);line-height:.9;margin:10px 0 0;letter-spacing:-.05em}
.live{display:flex;align-items:center;gap:9px;font-size:13px;font-weight:700}.dot{width:10px;height:10px;background:var(--red);border-radius:50%;box-shadow:0 0 0 0 rgba(237,91,70,.6);animation:pulse 1.8s infinite}@keyframes pulse{70%{box-shadow:0 0 0 10px transparent}}
.hero{display:grid;grid-template-columns:1.25fr .75fr;gap:20px;margin:24px 0}.panel{border:1.5px solid var(--ink);background:rgba(255,255,255,.45);box-shadow:6px 6px 0 var(--ink);padding:24px}
.big{font:700 clamp(52px,8vw,102px)/.9 "Iowan Old Style","Songti SC",serif;letter-spacing:-.06em}.label{font-size:12px;text-transform:uppercase;letter-spacing:.18em;color:var(--muted);font-weight:700}
.track{height:18px;background:#d7d0c5;border:1.5px solid var(--ink);margin-top:22px;overflow:hidden}.fill{height:100%;width:0;background:linear-gradient(90deg,var(--red),#f09955,var(--lime));transition:width .8s cubic-bezier(.2,.8,.2,1);position:relative}.fill:after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(135deg,transparent 0 9px,rgba(255,255,255,.28) 10px 13px);animation:move 1s linear infinite}@keyframes move{to{background-position:18px 0}}
.now{font:700 27px/1.15 "Iowan Old Style","Songti SC",serif;margin:10px 0 16px}.meta{display:grid;grid-template-columns:1fr 1fr;gap:14px;border-top:1px solid var(--line);padding-top:16px}.meta b{display:block;font-size:20px}.meta span{font-size:12px;color:var(--muted)}
.cases{display:grid;gap:14px}.card{display:grid;grid-template-columns:55px minmax(180px,1fr) 130px 110px;align-items:center;gap:18px;border-top:1.5px solid var(--ink);padding:18px 4px}.card:last-child{border-bottom:1.5px solid var(--ink)}
.index{font:700 34px/1 "Iowan Old Style",serif;color:var(--red)}.name{font-weight:750}.sub{font-size:12px;color:var(--muted);margin-top:4px}.mini{height:9px;background:#d7d0c5;border:1px solid var(--ink);margin-top:9px}.mini>i{display:block;height:100%;background:var(--blue);transition:width .7s}.phase{font-size:13px;font-weight:800}.pct{font:700 28px/1 "Iowan Old Style",serif;text-align:right}
.badge{display:inline-block;padding:4px 8px;border:1px solid var(--ink);font-size:10px;font-weight:800;letter-spacing:.1em;margin-left:8px}.running{background:var(--lime)}.complete{background:var(--blue);color:white}.pending{background:transparent}.failed{background:var(--red);color:white}
.foot{margin-top:28px;display:flex;justify-content:space-between;color:var(--muted);font-size:12px}.error{color:var(--red);font-weight:700}
@media(max-width:760px){.mast,.hero{grid-template-columns:1fr}.card{grid-template-columns:42px 1fr 70px}.phase{display:none}.shell{padding:24px 18px}.panel{box-shadow:4px 4px 0 var(--ink)}}
</style></head>
<body><main class="shell">
<header class="mast"><div><div class="eyebrow">AIWritePaper · Lean Benchmark</div><h1 class="title">精简评测台</h1></div><div class="live"><i class="dot"></i><span id="connection">实时连接</span></div></header>
<section class="hero"><div class="panel"><div class="label">Grok 标杆 · Gemini 与 Codex 补充样本</div><div class="big"><span id="overall">0</span><small style="font-size:.35em">%</small></div><div class="track"><div class="fill" id="overallFill"></div></div></div>
<div class="panel"><div class="label">当前动作</div><div class="now" id="current">等待数据</div><div class="meta"><div><b id="done">0 / 7</b><span>实际完成</span></div><div><b id="elapsed">00:00</b><span>最长运行时间</span></div></div></div></section>
<section><div class="label" style="margin:34px 0 8px">RUN QUEUE</div><div class="cases" id="cases"></div></section>
<footer class="foot"><span id="updated">尚未刷新</span><span>每 2 秒自动更新 · 只读监控</span></footer>
</main>
<script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function fmt(sec){sec=Math.max(0,sec||0);return `${String(Math.floor(sec/60)).padStart(2,'0')}:${String(Math.floor(sec%60)).padStart(2,'0')}`}
async function refresh(){try{const r=await fetch('/api/status?scope=lean',{cache:'no-store'});if(!r.ok)throw Error(r.status);const d=await r.json();
document.querySelector('#overall').textContent=d.overall_percent;document.querySelector('#overallFill').style.width=d.overall_percent+'%';document.querySelector('#done').textContent=`${d.complete_count} / ${d.cases.length}`;document.querySelector('#elapsed').textContent=fmt(d.current_elapsed_seconds);
document.querySelector('#current').textContent=d.running_count?`${d.running_count} 个任务并行 · ${d.current.phase}`:'队列等待';document.querySelector('#updated').textContent=`更新 ${d.server_time}`;document.querySelector('#connection').textContent='实时连接';document.querySelector('#connection').className='';
document.querySelector('#cases').innerHTML=d.cases.map((x,i)=>`<article class="card"><div class="index">${String(i+1).padStart(2,'0')}</div><div><div class="name">${esc(x.agent_label)}<span class="badge ${x.state_class}">${esc(x.status)}</span></div><div class="sub">${esc(x.title)} · ${esc(x.version)}</div><div class="mini"><i style="width:${x.progress}%"></i></div></div><div class="phase">${esc(x.phase)}<div class="sub">${x.artifact_count} 个文件 · ${fmt(x.last_activity_seconds)} 前更新</div></div><div class="pct">${x.progress}%</div></article>`).join('');
}catch(e){document.querySelector('#connection').textContent='连接中断';document.querySelector('#connection').className='error'}}
refresh();setInterval(refresh,2000);
</script></body></html>'''


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("实验Manifest不是对象")
    return value


def seconds_since(value: object) -> int:
    if not isinstance(value, str):
        return 0
    try:
        start = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return max(0, int((datetime.now().astimezone() - start).total_seconds()))
    except ValueError:
        return 0


def infer(case: dict) -> dict:
    root = Path(case["directory"])
    case_status = root / "case-manifest.json"
    if case_status.is_file():
        try:
            case = {**case, **load(case_status)}
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    files = [path for path in root.rglob("*") if path.is_file() and ".agents" not in path.parts and ".codex" not in path.parts and ".grok" not in path.parts and ".attempts" not in path.parts]
    output = locate_artifact_root(root)
    output_files = [path for path in output.rglob("*") if path.is_file()]
    names = {str(path.relative_to(output)) for path in output_files}
    progress, phase = 0, "等待启动"
    if case.get("status") in {"RUNNING", "FINISHED_INCOMPLETE", "COMPLETE"}:
        progress, phase = 4, "启动Agent"
    if "final-execution-prompt.md" in names:
        progress, phase = 15, "准备完成"
    if "03-evidence-matrix.csv" in names:
        progress, phase = 30, "证据与文献"
    if "01-research-contract.md" in names or any(name.startswith("chapters/") for name in names):
        progress, phase = 42, "大纲与章节"
    if "07-paper-full.md" in names:
        progress, phase = 68, "正文已整合"
    if "figures/figure-manifest.json" in names:
        image_count = sum(Path(name).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} for name in names if name.startswith("figures/"))
        progress, phase = min(84, 76 + image_count), "配图与视觉检查"
    docx = any(path.parent == output and path.suffix.lower() == ".docx" for path in output_files)
    pdf = any(path.parent == output and path.suffix.lower() == ".pdf" for path in output_files)
    if docx or pdf:
        progress, phase = 90 if docx and pdf else 86, "文档导出"
    if "13-delivery-verification.json" in names:
        progress, phase = 95, "最终机械验收"
    status = case.get("status", "PENDING")
    if "14-adjudicated-status.json" in names:
        final_status = None
        try:
            adjudication = load(output / "14-adjudicated-status.json")
            final_status = (adjudication.get("authoritative_status") or {}).get("final_status")
        except (OSError, ValueError, json.JSONDecodeError):
            pass
        if status == "RUNNING":
            progress, phase = (97, "返修与复验") if final_status == "FAIL" else (99, "完成前收尾")
        elif status == "COMPLETE":
            progress, phase = 100, "完成"
        else:
            progress, phase = 97, "裁决后待收尾"
    if status == "COMPLETE" and progress < 100:
        progress, phase = 99, "等待最终状态同步"
    if status in {"FINISHED_INCOMPLETE", "BLOCKED"}:
        phase = "需要处理"
    state_class = "running" if status == "RUNNING" else "complete" if progress == 100 else "failed" if status in {"FINISHED_INCOMPLETE", "BLOCKED"} else "pending"
    latest = max((path.stat().st_mtime for path in files), default=0)
    last_activity_seconds = max(0, int(datetime.now().timestamp() - latest)) if latest else 0
    return {**case, "progress": progress, "phase": phase, "artifact_count": len(files),
            "elapsed_seconds": seconds_since(case.get("started_at")),
            "last_activity_seconds": last_activity_seconds, "state_class": state_class,
            "artifact_root": str(output.relative_to(root)) if output != root else "."}


def locate_artifact_root(root: Path) -> Path:
    if (root / "07-paper-full.md").is_file() or (root / "14-adjudicated-status.json").is_file():
        return root
    candidates = []
    for name in ("07-paper-full.md", "run-manifest.json", "final-execution-prompt.md"):
        for path in root.rglob(name):
            if any(part in {".codex", ".grok", ".agents", ".attempts"} for part in path.parts):
                continue
            candidates.append(path.parent)
    if not candidates:
        return root
    return sorted(
        set(candidates),
        key=lambda path: (0 if (path / "07-paper-full.md").is_file() else 1, len(path.parts), str(path)),
    )[0]


def snapshot(lab: Path, scope: str) -> dict:
    manifest = load(lab / "ab-manifest.json")
    cases = manifest["cases"]
    by_id = {case["case_id"]: case for case in cases}
    if scope == "all":
        selected = [by_id[case_id] for case_id in manifest["randomized_order"]]
    elif scope in {"lean", "smoke-b"}:
        lean_ids = [
            "grok__review__B",
            "antigravity__apos__B", "antigravity__review__B", "antigravity__circuit__B",
            "codex__review__B", "codex__apos__B", "codex__circuit__B",
        ]
        selected = [by_id[case_id] for case_id in lean_ids if case_id in by_id]
    else:
        selected = [by_id[case_id] for case_id in manifest["randomized_order"] if by_id[case_id]["version"] == "v2.1.0-rc.2"][:3]
    rows = [infer(case) for case in selected]
    running_rows = [row for row in rows if row["status"] == "RUNNING"]
    running = running_rows[0] if running_rows else None
    return {
        "server_time": datetime.now().astimezone().strftime("%H:%M:%S"),
        "scope": scope, "overall_percent": round(sum(row["progress"] for row in rows) / max(len(rows), 1)),
        "complete_count": sum(row["progress"] == 100 for row in rows), "current": running,
        "running_count": len(running_rows),
        "current_elapsed_seconds": max((row["elapsed_seconds"] for row in running_rows), default=0), "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="启动A/B动态只读进度页")
    parser.add_argument("--lab", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    lab = args.lab.expanduser().resolve()
    if not (lab / "ab-manifest.json").is_file():
        raise SystemExit("实验Manifest不存在")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/favicon.ico":
                self.send_response(204); self.end_headers(); return
            if parsed.path == "/api/status":
                scope = parse_qs(parsed.query).get("scope", ["lean"])[0]
                data = json.dumps(snapshot(lab, scope), ensure_ascii=False).encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(data)))
                self.end_headers(); self.wfile.write(data); return
            if parsed.path in {"/", "/index.html"}:
                data = HTML.encode("utf-8")
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(data)))
                self.end_headers(); self.wfile.write(data); return
            self.send_error(404)

        def log_message(self, pattern, *values):
            return

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"A/B动态进度页：http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
