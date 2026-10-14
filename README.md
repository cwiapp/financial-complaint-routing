# 金融投诉文本自动分类与人工分流：阶段一

本目录包含阶段一 PDF 开题报告、可运行的 Python 规则基线及测试。当前原型只接收英文投诉叙述，输出六类产品中的一类或“转人工”。输出中的规则命中词是解释线索，不是模型概率，也不能据此判断投诉真伪或责任。

## 环境与数据

- Python 3.11 或更新版本；原型只用标准库。生成 PDF 的脚本另需 `reportlab`。
- 如果要重新生成 PDF，先执行 `python -m pip install -r requirements.txt`，再运行 `python build_report.py`。
- 将原始 `complaints.csv.zip` 放在本目录的上一级（与提供的 `complaints.xlsx` 同目录）。脚本仅读取压缩 CSV 的前 1,048,575 条记录，以对应 Excel 文件的数据行数；不会解压出 8.9 GB 的临时文件。
- 报告采用的数据是用户提供的本地副本。字段与 CFPB 投诉数据库一致，但原始下载日期、许可适用细节和文件哈希仍须由团队在提交前核实。
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

`audit` 给出工作簿对应数据段的覆盖率和六类样本数。`evaluate` 先按标准化叙述去重，剔除相同文本却标成不同类别的冲突组，再对首次出现在 2026 年 6 月的六类投诉进行规则基线评估。该月结果仅是静态原型检查，不能代表部署表现。阶段二会冻结训练/验证/测试划分并建立正式模型基线。

## 目录与提交前待补

- `阶段一开题报告.pdf`：5 页开题报告，封面成员信息已填写；提交时使用此文件。
- `prototype.py`：数据流式读取、数据审计、规则分流和评价。
- `test_prototype.py`：15 个边界及正确性测试。
- `requirements.txt`：运行依赖说明。

成员为杨俊炜、赵煜凡。Git 仓库为 <https://github.com/cwiapp/financial-complaint-routing>，阶段一提交标签为 `phase-1-submission`。团队名称与成员具体分工尚未提供，正式提交前需据实补充。
