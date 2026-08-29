#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/capture_provenance.py"


class CaptureProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data/raw").mkdir(parents=True)
        (self.root / "data/receipts").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_register_captures_existing_raw_file(self):
        (self.root / "data/raw/input.csv").write_text("x,y\n1,2\n", encoding="utf-8")
        result = self.run_script(
            "register", "--root", str(self.root), "--source", "data/raw/input.csv",
            "--origin", "USER_PROVIDED", "--collection-method", "用户上传",
            "--collector", "user", "--receipt", "data/receipts/input.json",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads((self.root / "data/receipts/input.json").read_text())
        self.assertEqual(payload["receipt_type"], "REGISTER")
        self.assertEqual(payload["producer"]["name"], "capture_provenance.py")

    def test_run_captures_inputs_outputs_and_exit_code(self):
        (self.root / "data/raw/input.txt").write_text("input", encoding="utf-8")
        producer = self.root / "produce.py"
        producer.write_text("from pathlib import Path\nPath('data/output.txt').write_text('output')\n", encoding="utf-8")
        result = self.run_script(
            "run", "--root", str(self.root), "--engine", "python",
            "--engine-class", "CALCULATION", "--input", "data/raw/input.txt",
            "--input", "produce.py", "--output", "data/output.txt",
            "--receipt", "data/receipts/run.json", "--", sys.executable, "produce.py",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads((self.root / "data/receipts/run.json").read_text())
        self.assertEqual(payload["exit_code"], 0)
        self.assertEqual(payload["outputs"][0]["file"], "data/output.txt")


if __name__ == "__main__":
    unittest.main()
