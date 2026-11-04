"""Generate the phase-two report from aggregate, reproducible experiment output."""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results" / "summary.json"
OUT = ROOT / "YangZhao_phase2_report.pdf"
REPO = "https://github.com/cwiapp/financial-complaint-routing"
TAG = "phase-2-submission-v3"

pdfmetrics.registerFont(TTFont("MSYH", r"C:\Windows\Fonts\msyh.ttc", subfontIndex=0))
pdfmetrics.registerFont(TTFont("MSYH-Bold", r"C:\Windows\Fonts\msyhbd.ttc", subfontIndex=0))
BLACK = colors.black
BAR = colors.HexColor("#707070")
PALE = colors.HexColor("#F2F2F2")
GRID = colors.HexColor("#C8C8C8")


class Report(BaseDocTemplate):
    def __init__(self, path: Path):
        super().__init__(str(path), pagesize=A4, leftMargin=20 * mm,
                         rightMargin=20 * mm, topMargin=19 * mm,
                         bottomMargin=20 * mm,
                         title="金融投诉文本自动分流：阶段二数据与实验设计",
                         author="Yang Junwei and Zhao Yufan")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width,
                      self.height, leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="main", frames=frame,
                                           onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(BLACK)
        canvas.setLineWidth(0.8)
        canvas.line(20 * mm, height - 13 * mm, width - 20 * mm, height - 13 * mm)
        canvas.setFont("MSYH", 8)
        canvas.setFillColor(BLACK)
        canvas.drawString(20 * mm, 12 * mm, "Python 与人工智能课程 · 阶段二报告")
        canvas.drawRightString(width - 20 * mm, 12 * mm, str(doc.page))
        canvas.restoreState()


TITLE = ParagraphStyle("title", fontName="MSYH-Bold", fontSize=19,
                       leading=27, textColor=BLACK, alignment=TA_CENTER,
                       wordWrap="CJK", spaceAfter=7)
SUBTITLE = ParagraphStyle("subtitle", fontName="MSYH", fontSize=11,
                          leading=17, textColor=BLACK, alignment=TA_CENTER,
                          spaceAfter=11)
H1 = ParagraphStyle("h1", fontName="MSYH-Bold", fontSize=13.5, leading=19,
                    textColor=BLACK, wordWrap="CJK", spaceBefore=10,
                    spaceAfter=6)
H2 = ParagraphStyle("h2", fontName="MSYH-Bold", fontSize=10.5, leading=15,
                    textColor=BLACK, wordWrap="CJK", spaceBefore=7,
                    spaceAfter=3)
BODY = ParagraphStyle("body", fontName="MSYH", fontSize=10, leading=15.5,
                      textColor=BLACK, wordWrap="CJK", spaceAfter=5)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.8, leading=13,
                       textColor=BLACK, spaceAfter=3)
TINY = ParagraphStyle("tiny", parent=BODY, fontSize=8.1, leading=11.5,
                      textColor=BLACK, spaceAfter=0)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.8, leading=12.5,
                      spaceAfter=0)
HEAD = ParagraphStyle("head", parent=CELL, fontName="MSYH-Bold",
                      textColor=BLACK)


def p(text: str, style=BODY) -> Paragraph:
    return Paragraph(text, style)


def section(number: str, title: str):
    return p(f"{number}　{title}", H1)


def sub(title: str):
    return p(title, H2)


