"""Stage-1 rule baseline for routing English financial complaint narratives.

This is deliberately a transparent baseline, not a calibrated probability model.
Only the narrative is used at inference time. The CSV ZIP beside the supplied
workbook is used for reproducible analysis of the workbook-sized first segment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


MAX_WORKBOOK_RECORDS = 1_048_575
PRODUCTS = (
    "Debt collection",
    "Checking or savings account",
    "Credit card",
    "Money transfer, virtual currency, or money service",
    "Mortgage",
    "Credit reporting or other personal consumer reports",
)
RULES = {
    PRODUCTS[0]: ("debt collector", "collection agency", "debt collection", "collector", "debt"),
    PRODUCTS[1]: ("checking account", "savings account", "bank account", "direct deposit", "overdraft"),
    PRODUCTS[2]: ("credit card", "card statement", "card issuer", "chargeback", "apr"),
    PRODUCTS[3]: ("wire transfer", "money transfer", "remittance", "cryptocurrency", "bitcoin"),
    PRODUCTS[4]: ("mortgage", "foreclosure", "home loan", "escrow", "loan servicer"),
    PRODUCTS[5]: ("credit report", "credit bureau", "credit reporting", "transunion", "experian", "equifax"),
}


def normalize(text: str) -> str:
    """Normalize whitespace for scoring and duplicate detection."""
    if not isinstance(text, str):
        raise TypeError("narrative must be a string")
    return " ".join(text.casefold().split())


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


def route(narrative: str) -> dict:
    """Return a product route or refer an ambiguous/invalid case for review."""
    if not isinstance(narrative, str):
        raise TypeError("narrative must be a string")
    cleaned = normalize(narrative)
    if not cleaned:
        return {"status": "review", "product": None, "reason": "empty_text", "evidence": []}
    if len(cleaned) < 20:
        return {"status": "review", "product": None, "reason": "too_short", "evidence": []}
    if len(cleaned) > 20_000:
        return {"status": "review", "product": None, "reason": "too_long", "evidence": []}

    hits = {}
    for product, phrases in RULES.items():
        matched = [phrase for phrase in phrases if _contains_phrase(cleaned, phrase)]
        if matched:
            hits[product] = matched
    if not hits:
        return {"status": "review", "product": None, "reason": "no_rule_match", "evidence": []}
    scores = {product: sum(2 if " " in phrase else 1 for phrase in phrases)
              for product, phrases in hits.items()}
    best = max(scores.values())
    winners = [product for product, score in scores.items() if score == best]
    if len(winners) != 1:
        return {"status": "review", "product": None, "reason": "ambiguous", "evidence": []}
    product = winners[0]
    return {"status": "auto", "product": product, "reason": "rule_match", "evidence": hits[product]}


def iter_workbook_segment(zip_path: Path):
    """Stream records corresponding to the workbook's first 1,048,575 data rows."""
    required = {"Date received", "Product", "Consumer complaint narrative", "Complaint ID"}
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open("complaints.csv") as raw:
            import io
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"missing columns: {sorted(missing)}")
            for number, row in enumerate(reader, 1):
                if number > MAX_WORKBOOK_RECORDS:
                    break
                yield row


def audit(zip_path: Path) -> dict:
    total = narrative_count = 0
    products = Counter()
    narrative_products = Counter()
    for row in iter_workbook_segment(zip_path):
        total += 1
        products[row["Product"]] += 1
        if row["Consumer complaint narrative"]:
            narrative_count += 1
            narrative_products[row["Product"]] += 1
    return {
        "records": total,
        "nonempty_narratives": narrative_count,
        "selected_six_narratives": sum(narrative_products[p] for p in PRODUCTS),
        "product_counts": {p: products[p] for p in PRODUCTS},
        "narrative_product_counts": {p: narrative_products[p] for p in PRODUCTS},
    }


def evaluation_rows(zip_path: Path, month: str = "2026-06") -> tuple[list[dict], dict]:
    """Deduplicate by normalized narrative across all months, then select month."""
    groups = defaultdict(list)
    for row in iter_workbook_segment(zip_path):
        narrative = row["Consumer complaint narrative"]
        if narrative and row["Product"] in PRODUCTS and row["Date received"]:
            key = hashlib.sha256(normalize(narrative).encode("utf-8")).hexdigest()
            groups[key].append(row)
    selected = []
    conflicting = duplicate = 0
    development_counts = Counter()
    for group in groups.values():
        if len(group) > 1:
            duplicate += len(group) - 1
        if len({r["Product"] for r in group}) > 1:
            conflicting += 1
            continue
        first = min(group, key=lambda r: (r["Date received"], r["Complaint ID"]))
        if first["Date received"][:7] < month:
            development_counts[first["Product"]] += 1
        if first["Date received"].startswith(month):
            selected.append(first)
    selected.sort(key=lambda r: (r["Date received"], r["Complaint ID"]))
    majority = max(PRODUCTS, key=lambda p: development_counts[p])
    return selected, {"duplicate_extra_rows": duplicate,
                      "conflicting_text_groups": conflicting,
                      "development_majority_label": majority}


def score(rows: list[dict], majority_label: str = PRODUCTS[0]) -> dict:
    if not rows:
        raise ValueError("evaluation set is empty")
    true = [r["Product"] for r in rows]
    routed = [route(r["Consumer complaint narrative"]) for r in rows]
    pred = [r["product"] for r in routed]
    auto = sum(p is not None for p in pred)
    correct_auto = sum(p == y for p, y in zip(pred, true) if p is not None)

    def macro_f1(predictions: list[str | None]) -> float:
        values = []
        for label in PRODUCTS:
            tp = sum(p == label and y == label for p, y in zip(predictions, true))
            fp = sum(p == label and y != label for p, y in zip(predictions, true))
            fn = sum(p != label and y == label for p, y in zip(predictions, true))
            values.append(0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn))
        return sum(values) / len(values)

    return {
        "n": len(rows),
        "class_counts": dict(Counter(true)),
        "majority_accuracy": sum(y == majority_label for y in true) / len(rows),
        "majority_macro_f1": macro_f1([majority_label] * len(rows)),
        "rule_coverage": auto / len(rows),
        "rule_accuracy_when_auto": correct_auto / auto if auto else None,
        "rule_macro_f1_abstention_as_error": macro_f1(pred),
        "review_reasons": dict(Counter(r["reason"] for r in routed if r["status"] == "review")),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("demo", "audit", "evaluate"))
    parser.add_argument("--data", type=Path, default=Path(__file__).resolve().parent.parent / "complaints.csv.zip")
    parser.add_argument("--text", help="English complaint text for demo")
    args = parser.parse_args()
    if args.action == "demo":
        if args.text is None:
            parser.error("demo requires --text")
        result = route(args.text)
    else:
        if not args.data.is_file():
            parser.error(f"data archive not found: {args.data}")
        if args.action == "audit":
            result = audit(args.data)
        else:
            rows, dedup = evaluation_rows(args.data)
            result = {"split": "2026-06", **dedup,
                      **score(rows, dedup["development_majority_label"])}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
