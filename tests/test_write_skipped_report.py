#!/usr/bin/env python3
from pathlib import Path
import subprocess, sys, tempfile, unittest, json
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/write_skipped_report.py"
class SkipReportTests(unittest.TestCase):
    def setUp(self): self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/"run-manifest.json").write_text("{}")
    def tearDown(self): self.temp.cleanup()
    def execute(self,mode,status):
        return subprocess.run([sys.executable,str(SCRIPT),"--root",str(self.root),"--category","evidence","--mode",mode,"--skip-status",status,"--reason","不适用","--input","run-manifest.json","--output","report.json"],capture_output=True,text=True)
    def test_figures_only_allows_not_applicable(self):
        r=self.execute("FIGURES_ONLY","SKIPPED_NOT_APPLICABLE");self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads((self.root/"report.json").read_text())["status"],"SKIPPED_NOT_APPLICABLE")
    def test_full_build_rejects_skip(self): self.assertNotEqual(self.execute("FULL_BUILD","SKIPPED_NOT_APPLICABLE").returncode,0)
if __name__=="__main__":unittest.main()
