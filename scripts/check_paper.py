#!/usr/bin/env python3
"""统一运行确定性检查并汇总当次结果，不生成论文或把返回码当学术PASS。"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from adjudicate_status import REPORT_SPECS, sha256
from compose_prompt import atomic_write

SKILL_ROOT = Path(__file__).resolve().parents[1]
VALID = {"FULL_BUILD", "RESUME", "REVISE_ONLY", "FIGURES_ONLY", "EXPORT_ONLY", "AUDIT_ONLY", "PROPOSAL_ONLY", "DEFENSE_ONLY"}


def under(root, value):
    root = root.resolve()
    if not isinstance(value, str) or not value:
        raise ValueError("缺少文件路径")
    path = (root / value).resolve()
    path.relative_to(root)
    return path


def output_path(root, value):
    root = root.resolve()
    path = under(root, value)
    unresolved = root / value
    for part in [unresolved, *unresolved.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f"输出路径不能经符号链接写入：{value}")
    if path.exists() and not path.is_file():
        raise ValueError(f"报告目标不是文件：{value}")
    return path


def load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON不是对象：{path.name}")
    return data


def make_plan(root, manifest, mode):
    """依模式选择核验，不按模型品牌决定研究步骤。"""
    root = root.resolve()
    matrix = load(SKILL_ROOT / "references/mode-checker-matrix.json")["modes"][mode]
    reexport = manifest.get("reexport_documents") is True
    steps = []
    if (root / "qa-observations.json").is_file() and not (mode == "FIGURES_ONLY" and not reexport):
        steps.append({"category": "views", "command": [sys.executable, str(SKILL_ROOT / "scripts/prepare_audit_views.py"), "--root", str(root), "--input", "qa-observations.json"], "report": None})
    for category, options in matrix.items():
        spec = REPORT_SPECS[category]
        relative = manifest.get(spec["manifest_field"], spec["default"])
        destination = output_path(root, relative)
        action = "RUN" if "RUN" in options else options[0]
        if mode == "FIGURES_ONLY":
            action = "RUN" if category == "figure" or (reexport and category in {"formula", "delivery"}) else "SKIPPED_NOT_APPLICABLE"
        if action not in options:
            raise ValueError(f"模式矩阵不允许{mode}.{category}.{action}")
        if action == "RUN":
            command = [sys.executable, str(SKILL_ROOT / "scripts" / spec["script"]), "--root", str(root), "--report", str(destination.relative_to(root))]
            if category == "figure" and mode == "FIGURES_ONLY" and not reexport:
                command.append("--skip-documents")
            if category == "delivery":
                for field, option in [("target_length", "--target"), ("min_length", "--minimum"), ("max_length", "--maximum")]:
                    if field in manifest:
                        value = manifest[field]
                        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                            raise ValueError(f"{field}不是有效正整数")
                        command += [option, str(value)]
        else:
            command = [sys.executable, str(SKILL_ROOT / "scripts/write_skipped_report.py"), "--root", str(root),
                       "--category", category, "--mode", mode, "--skip-status", action, "--reason",
                       f"{mode}限定的核验范围；未声称重新检查未涉及内容", "--input", "run-manifest.json",
                       "--output", str(destination.relative_to(root))]
        steps.append({"category": category, "action": action, "command": command, "report": str(destination.relative_to(root))})
    steps.append({"category": "adjudication", "command": [sys.executable, str(SKILL_ROOT / "scripts/adjudicate_status.py"), "--root", str(root), "--report", "14-adjudicated-status.json"], "report": "14-adjudicated-status.json"})
    return steps


def verify_upstream(root, category, path):
    upstream = load(path)
    spec = REPORT_SPECS[category]
    verifier = upstream.get("verifier", {})
    if upstream.get("status") in {"SKIPPED_NOT_APPLICABLE", "SKIPPED_UNCHANGED"}:
        raise ValueError(f"{category}不能链式复用跳过报告")
    if verifier.get("name") != spec["script"] or verifier.get("sha256") != sha256(SKILL_ROOT / "scripts" / spec["script"]):
        raise ValueError(f"{category}前序检查器版本不匹配")
    hashes = upstream.get("input_sha256")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError(f"{category}前序报告没有实际输入摘要")
    for name, digest in hashes.items():
        actual = under(root, name)
        if not actual.is_file() or digest != sha256(actual):
            raise ValueError(f"{category}前序输入已变化：{name}，须重新检查")


def preflight_outputs(root, manifest, steps):
    root = root.resolve()
    protected = {"run-manifest.json", "paper-request.json", "run-params.md", "final-execution-prompt.md", "qa-observations.json",
                 "03-evidence-matrix.csv", "references.bib", "07-paper-full.md", "figures/figure-manifest.json",
                 "00-capability-report.json"}
    for key in ("docx", "pdf"):
        if isinstance(manifest.get(key), str):
            protected.add(str(under(root, manifest[key]).relative_to(root)))
    paths = []
    for step in steps:
        if step["report"]:
            relative = step["report"]
            path = output_path(root, relative)
            if str(path.relative_to(root)) in protected:
                raise ValueError(f"报告不能覆盖原始输入：{relative}")
            paths.append(path)
    paths += [output_path(root, "12-final-qa-report.md")]
    if len(paths) != len(set(paths)):
        raise ValueError("多个检查报告指向同一文件")
    log_root = root / ".audit-logs"
    if log_root.is_symlink() or (log_root.exists() and not log_root.is_dir()):
        raise ValueError(".audit-logs必须是本目录内的真实文件夹")
    # 审查投影器的输出也不得经符号链接改写其他文件。
    for relative in ["claim-evidence-map.json", "figures/figure-semantic-audit.json", "16-document-visual-audit.json",
                     "issue-register.json", "figures/figure-manifest.md", "00-capability-report.md"]:
        output_path(root, relative)


def run_checks(root, manifest, steps):
    root = root.resolve()
    log_root = root / ".audit-logs"
    log_root.mkdir(exist_ok=True)
    logs = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("check-%Y%m%d-%H%M%S-"), dir=log_root))
    backups = logs / "upstream"; backups.mkdir()
    failures, results = [], []
    # 先隔离旧裁决，避免本次崩溃后把旧PASS误当新结果。
    previous = root / "14-adjudicated-status.json"
    if previous.is_file():
        shutil.move(str(previous), str(backups / previous.name))
    for index, step in enumerate(steps):
        category, command = step["category"], list(step["command"])
        report = under(root, step["report"]) if step["report"] else None
        if step.get("action") == "SKIPPED_UNCHANGED":
            try:
                if report is None or not report.is_file():
                    raise ValueError(f"{category}缺少前序报告，不能伪造未变化")
                verify_upstream(root, category, report)
            except (ValueError, OSError) as exc:
                if report is not None and report.is_file():
                    shutil.move(str(report), str(backups / f"{index:02d}-{category}-ineligible.json"))
                failures.append(f"{category}: {exc}")
                results.append({"category": category, "status": "BLOCKED", "errors": [str(exc)]})
                continue
        if report is not None and report.is_file():
            archived = backups / f"{index:02d}-{category}.json"
            shutil.move(str(report), str(archived))
            if step.get("action") == "SKIPPED_UNCHANGED":
                command += ["--upstream-report", str(archived.relative_to(root))]
        if report is not None:
            report.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (logs / f"{index:02d}-{category}.log").write_text("[stdout]\n" + proc.stdout + "\n[stderr]\n" + proc.stderr, encoding="utf-8")
            code = proc.returncode
        except OSError as exc:
            code = -1
            (logs / f"{index:02d}-{category}.log").write_text(str(exc), encoding="utf-8")
        payload = None
        if report is not None and report.is_file():
            try:
                payload = load(report)
            except (ValueError, OSError):
                failures.append(f"{category}: 当次报告不可解析")
        if code != 0:
            failures.append(f"{category}: 检查命令退出码{code}")
            if report is not None and report.is_file() and payload and "FAIL" not in str(payload.get("status", "")):
                shutil.move(str(report), str(backups / f"{index:02d}-{category}-failed-command.json"))
        if report is not None and payload is None:
            failures.append(f"{category}: 未生成当次报告")
        results.append({"category": category, "exit_code": code, "status": payload.get("status") if payload else None,
                        "errors": payload.get("errors", []) if payload else [], "warnings": payload.get("warnings", []) if payload else []})
    final_file = root / "14-adjudicated-status.json"
    final = load(final_file) if final_file.is_file() else {}
    authoritative = final.get("authoritative_status", {})
    status = authoritative.get("final_status")
    if failures or status not in {"PASS", "PARTIAL", "FAIL"}:
        status = "FAIL"
    if status != "PASS" and not failures:
        failures = [f"{row['category']}: {item}" for row in results for item in row.get("errors", [])]
    summary = {"status": status, "mode": manifest.get("run_mode"), "authoritative_status": authoritative,
               "failed_categories": failures, "checks": results, "report": str(root / "12-final-qa-report.md"),
               "logs": str(logs), "scope_note": "仅汇总当次机械检查；不代表独立学术评价，也不自动修改正文。"}
    lines = ["# 本次检查结果", "", f"- 范围：{manifest.get('run_mode')}", f"- 状态：{status}",
             "- 本报告不代替学术判断，不自动修订论文。", "", "## 需要处理的问题", ""]
    for row in results:
        lines.append(f"### {row['category']}：{row['status'] or '未生成结果'}")
        lines.append("")
        items = row.get("errors", []) + row.get("warnings", [])
        lines.extend(f"- {item}" for item in items)
        if not items:
            lines.append("- 详见本次原始日志；没有列出问题不等于已证明学术正确。")
        lines.append("")
    lines.extend(["## 命令失败", "", *[f"- {f}" for f in failures]])
    atomic_write(root / "12-final-qa-report.md", ("\n".join(lines) + "\n").encode())
    atomic_write(logs / "summary.json", (json.dumps(summary, ensure_ascii=False, indent=2) + "\n").encode())
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="一次运行适用检查并汇总真实问题")
    parser.add_argument("mode", nargs="?", choices=sorted(VALID))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--audit-dir", type=Path)
    parser.add_argument("--docx"); parser.add_argument("--pdf")
    parser.add_argument("--claim-level", choices=["OBSERVED_STUDY", "DESIGN_ONLY", "PROTOCOL_ONLY", "REVIEW_SYNTHESIS"])
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)
    source = args.root.resolve()
    try:
        manifest_path = output_path(source, "run-manifest.json")
        manifest = load(manifest_path)
        mode = args.mode or manifest.get("run_mode")
        if mode not in VALID:
            raise ValueError("缺少合法run_mode")
        if args.mode and mode != manifest.get("run_mode") and mode != "AUDIT_ONLY":
            raise ValueError("模式与现有契约不一致，不能默默重建任务")
        for field, value in (("docx", args.docx), ("pdf", args.pdf)):
            if value:
                path = under(source, value)
                if not path.is_file() or path.stat().st_size == 0:
                    raise ValueError(f"{field}文件不存在或为空")
                manifest[field] = str(path.relative_to(source))
        manifest["run_mode"] = mode
        if args.claim_level:
            manifest["research_claim_level"] = args.claim_level
        for field in ("docx", "pdf"):
            if isinstance(manifest.get(field), str) and (manifest.get("state_contract") == "DERIVED_ONLY" or getattr(args, field)):
                path = under(source, manifest[field])
                if path.is_file():
                    manifest[field + "_sha256"] = sha256(path)
        steps = make_plan(source, manifest, mode)
        preflight_outputs(source, manifest, steps)
        if args.plan:
            print(json.dumps({"status": "PLAN_ONLY", "mode": mode, "commands": steps}, ensure_ascii=False, indent=2))
            return 0
        work = source
        if mode == "AUDIT_ONLY":
            if args.audit_dir is None:
                raise ValueError("AUDIT_ONLY必须提供独立--audit-dir")
            audit = args.audit_dir.resolve()
            if audit.exists() or audit == source or source in audit.parents:
                raise ValueError("审计目录必须尚不存在且位于源目录之外")
            if args.audit_dir.is_symlink():
                raise ValueError("审计目录不能是符号链接")
            for path in source.rglob("*"):
                if path.is_symlink():
                    raise ValueError(f"源目录含符号链接，请提供无链接的审计副本：{path}")
            shutil.copytree(source, audit, ignore=shutil.ignore_patterns(".audit-logs"))
            work = audit
            context = {"source_root": str(source), "source_manifest_sha256": sha256(source / "run-manifest.json")}
            profile_name = manifest.get("profile_selection_report")
            if isinstance(profile_name, str):
                historical = under(source, profile_name)
                if historical.is_file():
                    context["profile_report_sha256"] = sha256(historical)
            manifest["audit_context"] = context
            for field in ["docx", "pdf", "profile_selection_report", *[spec["manifest_field"] for spec in REPORT_SPECS.values()]]:
                if isinstance(manifest.get(field), str):
                    manifest[field] = str(under(source, manifest[field]).relative_to(source))
            steps = make_plan(work, manifest, mode)
            preflight_outputs(work, manifest, steps)
        if args.docx or args.pdf or args.claim_level or manifest.get("state_contract") == "DERIVED_ONLY" or mode == "AUDIT_ONLY":
            atomic_write(work / "run-manifest.json", (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
        result = run_checks(work, manifest, steps)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result["status"] == "FAIL" else 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
