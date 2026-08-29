#!/usr/bin/env python3
from pathlib import Path
import importlib.util,sys,unittest
P=Path(__file__).resolve().parents[1]/"scripts/resolve_default_length.py";S=importlib.util.spec_from_file_location("lengths",P);M=importlib.util.module_from_spec(S);sys.modules[S.name]=M;S.loader.exec_module(M)
class LengthTests(unittest.TestCase):
    def test_unknown_chinese_thesis_keeps_25000(self):self.assertEqual(M.resolve("THESIS","UNSPECIFIED","zh-cn")["target"],25000)
    def test_undergraduate_chinese(self):self.assertEqual(M.resolve("THESIS","UNDERGRADUATE","zh-cn")["target"],20000)
    def test_english_master(self):self.assertEqual(M.resolve("THESIS","MASTER","en")["target"],15000)
    def test_journal(self):self.assertEqual(M.resolve("JOURNAL","UNSPECIFIED","zh-cn")["target"],10000)
    def test_explicit_wins(self):self.assertEqual(M.resolve("THESIS","UNDERGRADUATE","zh-cn",25000)["target"],25000)
    def test_custom_requires_explicit(self):
        with self.assertRaises(ValueError):M.resolve("CUSTOM","UNSPECIFIED","zh-cn")
if __name__=="__main__":unittest.main()
