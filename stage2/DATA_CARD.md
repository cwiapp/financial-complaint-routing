# 数据卡：金融投诉历史快照（阶段二）

## 来源、版本与适用范围

本项目使用用户提供的 `complaints.csv.zip` 历史快照。字段结构与 [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) 相似；原始下载日期、再分发许可和工作簿/压缩 CSV 的逐行一致性尚未独立核实。当前官网下载文件未必等同于本快照。公共仓库不包含源数据或任何真实投诉原文。

- ZIP SHA-256：`850d5d220285abecb4d4b94ae4c92a8f318476ce14bd0460c3d6361c79ae9694`。
- 读取前 1,048,575 条 CSV 数据行，对应给定工作簿可容纳的数据行数；不代表 ZIP 的全部记录。
- 接收日期范围：2014-07-15 至 2026-07-05。
- 非空投诉叙述：17,093 条（1.63%）；六个目标产品中的非空叙述：14,919 条。

## 字段字典与缺失情况

仅 `Consumer complaint narrative` 作为模型输入；`Product` 是监督标签。接收日期只用于时间划分，投诉 ID 只用于去重时确定最早记录。其余字段不进入模型，尤其是处理结果和回应日期等提交后的变量。

| 字段 | 含义 | 模型使用 | 缺失条数 | 缺失率 |
|---|---|---|---:|---:|
| Date received | Complaint receipt timestamp | time split only | 0 | 0.00% |
| Product | Financial product category | target label | 121 | 0.01% |
| Sub-product | Product subtype | audit only; excluded from features | 139 | 0.01% |
| Issue | Issue category | audit only; excluded from features | 145 | 0.01% |
| Sub-issue | Issue subtype | audit only; excluded from features | 12,173 | 1.16% |
| Consumer complaint narrative | Consumer narrative | sole model feature | 1,031,482 | 98.37% |
| Company public response | Public company response | post-submission; excluded | 642,432 | 61.27% |
| Company | Named company | audit only; excluded | 0 | 0.00% |
| State | Consumer state | audit only; excluded | 1,314 | 0.13% |
| ZIP code | Consumer ZIP code | sensitive; excluded | 913 | 0.09% |
| Tags | Complaint tags | audit only; excluded | 1,026,565 | 97.90% |
| Submitted via | Submission channel | audit only; excluded | 0 | 0.00% |
| Date sent to company | Forwarding date | post-submission; excluded | 39,019 | 3.72% |
| Company response to consumer | Response outcome | post-submission; excluded | 222,634 | 21.23% |
| Timely response? | Response timeliness | post-submission; excluded | 0 | 0.00% |
| Complaint ID | Record identifier | dedup tie-break only; excluded | 2,390 | 0.23% |

## 六类产品中的叙述可得率

| 产品类别 | 全部记录 | 非空叙述 | 可得率 |
|---|---:|---:|---:|
| Debt collection | 53,835 | 5,566 | 10.339% |
| Checking or savings account | 13,191 | 3,020 | 22.894% |
| Credit card | 13,509 | 3,009 | 22.274% |
| Money transfer, virtual currency, or money service | 5,706 | 1,328 | 23.274% |
| Mortgage | 5,139 | 1,082 | 21.055% |
| Credit reporting or other personal consumer reports | 946,029 | 914 | 0.097% |

## 清洗、划分和限制

六类非空叙述中有 1,504 条重复额外记录；1 个跨产品标签冲突的文本组被整组剔除。规范化文本先全局分组，再保留最早记录并按接收日期划分，以避免相同叙述跨集合。训练、验证、测试分别为 3,615、6,111、2,742 条；阶段一曾查看的 2026 年 6 月 946 条去重后记录被排除。

叙述是否公开并非随机。征信类的叙述可得率远低于其他目标类别，模型测试集因而不能代表全部投诉，也不能推断总体产品分布。文本可能包含个人信息或经过遮盖；仅在内存中用于受限的研究实验，输出和公共仓库只保留汇总统计。`Product` 标签也可能有噪声，未经过独立人工复核。

图表可由 `python make_charts.py` 读取同一 `results/summary.json` 重建；实验指标由 `python stage2.py` 重建。
