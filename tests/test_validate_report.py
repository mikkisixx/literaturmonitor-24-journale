#!/usr/bin/env python3
"""Regression tests for fail-closed monthly scientific provenance validation."""
import copy
import json
import pathlib
import tempfile
import unittest
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_report import validate

MONTH = "2026-10"
FILES = [
    f"months/{MONTH}.json",
    f"quality/{MONTH}.json",
    f"coverage/{MONTH}.json",
    f"publisher-evidence/{MONTH}.json",
]

class ReportValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = pathlib.Path(self.temp.name)
        for relative in FILES:
            dest = self.data / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / "data" / relative).read_bytes())
        # Normalize the fixture while an evidence-triggered monthly rebuild is queued.
        report = json.loads((self.data / f"months/{MONTH}.json").read_text())
        evidence = json.loads((self.data / f"publisher-evidence/{MONTH}.json").read_text())
        coverage_path = self.data / f"coverage/{MONTH}.json"
        coverage = json.loads(coverage_path.read_text())
        known = {a["doi"].lower() for a in report["articles"]}
        missing = [{**a, "in_monthly_report": False} for a in evidence["findings"] if a["doi"].lower() not in known]
        coverage["publisher_examples_checked"] = len(evidence["findings"])
        coverage["missing_publisher_articles"] = missing
        coverage["confirmed_missing_publisher_articles"] = len(missing)
        for row in coverage["journals"]:
            n = sum(a["journal"] == row["journal"] for a in missing)
            row["publisher_examples_missing"] = n
            if n:
                row["status"] = "confirmed_missing_publisher_articles"
        coverage_path.write_text(json.dumps(coverage))

    def mutate(self, relative, change):
        path = self.data / relative
        obj = json.loads(path.read_text())
        change(obj)
        path.write_text(json.dumps(obj))

    def test_real_report_passes_consistency_checks(self):
        validate(MONTH, self.data)

    def test_duplicate_publisher_evidence_is_rejected(self):
        def duplicate(obj):
            obj["findings"].append(copy.deepcopy(obj["findings"][0]))
        self.mutate(f"publisher-evidence/{MONTH}.json", duplicate)
        with self.assertRaises(AssertionError):
            validate(MONTH, self.data)

    def test_changed_publisher_date_is_rejected(self):
        self.mutate(f"publisher-evidence/{MONTH}.json",
                    lambda obj: obj["findings"][0].update(publisher_online_date="2026-10-29"))
        with self.assertRaises(AssertionError):
            validate(MONTH, self.data)

    def test_false_editorial_release_is_rejected(self):
        self.mutate(f"quality/{MONTH}.json",
                    lambda obj: obj.update(publication_ready=True, release_status="approved"))
        with self.assertRaises(AssertionError):
            validate(MONTH, self.data)

    def test_false_journal_coverage_is_rejected(self):
        self.mutate(f"coverage/{MONTH}.json",
                    lambda obj: obj["journals"][0].update(publisher_coverage_verified=True))
        with self.assertRaises(AssertionError):
            validate(MONTH, self.data)

if __name__ == "__main__":
    unittest.main()
