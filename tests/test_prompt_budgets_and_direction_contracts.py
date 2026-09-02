#!/usr/bin/env python3
"""紧凑预算、专业占比和方向源表的回归。"""

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_compiled import compact_source, direction_files, full_source, render_compact, render_compiled
from compose_prompt import MODULE_PATTERN, task_parts
from verify_figure_package import FigureVerifier


class PromptBudgetTests(unittest.TestCase):
    def test_all_directions_fit_compact_budget_and_professional_ratio(self):
        catalog = json.loads((ROOT / "references/prompt-modules.json").read_text())
        overhead = max(path.stat().st_size for path in (ROOT / "references/integrations").glob("*.md"))
        overhead += (ROOT / "references/profiles/staged-assistance.md").stat().st_size
        overhead += (ROOT / "references/profiles/execution-checkpoints-template.json").stat().st_size + 1500
        for direction in direction_files():
            selection = {"schema_version": "1.0", "run_mode": "FULL_BUILD", "direction_id": direction.stem,
                         "features": catalog["direction_defaults"][direction.stem]}
            compact, _ = task_parts(render_compact(direction).encode(), selection,
                                    f"RUN_MODE: FULL_BUILD\nDIRECTION_ID: {direction.stem}\n".encode())
            self.assertLessEqual(len(compact) + overhead, 15000, direction.stem)
            full, _ = task_parts(render_compiled(direction).encode(), selection,
                                 f"RUN_MODE: FULL_BUILD\nDIRECTION_ID: {direction.stem}\n".encode())
            method = dict(MODULE_PATTERN.findall(render_compiled(direction)))["method"]
            ratio = (len(full_source(direction).encode()) + len(method.encode())) / len(full)
            self.assertGreaterEqual(ratio, 0.30, direction.stem)
            self.assertIn(compact_source(direction), full_source(direction))


class DirectionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "figures").mkdir()
        self.verifier = FigureVerifier(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_circuit_requires_connection_table(self):
        self.verifier.verify_direction_contracts("electronic-circuit-design", {
            "figures": [{"exactness_class": "DOMAIN_EXACT"}]
        })
        self.assertTrue(any("CIRCUIT_CONNECTION_TABLE_MISSING" in error for error in self.verifier.errors))

    def test_valid_connection_table_is_bound(self):
        path = self.root / "figures/connection-table.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["from_component", "from_pin", "to_component", "to_pin", "net", "voltage_domain", "source"])
            writer.writeheader()
            writer.writerow({"from_component": "U1", "from_pin": "1", "to_component": "J1", "to_pin": "2",
                             "net": "3V3", "voltage_domain": "3.3V", "source": "datasheet p.2"})
        paths = self.verifier.verify_direction_contracts("electronic-circuit-design", {
            "figures": [{"exactness_class": "DOMAIN_EXACT"}]
        })
        self.assertEqual(self.verifier.errors, [])
        self.assertEqual(paths, [path.resolve()])


if __name__ == "__main__":
    unittest.main()