def table(rows, widths, header=True):
    cells = [[p(str(value), HEAD if header and i == 0 else CELL)
              for value in row] for i, row in enumerate(rows)]
    t = Table(cells, colWidths=widths, hAlign="LEFT",
              repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PALE),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1),
         [colors.white, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.3, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


class Bars(Flowable):
    def __init__(self, items, width=170 * mm, row_height=10 * mm,
                 max_value=None, suffix="%"):
        super().__init__()
        self.items = items
        self.width = width
        self.height = len(items) * row_height + 5 * mm
        self.row_height = row_height
        self.max_value = max_value or max(value for _, value in items)
        self.suffix = suffix

    def draw(self):
        canvas = self.canv
        label_w = 45 * mm
        value_w = 20 * mm
        bar_w = self.width - label_w - value_w - 5 * mm
        for i, (label, value) in enumerate(self.items):
            y = self.height - (i + 1) * self.row_height
            canvas.setFillColor(BLACK)
            canvas.setFont("MSYH", 8.6)
            canvas.drawString(0, y + 2 * mm, label)
            canvas.setFillColor(PALE)
            canvas.roundRect(label_w, y + 1.5 * mm, bar_w, 5.5 * mm,
                             2 * mm, fill=1, stroke=0)
            canvas.setFillColor(BAR)
            value_width = bar_w * value / self.max_value
            if value_width < 4 * mm:
                canvas.rect(label_w, y + 1.5 * mm,
                            max(value_width, 0.7 * mm), 5.5 * mm,
                            fill=1, stroke=0)
            else:
                canvas.roundRect(label_w, y + 1.5 * mm, value_width,
                                 5.5 * mm, 2 * mm, fill=1, stroke=0)
            canvas.setFillColor(BLACK)
            display = f"{value:,.0f}" if self.suffix == "" else f"{value:,.2f}{self.suffix}"
            canvas.drawRightString(self.width, y + 2 * mm, display)


def pct(value, digits=1):
    return f"{100 * value:.{digits}f}%"


def ci(value):
    if not value:
        return "未估计"
    return f"[{pct(value[0])}, {pct(value[1])}]"


def score_ci(value):
    if not value:
        return "未估计"
    return f"[{value[0]:.3f}, {value[1]:.3f}]"


def build():
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    r = data["report"]
    models = r["models"]
    labels = [
        ("Debt collection", "债务催收"),
        ("Checking or savings account", "存取款账户"),
        ("Credit card", "信用卡"),
        ("Money transfer, virtual currency, or money service", "转账／虚拟货币"),
        ("Mortgage", "按揭"),
        ("Credit reporting or other personal consumer reports", "征信"),
    ]
    majority = models["majority"]
    rule = models["rules_from_stage1"]
    nb = models["naive_bayes"]
    story = []

    # Page 1: revision, task and executive summary.
    story += [Spacer(1, 8 * mm), p("金融投诉文本的六类自动分流<br/>与人工复核系统", TITLE),
              p("阶段二报告｜数据与实验设计", SUBTITLE)]
    story += [table([
        ["项目", "提交信息"],
        ["课程 / 阶段", "Python 与人工智能 / 阶段二"],
        ["团队 / 成员", "杨俊炜、赵煜凡"],
        ["Git 仓库 URL / 提交标识",
         f'<link href="{REPO}/tree/{TAG}" color="#000000">{REPO}</link><br/>{TAG}（Git 标签）'],
        ["日期", "2026 年 11 月 4 日"],
    ], [44 * mm, 126 * mm]), Spacer(1, 5 * mm)]
    story += [p("执行摘要", H1), p(
        f"本阶段将金融投诉文本分类限定为历史公开叙述中的六类产品分流。"
        f"在工作簿对应的 {r['source_rows']:,} 条记录中，只有 {r['narrative_rows']:,} 条有叙述；"
        f"六类共有 {r['six_rows']:,} 条。按标准化文本去重并先分组再按月份划分，"
        f"训练、验证、测试集分别为 {r['train_n']:,}、{r['val_n']:,}、{r['test_n']:,} 条。"
        f"测试集上朴素贝叶斯宏平均 F1 为 {nb['macro_f1']:.3f}，与多数类和规则基线同集比较。"
        "主要局限是叙述选择偏差、标签噪声和历史数据时效；下一阶段将比较更强模型及错误成本。")]
    story += [section("1", "修订问题与成功定义"),
              p("<b>决策任务：</b>只根据首次受理时可获得的英文投诉叙述，建议六类产品路由；低置信或无效输入交人工复核。Product 是消费者选择的代理标签，不是经调查裁定的事实。系统不判断投诉真伪、违法性或赔偿。"),
              p("<b>评分标准响应：</b>已收到阶段二六项评分标准，未收到阶段一逐条教师批注。本报告按六项标准组织证据：数据来源与字典、缺失与探索分析、处理与防泄漏、基线、评估及伦理复现。"),
              p("<b>成功标准：</b>沿用阶段一预设的探索性门槛：宏平均 F1 ≥ 0.65、自动处理正确率 ≥ 0.85 且覆盖率 ≥ 0.50；并报告整体准确率和各类召回率。阈值不依据五月测试结果调整。", SMALL)]
    story += [sub("阶段一到阶段二的可核对变化"),
              table([["事项", "阶段一", "阶段二"],
                     ["数据使用", "六月试运行片段", "历史快照审计、跨月去重和固定三段划分"],
                     ["方法", "多数类与固定规则", "增加训练集拟合的词袋朴素贝叶斯"],
                     ["证据", "单月原型检查", "五月独立测试、类别召回率与 95% 区间"]],
                    [34 * mm, 53 * mm, 83 * mm])]
    story += [PageBreak()]

    # Page 2: source, unit, dictionary and data quality.
    story += [section("2", "数据集文档与来源（15 分）"),
              p("<b>来源与收集过程：</b>赵煜凡负责数据采集并向小组提供 complaints.csv.zip 与 complaints.xlsx 本地历史副本；本次由压缩 CSV 顺序读取前 1,048,575 条记录（Excel 最大数据行数），核对两份文件的表头及前两行，并计算压缩包 SHA-256。未逐行核对整个工作簿，也不推断完整 CFPB 数据库。原始下载时间、下载筛选条件和当时的许可凭证未随文件提供，故本报告只确认本地副本；CFPB 当前公开页面称其发布的数据可自由使用与分析。[1]"),
              p("<b>总体与观察单位：</b>本地前段记录的收件日期范围为 2014-07-15 至 2026-07-05，共 16 列；一行为一条公开投诉记录，Complaint ID 是记录标识，但存在缺失。模型输入仅为 Consumer complaint narrative；Product 为六类代理标签。公司回复等受理后字段及 Issue、Sub-issue 等相关结构化字段不进入推理。", SMALL),
              sub("表 1　核心字段字典与用途")]
    story += [table([
        ["字段", "类型／含义", "用途"],
        ["Complaint ID", "整数；投诉记录标识", "去重排序与完整性检查，不作特征"],
        ["Date received", "日期；CFPB 收件日", "按首次出现日期进行时间划分"],
        ["Product", "类别；消费者选择的产品", "六类监督标签，含噪声"],
        ["Consumer complaint narrative", "自由文本；公开叙述", "唯一预测特征；空值不入文本样本"],
        ["Issue / Sub-issue", "类别；消费者选择的问题", "仅数据字典，不用于推理"],
        ["Company response to consumer", "类别；公司处理结果", "受理后信息，禁止用作特征"],
        ["State / ZIP code", "地理字段，可能为空", "仅偏差审计，不用于推理"],
    ], [49 * mm, 59 * mm, 62 * mm])]
    story += [Spacer(1, 4 * mm), sub("样本质量与保留规则"),
              p(f"16 列中叙述缺失 {r['source_rows'] - r['narrative_rows']:,} 条（{pct(1-r['narrative_rows']/r['source_rows'],2)}）；"
                f"六类可用叙述 {r['six_rows']:,} 条。标准化文本完全重复的额外行 {r['dedup_extra_rows']:,} 条，"
                f"跨类别冲突组 {r['conflict_groups']} 个；这些组不进入建模。"
                f"其中 {data['source']['selected_over_20000_chars']} 条超过阶段一规则器 20,000 字符的输入限额。", SMALL),
              p(f"六类文本中有 {data['source']['selected_redaction_marker_rows']:,} 条含脱敏占位符，仍可能残留可识别信息；报告、日志及公开仓库只保存聚合统计与人工编写测试句，不保存原文。", SMALL)]
    missing = r["field_missing"]
    story += [sub("关键字段缺失速览"),
              table([["字段", "缺失条数", "对本研究的影响"],
                     ["Consumer complaint narrative", f"{missing['Consumer complaint narrative']:,}", "决定文本样本的严重选择偏差"],
                     ["Complaint ID", f"{missing['Complaint ID']:,}", "全体记录不宜仅以 ID 去重"],
                     ["Product", f"{missing['Product']:,}", "不能映射六类标签"],
                     ["Issue / State", f"{missing['Issue']:,} / {missing['State']:,}", "只做审计，不作模型输入"]],
                    [62 * mm, 27 * mm, 81 * mm]),
              Spacer(1, 3 * mm),
              p(f"输入快照的 SHA-256：{data['source']['sha256']}。校验值与数据卡片一致才运行正式实验。", TINY)]
    story += [PageBreak()]

    # Page 3: purposeful EDA and design change.
    story += [section("3", "数据质量与探索性分析（20 分）"),
              sub("图 1　六类记录中含叙述的比例（%）")]
    availability = [(short, 100 * r["class_narratives"][label] /
                     r["class_total"][label]) for label, short in labels]
    story += [Bars(availability, max_value=25),
              p("图 1 来源：本地前段数据的 Product 与叙述非空交叉统计；百分比为各产品内部覆盖率。征信占全部记录约 90.22%，但其叙述覆盖率只有约 0.10%，与其他类别差距巨大。", SMALL),
              sub("图 2　2026 年 3–5 月六类原始叙述量（条）"),
              Bars([(f"{month} 月", r["month_raw_narratives"][f"2026-{month:02d}"])
                    for month in (3, 4, 5)],
                   row_height=11 * mm, max_value=7000, suffix=""),
              p("图 2 为去重前记录量；四月异常增高，不能把随机抽取记录视为独立、平稳的未来样本。具体成因不能仅凭这份副本确定。", SMALL),
              sub("观察如何改变设计"),
              p("<b>限定推断总体：</b>仅评价有公开叙述的六类投诉；不把结果推广至全部投诉，也不据投诉量推断产品风险。[1]"),
              p(f"征信为全部记录的 {pct(r['class_total'][labels[-1][0]]/r['source_rows'],2)}，却仅占所有非空叙述的 {pct(r['class_narratives'][labels[-1][0]]/r['narrative_rows'],2)}；"
                "这不是自然发生的类别平衡，而是公开叙述的选择机制所致。", SMALL),
              p("<b>先去重再按时间划分：</b>跨月份存在完全相同的标准化文本。保留每组最早记录，冲突标签组剔除，使同一文本不跨训练、验证和测试；五月独立测试不用于参数选择。"),
              p("<b>类别分布随时间变化：</b>去重后债务催收占训练、验证、测试集的 40.5%、31.0%、28.2%，信用卡则从 18.9% 升至 22.3%、24.3%。因此随机切分会掩盖未来月份的变化；评估仍须看宏平均 F1 和各类召回。", SMALL)]
    story += [PageBreak()]

    # Page 4: reproducible pipeline and fixed split.
    story += [section("4", "处理与防泄漏（20 分）"),
              p("压缩 CSV 顺序读取前 1,048,575 条；校验 16 列及日期、产品、叙述字段；筛选六类且有非空文本的行。以 casefold 与空白归一化后的文本为键，跨全部月份分组：多标签冲突组剔除，其余选最早 Date received（再以 Complaint ID 打破并列）。只输出聚合统计，不导出原文或逐行文本哈希。"),
              sub("图 3　固定流水线"),
              table([["来源", "筛选与分组", "时间划分", "训练与评价"],
                     ["CSV ZIP 前段<br/>校验列与哈希", "六类非空叙述<br/>归一化文本去重", "≤3 月训练<br/>4 月验证<br/>5 月测试", "训练集拟合词表<br/>验证集选 α<br/>测试集只评一次"]],
                    [38 * mm, 44 * mm, 42 * mm, 46 * mm]),
              p("图 3　同一标准化文本先归为单组，再按组的首次日期分配；六月已在阶段一试运行查看，本阶段排除。", SMALL),
              sub("表 2　冻结划分及每类样本量")]
    split_rows = [["类别", "训练 ≤3 月", "验证 4 月", "测试 5 月"]]
    for label, short in labels:
        split_rows.append([short, r["train_classes"][label],
                           r["val_classes"][label], r["test_classes"][label]])
    split_rows.append(["合计", r["train_n"], r["val_n"], r["test_n"]])
    story += [table(split_rows, [62 * mm, 36 * mm, 36 * mm, 36 * mm]),
              p(f"共排除阶段一已查看的六月样本 {r['june_excluded_n']:,} 条。"
                "分割以固定日期界限定义，不使用测试标签调阈值。文本词袋、词表与条件概率只在训练集拟合；验证集只用于选 α。", SMALL),
              sub("可复现性与验证"),
              p("脚本固定日期边界、词元规则、候选 α={0.1,1,5} 与自助重采样种子 42；输入以 SHA-256 标识。13 项自动测试覆盖缺列、空叙述、跨月重复、冲突标签、训练词表隔离、类别指标及边界条件。公开仓库含合成小样本供无原始数据时运行；真实数值需用户提供的同一快照。", SMALL),
              table([["验证项", "运行结果"],
                     ["跨集合标准化文本哈希交集", "0"],
                     ["词表仅在训练集拟合", f"{r['train_n']:,} 条；{data['model']['vocabulary_size']:,} 个词"],
                     ["五月测试是否用于选择 α", "否；只在四月验证集选择"],
                     ["运行环境与耗时", f"Python {data['environment']['python']} 标准库；全流程 {data['runtime_seconds']['total']:.1f} 秒"]],
                    [79 * mm, 91 * mm])]
    story += [PageBreak()]

    # Page 5: baselines and evaluation.
    story += [section("5", "基线实现（15 分）与评估设计（20 分）"),
              p("比较三条路线：训练集多数类（不看文本）；阶段一固定关键词规则（可转人工）；训练集拟合词袋的多项式朴素贝叶斯（在四月验证集选平滑 α）。三者在同一五月测试集评估。主指标为六类宏平均 F1，使少数类与多数类等权；准确率反映总体错分，规则还报告自动覆盖率及自动处理正确率。"),
              sub("表 3　2026 年 5 月独立测试集结果")]
    model_rows = [["方法", "准确率", "宏平均 F1", "宏 F1 95% 区间"]]
    for key, display in [("majority", "训练多数类"),
                         ("rules_from_stage1", "固定规则"),
                         ("naive_bayes", "词袋朴素贝叶斯")]:
        m = models[key]
        model_rows.append([display, pct(m["accuracy"]),
                           f"{m['macro_f1']:.3f}",
                           score_ci(m.get("macro_f1_ci_95"))])
    story += [table(model_rows, [43 * mm, 27 * mm, 30 * mm, 70 * mm]),
              p(f"区间为固定五月测试行的 500 次自助重采样分位数；朴素贝叶斯准确率 Wilson 95% 区间为 {ci(nb.get('accuracy_ci_95'))}。该区间未覆盖时间漂移等系统误差。模型选择只看四月验证集，不再修改五月测试集。", SMALL),
              p(f"固定规则自动覆盖率为 {pct(rule['coverage'])}，仅对自动处理的样本计算正确率为 {pct(rule['accuracy_when_auto'])}；表中整体准确率将转人工计为未正确分类。", SMALL),
              sub("表 4　五月测试集各类召回率")]
    recall_rows = [["类别", "训练多数类", "固定规则", "朴素贝叶斯"]]
    for label, short in labels:
        recall_rows.append([short,
                            pct(majority["per_class_recall"][label]),
                            pct(rule["per_class_recall"][label]),
                            pct(nb["per_class_recall"][label])])
    story += [table(recall_rows, [62 * mm, 36 * mm, 36 * mm, 36 * mm]),
              p("<b>错误类型：</b>朴素贝叶斯只识别出 249 条转账类中的 103 条（召回率 41.4%）；有 123 条被错分为存取款账户，是该类最大的误路由。单靠整体准确率无法发现这一风险。", SMALL),
              p("<b>门槛结论：</b>朴素贝叶斯宏 F1 达到阶段一的 0.65 门槛，但全覆盖自动正确率仅 74.2%；规则覆盖率 58.6%、自动正确率 69.1%。两者均未达到 85% 的自动正确率目标，暂不能作为无人复核的自动分流。阶段三应在验证集选择拒答阈值，测试集报告覆盖率与错误率权衡。", SMALL),
              p(f"验证集选出的朴素贝叶斯平滑参数 α = {escape(str(r.get('chosen_alpha')))}。"
                "本阶段结果属于离线历史样本，不代表真实部署表现；下一阶段需比较 TF-IDF 线性模型并做近重复及时间漂移检查。", SMALL)]
    tuned_rows = [["验证集 α", "准确率", "宏平均 F1"]]
    for item in data["validation_alpha_scores"]:
        tuned_rows.append([str(item["alpha"]), pct(item["accuracy"]),
                           f"{item['macro_f1']:.3f}"])
    story += [sub("表 5　四月验证集的 α 选择记录"),
              table(tuned_rows, [57 * mm, 56 * mm, 57 * mm]),
              p("α 先按宏平均 F1 最大选择；若相同，再比较准确率与较小 α。五月测试集只用于最终描述，未参与本次选择。", SMALL)]
    story += [PageBreak()]

    # Page 6: risks, next actions and references.
    story += [section("6", "伦理、写作与可复现性（10 分）"),
              sub("6.1 数据与伦理风险"),
              p("<b>选择与测量偏差：</b>叙述公开与否高度依赖产品类别；Product 是自报标签，不等于专家验证。CFPB 说明其数据库不是消费者经历的统计代表样本。[1][2]"),
              p("<b>时间适用性：</b>CFPB 于 2026-08-14 宣布停止酌情发布投诉叙述。[3] 本研究只处理用户提供的历史快照，不能假定未来可持续获得同结构的新叙述。四月样本激增也需在阶段三做漂移分析。"),
              p("<b>隐私与错误后果：</b>公开叙述的脱敏占位符不保证完全无个人信息；不发布原文。错分可能延误人工处理，系统应显示建议与原因，支持人工改派和审计，不用于判断事实、违法或赔偿。"),
              sub("6.2 阶段三至五的可验收计划"),
              table([["阶段／拟负责人", "依赖与交付完成标准"],
                     ["阶段三<br/>杨俊炜：建模评估<br/>赵煜凡：数据采集", "以阶段二冻结切分为依赖；比较 NB、TF-IDF 线性模型与规则，给出同集宏 F1、各类召回、错误类型和运行成本。"],
                     ["阶段四<br/>杨俊炜：集成测试<br/>赵煜凡：数据采集", "在选定模型上实现本地 CLI：输入文本、类别或转人工输出；端到端测试覆盖空值、过长文本和异常路径。"],
                     ["阶段五<br/>杨俊炜：审计修复<br/>赵煜凡：数据采集", "以阶段四系统为对象，验证集选拒答阈值；完成扰动、类别与时间漂移审计，形成回滚规则和整合报告。"]],
                    [45 * mm, 125 * mm]),
              Spacer(1, 2 * mm),
              p("每阶段保存输入哈希、运行环境、测试日志和独立 Git 标签；发布后的标签不移动。", SMALL),
              sub("6.3 明确分工与 AI 使用声明"),
              table([["成员", "阶段二负责事项", "对应可核对产物"],
                     ["赵煜凡", "数据采集；向小组提供 CFPB 投诉本地历史快照。", "complaints.xlsx、complaints.csv.zip（原始文件不公开）"],
                     ["杨俊炜", "研究问题修订；数据字典与质量分析；清洗、去重和防泄漏划分；基线、评估与测试；图表、报告及 Git 仓库整理。", "DATA_CARD.md、stage2.py、test_stage2.py、results/、本报告与 README.md"]],
                    [21 * mm, 81 * mm, 68 * mm]),
              Spacer(1, 2 * mm),
              p("上述为团队告知的责任分工。阶段二代码、数据分析和报告草稿由 OpenAI Codex 协助生成；成员应复核结果、理解署名工作，并按课程政策披露 AI 辅助范围。", SMALL),
              sub("参考资料"),
              p("[1] CFPB, Consumer Complaint Database, 2026. <link href='https://www.consumerfinance.gov/data-research/consumer-complaints/' color='#000000'>consumerfinance.gov/data-research/consumer-complaints/</link>。", TINY),
              p("[2] CFPB, How we share complaint data, 2026. <link href='https://www.consumerfinance.gov/complaint/data-use/' color='#000000'>consumerfinance.gov/complaint/data-use/</link>。", TINY),
              p("[3] CFPB, The CFPB to Cease Discretionary Publication of Complaint Narratives and Visualizations, 2026-08-14. <link href='https://www.consumerfinance.gov/about-us/newsroom/the-cfpb-to-cease-discretionary-publication-of-complaint-narratives-and-visualizations/' color='#000000'>CFPB 公告</link>。", TINY),
              p("本地资料：用户提供的 complaints.xlsx、complaints.csv.zip 与作业指导.pdf。数据字典和完整运行方式见仓库 DATA_CARD.md 与 README.md；原始文件不随仓库发布。", TINY)]

    Report(OUT).build(story)
    return OUT


if __name__ == "__main__":
    print(build())
