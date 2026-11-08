"""Synthetic tests; no real complaint narrative is embedded or exported."""

import csv
import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from stage2 import (
    CountNaiveBayes, PRODUCTS, deduplicate, evaluate, iter_source, normalize,
    paired_bootstrap_macro_f1_delta, parse_received, rule_predict, rule_route,
    run_experiment, scan_source, split_rows, tokenize, wilson,
)


HEADERS = ["Date received", "Product", "Consumer complaint narrative", "Complaint ID"]
FIXTURE_ROOT = Path(__file__).resolve().parent / "tmp"
FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)


def write_fixture(path: Path, rows: list[dict], headers=HEADERS) -> None:
    data = io.StringIO(newline="")
    writer = csv.DictWriter(data, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("complaints.csv", data.getvalue())


def row(day: str, label: str, text: str, identifier: str) -> dict:
    return {"Date received": day, "Product": label,
            "Consumer complaint narrative": text, "Complaint ID": identifier}


class Stage2Tests(unittest.TestCase):
    def test_date_parses_timestamp_and_rejects_malformed(self):
        self.assertEqual(parse_received("2026-04-03T08:15:00.000Z"), date(2026, 4, 3))
        self.assertIsNone(parse_received("not-a-date"))

    def test_normalization_and_redaction_tokens(self):
        self.assertEqual(normalize(" CREDIT\n card  "), "credit card")
        self.assertEqual(tokenize("XXXX credit card XX"), ["credit", "card"])

    def test_missing_required_column_rejected(self):
        with tempfile.TemporaryDirectory(dir=FIXTURE_ROOT) as d:
            path = Path(d) / "fixture.zip"
            headers = ["Date received", "Product", "Consumer complaint narrative"]
            write_fixture(path, [{k: "x" for k in headers}], headers)
            with self.assertRaisesRegex(ValueError, "Complaint ID"):
                list(iter_source(path))

    def test_scan_counts_missing_and_target_narratives(self):
        with tempfile.TemporaryDirectory(dir=FIXTURE_ROOT) as d:
            path = Path(d) / "fixture.zip"
            rows = [row("2026-03-01", PRODUCTS[0], "Debt collector called again.", "1"),
                    row("2026-03-02", PRODUCTS[1], "", "2"),
                    row("bad", "Other", "A complaint about another product.", "3")]
            write_fixture(path, rows)
            audit, candidates = scan_source(path)
            self.assertEqual(audit["rows_read"], 3)
            self.assertEqual(audit["missing_counts"]["Consumer complaint narrative"], 1)
            self.assertEqual(audit["invalid_received_dates"], 1)
            self.assertEqual(audit["selected_six_narratives"], 1)
            self.assertEqual(audit["monthly_selected_six_narratives"], {"2026-03": 1})
            self.assertEqual(audit["selected_narrative_length_chars"]["n"], 1)
            self.assertEqual(len(candidates), 1)

    def test_later_label_disagreement_cannot_remove_earlier_training_row(self):
        candidates = [
            {"hash": "same", "text": "example", "label": PRODUCTS[0], "date": date(2026, 5, 1), "id": "2"},
            {"hash": "same", "text": "example", "label": PRODUCTS[0], "date": date(2026, 3, 1), "id": "1"},
            {"hash": "conflict", "text": "different", "label": PRODUCTS[0], "date": date(2026, 3, 1), "id": "3"},
            {"hash": "conflict", "text": "different", "label": PRODUCTS[1], "date": date(2026, 4, 1), "id": "4"},
        ]
        kept, stats = deduplicate(candidates)
        self.assertEqual([r["id"] for r in kept], ["1", "3"])
        self.assertEqual(stats["duplicate_extra_rows"], 2)
        self.assertEqual(stats["conflicting_label_groups_excluded"], 0)
        self.assertEqual(stats["later_label_disagreement_groups_kept_first"], 1)
        self.assertEqual(stats["later_label_disagreement_rows_dropped"], 1)
        splits, _ = split_rows(kept)
        self.assertEqual({r["id"] for r in splits["train"]}, {"1", "3"})

    def test_first_day_cross_label_conflict_excludes_group_without_future_label(self):
        candidates = [
            {"hash": "ambiguous", "text": "same", "label": PRODUCTS[0], "date": date(2026, 3, 1), "id": "1"},
            {"hash": "ambiguous", "text": "same", "label": PRODUCTS[1], "date": date(2026, 3, 1), "id": "2"},
            {"hash": "ambiguous", "text": "same", "label": PRODUCTS[0], "date": date(2026, 5, 1), "id": "3"},
        ]
        kept, stats = deduplicate(candidates)
        self.assertEqual(kept, [])
        self.assertEqual(stats["earliest_day_conflicting_groups_excluded"], 1)
        self.assertEqual(stats["earliest_day_conflicting_rows_excluded"], 3)

    def test_group_first_temporal_split_prevents_duplicate_leakage(self):
        candidates = [
            {"hash": "repeat", "text": "same text", "label": PRODUCTS[0], "date": date(2026, 3, 1), "id": "1"},
            {"hash": "repeat", "text": "same text", "label": PRODUCTS[0], "date": date(2026, 5, 1), "id": "2"},
            {"hash": "new", "text": "new text", "label": PRODUCTS[1], "date": date(2026, 5, 2), "id": "3"},
        ]
        kept, _ = deduplicate(candidates)
        splits, _ = split_rows(kept)
        self.assertEqual(len(splits["train"]), 1)
        self.assertEqual(len(splits["test"]), 1)
        self.assertEqual(splits["test"][0]["hash"], "new")

    def test_split_excludes_june_trial_from_test(self):
        rows = [{"hash": "j", "text": "example", "label": PRODUCTS[0],
                 "date": date(2026, 6, 1), "id": "1"}]
        splits, details = split_rows(rows)
        self.assertEqual(sum(len(v) for v in splits.values()), 0)
        self.assertEqual(details["outside_window_by_month"], {"2026-06": 1})

    def test_vocabulary_fitted_only_on_training_text(self):
        training = [{"text": "collector collector debt", "label": PRODUCTS[0]},
                    {"text": "collector debt", "label": PRODUCTS[0]},
                    {"text": "mortgage mortgage loan", "label": PRODUCTS[4]},
                    {"text": "mortgage loan", "label": PRODUCTS[4]}]
        model = CountNaiveBayes().fit(training)
        self.assertIn("collector", model.vocabulary)
        self.assertNotIn("mayonlytoken", model.vocabulary)
        model.predict_one("mayonlytoken collector")
        self.assertNotIn("mayonlytoken", model.vocabulary)

    def test_trained_baseline_learns_discriminative_words(self):
        training = ([{"text": "collector debt collection", "label": PRODUCTS[0]}] * 3
                    + [{"text": "mortgage escrow foreclosure", "label": PRODUCTS[4]}] * 3)
        model = CountNaiveBayes().fit(training)
        self.assertEqual(model.predict_one("mortgage escrow"), PRODUCTS[4])
        self.assertEqual(model.predict_one("collector debt"), PRODUCTS[0])

    def test_rule_review_is_scored_as_error_not_hidden(self):
        rows = [{"label": PRODUCTS[0]}, {"label": PRODUCTS[4]}]
        metrics = evaluate(rows, [PRODUCTS[0], None], True)
        self.assertEqual(metrics["accuracy"], 0.5)
        self.assertEqual(metrics["coverage"], 0.5)
        self.assertEqual(metrics["accuracy_when_auto"], 1.0)
        self.assertEqual(metrics["confusion_matrix"][PRODUCTS[4]]["review"], 1)

    def test_rule_baseline_preserves_ambiguous_review(self):
        self.assertIsNone(rule_predict("my mortgage and debt are both listed incorrectly"))
        self.assertEqual(rule_route("my mortgage and debt are both listed incorrectly")[1],
                         "ambiguous")

    def test_paired_bootstrap_uses_same_rows_and_fixed_seed(self):
        true = [PRODUCTS[0], PRODUCTS[0], PRODUCTS[4], PRODUCTS[4], PRODUCTS[1], PRODUCTS[1]]
        nb = list(true)
        rules = [PRODUCTS[0], None, PRODUCTS[4], None, PRODUCTS[1], None]
        first = paired_bootstrap_macro_f1_delta(true, nb, rules, draws=100, seed=7)
        again = paired_bootstrap_macro_f1_delta(true, nb, rules, draws=100, seed=7)
        self.assertEqual(first, again)
        self.assertGreater(first["delta_macro_f1"], 0)
        self.assertGreaterEqual(first["ci_95_percentile"][0], 0)

    def test_wilson_interval_handles_empty_and_bounds(self):
        self.assertIsNone(wilson(0, 0))
        low, high = wilson(7, 10)
        self.assertLess(low, 0.7)
        self.assertGreater(high, 0.7)
        self.assertGreaterEqual(low, 0)
        self.assertLessEqual(high, 1)

    def test_end_to_end_fixture_exports_aggregates_only(self):
        with tempfile.TemporaryDirectory(dir=FIXTURE_ROOT) as d:
            path = Path(d) / "fixture.zip"
            rows = []
            for i, label in enumerate(PRODUCTS):
                token = ("collector", "checking", "card", "transfer", "mortgage", "bureau")[i]
                for j in range(2):
                    rows.append(row(f"2026-03-0{j+1}", label,
                                    f"Synthetic {token} {token} issue number {i} {j}", f"t{i}{j}"))
                rows.append(row("2026-04-01", label,
                                f"Synthetic {token} {token} validation issue", f"v{i}"))
                rows.append(row("2026-05-01", label,
                                f"Synthetic {token} {token} test issue", f"e{i}"))
            write_fixture(path, rows)
            result = run_experiment(path, max_rows=len(rows), expected_sha256=None)
            self.assertEqual(result["report"]["train_n"], 12)
            self.assertEqual(result["report"]["test_n"], 6)
            self.assertFalse(result["checks"]["raw_narratives_exported"])
            self.assertNotIn("Synthetic collector", str(result))
            self.assertEqual(result["model"]["train_rows"], 12)


if __name__ == "__main__":
    unittest.main()
