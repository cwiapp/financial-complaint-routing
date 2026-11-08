# 金融投诉文本自动分类与人工分流

本仓库按阶段累积项目证据。根目录保留阶段一开题报告、Python 规则原型和测试；[`stage2/`](stage2/) 包含阶段二数据卡、固定实验流水线、训练基线、汇总结果、图表与报告。当前原型只接收英文投诉叙述，输出六类产品中的一类或“转人工”。规则命中词是解释线索，不是模型概率，也不能据此判断投诉真伪或责任。

## 环境与数据

- Python 3.11 或更新版本；原型只用标准库。生成 PDF 的脚本另需 `reportlab`。
- 如果要重新生成 PDF，先执行 `python -m pip install -r requirements.txt`，再运行 `python build_report.py`。
- 本机原始快照为 `D:\Desktop\金融论文\complaints.csv.zip`，位于本仓库外（与提供的 `complaints.xlsx` 同目录）。脚本仅读取压缩 CSV 的前 1,048,575 条记录，以对应 Excel 文件可容纳的数据行数；不会解压出完整 CSV 临时文件。迁移仓库后，请通过 `--data` 显式传入快照路径。
- 报告采用的数据是用户提供的本地副本。字段与 CFPB 投诉数据库相似；原始下载日期、筛选条件和当时许可凭证仍需团队补充。阶段二已核验 ZIP 哈希，完整来源链仍不能独立确认。
- 原始投诉叙述不随项目提交；示例句子为人工编写。
- 本地数据版本：`complaints.xlsx` 的 SHA-256 为 `12CEDEB7B886B8DEA2DF2580A5FA05888ECA9DC61463FA4EF5F8222E14CF7455`；`complaints.csv.zip` 的 SHA-256 为 `850D5D220285ABECB4D4B94AE4C92A8F318476CE14BD0460C3D6361C79AE9694`。

## 运行

在本目录执行：

```powershell
python prototype.py demo --text "A debt collector keeps calling about a debt I do not owe."
python prototype.py audit
python prototype.py evaluate
python -m unittest -v
```

`audit` 给出工作簿对应数据段的覆盖率和六类样本数。阶段一 `evaluate` 先按标准化叙述去重，剔除相同文本却标成不同类别的冲突组，再对首次出现在 2026 年 6 月的六类投诉进行规则基线评估。该月结果仅是静态原型检查，不能代表部署表现。阶段二采用按首次接收日固定标签的去重规则和历史时间划分，见 [`stage2/README.md`](stage2/README.md)。

阶段二在仓库根目录的复现入口（ZIP 保持在仓库外）：

```powershell
python stage2/test_stage2.py -v
python stage2/stage2.py --data "D:\Desktop\金融论文\complaints.csv.zip" --output stage2/results/summary.json
python stage2/make_charts.py --summary stage2/results/summary.json
python stage2/make_data_card.py --summary stage2/results/summary.json
```

这里的 2026 年 5 月结果在此前版本已经被查看；第四版是回顾性复评，不能称为从未查看过的独立测试。平滑参数仅依 4 月验证集确定，5 月未用于本次选参。

## 目录与提交版本

- `YangZhao_phase1_report.pdf`：阶段一已发布版本的报告副本；阶段一标签仍保留原提交。
- `stage2/YangZhao_phase2_report.pdf`：按阶段二六项评分标准修订的报告；对应 `phase-2-submission-v4` 标签。旧版可从先前的阶段二标签读取。
- `prototype.py`：数据流式读取、数据审计、规则分流和评价。
- `test_prototype.py`：15 个边界及正确性测试。
- `requirements.txt`：运行依赖说明。

成员为杨俊炜、赵煜凡。Git 仓库为 <https://github.com/cwiapp/financial-complaint-routing>。阶段一标签为 `phase-1-submission`；阶段二保留此前标签 `phase-2-submission`、`phase-2-submission-v2` 和 `phase-2-submission-v3`，本次修订为 `phase-2-submission-v4`。阶段二明确分工见 [`stage2/CONTRIBUTIONS.md`](stage2/CONTRIBUTIONS.md)。
