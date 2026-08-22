"""validate_evidence 的 P0 单元测试。"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_evidence as validator  # noqa: E402


class ValidateEvidenceTests(unittest.TestCase):
    """覆盖真实证据硬门槛、模拟证据和 JSON 报告。"""

    def _write_manifest(self, root: Path, entries: list[dict[str, object]]) -> None:
        (root / "evidence-manifest.json").write_text(
            json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _base_entry(level: str, **updates: object) -> dict[str, object]:
        entry: dict[str, object] = {
            "id": "e-1",
            "claim": "模拟流程输出，不代表真实系统结果",
            "evidence_level": level,
            "sources": ["模拟输入"],
            "command": "python simulate.py",
            "outputs": [],
            "sha256": {},
            "limitations": ["仅用于测试"],
        }
        entry.update(updates)
        return entry

    def test_模拟证据合法通过(self) -> None:
        """模拟证据可以记录，但必须保留其非真实边界。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write_manifest(root, [self._base_entry("SIMULATED")])

            report = validator.validate_manifest(root)

            self.assertEqual(report.status, validator.STATUS_PASS)
            self.assertEqual(report.errors, [])

    def test_外部核验必须提供来源(self) -> None:
        """VERIFIED_EXTERNAL 不能只有结论而没有可复核来源。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self._base_entry(
                "VERIFIED_EXTERNAL",
                claim="某标准定义了接口约束",
                sources=[],
                command="",
                limitations=["仅支持定义性主张"],
            )
            self._write_manifest(root, [entry])
            report = validator.validate_manifest(root)

        self.assertEqual(report.status, validator.STATUS_FAIL)
        self.assertTrue(any("必须提供可核验来源" in error for error in report.errors))

    def test_证据清单不得读取项目外路径(self) -> None:
        """--manifest 不能借绝对路径读取其他项目文件。"""

        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "paper"
            root.mkdir()
            outside = parent / "outside.json"
            outside.write_text('{"entries": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
                validator.resolve_manifest(root, outside)

    def test_真实证据缺命令原始输出和哈希失败(self) -> None:
        """OBSERVED_REAL_SYSTEM 不允许用空字段代替运行证据。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self._base_entry(
                "OBSERVED_REAL_SYSTEM",
                claim="观察到真实系统输出",
                command="",
                outputs=[],
                sha256={},
            )
            self._write_manifest(root, [entry])

            report = validator.validate_manifest(root)

            self.assertEqual(report.status, validator.STATUS_FAIL)
            self.assertTrue(any("真实运行命令" in error for error in report.errors))
            self.assertTrue(any("原始输出" in error for error in report.errors))
            self.assertTrue(any("SHA-256" in error for error in report.errors))

    def test_模拟证据不得声称真实系统结果(self) -> None:
        """模拟级别的主张不能伪装为线上实测。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self._base_entry("HARDCODED_EXAMPLE", claim="真实系统已部署并实测提升")
            self._write_manifest(root, [entry])

            report = validator.validate_manifest(root)

            self.assertEqual(report.status, validator.STATUS_FAIL)
            self.assertTrue(any("疑似声称真实系统结果" in error for error in report.errors))

    def test_模拟与真实混合表述不得绕过(self) -> None:
        """出现“模拟”不能自动抵消后面的真实系统实测断言。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entry = self._base_entry(
                "SIMULATED",
                claim="模拟性能数据已在真实系统中实测，准确率为98%",
            )
            self._write_manifest(root, [entry])
            report = validator.validate_manifest(root)

        self.assertEqual(report.status, validator.STATUS_FAIL)
        self.assertTrue(any("疑似声称真实系统结果" in error for error in report.errors))

    def test_模拟输出文件不得夹带真实实测断言(self) -> None:
        """清单 claim 合规时也要检查其项目内原始文本输出。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "simulation-result.txt"
            output.write_text("真实系统实测准确率为98%", encoding="utf-8")
            entry = self._base_entry(
                "SIMULATED",
                outputs=["simulation-result.txt"],
            )
            self._write_manifest(root, [entry])
            report = validator.validate_manifest(root)

        self.assertEqual(report.status, validator.STATUS_FAIL)
        self.assertTrue(any("输出疑似声称真实系统结果" in error for error in report.errors))

    def test_论文不得把模拟数值改写成实测(self) -> None:
        """证据 claim 合规时，正文仍不能把同一数值包装成真实系统结果。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chapters").mkdir()
            (root / "chapters/07.md").write_text(
                "真实系统实测准确率为98%", encoding="utf-8"
            )
            entry = self._base_entry(
                "SIMULATED",
                claim="模拟准确率为98%，不代表真实系统结果",
            )
            self._write_manifest(root, [entry])
            report = validator.validate_manifest(root)

        self.assertEqual(report.status, validator.STATUS_FAIL)
        self.assertTrue(any("写成真实实测" in error for error in report.errors))

    def test_真实证据只有哈希仍不足以通过(self) -> None:
        """文件与哈希不能证明命令实际执行，还必须有 execution_record。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw-output.txt"
            raw.write_text("真实命令原始输出\n", encoding="utf-8")
            digest = hashlib.sha256(raw.read_bytes()).hexdigest()
            entry = self._base_entry(
                "OBSERVED_REAL_SYSTEM",
                claim="观察到测试命令的原始输出",
                command="python test.py",
                outputs=["raw-output.txt"],
                sha256={"raw-output.txt": digest},
                execution_record="execution-record.json",
            )
            (root / "execution-record.json").write_text(
                json.dumps(
                    {
                        "run_id": "test-run-1",
                        "started_at": "2026-08-22T00:00:00Z",
                        "finished_at": "2026-08-22T00:00:01Z",
                        "command": ["python", "test.py"],
                        "command_argv": ["python", "test.py"],
                        "cwd": str(root),
                        "return_code": 0,
                        "timed_out": False,
                        "output_log": "raw-output.txt",
                        "sha256": digest,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self._write_manifest(root, [entry])

            report = validator.validate_manifest(root)

            self.assertEqual(report.status, validator.STATUS_FAIL)
            self.assertTrue(any("execution_record" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
