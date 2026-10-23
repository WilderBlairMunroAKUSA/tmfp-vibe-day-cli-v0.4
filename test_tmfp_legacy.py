"""Offline end-to-end tests. Requires Python 3.10+ and Git."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).with_name("tmfp.py")

class SliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "workspace"
        self.call("init", "--timezone", "UTC")

    def call(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(CLI), "--home", str(self.root), *args],
                           text=True, capture_output=True, timeout=8)
        if ok and p.returncode:
            self.fail(f"{args}\n{p.stderr}\n{p.stdout}")
        return p

    def test_lifecycle_projection_and_detection(self):
        self.call("start", "--mode", "WORKBENCH", "--topic", "testing")
        self.call("state", "--address", "aurora-future", "--focus", "chat:turn-007", "--mode", "MARGINALIA")
        marked = self.call("mark", "That's not what I meant!", "--data", '{"note": "important"}')
        pid = marked.stdout.strip()
        self.assertTrue(pid.startswith("piece:"))
        file = Path(self.tmp.name) / "idea.txt"
        file.write_text("piecebrain pieceprocess piecespace", encoding="utf-8")
        fileout = self.call("add", "--file", str(file), "--key", "source", "--description", "a source artifact")
        artifact_id = fileout.stdout.split()[0]
        self.call("relate", pid, "motivated_by", artifact_id)
        self.call("add", "--uri", "https://youtube.com/watch?v=abc", "--kind", "video", "--description", "not-yet-verified remote replay")
        self.call("checkpoint", "partial work in progress")
        self.call("stop")
        self.call("seal")
        self.call("verify")
        self.call("export-hf")
        ds = (self.root / "days").glob("tmfp-*")
        day = next(ds)
        date = day.name.removeprefix("tmfp-")
        export = self.root / "exports" / date
        self.assertIn("config_name: pieces", (export / "README.md").read_text())
        self.assertIn("config_name: relations", (export / "README.md").read_text())
        piece_rows = [json.loads(x) for x in (export / "data/pieces.jsonl").read_text().splitlines()]
        self.assertEqual(len(piece_rows), 3)
        object_ref = [r["uri"] for r in piece_rows if r["evidence_status"] == "local_bytes_hashed"][0]
        self.assertEqual((export / object_ref).read_text(), file.read_text())
        self.assertIn("aurora-future", (day / "pieces.jsonl").read_text())
        self.assertEqual(json.loads((export / "data/days.jsonl").read_text())["merkle_root"],
                         json.loads((day / "integrity/manifest.json").read_text())["root_sha256"])
        with (day / "pieces.jsonl").open("a") as f:
            f.write('{"fake":true}\n')
        self.assertNotEqual(self.call("verify", ok=False).returncode, 0)
        self.call("seal")
        self.call("verify")

    def test_cross_day_relations_and_ancestor(self):
        # Two independently indexed civil days. Cross-day relations don't need a common repo.
        self.call("add", "--date", "2026-10-18", "--uri", "https://example.com/day1", "--description", "prior event")
        prior_day = self.root / "days/tmfp-2026-10-18"
        prior_piece = json.loads((prior_day / "pieces.jsonl").read_text().splitlines()[0])["id"]
        self.call("seal", "--date", "2026-10-18")
        self.call("add", "--date", "2026-10-19", "--uri", "https://example.com/day2", "--description", "future event")
        self.call("relate", "--date", "2026-10-19", "tmfp:day:2026-10-19", "references", prior_piece)
        self.call("seal", "--date", "2026-10-19")
        self.call("verify", "--date", "2026-10-19", "--ancestors")
        self.call("export-hf", "--date", "2026-10-19")
        self.call("export-corpus")
        corpus = self.root / "exports/corpus/data/days.jsonl"
        self.assertEqual(len(corpus.read_text().splitlines()), 2)
        self.assertTrue((self.root / "exports/corpus/data/relations.jsonl").is_file())
        p = self.root / "days/tmfp-2026-10-19/day.json"
        self.assertEqual(json.loads(p.read_text())["previous_index_snapshot"]["day_id"], "tmfp:day:2026-10-18")
        manifest = prior_day / "integrity/manifest.json"
        original = json.loads(manifest.read_text())
        original["root_sha256"] = "0"*64
        manifest.write_text(json.dumps(original))
        self.assertNotEqual(self.call("verify", "--date", "2026-10-19", "--ancestors", ok=False).returncode,0)

    def test_temporal_qkv_cross_day_and_readonly_outcome(self):
        started = self.call("expect", "--date", "2026-10-18", "--q", "prior world moment",
                            "--k", "expected state", "--design", "intentional_intervention",
                            "--mark", "piece:marked-test")
        eid = started.stdout.strip()
        self.assertTrue(eid.startswith("experience:"))
        self.assertEqual(self.call("resolve", "no-such-case", "--v", "x", ok=False).returncode, 1)
        self.call("seal", "--date", "2026-10-18")
        self.call("resolve", "--date", "2026-10-19", eid, "--v", "actual state",
                  "--evidence", "piece:observation-test")
        self.assertNotEqual(self.call("resolve", "--date", "2026-10-19", eid,
                                      "--v", "retroactive alteration", ok=False).returncode, 0)
        self.call("seal", "--date", "2026-10-19")
        self.call("export-hf", "--date", "2026-10-19")
        self.call("export-corpus")
        day = self.root / "exports/2026-10-19/data/qkv.jsonl"
        corpus = self.root / "exports/corpus/data/qkv.jsonl"
        record = json.loads(day.read_text().splitlines()[0])
        self.assertEqual(record["expectation_day_id"], "tmfp:day:2026-10-18")
        self.assertEqual(record["q"], "prior world moment")
        self.assertEqual(record["v"], "actual state")
        self.assertEqual(record["causal_status"], "not_established")
        self.assertEqual(record, json.loads(corpus.read_text().splitlines()[0]))
        self.assertIn("config_name: qkv", (self.root / "exports/2026-10-19/README.md").read_text())
        self.call("verify", "--date", "2026-10-18")
        self.call("verify", "--date", "2026-10-19")

    def test_empty_day_export_and_remote_not_hashed(self):
        self.call("start")
        self.call("stop")
        self.call("seal")
        self.call("export-hf")
        exp = next((self.root / "exports").iterdir())
        readme = (exp / "README.md").read_text()
        self.assertIn("config_name: datasets\n    default: true", readme)
        self.assertFalse((exp / "data/pieces.jsonl").exists())

if __name__ == "__main__":
    unittest.main()
