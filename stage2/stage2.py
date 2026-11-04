"""Stage-2 audit and reproducible text-classification experiment.

Only aggregate JSON is written. Complaint narratives stay in memory and are
never printed, logged, or saved. The input is the user-provided CSV ZIP; its
first 1,048,575 records correspond to the supplied workbook-sized extract.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import random
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_DATA = HERE.parent / "complaints.csv.zip"
DEFAULT_OUTPUT = HERE / "results" / "summary.json"
EXPECTED_SHA256 = "850d5d220285abecb4d4b94ae4c92a8f318476ce14bd0460c3d6361c79ae9694"
MAX_ROWS = 1_048_575
SEED = 42
BOOTSTRAPS = 500
MAX_TOKENS = 5000
MIN_DOC_FREQ = 2
ALPHAS = (0.1, 1.0, 5.0)
PRODUCTS = (
    "Debt collection",
    "Checking or savings account",
    "Credit card",
    "Money transfer, virtual currency, or money service",
    "Mortgage",
    "Credit reporting or other personal consumer reports",
)
REQUIRED = {"Date received", "Product", "Consumer complaint narrative", "Complaint ID"}
RULES = {
    PRODUCTS[0]: ("debt collector", "collection agency", "debt collection", "collector", "debt"),
    PRODUCTS[1]: ("checking account", "savings account", "bank account", "direct deposit", "overdraft"),
    PRODUCTS[2]: ("credit card", "card statement", "card issuer", "chargeback", "apr"),
    PRODUCTS[3]: ("wire transfer", "money transfer", "remittance", "cryptocurrency", "bitcoin"),
    PRODUCTS[4]: ("mortgage", "foreclosure", "home loan", "escrow", "loan servicer"),
    PRODUCTS[5]: ("credit report", "credit bureau", "credit reporting", "transunion", "experian", "equifax"),
}
DATA_DICTIONARY = {
    "Date received": ("Complaint receipt timestamp", "time split only"),
    "Product": ("Financial product category", "target label"),
    "Sub-product": ("Product subtype", "audit only; excluded from features"),
    "Issue": ("Issue category", "audit only; excluded from features"),
    "Sub-issue": ("Issue subtype", "audit only; excluded from features"),
    "Consumer complaint narrative": ("Consumer narrative", "sole model feature"),
    "Company public response": ("Public company response", "post-submission; excluded"),
    "Company": ("Named company", "audit only; excluded"),
    "State": ("Consumer state", "audit only; excluded"),
    "ZIP code": ("Consumer ZIP code", "sensitive; excluded"),
    "Tags": ("Complaint tags", "audit only; excluded"),
    "Submitted via": ("Submission channel", "audit only; excluded"),
    "Date sent to company": ("Forwarding date", "post-submission; excluded"),
    "Company response to consumer": ("Response outcome", "post-submission; excluded"),
    "Timely response?": ("Response timeliness", "post-submission; excluded"),
    "Complaint ID": ("Record identifier", "dedup tie-break only; excluded"),
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("narrative must be a string")
    return " ".join(text.casefold().split())


def parse_received(value: str) -> date | None:
    try:
        return date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def iter_source(zip_path: Path, max_rows: int = MAX_ROWS):
    with zipfile.ZipFile(zip_path) as archive:
        if "complaints.csv" not in archive.namelist():
            raise ValueError("archive must contain complaints.csv")
        with archive.open("complaints.csv") as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            columns = reader.fieldnames or []
            if missing := REQUIRED - set(columns):
                raise ValueError(f"missing required columns: {sorted(missing)}")
            for index, row in enumerate(reader, 1):
                if index > max_rows:
                    break
                yield columns, row


def scan_source(zip_path: Path, max_rows: int = MAX_ROWS) -> tuple[dict, list[dict]]:
    columns: list[str] = []
    missing = Counter()
    products = Counter()
    narrative_products = Counter()
    monthly_all = Counter()
    monthly_narrative = Counter()
    monthly_six_narrative = Counter()
    rows_read = narrative_count = selected_count = invalid_dates = 0
    selected_invalid_dates = redaction_markers = long_narratives = 0
    earliest: date | None = None
    latest: date | None = None
    candidates: list[dict] = []
    for columns, row in iter_source(zip_path, max_rows):
        rows_read += 1
        for column in columns:
            if not (row.get(column) or "").strip():
                missing[column] += 1
        product = row["Product"]
        products[product] += 1
        received = parse_received(row["Date received"])
        if received is None:
            invalid_dates += 1
        else:
            earliest = received if earliest is None else min(earliest, received)
            latest = received if latest is None else max(latest, received)
            monthly_all[received.strftime("%Y-%m")] += 1
        narrative = (row["Consumer complaint narrative"] or "").strip()
        if not narrative:
            continue
        narrative_count += 1
        narrative_products[product] += 1
        if received is not None:
            monthly_narrative[received.strftime("%Y-%m")] += 1
        if product not in PRODUCTS:
            continue
        selected_count += 1
        if received is None:
            selected_invalid_dates += 1
            continue
        monthly_six_narrative[received.strftime("%Y-%m")] += 1
        cleaned = normalize(narrative)
        redaction_markers += bool(re.search(r"\bx{4,}\b", cleaned))
        long_narratives += len(cleaned) > 20_000
        candidates.append({
            "hash": hashlib.sha256(cleaned.encode("utf-8")).hexdigest(),
            "text": cleaned,
            "label": product,
            "date": received,
            "id": row["Complaint ID"] or "",
        })
    if not rows_read:
        raise ValueError("source contains no rows")
    audit = {
        "rows_read": rows_read,
        "columns": columns,
        "missing_counts": {name: missing[name] for name in columns},
        "product_counts": dict(sorted(products.items())),
        "narrative_product_counts": dict(sorted(narrative_products.items())),
        "nonempty_narratives": narrative_count,
        "narrative_rate": narrative_count / rows_read,
        "selected_six_narratives": selected_count,
        "invalid_received_dates": invalid_dates,
        "selected_invalid_received_dates": selected_invalid_dates,
        "received_min": earliest.isoformat() if earliest else None,
        "received_max": latest.isoformat() if latest else None,
        "monthly_records": dict(sorted(monthly_all.items())),
        "monthly_narratives": dict(sorted(monthly_narrative.items())),
        "monthly_selected_six_narratives": dict(sorted(monthly_six_narrative.items())),
        "selected_redaction_marker_rows": redaction_markers,
        "selected_over_20000_chars": long_narratives,
    }
    return audit, candidates


def deduplicate(candidates: list[dict]) -> tuple[list[dict], dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        groups[row["hash"]].append(row)
    kept = []
    duplicate_extra = conflicting_groups = conflicting_rows = 0
    for group in groups.values():
        duplicate_extra += len(group) - 1
        if len({r["label"] for r in group}) > 1:
            conflicting_groups += 1
            conflicting_rows += len(group)
            continue
        kept.append(min(group, key=lambda r: (r["date"], r["id"])))
    kept.sort(key=lambda r: (r["date"], r["id"], r["hash"]))
    return kept, {
        "normalized_text_groups": len(groups),
        "duplicate_extra_rows": duplicate_extra,
        "conflicting_label_groups_excluded": conflicting_groups,
        "conflicting_rows_excluded": conflicting_rows,
        "unique_nonconflicting_rows": len(kept),
    }


def split_rows(rows: list[dict]) -> tuple[dict[str, list[dict]], dict]:
    splits: dict[str, list[dict]] = {"train": [], "validation": [], "test": []}
    outside = Counter()
    for row in rows:
        when = row["date"]
        if when <= date(2026, 3, 31):
            splits["train"].append(row)
        elif date(2026, 4, 1) <= when <= date(2026, 4, 30):
            splits["validation"].append(row)
        elif date(2026, 5, 1) <= when <= date(2026, 5, 31):
            splits["test"].append(row)
        else:
            outside[when.strftime("%Y-%m")] += 1
    hashes = [{row["hash"] for row in rows} for rows in splits.values()]
    if any(hashes[i] & hashes[j] for i in range(3) for j in range(i + 1, 3)):
        raise AssertionError("normalized narrative leaked across temporal splits")
    details = {
        name: {
            "n": len(group),
            "date_min": min((r["date"] for r in group), default=None).isoformat() if group else None,
            "date_max": max((r["date"] for r in group), default=None).isoformat() if group else None,
            "class_counts": {p: sum(r["label"] == p for r in group) for p in PRODUCTS},
        }
        for name, group in splits.items()
    }
    return splits, {"splits": details, "outside_window_by_month": dict(sorted(outside.items()))}


def tokenize(text: str) -> list[str]:
    # Redaction placeholders carry no useful product meaning. Cap long inputs.
    tokens = [t for t in re.findall(r"[a-z]+", text.casefold())
              if len(t) >= 2 and set(t) != {"x"}]
    return tokens[:MAX_TOKENS]


class CountNaiveBayes:
    def __init__(self, min_doc_freq: int = MIN_DOC_FREQ):
        self.min_doc_freq = min_doc_freq
        self.vocabulary: set[str] = set()
        self.class_docs = Counter()
        self.word_counts: dict[str, Counter] = {p: Counter() for p in PRODUCTS}
        self.totals = Counter()
        self.trained = False

    def fit(self, rows: list[dict]) -> "CountNaiveBayes":
        if not rows:
            raise ValueError("training set is empty")
        docfreq = Counter()
        tokenized = []
        for row in rows:
            tokens = tokenize(row["text"])
            tokenized.append((row["label"], tokens))
            docfreq.update(set(tokens))
        self.vocabulary = {word for word, count in docfreq.items()
                           if count >= self.min_doc_freq}
        if not self.vocabulary:
            raise ValueError("no vocabulary terms meet min_doc_freq")
        for label, tokens in tokenized:
            self.class_docs[label] += 1
            counts = Counter(t for t in tokens if t in self.vocabulary)
            self.word_counts[label].update(counts)
            self.totals[label] += sum(counts.values())
        self.trained = True
        return self

    def predict_one(self, text: str, alpha: float = 1.0) -> str:
        if not self.trained or alpha <= 0:
            raise ValueError("fit model first; alpha must be positive")
        counts = Counter(t for t in tokenize(text) if t in self.vocabulary)
        vocab_size = len(self.vocabulary)
        n_docs = sum(self.class_docs.values())
        scores = []
        for label in PRODUCTS:
            prior = (self.class_docs[label] + 1) / (n_docs + len(PRODUCTS))
            denom = self.totals[label] + alpha * vocab_size
            score = math.log(prior) + sum(
                count * (math.log(self.word_counts[label][word] + alpha) - math.log(denom))
                for word, count in counts.items()
            )
            scores.append(score)
        return PRODUCTS[max(range(len(PRODUCTS)), key=lambda i: scores[i])]

    def predict(self, rows: list[dict], alpha: float = 1.0) -> list[str]:
        return [self.predict_one(row["text"], alpha) for row in rows]


def rule_predict(text: str) -> str | None:
    if not text or len(text) < 20 or len(text) > 20_000:
        return None
    hits = {}
    for product, phrases in RULES.items():
        found = [phrase for phrase in phrases
                 if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text)]
        if found:
            hits[product] = sum(2 if " " in phrase else 1 for phrase in found)
    if not hits:
        return None
    best = max(hits.values())
    winners = [p for p, score in hits.items() if score == best]
    return winners[0] if len(winners) == 1 else None


def wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z * z / total
    midpoint = (p + z * z / (2 * total)) / denom
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [max(0, midpoint - radius), min(1, midpoint + radius)]


def macro_f1(true: list[str], pred: list[str | None]) -> float:
    values = []
    for label in PRODUCTS:
        tp = sum(a == label and b == label for a, b in zip(true, pred))
        fp = sum(a != label and b == label for a, b in zip(true, pred))
        fn = sum(a == label and b != label for a, b in zip(true, pred))
        values.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(values) / len(PRODUCTS)


def bootstrap_macro_f1(true: list[str], pred: list[str | None],
                       draws: int = BOOTSTRAPS, seed: int = SEED) -> list[float] | None:
    if not true:
        return None
    rng = random.Random(seed)
    n = len(true)
    scores = []
    for _ in range(draws):
        indexes = [rng.randrange(n) for _ in range(n)]
        scores.append(macro_f1([true[i] for i in indexes], [pred[i] for i in indexes]))
    scores.sort()
    return [scores[int(.025 * (draws - 1))], scores[int(.975 * (draws - 1))]]


def evaluate(rows: list[dict], pred: list[str | None],
             with_interval: bool = False) -> dict:
    if len(rows) != len(pred) or not rows:
        raise ValueError("nonempty labels and predictions must have equal length")
    true = [r["label"] for r in rows]
    n = len(true)
    correct = sum(a == b for a, b in zip(true, pred))
    auto = sum(p is not None for p in pred)
    correct_auto = sum(a == b for a, b in zip(true, pred) if b is not None)
    class_metrics = {}
    for label in PRODUCTS:
        support = sum(a == label for a in true)
        tp = sum(a == label and b == label for a, b in zip(true, pred))
        fp = sum(a != label and b == label for a, b in zip(true, pred))
        fn = support - tp
        class_metrics[label] = {
            "support": support,
            "precision": tp / (tp + fp) if tp + fp else 0.0,
            "recall": tp / support if support else None,
            "f1": 2 * tp / (2 * tp + fp + fn) if tp else 0.0,
        }
    result = {
        "n": n,
        "correct": correct,
        "accuracy": correct / n,
        "macro_f1": macro_f1(true, pred),
        "coverage": auto / n,
        "accuracy_when_auto": correct_auto / auto if auto else None,
        "per_class": class_metrics,
        "confusion_matrix": {
            label: {outcome: sum(a == label and ((b is None) if outcome == "review" else b == outcome)
                                for a, b in zip(true, pred))
                    for outcome in (*PRODUCTS, "review")}
            for label in PRODUCTS
        },
    }
    if with_interval:
        result.update({
            "accuracy_95_wilson": wilson(correct, n),
            "coverage_95_wilson": wilson(auto, n),
            "accuracy_when_auto_95_wilson": wilson(correct_auto, auto),
            "macro_f1_95_bootstrap": bootstrap_macro_f1(true, pred),
        })
    return result


def run_experiment(zip_path: Path, max_rows: int = MAX_ROWS,
                   expected_sha256: str | None = EXPECTED_SHA256) -> dict:
    start = time.perf_counter()
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    digest = sha256_file(zip_path)
    if expected_sha256 and digest.lower() != expected_sha256.lower():
        raise ValueError("source SHA-256 differs from documented snapshot")
    audit, candidates = scan_source(zip_path, max_rows)
    scanned = time.perf_counter()
    unique, dedup = deduplicate(candidates)
    splits, split_details = split_rows(unique)
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    if not all((train, validation, test)):
        raise ValueError("train, validation, and test must all be nonempty")
    majority_label = max(PRODUCTS, key=lambda p: sum(r["label"] == p for r in train))
    model = CountNaiveBayes().fit(train)
    tuned = []
    for alpha in ALPHAS:
        predictions = model.predict(validation, alpha)
        score = evaluate(validation, predictions)
        tuned.append({"alpha": alpha, "accuracy": score["accuracy"],
                      "macro_f1": score["macro_f1"]})
    # Validation alone chooses alpha. The May test set is accessed only after this.
    chosen = max(tuned, key=lambda x: (x["macro_f1"], x["accuracy"], -x["alpha"]))
    trained = time.perf_counter()
    test_majority = [majority_label] * len(test)
    test_rules = [rule_predict(r["text"]) for r in test]
    test_nb = model.predict(test, chosen["alpha"])
    unknown_docs = sum(not any(t in model.vocabulary for t in tokenize(r["text"])) for r in test)
    capped_docs = sum(len(re.findall(r"[a-z]+", r["text"])) > MAX_TOKENS for r in test)
    result = {
        "protocol": {
            "version": "stage2-v1",
            "seed": SEED,
            "source_scope": f"first {max_rows:,} CSV records, matching workbook capacity",
            "train_period": "through 2026-03-31",
            "validation_period": "2026-04-01 to 2026-04-30",
            "test_period": "2026-05-01 to 2026-05-31",
            "excluded_prior_trial": "2026-06 and later",
            "leakage_control": "hash normalized narrative across all months; drop cross-label groups; keep earliest row before time split; train-only vocabulary",
            "feature_policy": "narrative only; redaction placeholder tokens removed; max 5000 tokens",
            "uncertainty": "95% Wilson intervals for rates; 500 paired-row bootstrap replicates for macro-F1",
        },
        "source": {"archive": zip_path.name, "sha256": digest, **audit},
        "data_dictionary": {name: {"meaning": meaning, "model_role": role}
                            for name, (meaning, role) in DATA_DICTIONARY.items()},
        "deduplication": dedup,
        **split_details,
        "model": {
            "name": "bag-of-words multinomial naive Bayes",
            "train_rows": len(train),
            "min_document_frequency": MIN_DOC_FREQ,
            "vocabulary_size": len(model.vocabulary),
            "alpha_candidates": list(ALPHAS),
            "selected_alpha": chosen["alpha"],
            "test_docs_without_train_vocabulary": unknown_docs,
            "test_docs_over_token_cap": capped_docs,
        },
        "validation_alpha_scores": tuned,
        "test": {
            "majority_label_from_train": majority_label,
            "majority": evaluate(test, test_majority, True),
            "rules_from_stage1": evaluate(test, test_rules, True),
            "naive_bayes": evaluate(test, test_nb, True),
        },
        "checks": {
            "hash_overlap_across_splits": 0,
            "vocabulary_fit_rows": len(train),
            "test_used_for_alpha_selection": False,
            "raw_narratives_exported": False,
        },
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "dependencies": "Python standard library only"},
        "runtime_seconds": {"hash_and_scan": round(scanned - start, 3),
                            "dedup_fit_validation": round(trained - scanned, 3),
                            "total": round(time.perf_counter() - start, 3)},
    }
    result["report"] = {
        "source_rows": audit["rows_read"],
        "narrative_rows": audit["nonempty_narratives"],
        "six_rows": audit["selected_six_narratives"],
        "dedup_extra_rows": dedup["duplicate_extra_rows"],
        "conflict_groups": dedup["conflicting_label_groups_excluded"],
        "train_n": len(train),
        "val_n": len(validation),
        "test_n": len(test),
        "june_excluded_n": split_details["outside_window_by_month"].get("2026-06", 0),
        "train_classes": split_details["splits"]["train"]["class_counts"],
        "val_classes": split_details["splits"]["validation"]["class_counts"],
        "test_classes": split_details["splits"]["test"]["class_counts"],
        "class_total": {p: audit["product_counts"].get(p, 0) for p in PRODUCTS},
        "class_narratives": {p: audit["narrative_product_counts"].get(p, 0) for p in PRODUCTS},
        "month_raw_narratives": {m: audit["monthly_selected_six_narratives"].get(m, 0)
                                 for m in ("2026-03", "2026-04", "2026-05", "2026-06")},
        "field_missing": audit["missing_counts"],
        "chosen_alpha": chosen["alpha"],
        "models": {
            name: {
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "coverage": metrics["coverage"],
                "accuracy_when_auto": metrics["accuracy_when_auto"],
                "per_class_recall": {p: metrics["per_class"][p]["recall"] for p in PRODUCTS},
                "accuracy_ci_95": metrics["accuracy_95_wilson"],
                "macro_f1_ci_95": metrics["macro_f1_95_bootstrap"],
            }
            for name, metrics in result["test"].items() if name != "majority_label_from_train"
        },
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--max-rows", type=int, default=MAX_ROWS)
    parser.add_argument("--skip-hash-check", action="store_true",
                        help="Only for small synthetic fixtures; output still records observed SHA-256")
    args = parser.parse_args()
    if args.max_rows <= 0:
        parser.error("--max-rows must be positive")
    result = run_experiment(args.data, args.max_rows,
                            None if args.skip_hash_check else EXPECTED_SHA256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote aggregate results: {args.output}")
    print(f"Train/validation/test: {result['splits']['train']['n']}/"
          f"{result['splits']['validation']['n']}/{result['splits']['test']['n']}")
    print(f"May test macro-F1: majority={result['test']['majority']['macro_f1']:.4f}, "
          f"rules={result['test']['rules_from_stage1']['macro_f1']:.4f}, "
          f"naive_bayes={result['test']['naive_bayes']['macro_f1']:.4f}")


if __name__ == "__main__":
    main()
