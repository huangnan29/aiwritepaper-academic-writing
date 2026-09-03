#!/usr/bin/env python3
"""AIWritePaper真实论文A/B控制器：隔离版本、启动Agent、续跑、匿名和汇总。"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tarfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "aiwritepaper-academic-writing"
VERSIONS = {
    "A": {"label": "v1.9.1", "ref": "v1.9.1"},
    "B": {"label": "v2.1.0-rc.2", "ref": "v2.1.0-rc.2"},
}
TOPICS = {
    "circuit": {
        "direction": "electronic-circuit-design",
        "title": "基于ESP32的室内空气质量多传感器监测节点电路设计",
    },
    "apos": {
        "direction": "mathematics-education",
        "title": "APOS理论视角下高中函数概念教学设计研究",
    },
    "review": {
        "direction": "literature-review-synthesis",
        "title": "大语言模型支持形成性评价的研究进展与证据综合",
    },
}
AGENTS = {
    "codex": {"binary": "codex", "model": "gpt-5.6-sol", "skill_root": ".codex/skills"},
    "grok": {"binary": "grok", "model": "grok-4.6", "skill_root": ".grok/skills"},
    "antigravity": {"binary": "agy", "model": "gemini-3.8-flash-high", "skill_root": ".agents/skills"},
}
PROMPT = "使用 aiwritepaper-academic-writing 完成《{title}》。只使用真实材料；按Skill持续完成正文、配图、DOCX、PDF和验收，不要停在计划。"
MANIFEST = "ab-manifest.json"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    if mode is not None:
        os.chmod(path, mode)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON根对象无效: {path}")
    return payload


def skill_version(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("version:"):
            return line.split(":", 1)[1].strip().strip('"\'')
    raise ValueError(f"Skill缺少版本: {path}")


def extract_ref(ref: str, target: Path) -> None:
    """从本地仓库精确ref提取无Git元数据的只读快照。"""
    result = subprocess.run(
        ["git", "-C", str(ROOT), "archive", "--format=tar", ref],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"无法提取{ref}: {result.stderr.decode(errors='replace')}")
    target.mkdir(parents=True, exist_ok=False)
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        members = archive.getmembers()
        for member in members:
            candidate = (target / member.name).resolve()
            candidate.relative_to(target.resolve())
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError(f"版本快照含不允许的链接或设备: {member.name}")
        if sys.version_info >= (3, 12):
            archive.extractall(target, members=members, filter="data")
        else:
            archive.extractall(target, members=members)


def case_path(lab: Path, agent: str, topic: str, arm: str) -> Path:
    return lab / "runs" / agent / topic / f"{arm}-{VERSIONS[arm]['label']}"


def initialize(lab: Path, seed: int) -> dict[str, Any]:
    lab = lab.resolve()
    manifest_path = lab / MANIFEST
    if manifest_path.exists():
        payload = read_json(manifest_path)
        if payload.get("schema_version") != "1.0":
            raise ValueError("目标目录已有非A/B实验内容")
        return payload
    if lab.exists() and any(lab.iterdir()):
        raise ValueError("A/B根目录已存在且非空，拒绝覆盖")
    lab.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, Any]] = []
    for agent, agent_info in AGENTS.items():
        for topic, topic_info in TOPICS.items():
            for arm, version in VERSIONS.items():
                directory = case_path(lab, agent, topic, arm)
                directory.mkdir(parents=True)
                skill_dir = directory / agent_info["skill_root"] / SKILL_NAME
                extract_ref(version["ref"], skill_dir)
                actual = skill_version(skill_dir / "SKILL.md")
                expected = version["label"].removeprefix("v")
                if actual != expected:
                    raise ValueError(f"版本不一致: {directory}，实际{actual}，预期{expected}")
                prompt = PROMPT.format(title=topic_info["title"])
                (directory / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
                case = {
                    "case_id": f"{agent}__{topic}__{arm}", "agent": agent,
                    "agent_label": "Antigravity CLI" if agent == "antigravity" else agent,
                    "model": agent_info["model"], "topic": topic, "direction_id": topic_info["direction"],
                    "title": topic_info["title"], "arm": arm, "version": version["label"],
                    "version_ref": version["ref"], "skill_file": str((skill_dir / "SKILL.md").relative_to(directory)),
                    "skill_sha256": sha(skill_dir / "SKILL.md"), "directory": str(directory),
                    "status": "PENDING", "attempts": 0, "created_at": now(),
                }
                write_json(directory / "case-manifest.json", case)
                cases.append(case)
    order = [case["case_id"] for case in cases]
    random.Random(seed).shuffle(order)
    payload = {
        "schema_version": "1.0", "created_at": now(), "seed": seed,
        "source_repository": str(ROOT), "cases": cases, "randomized_order": order,
        "scope_note": "只改变Skill版本；不同版本位于独立项目目录，不切换全局仓库。",
    }
    write_json(manifest_path, payload)
    return payload


def case_command(case: dict[str, Any]) -> list[str]:
    directory = Path(case["directory"])
    prompt = (directory / "prompt.txt").read_text(encoding="utf-8").strip()
    if case["agent"] == "codex":
        return [
            "codex", "--search", "exec", "-C", str(directory), "--skip-git-repo-check",
            "-m", case["model"], "-s", "workspace-write",
            "-o", str(directory / "runner-final-message.txt"), prompt,
        ]
    if case["agent"] == "grok":
        return [
            "grok", "--cwd", str(directory), "-m", case["model"],
            "--permission-mode", "auto", "--output-format", "json", "-p", prompt,
        ]
    return [
        "agy", "--new-project", "--model", case["model"], "--effort", "high",
        "--dangerously-skip-permissions", "--print-timeout", "8h",
        "--output-format", "json", "-p", prompt,
    ]


def doctor(lab: Path) -> tuple[dict[str, Any], bool]:
    manifest = read_json(lab / MANIFEST)
    checks: dict[str, Any] = {"checked_at": now(), "agents": {}, "versions": []}
    ok = True
    for agent, info in AGENTS.items():
        binary = shutil.which(info["binary"])
        row: dict[str, Any] = {"binary": binary, "ready": bool(binary)}
        if binary:
            probe = {
                "codex": [binary, "login", "status"],
                "grok": [binary, "models"],
                "antigravity": [binary, "models"],
            }[agent]
            cwd = next(Path(case["directory"]) for case in manifest["cases"] if case["agent"] == agent)
            result = subprocess.run(probe, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=60, check=False)
            output = result.stdout[-4000:]
            row.update({"probe_exit": result.returncode, "probe_output": output})
            if result.returncode != 0 or "not authenticated" in output.lower():
                row["ready"] = False
            if agent == "antigravity":
                if AGENTS["antigravity"]["model"] not in output:
                    row["ready"] = False
                discoveries = []
                for arm in VERSIONS:
                    representative = next(
                        Path(case["directory"]) for case in manifest["cases"]
                        if case["agent"] == "antigravity" and case["arm"] == arm
                    )
                    skill_probe = subprocess.run(
                        [binary, "--new-project", "--model", AGENTS["antigravity"]["model"],
                         "--output-format", "json", "--print-timeout", "1m", "-p", "/skills"],
                        cwd=representative, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, timeout=90, check=False,
                    )
                    expected_skill = str((representative / AGENTS["antigravity"]["skill_root"] / SKILL_NAME / "SKILL.md").resolve())
                    discovered = skill_probe.returncode == 0 and expected_skill in skill_probe.stdout
                    discoveries.append({"arm": arm, "path": expected_skill, "discovered": discovered})
                    if not discovered:
                        row["ready"] = False
                row["skill_discoveries"] = discoveries
                row["skill_discovered"] = all(item["discovered"] for item in discoveries)
        checks["agents"][agent] = row
        ok = ok and row["ready"]
    for case in manifest["cases"]:
        directory = Path(case["directory"])
        skill_file = directory / case["skill_file"]
        actual = skill_version(skill_file) if skill_file.is_file() else None
        expected = case["version"].removeprefix("v")
        valid = actual == expected and sha(skill_file) == case["skill_sha256"] if skill_file.is_file() else False
        checks["versions"].append({"case_id": case["case_id"], "expected": expected, "actual": actual, "valid": valid})
        ok = ok and valid
    checks["status"] = "READY" if ok else "BLOCKED"
    write_json(lab / "doctor-report.json", checks)
    return checks, ok


def selected_cases(manifest: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    by_id = {case["case_id"]: case for case in manifest["cases"]}
    result = []
    for case_id in manifest["randomized_order"]:
        case = by_id[case_id]
        if args.agent and case["agent"] not in args.agent:
            continue
        if args.version and case["version"] not in args.version:
            continue
        if args.topic and case["topic"] not in args.topic:
            continue
        if case.get("status") == "COMPLETE" and not args.rerun:
            continue
        result.append(case)
    return result[: args.limit] if args.limit else result


def inspect_delivery(directory: Path) -> dict[str, Any]:
    docx = list(directory.glob("*.docx"))
    pdf = list(directory.glob("*.pdf"))
    adjudication = directory / "14-adjudicated-status.json"
    body = directory / "07-paper-full.md"
    complete = body.is_file() and bool(docx) and bool(pdf) and adjudication.is_file()
    authority = None
    if adjudication.is_file():
        try:
            authority = read_json(adjudication).get("authoritative_status")
        except (OSError, ValueError, json.JSONDecodeError):
            authority = None
    return {
        "complete_files": complete, "body": body.is_file(), "docx": [path.name for path in docx],
        "pdf": [path.name for path in pdf], "adjudication": adjudication.is_file(),
        "authoritative_status": authority,
    }


def archive_previous_attempt(directory: Path, attempt: int) -> Path | None:
    """把失败/中断输出移入审计目录，保留固定Prompt和版本Skill。"""
    preserved = {".codex", ".grok", ".agents", ".attempts", "prompt.txt", "case-manifest.json"}
    candidates = [item for item in directory.iterdir() if item.name not in preserved]
    if not candidates:
        return None
    target = directory / ".attempts" / f"attempt-{attempt:03d}"
    if target.exists():
        raise ValueError(f"尝试归档目录已存在: {target}")
    target.mkdir(parents=True)
    for item in candidates:
        shutil.move(str(item), str(target / item.name))
    return target


def run_cases(lab: Path, args: argparse.Namespace) -> int:
    manifest_path = lab / MANIFEST
    manifest = read_json(manifest_path)
    cases = selected_cases(manifest, args)
    if not cases:
        print(json.dumps({"status": "NOTHING_TO_RUN"}, ensure_ascii=False))
        return 0
    if args.dry_run:
        print(json.dumps({"status": "DRY_RUN", "cases": [
            {"case_id": case["case_id"], "directory": case["directory"], "command": case_command(case)}
            for case in cases
        ]}, ensure_ascii=False, indent=2))
        return 0
    health, _ = doctor(lab)
    blocked_agents = sorted({case["agent"] for case in cases if not health["agents"][case["agent"]]["ready"]})
    if blocked_agents:
        print(json.dumps({"status": "BLOCKED", "agents": blocked_agents,
                          "doctor_report": str(lab / "doctor-report.json")}, ensure_ascii=False))
        return 2
    failures = 0
    for case in cases:
        binary = shutil.which(AGENTS[case["agent"]]["binary"])
        if not binary:
            case.update(status="BLOCKED", error="AGENT_BINARY_MISSING", finished_at=now())
            failures += 1
            write_json(manifest_path, manifest)
            continue
        directory = Path(case["directory"])
        archived = None
        if int(case.get("attempts", 0)) > 0 and case.get("status") != "COMPLETE":
            archived = archive_previous_attempt(directory, int(case["attempts"]))
        case.update(status="RUNNING", attempts=int(case.get("attempts", 0)) + 1, started_at=now(), error=None)
        if archived is not None:
            case["previous_attempt_archive"] = str(archived)
        write_json(manifest_path, manifest)
        command = case_command(case)
        started = time.monotonic()
        try:
            with (directory / "runner-stdout.log").open("a", encoding="utf-8") as stdout, \
                 (directory / "runner-stderr.log").open("a", encoding="utf-8") as stderr:
                result = subprocess.run(command, cwd=directory, stdout=stdout, stderr=stderr,
                                        timeout=args.timeout_hours * 3600, check=False, text=True)
            exit_code = result.returncode
        except KeyboardInterrupt:
            case.update(status="FINISHED_INCOMPLETE", exit_code=130, error="INTERRUPTED",
                        elapsed_seconds=round(time.monotonic() - started, 1), finished_at=now())
            write_json(directory / "case-manifest.json", case)
            write_json(manifest_path, manifest)
            return 130
        except subprocess.TimeoutExpired:
            exit_code = 124
            case["error"] = "TIMEOUT"
        except OSError as exc:
            exit_code = 127
            case["error"] = str(exc)
        delivery = inspect_delivery(directory)
        case.update(
            status="COMPLETE" if exit_code == 0 and delivery["complete_files"] else "FINISHED_INCOMPLETE",
            exit_code=exit_code, elapsed_seconds=round(time.monotonic() - started, 1),
            delivery=delivery, finished_at=now(),
        )
        write_json(directory / "case-manifest.json", case)
        write_json(manifest_path, manifest)
        if case["status"] != "COMPLETE":
            failures += 1
    return 1 if failures else 0


def status(lab: Path) -> dict[str, Any]:
    manifest = read_json(lab / MANIFEST)
    counts: dict[str, int] = {}
    rows = []
    for case in manifest["cases"]:
        delivery = inspect_delivery(Path(case["directory"]))
        current = "COMPLETE" if delivery["complete_files"] else case.get("status", "PENDING")
        counts[current] = counts.get(current, 0) + 1
        rows.append({"case_id": case["case_id"], "version": case["version"], "status": current,
                     "final_status": (delivery.get("authoritative_status") or {}).get("final_status")})
    payload = {"status": "OK", "counts": counts, "cases": rows}
    write_json(lab / "status-report.json", payload)
    return payload


def make_blind(lab: Path, seed: int) -> dict[str, Any]:
    manifest = read_json(lab / MANIFEST)
    complete = [case for case in manifest["cases"] if inspect_delivery(Path(case["directory"]))["complete_files"]]
    identifiers = [f"R{number:03d}" for number in range(1, len(complete) + 1)]
    random.Random(seed).shuffle(identifiers)
    mapping = []
    blind_root = lab / "blind"
    packages = lab / "review-packages"
    if (lab / "blind-map.private.json").exists():
        raise ValueError("匿名映射已存在，拒绝重新随机化")
    for case, review_id in zip(complete, identifiers):
        source = Path(case["directory"])
        target = blind_root / review_id
        target.mkdir(parents=True, exist_ok=False)
        ignored = {".codex", ".grok", ".agents", ".audit-logs", "case-manifest.json", "prompt.txt",
                   "paper-request.json", "run-params.md", "task-selection.json", "00-profile-selection.json",
                   "00-prompt-composition.json", "final-execution-prompt.md", "runner-stdout.log", "runner-stderr.log",
                   "runner-final-message.txt"}
        for item in source.iterdir():
            if item.name in ignored or item.name.startswith("final-execution-prompt."):
                continue
            destination = target / item.name
            if item.is_dir():
                shutil.copytree(item, destination)
            elif item.is_file():
                shutil.copy2(item, destination)
        original_manifest = read_json(source / "run-manifest.json")
        sanitized = {
            "direction_id": case["direction_id"], "docx": original_manifest.get("docx"),
            "pdf": original_manifest.get("pdf"), "blind_review_id": review_id,
        }
        write_json(target / "run-manifest.json", sanitized)
        adjudication_path = target / "14-adjudicated-status.json"
        if adjudication_path.is_file():
            adjudication = read_json(adjudication_path)
            adjudication["run_identity"] = {"review_id": review_id, "identity_blinded": True}
            write_json(adjudication_path, adjudication)
        output = packages / f"{review_id}.json"
        evaluator = ROOT / "eval/build_review_package.py"
        result = subprocess.run([sys.executable, str(evaluator), "--root", str(target), "--output", str(output)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode != 0:
            raise ValueError(f"冻结{review_id}失败: {result.stdout}{result.stderr}")
        mapping.append({"review_id": review_id, "case_id": case["case_id"], "agent": case["agent"],
                        "topic": case["topic"], "arm": case["arm"], "version": case["version"]})
    private = {"schema_version": "1.0", "created_at": now(), "seed": seed, "mapping": mapping}
    write_json(lab / "blind-map.private.json", private, mode=0o600)
    public = {"status": "READY", "packages": [item["review_id"] for item in mapping],
              "review_directory": str(blind_root), "mapping_file": "PRIVATE_NOT_FOR_REVIEWER"}
    write_json(lab / "blind-status.json", public)
    return public


def summarize(lab: Path) -> dict[str, Any]:
    mapping = read_json(lab / "blind-map.private.json")["mapping"]
    reviews = lab / "reviews"
    rows = []
    for item in mapping:
        path = reviews / f"{item['review_id']}.json"
        if not path.is_file():
            rows.append({**item, "review_status": "MISSING"})
            continue
        review = read_json(path)
        rows.append({**item, "review_status": "READY", "total": review.get("total"),
                     "scores": review.get("scores"), "issues": review.get("issues", [])})
    pairs = []
    groups: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["agent"], row["topic"]), {})[row["arm"]] = row
    for (agent, topic), arms in groups.items():
        a, b = arms.get("A"), arms.get("B")
        if not a or not b or not isinstance(a.get("total"), (int, float)) or not isinstance(b.get("total"), (int, float)):
            pairs.append({"agent": agent, "topic": topic, "status": "INCOMPLETE"})
            continue
        critical_b = sum(str(issue.get("severity", "")).upper() == "CRITICAL" for issue in b.get("issues", []) if isinstance(issue, dict))
        delta = round(float(b["total"]) - float(a["total"]), 2)
        pairs.append({"agent": agent, "topic": topic, "status": "PASS" if delta >= -1.5 and critical_b == 0 else "FAIL",
                      "a_total": a["total"], "b_total": b["total"], "delta": delta, "b_critical": critical_b})
    payload = {"schema_version": "1.0", "generated_at": now(), "rows": rows, "pairs": pairs,
               "complete_reviews": sum(row.get("review_status") == "READY" for row in rows)}
    write_json(lab / "ab-results.json", payload)
    lines = ["# AIWritePaper A/B结果", "", f"- 已评审：{payload['complete_reviews']}/{len(rows)}", "",
             "| Agent | 题目 | A | B | 差值 | 判定 |", "|---|---|---:|---:|---:|---|"]
    for pair in pairs:
        lines.append(f"| {pair['agent']} | {pair['topic']} | {pair.get('a_total', '-')} | {pair.get('b_total', '-')} | {pair.get('delta', '-')} | {pair['status']} |")
    (lab / "ab-results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="AIWritePaper隔离A/B控制器")
    value.add_argument("--lab", required=True, type=Path, help="独立A/B根目录")
    sub = value.add_subparsers(dest="action", required=True)
    init = sub.add_parser("init", help="一次建立18个版本隔离目录")
    init.add_argument("--seed", type=int, default=2102)
    sub.add_parser("doctor", help="检查登录、CLI与Skill版本")
    run = sub.add_parser("run", help="按随机顺序执行并可断点续跑")
    run.add_argument("--agent", action="append", choices=sorted(AGENTS))
    run.add_argument("--version", action="append", choices=[item["label"] for item in VERSIONS.values()])
    run.add_argument("--topic", action="append", choices=sorted(TOPICS))
    run.add_argument("--limit", type=int)
    run.add_argument("--timeout-hours", type=int, default=8)
    run.add_argument("--rerun", action="store_true")
    run.add_argument("--dry-run", action="store_true")
    sub.add_parser("status", help="核对真实文件与运行状态")
    blind = sub.add_parser("blind", help="生成匿名副本和私有映射")
    blind.add_argument("--seed", type=int, default=5102)
    sub.add_parser("summarize", help="读取reviews目录并生成A/B表")
    return value


def main() -> int:
    args = parser().parse_args()
    lab = args.lab.expanduser().resolve()
    try:
        if args.action == "init":
            result = initialize(lab, args.seed)
        elif args.action == "doctor":
            result, ready = doctor(lab)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if ready else 2
        elif args.action == "run":
            return run_cases(lab, args)
        elif args.action == "status":
            result = status(lab)
        elif args.action == "blind":
            result = make_blind(lab, args.seed)
        else:
            result = summarize(lab)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
