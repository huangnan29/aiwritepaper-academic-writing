#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];RESUME=ROOT/"scripts/prepare_resume.py";REVISE=ROOT/"scripts/compose_revision.py"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class ResumeRevisionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);(self.root/"final-execution-prompt.md").write_text("原提示词");(self.root/"00-prompt-composition.json").write_text(json.dumps({"sha256":sha(self.root/"final-execution-prompt.md")}));(self.root/"stage.md").write_text("阶段")
        stages={n:{"status":("PASS" if n=="EVIDENCE" else "PENDING"),"outputs":([{"file":"stage.md","sha256":sha(self.root/"stage.md")}] if n=="EVIDENCE" else [])} for n in ["EVIDENCE","OUTLINE","DRAFT","FIGURES","DOCUMENTS","VALIDATION"]}
        (self.root/"00-execution-checkpoints.json").write_text(json.dumps({"stages":stages}));(self.root/"run-manifest.json").write_text(json.dumps({"execution_checkpoints":"00-execution-checkpoints.json"}))
    def tearDown(self):self.temp.cleanup()
    def test_resume_freezes_valid_stage(self):
        r=subprocess.run([sys.executable,str(RESUME),"--root",str(self.root)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);p=json.loads((self.root/"00-resume-plan.json").read_text());self.assertEqual(p["resume_from"],"OUTLINE");self.assertEqual(p["frozen_stages"],["EVIDENCE"])
    def test_resume_rejects_changed_prompt(self):
        (self.root/"final-execution-prompt.md").write_text("被改写");r=subprocess.run([sys.executable,str(RESUME),"--root",str(self.root)],capture_output=True,text=True);self.assertNotEqual(r.returncode,0)
    def test_revision_composition_preserves_inputs(self):
        (self.root/"request.md").write_text("导师意见");(self.root/"rules.md").write_text("修改规则");r=subprocess.run([sys.executable,str(REVISE),"--base-prompt",str(self.root/"final-execution-prompt.md"),"--request",str(self.root/"request.md"),"--rules",str(self.root/"rules.md"),"--output",str(self.root/"revision.md"),"--report",str(self.root/"revision-report.json")],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertIn("导师意见",(self.root/"revision.md").read_text())
if __name__=="__main__":unittest.main()
