"""Render a data card from aggregate summary.json; never reads raw narratives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage2 import HERE, PRODUCTS


def build_card(data: dict) -> str:
    source = data["source"]
    report = data["report"]
    dedup = data["deduplication"]
    length = source["selected_narrative_length_chars"]
    paired = report["paired_delta_nb_minus_rules"]
    rows = [
        "# 数据卡：金融投诉历史快照（阶段二）",
        "",
        "## 来源、版本与适用范围",
        "",
        "团队声明由赵煜凡负责数据采集，向小组提供 `complaints.csv.zip` 与 `complaints.xlsx` 本地历史快照。研究脚本顺序读取 ZIP 中的前段记录，核对两份文件的表头及前两行并计算 ZIP 哈希；未逐行核对整个工作簿。字段结构与 [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) 相似。CFPB 当前页面说明其发布的数据可自由使用与分析，但本地快照的原始下载日期、筛选条件及当时许可凭证未随文件提供，故无法独立核实其完整来源链；当前官网下载文件也未必等同于该快照。公共仓库不包含源数据或真实投诉原文。",
        "",
        f"- ZIP SHA-256：`{source['sha256']}`。",
        f"- 读取前 {source['rows_read']:,} 条 CSV 数据行，对应给定工作簿可容纳的数据行数；不代表 ZIP 的全部记录。",
        f"- 接收日期范围：{source['received_min']} 至 {source['received_max']}。",
        f"- 非空投诉叙述：{source['nonempty_narratives']:,} 条（{source['narrative_rate']:.2%}）；六个目标产品中的非空叙述：{source['selected_six_narratives']:,} 条。",
        "- 观察单位：一条投诉记录；同一规范化叙述重复出现时，以首次接收日的记录作为建模观察。目标总体仅限有公开英文叙述的六类历史投诉。",
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
        "## 数据质量与时间分布",
        "",
        f"六类非空叙述按大小写与空白规范化后的字符长度中位数为 {length['median']:,}，95 分位为 {length['p95']:,}，99 分位为 {length['p99']:,}，最长为 {length['max']:,}；{length['bins']['>=5000']:,} 条达到 5,000 字符。长度统计先于模型的 5,000 个英文词元截断。{source['selected_redaction_marker_rows']:,} 条含脱敏占位符，遮盖并不保证无个人信息。",
        "",
        "| 产品类别 | 训练 ≤3 月 | 4 月验证 | 5 月历史复评 |",
        "|---|---:|---:|---:|",
    ])
    for product in PRODUCTS:
        train = report["train_classes"][product]
        val = report["val_classes"][product]
        test = report["test_classes"][product]
        rows.append(f"| {product} | {train:,} ({train/report['train_n']:.1%}) | {val:,} ({val/report['val_n']:.1%}) | {test:,} ({test/report['test_n']:.1%}) |")
    rows.extend([
        "",
        f"债务催收占比从训练集约 {report['train_classes'][PRODUCTS[0]]/report['train_n']:.1%} 降到五月约 {report['test_classes'][PRODUCTS[0]]/report['test_n']:.1%}，信用卡从约 {report['train_classes'][PRODUCTS[2]]/report['train_n']:.1%} 升到 {report['test_classes'][PRODUCTS[2]]/report['test_n']:.1%}；这支持按时间评估并同时报告宏平均 F1 与各类召回率。四月样本量高于训练期，具体成因不能仅凭本快照确定。",
        "",
        "## 清洗、划分和限制",
        "",
        f"六类非空叙述中有 {dedup['duplicate_extra_rows']:,} 条重复额外记录。先把规范化文本全局分组，最早接收日固定标签；最早日若有不同产品标签，则整组排除。本快照最早日冲突为 {dedup['earliest_day_conflicting_groups_excluded']} 组、{dedup['earliest_day_conflicting_rows_excluded']} 条。较晚日期才出现异标签的为 {dedup['later_label_disagreement_groups_kept_first']} 组、{dedup['later_label_disagreement_rows_dropped']} 条：较早的记录保留，较晚记录丢弃，不让未来标签改变历史观察。每组最多保留一条最早日记录，再按接收日期划分；跨集合规范化文本哈希交集为 {data['checks']['hash_overlap_across_splits']}。",
        "",
        f"训练、验证、五月历史复评分别为 {report['train_n']:,}、{report['val_n']:,}、{report['test_n']:,} 条；阶段一曾查看的 2026 年 6 月 {report['june_excluded_n']:,} 条去重后记录被排除。五月标签和结果在此前阶段二版本中已被查看，本版属于回顾性复评，不能称五月为未查看过的独立测试；本次平滑参数仍只依四月验证集确定。",
        "",
        f"同一批五月行上的朴素贝叶斯与规则基线宏平均 F1 差值为 {paired['delta_macro_f1']:.3f}；{paired['draws']} 次配对自助重采样所得 95% 分位数区间为 [{paired['ci_95_percentile'][0]:.3f}, {paired['ci_95_percentile'][1]:.3f}]。区间反映固定历史样本的抽样波动，不包括时间漂移、文本近重复或重复查看五月结果的影响。",
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
