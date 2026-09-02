"""剪枝审计链的完整往返验证，所有测试输出仅在临时目录。"""
import json
from pathlib import Path
import subprocess
import sys
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_audit_views as fixtures

ROOT = Path(__file__).resolve().parents[1]


class PruningRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AuditViewTests()
        self.fixture.setUp()
        self.root, self.qa = self.fixture.root, self.fixture.qa
        (self.root / 'checked.png').write_bytes(b'\x89PNG\r\n\x1a\n' + b'fixture')
        (self.root / 'figures/figure-manifest.json').write_text('{"figures": []}')
        (self.root / '13-delivery-verification.json').write_text('{"warnings": []}')
        manifest = json.loads((self.root / 'run-manifest.json').read_text())
        manifest['document_profile'] = 'JOURNAL'
        (self.root / 'run-manifest.json').write_text(json.dumps(manifest))
        self.qa['figures'] = []
        self.qa['review']['issues']['items'] = []
        self.qa['document_checks'] = []
        for name in ['cover', 'primary_abstract', 'toc', 'complex_table', 'complex_formula', 'representative_figure', 'references', 'last_page']:
            if name in {'cover', 'toc', 'complex_table', 'complex_formula', 'representative_figure'}:
                item = {'checkpoint': name, 'status': 'NOT_APPLICABLE', 'reason': '测试期刊稿无此结构'}
            else:
                item = {'checkpoint': name, 'status': 'PASS', 'page': 1, 'checked_file': 'checked.png', 'visual_receipt': 'receipt.txt'}
            self.qa['document_checks'].append(item)
        self.docx(False)

    def tearDown(self):
        self.fixture.tearDown()

    def docx(self, formula):
        content = '<m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>' if formula else ''
        with zipfile.ZipFile(self.root / 'paper.docx', 'w') as archive:
            archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><w:body><w:p>' + content + '</w:p></w:body></w:document>')
            archive.writestr('word/styles.xml', '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style><w:tblPr/></w:style></w:styles>')

    def chain(self):
        (self.root / 'qa-review.json').write_text(json.dumps(self.qa))
        made = self.fixture.run_prepare()
        self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
        subprocess.run([sys.executable, str(ROOT / 'scripts/verify_quality_package.py'), '--root', str(self.root)], capture_output=True)
        return json.loads((self.root / '17-quality-verification.json').read_text())

    def test_unscored_self_is_partial_not_spurious_failure(self):
        result = self.chain()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['status'], 'QUALITY_PARTIAL')
        self.assertIsNone(result['metrics']['numeric_score'])
        self.assertFalse(result['metrics']['ninety_plus_verified'])

    def test_scored_self_cannot_become_independent(self):
        self.qa['review'].update(scores={'evidence': 25, 'content': 20, 'structure': 15, 'figures': 15, 'documents': 15, 'integrity': 10}, total=100)
        result = self.chain()
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['status'], 'QUALITY_PARTIAL')
        self.assertFalse(result['metrics']['ninety_plus_verified'])

    def test_formula_present_cannot_claim_not_applicable(self):
        self.docx(True)
        self.assertIn('DOCUMENT_VISUAL_NA_UNPROVEN', self.chain()['errors'])

    def test_stale_binding_is_not_resigned(self):
        self.qa['review']['reviewed_artifacts'] = {'07-paper-full.md': '0' * 64}
        (self.root / 'qa-review.json').write_text(json.dumps(self.qa))
        self.assertNotEqual(self.fixture.run_prepare().returncode, 0)
        self.assertFalse((self.root / '09-final-peer-review.json').exists())


if __name__ == '__main__':
    unittest.main()
