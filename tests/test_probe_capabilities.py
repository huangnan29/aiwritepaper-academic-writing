"""能力探测模块的稳定接口测试。"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))

import probe_capabilities


class ProbeCapabilitiesTest(unittest.TestCase):
    """验证 JSON 契约、图片能力边界和 CLI 输出。"""

    def test_all_p0_capabilities_have_stable_fields(self) -> None:
        """每项 P0 能力都必须有状态、证据和限制。"""

        with tempfile.TemporaryDirectory() as directory:
            report = probe_capabilities.probe_capabilities(Path(directory))

        self.assertEqual(tuple(report["capabilities"]), probe_capabilities.CAPABILITY_NAMES)
        self.assertEqual(report["schema_version"], "1.0")
        for name in probe_capabilities.CAPABILITY_NAMES:
            item = report["capabilities"][name]
            self.assertIn(item["status"], probe_capabilities.STATUSES)
            self.assertIsInstance(item["evidence"], list)
            self.assertIsInstance(item["limitations"], list)
            self.assertTrue(item["evidence"])
            self.assertTrue(item["limitations"])

    def test_missing_capability_key_is_runtime_error(self) -> None:
        """报告缺少能力项时不能因为其余项可用而返回成功。"""

        report = {
            "capabilities": {
                name: {"status": "AVAILABLE"}
                for name in probe_capabilities.CAPABILITY_NAMES[:-1]
            }
        }
        self.assertEqual(
            probe_capabilities._exit_code(report),
            probe_capabilities.EXIT_RUNTIME_ERROR,
        )

    def test_image_generator_is_unverified_without_explicit_declaration(self) -> None:
        """未声明时不能从 shell 工具推断图片生成能力。"""

        result = probe_capabilities._probe_image_generator(None)

        self.assertEqual(result.status, "UNVERIFIED")
        self.assertIn("显式 CLI", " ".join(result.evidence))
        self.assertNotIn("AVAILABLE", result.evidence)

    def test_image_generator_declaration_without_artifact_stays_unverified(self) -> None:
        """显式声明没有真实产物时仍不能升级为 AVAILABLE。"""

        result = probe_capabilities._probe_image_generator("gpt-image-2")
        self.assertEqual(result.status, "UNVERIFIED")
        self.assertIn("gpt-image-2", " ".join(result.evidence))

        secret_result = probe_capabilities._probe_image_generator("tool sk-test-secret-value")
        secret_text = " ".join(secret_result.evidence + secret_result.limitations)
        self.assertNotIn("sk-test-secret-value", secret_text)
        self.assertIn("REDACTED_SECRET", secret_text)

    def test_image_generator_valid_artifact_only_marks_partial(self) -> None:
        """声明加图片文件仍不能单独证明工具在本次被真实调用。"""

        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "generated.png"
            artifact.write_bytes(b"\x89PNG\r\n\x1a\n" + b"valid-image")
            result = probe_capabilities._probe_image_generator("gpt-image-2", artifact)

        self.assertEqual(result.status, "PARTIAL")

    def test_cli_json_and_output_file_are_machine_readable(self) -> None:
        """--json 与 --output 应产生可解析且不混入人类摘要的 JSON。"""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_path = root / "capabilities.json"
            image_path = root / "generated.png"
            image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"valid-image")
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = probe_capabilities.main(
                    [
                        "--root",
                        str(root),
                        "--json",
                        "--output",
                        str(output_path),
                        "--image-generator",
                        "test-generator",
                        "--image-generator-artifact",
                        str(image_path),
                    ]
                )

            report_from_stdout = json.loads(stdout.getvalue())
            report_from_file = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(report_from_stdout, report_from_file)
        self.assertEqual(exit_code, report_from_stdout["exit_code"])
        self.assertEqual(report_from_stdout["capabilities"]["IMAGE_GENERATOR"]["status"], "PARTIAL")
        self.assertEqual(stderr.getvalue(), "")

    def test_human_output_does_not_echo_environment_values(self) -> None:
        """人类摘要不应输出环境变量或外部命令原始日志。"""

        old_value = os.environ.get("CAPABILITY_PROBE_TEST_SECRET")
        os.environ["CAPABILITY_PROBE_TEST_SECRET"] = "secret-value-that-must-not-appear"
        try:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                probe_capabilities.main(["--root", "."])
        finally:
            if old_value is None:
                os.environ.pop("CAPABILITY_PROBE_TEST_SECRET", None)
            else:
                os.environ["CAPABILITY_PROBE_TEST_SECRET"] = old_value

        self.assertNotIn("secret-value-that-must-not-appear", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
