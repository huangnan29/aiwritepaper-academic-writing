#!/usr/bin/env python3
from pathlib import Path
import json,subprocess,sys,tempfile,unittest
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/verify_quality_package.py"
class QualityTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();r=Path(self.t.name);(r/"figures").mkdir();self.r=r
  data={"run-manifest.json":{"direction_id":"electronic-circuit-design"},"15-quality-scorecard.json":{"direction_id":"electronic-circuit-design","scores":{"evidence":23,"content":18,"structure":14,"figures":14,"documents":14,"integrity":9},"critical":[],"important":[],"total":92},"claim-evidence-map.json":{"claims":[{"location":"结论","importance":"CONCLUSION","evidence_ids":["S1"]}]},"figures/figure-manifest.json":{"figures":[{"figure_id":"f1"}]},"figures/figure-semantic-audit.json":{"figures":[{"figure_id":"f1","status":"PASS"}]},"16-document-visual-audit.json":{"checks":[{"checkpoint":x,"status":"PASS"} for x in ["cover","primary_abstract","toc","complex_table","complex_formula","representative_figure","references","last_page"]]}}
  for p,v in data.items():(r/p).write_text(json.dumps(v,ensure_ascii=False))
 def tearDown(self):self.t.cleanup()
 def runq(self):return subprocess.run([sys.executable,str(SCRIPT),"--root",str(self.r)],capture_output=True,text=True)
 def test_quality_ok(self):self.assertEqual(self.runq().returncode,0);self.assertEqual(json.loads((self.r/"17-quality-verification.json").read_text())["status"],"QUALITY_OK")
 def test_critical_fails(self):p=self.r/"15-quality-scorecard.json";x=json.loads(p.read_text());x["critical"]=["错误"];p.write_text(json.dumps(x));self.assertNotEqual(self.runq().returncode,0)
if __name__=="__main__":unittest.main()
