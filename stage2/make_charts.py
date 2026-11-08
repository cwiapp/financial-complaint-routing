"""Build privacy-safe SVG figures from aggregate summary.json only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from stage2 import HERE, PRODUCTS


LABELS = ("Debt collection", "Checking/savings", "Credit card",
          "Money transfer", "Mortgage", "Credit reporting")
COLORS = ("#2475B8", "#12A393", "#E6A43C", "#8360C3", "#D26A61", "#6E879E")


def svg_start(width: int, height: int, title: str) -> list[str]:
    return [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'role="img" aria-label="{escape(title)}">',
            '<rect width="100%" height="100%" fill="white"/>',
            f'<text x="38" y="43" font-family="Arial" font-size="22" '
            f'font-weight="bold" fill="#000000">{escape(title)}</text>']


def narrative_rates(data: dict) -> str:
    totals = data["report"]["class_total"]
    narratives = data["report"]["class_narratives"]
    rates = [narratives[p] / totals[p] if totals[p] else 0 for p in PRODUCTS]
    max_rate = max(rates) * 1.08
    lines = svg_start(980, 470, "Narrative availability differs sharply by product")
    lines.append('<text x="39" y="68" font-family="Arial" font-size="13" fill="#000000">'
                 'Share of records with nonempty consumer narratives; first workbook-sized source segment</text>')
    for i, (label, rate, color) in enumerate(zip(LABELS, rates, COLORS)):
        y = 104 + i * 51
        width = max(1, round(550 * rate / max_rate))
        lines.append(f'<text x="39" y="{y+19}" font-family="Arial" font-size="14" '
                     f'fill="#000000">{escape(label)}</text>')
        lines.append(f'<rect x="285" y="{y}" width="550" height="24" rx="4" fill="#E7EEF4"/>')
        lines.append(f'<rect x="285" y="{y}" width="{width}" height="24" rx="4" fill="{color}"/>')
        pct = f"{rate*100:.3f}%" if rate < .01 else f"{rate*100:.1f}%"
        lines.append(f'<text x="855" y="{y+18}" font-family="Arial" font-size="14" '
                     f'font-weight="bold" fill="#000000">{pct}</text>')
    lines.append('<text x="39" y="445" font-family="Arial" font-size="12" fill="#000000">'
                 'A narrative-only model observes a selective subset; this is not a population prevalence estimate.</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def split_shift(data: dict) -> str:
    splits = data["report"]
    groups = [("Train through Mar", splits["train_classes"], splits["train_n"]),
              ("Apr validation", splits["val_classes"], splits["val_n"]),
              ("May retrospective", splits["test_classes"], splits["test_n"])]
    lines = svg_start(980, 530, "Class mix and volume change across time splits")
    lines.append('<text x="39" y="68" font-family="Arial" font-size="13" fill="#000000">'
                 'First receipt day fixes label; later disagreements cannot delete earlier records</text>')
    left = 325
    for i, (name, counts, n) in enumerate(groups):
        y = 108 + i * 83
        lines.append(f'<text x="39" y="{y+17}" font-family="Arial" font-size="14" '
                     f'fill="#000000">{escape(name)} (n={n:,})</text>')
        x = left
        for label, color in zip(PRODUCTS, COLORS):
            width = 555 * counts[label] / n
            lines.append(f'<rect x="{x:.2f}" y="{y}" width="{width:.2f}" '
                         f'height="30" fill="{color}"/>')
            x += width
    for i, (label, color) in enumerate(zip(LABELS, COLORS)):
        column = i % 3
        row = i // 3
        x = 39 + column * 310
        y = 391 + row * 36
        lines.append(f'<rect x="{x}" y="{y-13}" width="17" height="17" fill="{color}"/>')
        lines.append(f'<text x="{x+25}" y="{y}" font-family="Arial" font-size="13" '
                     f'fill="#000000">{escape(label)}</text>')
    lines.append('<text x="39" y="493" font-family="Arial" font-size="12" fill="#000000">'
                 f'April contains {splits["val_n"]:,} eligible narratives versus {splits["train_n"]:,} in training; May was inspected earlier.</text>')
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=HERE / "results" / "summary.json")
    args = parser.parse_args()
    data = json.loads(args.summary.read_text(encoding="utf-8"))
    out = args.summary.parent
    (out / "fig1_narrative_availability.svg").write_text(narrative_rates(data), encoding="utf-8")
    (out / "fig2_temporal_class_mix.svg").write_text(split_shift(data), encoding="utf-8")
    print(f"Wrote two aggregate SVG figures to {out}")


if __name__ == "__main__":
    main()
