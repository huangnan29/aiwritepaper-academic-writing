#!/usr/bin/env python3
"""文献、引用与数据来源检查器的隔离测试。"""

from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_evidence_integrity.py"
SPEC = importlib.util.spec_from_file_location("verify_evidence_integrity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


FIELDS = [
    "source_id", "title", "authors", "year", "doi", "url", "verification_source",
    "supported_claims", "chapters", "status", "evidence_role", "access_mode",
    "publication_status", "notes", "fulltext_locator", "page_locator", "source_file",
    "source_sha256", "citation_token",
]


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        self.markdown = self.root / "07-paper-full.md"
        self.markdown.write_text(
            "# 第1章 绪论\n正文主张[1]。\n\n# 参考文献\n[1] Example study.\n",
            encoding="utf-8",
        )
        self.manifest = {
            "model_label": "test-model", "skill_version": "1.9.0",
            "citation_mode": "NUMERIC", "research_claim_level": "DESIGN_ONLY",
            "execution_profile": "FULL_AUTONOMY",
            "profile_selection_report": "00-profile-selection.json",
            "run_mode": "FULL_BUILD", "direction_id": "electronic-circuit-design",
        }
        (self.root / "run-manifest.json").write_text(
            json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8"
        )
        capability_path = self.root / "00-capability-report.json"
        capability_path.write_text(json.dumps({
            "schema_version": "1.0", "agent_adapter": "test",
        }), encoding="utf-8")
        selector_script = Path(__file__).resolve().parents[1] / "scripts/select_execution_profile.py"
        (self.root / "00-profile-selection.json").write_text(json.dumps({
            "schema_version": "1.0", "selected_profile": "FULL_AUTONOMY",
            "model_label": "test-model", "capability_report": "00-capability-report.json",
            "capability_report_sha256": MODULE.sha256(capability_path),
            "selector": {
                "name": "select_execution_profile.py", "sha256": MODULE.sha256(selector_script),
            },
        }), encoding="utf-8")
        self.rows = [{
            "source_id": "S1", "title": "Example Study", "authors": "Author A",
            "year": "2024", "doi": "10.1000/example", "url": "https://example.org/fulltext",
            "verification_source": "Publisher full text", "supported_claims": "支持正文主张",
            "chapters": "第1章", "status": "VERIFIED_FULLTEXT", "evidence_role": "EVIDENCE",
            "access_mode": "OPEN_WEB", "publication_status": "PUBLISHED", "notes": "已读全文",
            "fulltext_locator": "https://example.org/fulltext", "page_locator": "section 2",
            "source_file": "", "source_sha256": "", "citation_token": "[1]",
        }]
        self.write_matrix()
        self.provenance = {
            "schema_version": "1.0", "research_claim_level": "DESIGN_ONLY", "datasets": [],
        }
        self.write_provenance()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_matrix(self) -> None:
        with (self.root / "03-evidence-matrix.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(self.rows)

    def write_provenance(self) -> None:
        (self.root / "data/data-provenance.json").write_text(
            json.dumps(self.provenance, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def resolved(item):
        source_id, doi, title = item
        return {
            "source_id": source_id, "doi": doi, "status": "RESOLVED_CROSSREF",
            "declared_title": title, "resolved_title": title, "similarity": 1.0,
            "mismatch": False,
        }

    def run_verifier(self, resolver=None) -> MODULE.EvidenceVerifier:
        verifier = MODULE.EvidenceVerifier(self.root)
        manifest = verifier.load_manifest(self.root / "run-manifest.json")
        verifier.verify_profile_selection(manifest)
        rows = verifier.load_matrix(self.root / "03-evidence-matrix.csv")
        verifier.verify_citations(self.markdown, rows, manifest.get("citation_mode", ""))
        with mock.patch.object(
            MODULE.EvidenceVerifier, "crossref_lookup", side_effect=resolver or self.resolved
        ):
            verifier.verify_dois(rows)
        verifier.verify_provenance(
            self.root / "data/data-provenance.json", self.markdown,
            manifest.get("research_claim_level", ""),
        )
        return verifier

    def test_valid_evidence_package_passes(self) -> None:
        self.assertEqual(self.run_verifier().errors, [])

    def test_crossref_cannot_be_fulltext_evidence(self) -> None:
        self.rows[0]["verification_source"] = "Crossref"
        self.write_matrix()
        self.assertTrue(any("FULLTEXT_DISCOVERY_ONLY" in item for item in self.run_verifier().errors))

    def test_doi_title_mismatch_fails(self) -> None:
        def mismatch(item):
            payload = self.resolved(item)
            payload.update({"resolved_title": "Different Paper", "similarity": 0.1, "mismatch": True})
            return payload

        self.assertTrue(any("DOI_TITLE_MISMATCH" in item for item in self.run_verifier(mismatch).errors))

    def test_uncited_reference_fails(self) -> None:
        self.markdown.write_text(
            "# 第1章 绪论\n没有引用。\n\n# 参考文献\n[1] Example study.\n", encoding="utf-8"
        )
        self.assertTrue(any("REFERENCES_NOT_CITED" in item for item in self.run_verifier().errors))

    def test_model_synthetic_result_fails(self) -> None:
        data = self.root / "data/result.csv"
        data.write_text("group,value\nA,12\n", encoding="utf-8")
        self.provenance["datasets"] = [{
            "dataset_id": "D1", "origin": "MODEL_SYNTHETIC", "claim_role": "RESULT",
            "file": "data/result.csv", "sha256": MODULE.sha256(data), "supports_claims": ["结果"],
        }]
        self.write_provenance()
        self.assertTrue(any("MODEL_SYNTHETIC_RESULT_FORBIDDEN" in item for item in self.run_verifier().errors))

    def test_self_written_observation_receipt_fails(self) -> None:
        data = self.root / "data/result.csv"
        data.write_text("group,value\nA,12\n", encoding="utf-8")
        receipt = self.root / "data/receipt.txt"
        receipt.write_text("企业ERP已核验", encoding="utf-8")
        self.provenance["datasets"] = [{
            "dataset_id": "D1", "origin": "AUTHOR_OBSERVED", "claim_role": "RESULT",
            "file": "data/result.csv", "sha256": MODULE.sha256(data), "supports_claims": ["结果"],
            "source_artifacts": [{"file": "data/result.csv", "sha256": MODULE.sha256(data), "origin": "AUTHOR_OBSERVED"}],
            "observation_receipt": "data/receipt.txt", "observation_receipt_sha256": MODULE.sha256(receipt),
        }]
        self.write_provenance()
        errors = self.run_verifier().errors
        self.assertTrue(any("REGISTER_RECEIPT_INVALID" in item for item in errors))

    def test_captured_observed_raw_source_passes(self) -> None:
        raw_dir = self.root / "data/raw"
        raw_dir.mkdir()
        data = raw_dir / "observations.csv"
        data.write_text("group,value\nA,12\n", encoding="utf-8")
        receipt = self.root / "data/observation.json"
        capture = Path(__file__).resolve().parents[1] / "scripts/capture_provenance.py"
        result = subprocess.run([
            sys.executable, str(capture), "register", "--root", str(self.root),
            "--source", "data/raw/observations.csv", "--origin", "AUTHOR_OBSERVED",
            "--collection-method", "授权仪器导出", "--collector", "researcher",
            "--receipt", "data/observation.json",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.manifest["research_claim_level"] = "OBSERVED_STUDY"
        (self.root / "run-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        self.provenance = {
            "schema_version": "1.0", "research_claim_level": "OBSERVED_STUDY",
            "datasets": [{
                "dataset_id": "D1", "origin": "AUTHOR_OBSERVED", "claim_role": "RESULT",
                "file": "data/raw/observations.csv", "sha256": MODULE.sha256(data),
                "supports_claims": ["观察结果"],
                "source_artifacts": [{
                    "file": "data/raw/observations.csv", "sha256": MODULE.sha256(data),
                    "origin": "AUTHOR_OBSERVED",
                }],
                "observation_receipt": "data/observation.json",
                "observation_receipt_sha256": MODULE.sha256(receipt),
            }],
        }
        self.write_provenance()
        self.assertEqual(self.run_verifier().errors, [])

    def test_invalid_direction_fails(self) -> None:
        self.manifest["direction_id"] = "invented-direction"
        (self.root / "run-manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        self.assertTrue(any("DIRECTION_ID_INVALID" in item for item in self.run_verifier().errors))

    def test_design_claiming_observed_result_without_data_fails(self) -> None:
        self.markdown.write_text(
            "# 第1章 绪论\n本系统实测结果显著提高了15%。[1]\n\n# 参考文献\n[1] Example study.\n",
            encoding="utf-8",
        )
        self.assertTrue(any("OBSERVED_RESULT_WITHOUT_DATA" in item for item in self.run_verifier().errors))

    def test_profile_mismatch_fails(self) -> None:
        profile_path = self.root / "00-profile-selection.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["selected_profile"] = "WEAK_MODEL"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        self.assertTrue(any("PROFILE_SELECTION_MISMATCH" in item for item in self.run_verifier().errors))

    def test_stale_profile_selector_fails(self) -> None:
        profile_path = self.root / "00-profile-selection.json"
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        profile["selector"]["sha256"] = "0" * 64
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        self.assertTrue(any("PROFILE_SELECTOR_STALE" in item for item in self.run_verifier().errors))


if __name__ == "__main__":
    unittest.main()
