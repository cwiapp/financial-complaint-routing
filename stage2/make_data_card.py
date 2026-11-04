"""Render a data card from aggregate summary.json; never reads raw narratives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage2 import HERE, PRODUCTS


def build_card(data: dict) -> str:
    source = data["source"]
    report = data["report"]
    rows = [
        "# 数据卡：金融投诉历史快照（阶段二）",
        "",
        "## 来源、版本与适用范围",
        "",
        "本项目使用用户提供的 `complaints.csv.zip` 历史快照。字段结构与 [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) 相似；原始下载日期、再分发许可和工作簿/压缩 CSV 的逐行一致性尚未独立核实。当前官网下载文件未必等同于本快照。公共仓库不包含源数据或任何真实投诉原文。",
        "",
        f"- ZIP SHA-256：`{source['sha256']}`。",
        f"- 读取前 {source['rows_read']:,} 条 CSV 数据行，对应给定工作簿可容纳的数据行数；不代表 ZIP 的全部记录。",
        f"- 接收日期范围：{source['received_min']} 至 {source['received_max']}。",
        f"- 非空投诉叙述：{source['nonempty_narratives']:,} 条（{source['narrative_rate']:.2%}）；六个目标产品中的非空叙述：{source['selected_six_narratives']:,} 条。",
        "",
        "## 字段字典与缺失情况",
        "",
        "仅 `Consumer complaint narrative` 作为模型输入；`Product` 是监督标签。接收日期只用于时间划分，投诉 ID 只用于去重时确定最早记录。其余字段不进入模型，尤其是处理结果和回应日期等提交后的变量。",
        "",
        "| 字段 | 含义 | 模型使用 | 缺失条数 | 缺失率 |",
        "|---|---|---|---:|---:|",
    ]
    for column in source["columns"]:
        info = data["data_dictionary"].get(column, {})
        missing = source["missing_counts"][column]
        rows.append(f"| {column} | {info.get('meaning', 'unmapped')} | {info.get('model_role', 'excluded')} | {missing:,} | {missing/source['rows_read']:.2%} |")
    rows.extend([
        "",
        "## 六类产品中的叙述可得率",
        "",
        "| 产品类别 | 全部记录 | 非空叙述 | 可得率 |",
        "|---|---:|---:|---:|",
    ])
    for product in PRODUCTS:
        total = report["class_total"][product]
        narrative = report["class_narratives"][product]
        rows.append(f"| {product} | {total:,} | {narrative:,} | {narrative/total:.3%} |")
    rows.extend([
        "",
        "## 清洗、划分和限制",
        "",
        f"六类非空叙述中有 {report['dedup_extra_rows']:,} 条重复额外记录；{report['conflict_groups']} 个跨产品标签冲突的文本组被整组剔除。规范化文本先全局分组，再保留最早记录并按接收日期划分，以避免相同叙述跨集合。训练、验证、测试分别为 {report['train_n']:,}、{report['val_n']:,}、{report['test_n']:,} 条；阶段一曾查看的 2026 年 6 月 {report['june_excluded_n']:,} 条去重后记录被排除。",
        "",
        "叙述是否公开并非随机。征信类的叙述可得率远低于其他目标类别，模型测试集因而不能代表全部投诉，也不能推断总体产品分布。文本可能包含个人信息或经过遮盖；仅在内存中用于受限的研究实验，输出和公共仓库只保留汇总统计。`Product` 标签也可能有噪声，未经过独立人工复核。",
        "",
        "图表可由 `python make_charts.py` 读取同一 `results/summary.json` 重建；实验指标由 `python stage2.py` 重建。",
        "",
    ])
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=HERE / "results" / "summary.json")
    parser.add_argument("--output", type=Path, default=HERE / "DATA_CARD.md")
    args = parser.parse_args()
    data = json.loads(args.summary.read_text(encoding="utf-8"))
    args.output.write_text(build_card(data), encoding="utf-8")
    print(f"Wrote data card: {args.output}")


if __name__ == "__main__":
    main()
