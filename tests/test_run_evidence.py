"""run_evidence 安全执行器与真实证据执行记录的单元测试。"""

from __future__ import annotations

import hashlib
import io
import json
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_evidence  # noqa: E402
import validate_evidence as validator  # noqa: E402


class RunEvidenceTests(unittest.TestCase):
    """覆盖成功、非零、超时、路径越界和执行记录篡改。"""

    @staticmethod
    def _call_main(arguments: list[str]) -> int:
        """捕获 CLI 摘要，保持单元测试输出干净。"""

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return run_evidence.main(arguments)

    @staticmethod
    def _entry(record: dict[str, object], root: Path) -> dict[str, object]:
        """根据执行记录构造可校验的观察证据条目。"""

        output_log = str(record["output_log"])
        return {
            "id": str(record["id"]),
            "claim": str(record["claim"]),
            "evidence_level": "OBSERVED_REAL_SYSTEM",
            "sources": ["本地命令执行记录"],
            "command": shlex.join([str(item) for item in record["command"]]),
            "outputs": [output_log],
            "sha256": {output_log: str(record["sha256"])},
            "limitations": ["仅覆盖此次本地命令运行"],
            "execution_record": "records/execution.json",
        }

    @staticmethod
    def _write_manifest(root: Path, entry: dict[str, object]) -> None:
        """写入证据清单。"""

        (root / "evidence-manifest.json").write_text(
            json.dumps({"entries": [entry]}, ensure_ascii=False), encoding="utf-8"
        )

    def _run_success(self, root: Path) -> dict[str, object]:
        """执行一次成功命令并返回执行记录。"""

        result = self._call_main(
            [
                "--root",
                str(root),
                "--id",
                "e-1",
                "--claim",
                "观察到真实命令输出",
                "--output-log",
                "logs/output.log",
                "--record-output",
                "records/execution.json",
                "--timeout",
                "5",
                "--",
                sys.executable,
                "-c",
                "import sys; print('标准输出'); print('标准错误', file=sys.stderr)",
            ]
        )
        self.assertEqual(result, 0)
        return json.loads((root / "records/execution.json").read_text(encoding="utf-8"))

    def test_成功命令生成记录且验证通过(self) -> None:
        """成功命令的 stdout、stderr 和日志摘要可以通过真实证据校验。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self._run_success(root)
            log = root / str(record["output_log"])
            self.assertIn("标准输出", log.read_text(encoding="utf-8"))
            self.assertIn("标准错误", log.read_text(encoding="utf-8"))
            self.assertEqual(record["return_code"], 0)
            self.assertFalse(record["timed_out"])
            self.assertTrue(record["run_id"])
            self.assertEqual(record["sha256"], hashlib.sha256(log.read_bytes()).hexdigest())

            entry = self._entry(record, root)
            self._write_manifest(root, entry)
            report = validator.validate_manifest(root)
            self.assertEqual(report.status, validator.STATUS_PASS, report.errors)

    def test_非零命令记录失败且不能作为真实证据(self) -> None:
        """非零返回码必须被真实证据校验器拒绝。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self._call_main(
                [
                    "--root",
                    str(root),
                    "--id",
                    "e-2",
                    "--claim",
                    "非零命令",
                    "--output-log",
                    "output.log",
                    "--record-output",
                    "execution.json",
                    "--",
                    sys.executable,
                    "-c",
                    "print('失败输出'); raise SystemExit(3)",
                ]
            )
            self.assertEqual(result, 3)
            record = json.loads((root / "execution.json").read_text(encoding="utf-8"))
            self.assertEqual(record["return_code"], 3)
            entry = self._entry(record, root)
            entry["execution_record"] = "execution.json"
            self._write_manifest(root, entry)
            report = validator.validate_manifest(root)
            self.assertEqual(report.status, validator.STATUS_FAIL)
            self.assertTrue(any("return_code 不是 0" in error for error in report.errors))

    def test_超时清理进程组并记录超时(self) -> None:
        """超时命令被终止并标记 timed_out，不能伪装成成功观察。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self._call_main(
                [
                    "--root",
                    str(root),
                    "--id",
                    "e-3",
                    "--claim",
                    "超时命令",
                    "--output-log",
                    "timeout.log",
                    "--record-output",
                    "timeout.json",
                    "--timeout",
                    "0.1",
                    "--",
                    sys.executable,
                    "-c",
                    "import time; print('开始'); time.sleep(10)",
                ]
            )
            self.assertEqual(result, 124)
            record = json.loads((root / "timeout.json").read_text(encoding="utf-8"))
            self.assertTrue(record["timed_out"])
            self.assertNotEqual(record["return_code"], 0)

    def test_输出和记录路径越界被拒绝(self) -> None:
        """输出路径和执行记录路径都不能写到项目根目录之外。"""

        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "project"
            root.mkdir()
            outside_log = parent / "outside.log"
            result = self._call_main(
                [
                    "--root",
                    str(root),
                    "--id",
                    "e-4",
                    "--claim",
                    "越界路径",
                    "--output-log",
                    "../outside.log",
                    "--record-output",
                    "record.json",
                    "--",
                    sys.executable,
                    "-c",
                    "print('不应执行')",
                ]
            )
            self.assertEqual(result, 2)
            self.assertFalse(outside_log.exists())

            result = self._call_main(
                [
                    "--root",
                    str(root),
                    "--id",
                    "e-4",
                    "--claim",
                    "越界记录",
                    "--output-log",
                    "output.log",
                    "--record-output",
                    "../outside.json",
                    "--",
                    sys.executable,
                    "-c",
                    "print('不应执行')",
                ]
            )
            self.assertEqual(result, 2)
            self.assertFalse((parent / "outside.json").exists())

    def test_篡改执行记录或日志哈希失败(self) -> None:
        """执行记录的返回码或日志摘要被篡改时必须失败。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = self._run_success(root)
            entry = self._entry(record, root)
            self._write_manifest(root, entry)
            record_path = root / "records/execution.json"
            tampered = json.loads(record_path.read_text(encoding="utf-8"))
            tampered["return_code"] = 0
            tampered["sha256"] = "0" * 64
            record_path.write_text(
                json.dumps(tampered, ensure_ascii=False), encoding="utf-8"
            )
            report = validator.validate_manifest(root)
            self.assertEqual(report.status, validator.STATUS_FAIL)
            self.assertTrue(
                any(
                    "execution_record.sha256" in error
                    and ("日志内容" in error or "manifest" in error)
                    for error in report.errors
                )
            )

    def test_命令参数疑似凭证时拒绝记录(self) -> None:
        """执行记录不能持久化 API Key 或密码参数。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self._call_main(
                [
                    "--root", str(root),
                    "--id", "secret-1",
                    "--claim", "凭证测试",
                    "--output-log", "secret.log",
                    "--record-output", "secret.json",
                    "--",
                    sys.executable,
                    "--api-key=sk-test-secret-value",
                ]
            )

        self.assertEqual(result, 2)

    def test_陈旧伪造执行记录不能通过(self) -> None:
        """旧日志配合手写的历史执行时间不能冒充本次真实命令。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "old.log"
            log.write_text("旧输出", encoding="utf-8")
            digest = hashlib.sha256(log.read_bytes()).hexdigest()
            record = {
                "run_id": "fake-run",
                "id": "old-1",
                "claim": "观察到真实命令输出",
                "started_at": "2000-01-01T00:00:00Z",
                "finished_at": "2000-01-01T00:00:01Z",
                "command": ["echo", "never-ran"],
                "command_argv": ["echo", "never-ran"],
                "cwd": str(root),
                "return_code": 0,
                "timed_out": False,
                "output_log": "old.log",
                "sha256": digest,
            }
            record_path = root / "old-record.json"
            record_path.write_text(json.dumps(record), encoding="utf-8")
            entry = {
                "id": "old-1",
                "claim": "观察到真实命令输出",
                "evidence_level": "OBSERVED_REAL_SYSTEM",
                "sources": ["本地命令执行记录"],
                "command": ["echo", "never-ran"],
                "outputs": ["old.log"],
                "sha256": {"old.log": digest},
                "limitations": ["仅覆盖此次命令"],
                "execution_record": "old-record.json",
            }
            self._write_manifest(root, entry)
            report = validator.validate_manifest(root)

        self.assertEqual(report.status, validator.STATUS_FAIL)
        self.assertTrue(any("运行窗口" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
