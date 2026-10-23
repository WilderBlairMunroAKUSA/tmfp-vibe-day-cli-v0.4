"""New v0.4 behavior, tested end to end without publication or third-party libraries."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).with_name("tmfp.py")


class VibeDayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "vibe"
        self.call("init", "--timezone", "UTC", "--first-day-number", "7")

    def call(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(CLI), "--home", str(self.root), *args],
                                capture_output=True, text=True, timeout=20)
        if ok and result.returncode:
            self.fail(f"{args}:\n{result.stderr}\n{result.stdout}")
        return result

    def test_one_day_as_query_with_generic_kv_and_context(self):
        date = "2026-11-01"
        self.call("start", "--date", date, "--topic", "Vibe-inventing world peace")
        kid = self.call("member", "--date", date, "--key", "theory", "--value-json",
                        '{"nested":{"image":"object"},"confidence":null}',
                        "--context", '{"why":"question for an agent"}',
                        "--source-ref", "piece:source-a").stdout.strip()
        self.assertTrue(kid.startswith("member:"))
        cid = self.call("context", "--date", date, "--key", "provenance",
                        "--value-json", '{"origin":"livestream","license":null}',
                        "--subject", kid, "--source-ref", "https://example.org/a").stdout.strip()
        self.assertTrue(cid.startswith("context:"))
        missing = self.call("need", "--date", date, "Who authored the original text?",
                            "--subject", kid).stdout.strip()
        self.assertTrue(missing.startswith("need:"))
        self.call("answer", "--date", date, missing, "--value", "Unknown; under review",
                  "--source-ref", "https://example.org/context")
        self.call("anchor", "--date", date, "--recording", "piece:recording",
                  "--media-time-ms", "2500", "--utc", "2026-11-01T12:00:00Z")
        self.call("stop")   # stop resolves to actual current civil day; may create an extra day
        self.call("seal", "--date", date)
        self.call("verify", "--date", date)
        self.call("export-hf", "--date", date)
        repo = self.root / "days" / f"tmfp-{date}"
        meta = json.loads((repo / "dataset.json").read_text())
        self.assertEqual(meta["title"], "Vibe-Inventing World Peace | Day 7 of ???")
        self.assertEqual(meta["day_number"], 7)
        export = self.root / "exports" / date / "data"
        ds = json.loads((export / "datasets.jsonl").read_text())
        self.assertEqual(ds["dataset_id"], meta["dataset_id"])
        self.assertIn(kid, json.loads(ds["member_refs_json"]))
        members = [json.loads(r) for r in (export / "members.jsonl").read_text().splitlines()]
        self.assertEqual(len([r for r in members if r["id"] == kid]), 1)
        self.assertEqual(json.loads([r for r in members if r["id"] == kid][0]["value_json"]),
                         {"nested": {"image": "object"}, "confidence": None})
        chunks = [json.loads(r) for r in (export / "lm_chunks.jsonl").read_text().splitlines()]
        self.assertTrue(all(json.loads(r["text"])["query_entity"]["dataset_id"] == meta["dataset_id"]
                            for r in chunks))
        self.assertEqual(sum(r["member_count"] for r in chunks), len(members))
        self.assertIn("config_name: context_requests", (export.parent / "README.md").read_text())

    def test_day_numbers_and_series_members(self):
        self.call("member", "--date", "2026-11-02", "--key", "a", "--value", "A")
        self.call("seal", "--date", "2026-11-02")
        self.call("member", "--date", "2026-11-03", "--key", "b", "--value", "B")
        self.call("seal", "--date", "2026-11-03")
        self.call("export-corpus")
        day2 = json.loads((self.root / "days/tmfp-2026-11-03/dataset.json").read_text())
        self.assertEqual(day2["day_number"], 8)
        series = [json.loads(x) for x in (self.root / "exports/corpus/data/series_members.jsonl").read_text().splitlines()]
        self.assertEqual([r["key"] for r in series], ["day-0007", "day-0008"])
        self.assertEqual(series[0]["subject_id"], "tmfp:series:vibe-inventing-world-peace")

    def test_backward_compatible_prediction_is_derived_only(self):
        exp = self.call("expect", "--date", "2026-11-04", "--q", "a",
                        "--k", "I predict X").stdout.strip()
        self.call("resolve", "--date", "2026-11-05", exp, "--v", "not X")
        self.call("seal", "--date", "2026-11-05")
        self.call("export-hf", "--date", "2026-11-05")
        self.assertFalse((self.root / "exports/2026-11-05/data/qkv_predictions.jsonl").exists())
        self.call("seal", "--date", "2026-11-04")
        self.call("export-hf", "--date", "2026-11-05")
        row = json.loads((self.root / "exports/2026-11-05/data/qkv_predictions.jsonl").read_text())
        self.assertEqual(row["completion"], "not X")
        self.assertEqual(row["expectation_day_id"], "tmfp:day:2026-11-04")
        self.assertTrue((self.root / "exports/2026-11-05/data/datasets.jsonl").exists())

    def test_public_publish_requires_explicit_review(self):
        self.call("member", "--date", "2026-11-06", "--key", "a", "--value", "a")
        self.call("seal", "--date", "2026-11-06")
        gh = self.call("publish-github", "--date", "2026-11-06", "--owner", "example",
                       "--public", ok=False)
        self.assertEqual(gh.returncode, 1)
        self.assertIn("--reviewed", gh.stderr)
        hf = self.call("publish-hf", "--date", "2026-11-06", "--repo", "example/test",
                       "--public", ok=False)
        self.assertEqual(hf.returncode, 1)
        self.assertIn("--reviewed", hf.stderr)

    def test_multiple_members_have_single_day_dataset_identity(self):
        date = "2026-11-07"
        for i in range(16):
            self.call("member", "--date", date, "--key", f"e{i}",
                      "--value-json", json.dumps({"text": "abc" * (i + 1)}))
        self.call("seal", "--date", date)
        self.call("export-hf", "--date", date)
        root = self.root / "exports" / date / "data"
        self.assertEqual(len((root / "datasets.jsonl").read_text().splitlines()), 1)
        records = [json.loads(x) for x in (root / "members.jsonl").read_text().splitlines()]
        self.assertEqual(len([r for r in records if r["kind"] == "kv"]), 16)
        self.assertEqual(len({r["dataset_id"] for r in records}), 1)


if __name__ == "__main__":
    unittest.main()
