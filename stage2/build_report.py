"""Build the phase-two PDF from the project's aggregate experiment results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, HRFlowable, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "YangZhao_phase2_report.pdf"
REPO = "https://github.com/cwiapp/financial-complaint-routing"
TAG = "phase-2-submission"
TITLE = "六类金融投诉的文本分流"
CFPB = "https://www.consumerfinance.gov"
WIDTH = A4[0] - 40 * mm
BLACK = colors.black
PALE = colors.HexColor("#F2F2F2")
LINE = colors.HexColor("#BEBEBE")
MID = colors.HexColor("#777777")
DARK = colors.HexColor("#363636")

PRODUCTS = (
    ("Debt collection", "债务催收", "催收"),
    ("Checking or savings account", "存取款账户", "账户"),
    ("Credit card", "信用卡", "信用卡"),
    ("Money transfer, virtual currency, or money service", "转账／虚拟货币", "转账"),
    ("Mortgage", "按揭", "按揭"),
    ("Credit reporting or other personal consumer reports", "征信", "征信"),
)
TRANSFER, ACCOUNT = PRODUCTS[3][0], PRODUCTS[1][0]

for name, file in (("Report", "msyh.ttc"), ("Report-Bold", "msyhbd.ttc")):
    pdfmetrics.registerFont(TTFont(name, str(Path("C:/Windows/Fonts") / file), subfontIndex=0))
pdfmetrics.registerFontFamily("Report", normal="Report", bold="Report-Bold",
                              italic="Report", boldItalic="Report-Bold")


def style(name, size, after=0, bold=False, right_indent=0):
    return ParagraphStyle(name, fontName="Report-Bold" if bold else "Report",
                          fontSize=size, leading=size * 1.15, textColor=BLACK,
                          wordWrap="CJK", spaceAfter=after, rightIndent=right_indent)


# Allow CJK end punctuation to hang within the text frame, inside the page margin.
BODY = style("body", 11, after=8, right_indent=11)
NOTE = style("note", 10, after=5, right_indent=10)
CELL = style("cell", 10)
HEAD = style("head", 10, bold=True)
CAPTION = style("caption", 10, after=5, bold=True)
HERO = style("hero", 12, after=8, bold=True)
DECK = style("deck", 11, after=10)
H2 = style("h2", 12, after=6, bold=True)
BIG = style("big", 12, after=3, bold=True)
CODE = style("code", 10)


class Report(BaseDocTemplate):
    def __init__(self, output):
        super().__init__(str(output), pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                         topMargin=30*mm, bottomMargin=29*mm, title=TITLE,
                         author="Yang Junwei and Zhao Yufan", invariant=1)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="report", frames=frame, onPage=self.decorate))

    def decorate(self, canvas, _doc):
        canvas.saveState()
        width, height = A4
        left, right = 20*mm, width - 20*mm
        draw_text(canvas, left, height - 24.5*mm, "Python 与人工智能课程", bold=True)
        draw_text(canvas, right, height - 24.5*mm, "阶段二　数据与实验设计", right=True)
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(left, height - 27*mm, right, height - 27*mm)
        canvas.line(left, 27*mm, right, 27*mm)
        draw_text(canvas, left, 22*mm, "金融投诉文本分流　杨俊炜、赵煜凡")
        draw_text(canvas, right, 22*mm, f"第 {canvas.getPageNumber()} 页", right=True)
        canvas.restoreState()


def p(value, paragraph_style=BODY):
    return Paragraph(str(value), paragraph_style)


def draw_text(canvas, x, y, value, *, bold=False, right=False, center=False):
    canvas.setFont("Report-Bold" if bold else "Report", 10)
    canvas.setFillColor(BLACK)
    draw = canvas.drawRightString if right else canvas.drawCentredString if center else canvas.drawString
    draw(x, y, str(value))


def table(rows, widths, *, header=True, spacing=5):
    cells = [[value if isinstance(value, Flowable) else p(value, HEAD if i == 0 and header else CELL)
              for value in row] for i, row in enumerate(rows)]
    t = Table(cells, colWidths=[WIDTH * w for w in widths], hAlign="LEFT",
              repeatRows=1 if header else 0)
    rules = [("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 7),
             ("RIGHTPADDING", (0, 0), (-1, -1), 11),
             ("TOPPADDING", (0, 0), (-1, -1), spacing),
             ("BOTTOMPADDING", (0, 0), (-1, -1), spacing),
             ("LINEBELOW", (0, 0), (-1, -1), 0.35, LINE)]
    if header:
        rules += [("BACKGROUND", (0, 0), (-1, 0), PALE),
                  ("LINEABOVE", (0, 0), (-1, 0), 0.8, DARK)]
    t.setStyle(TableStyle(rules))
    return t


def panels(items):
    cells = [[p(value, BIG), p(label, HEAD), p(detail, NOTE)] for value, label, detail in items]
    panels_table = Table([[c for c in cells]], colWidths=[WIDTH / len(cells)] * len(cells))
    panels_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("LINEBEFORE", (1, 0), (-1, -1), 1, colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return panels_table


def heading(title, deck):
    return [p(title, HERO), p(deck, DECK)]


def section(value):
    return p(value, H2)


def caption(value):
    return p(value, CAPTION)


def gap(points=7):
    return Spacer(1, points)


def rule():
    return HRFlowable(width="100%", thickness=0.6, color=LINE, spaceBefore=1, spaceAfter=8)


def pct(value, digits=1):
    return "—" if value is None else f"{value:.{digits}%}"


def score_ci(values):
    return f"[{values[0]:.3f}, {values[1]:.3f}]"


def pct_ci(values):
    return f"[{pct(values[0])}, {pct(values[1])}]"


def link(url, label=None):
    return f'<link href="{escape(url)}" color="#000000">{escape(label or url)}</link>'


class CoveragePlot(Flowable):
    """Within-product narrative availability, with denominators on the right."""

    def __init__(self, report):
        super().__init__()
        self.report = report
        self.width, self.height = WIDTH, 143

    def draw(self):
        c = self.canv
        start, end = 88, WIDTH - 111
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        for tick in range(0, 26, 5):
            x = start + (end - start) * tick / 25
            c.line(x, 9, x, 121)
            draw_text(c, x, 129, f"{tick}%", center=True)
        draw_text(c, WIDTH, 129, "含叙述数 / 总数", right=True)
        for i, (key, label, _) in enumerate(PRODUCTS):
            y = 108 - 19 * i
            n, total = self.report["class_narratives"][key], self.report["class_total"][key]
            ratio = n / total
            x = start + (end - start) * ratio * 4
            draw_text(c, 0, y - 3, label)
            c.setFillColor(DARK)
            c.rect(start, y - 3.5, x - start, 7, fill=1, stroke=0)
            c.circle(x, y, 1.8, fill=1, stroke=0)
            draw_text(c, x + 5, y - 3, pct(ratio, 2))
            draw_text(c, WIDTH, y - 3, f"{n:,} / {total:,}", right=True)


class MixPlot(Flowable):
    """Class shares on the same scale across chronological partitions."""

    def __init__(self, splits):
        super().__init__()
        self.splits = splits
        self.width, self.height = WIDTH, 144

    def draw(self):
        c = self.canv
        label_width = 89
        col = (WIDTH - label_width) / 3
        partitions = (("train", "训练"), ("validation", "四月验证"), ("test", "五月测试"))
        for j, (key, display) in enumerate(partitions):
            start = label_width + col * j
            split = self.splits[key]
            draw_text(c, start, 128, f"{display}  n={split['n']:,}", bold=True)
            for i, (product, label, _) in enumerate(PRODUCTS):
                y = 108 - i * 19
                if j == 0:
                    draw_text(c, 0, y - 3, label)
                ratio = split["class_counts"][product] / split["n"]
                c.setFillColor(PALE)
                c.rect(start, y - 3.5, col - 39, 7, fill=1, stroke=0)
                c.setFillColor((MID, MID, DARK)[j])
                c.rect(start, y - 3.5, (col - 39) * ratio * 2, 7, fill=1, stroke=0)
                draw_text(c, start + col - 5, y - 3, pct(ratio), right=True)


class LengthPlot(Flowable):
    """Counts by nonuniform character-length interval."""

    def __init__(self, bins):
        super().__init__()
        self.bins = bins
        self.width, self.height = WIDTH, 84

    def draw(self):
        c = self.canv
        max_count = max(self.bins.values())
        intervals = (("<200", "0-199"), ("200-499", "200-499"), ("500-999", "500-999"),
                     ("1000-1999", "1,000-1,999"), ("2000-4999", "2,000-4,999"), (">=5000", "5,000 及以上"))
        col = WIDTH / len(intervals)
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        c.line(0, 18, WIDTH, 18)
        for i, (key, label) in enumerate(intervals):
            x = (i + 0.5) * col
            count = self.bins[key]
            height = count / max_count * 48
            c.setFillColor(DARK if count == max_count else MID)
            c.rect(x - 16, 18, 32, height, fill=1, stroke=0)
            draw_text(c, x, 23 + height, f"{count:,}", center=True)
            draw_text(c, x, 5, label, center=True)


class ConfusionPlot(Flowable):
    """Absolute counts and row shares for the six-class test confusion matrix."""

    def __init__(self, matrix):
        super().__init__()
        self.matrix = matrix
        self.width, self.height = WIDTH, 156

    def draw(self):
        c = self.canv
        x0, col, h = 112, 61, 19
        draw_text(c, 0, 139, "实际类别", bold=True)
        draw_text(c, x0 - 8, 139, "样本数", bold=True, right=True)
        for j, (_, _, short) in enumerate(PRODUCTS):
            draw_text(c, x0 + col * (j + .5), 139, short, bold=True, center=True)
        for i, (actual, label, _) in enumerate(PRODUCTS):
            y = 119 - i * h
            row = self.matrix[actual]
            n = sum(row.values())
            draw_text(c, 0, y - 2, label)
            draw_text(c, x0 - 8, y - 2, f"{n:,}", right=True)
            for j, (predicted, _, _) in enumerate(PRODUCTS):
                x = x0 + j * col
                value = row[predicted]
                strength = 1 - 0.30 * value / n
                c.setFillColor(colors.Color(strength, strength, strength))
                c.setStrokeColor(LINE)
                c.setLineWidth(0.45)
                c.rect(x, y - 8, col, h, fill=1, stroke=1)
                if (actual, predicted) == (TRANSFER, ACCOUNT):
                    c.setStrokeColor(BLACK)
                    c.setLineWidth(1.5)
                    c.rect(x + .8, y - 7.2, col - 1.6, h - 1.6, fill=0, stroke=1)
                draw_text(c, x + col / 2, y - 2, value,
                          bold=i == j or (actual, predicted) == (TRANSFER, ACCOUNT), center=True)


def share(splits, name, product):
    return splits[name]["class_counts"][product] / splits[name]["n"]


def build(data, output):
    source, r, splits = data["source"], data["report"], data["splits"]
    dedup, check, experiment = data["deduplication"], data["checks"], data["test"]
    majority, rules, nb = (experiment[name] for name in ("majority", "rules_from_stage1", "naive_bayes"))
    paired = r["paired_delta_nb_minus_rules"]
    delta, delta_ci = paired["delta_macro_f1"], paired["ci_95_percentile"]
    n = nb["n"]
    confusion = nb["confusion_matrix"]
    transferred = confusion[TRANSFER]
    transfer_total = sum(transferred.values())
    reviews = sum(row.get("review", 0) for row in rules["confusion_matrix"].values())
    rule_errors = n - reviews - rules["correct"]
    nb_errors = n - nb["correct"]
    review_reasons = r["rule_review_reason_counts"]
    split_total = sum(v["n"] for v in splits.values())
    target_text = source["selected_six_narratives"] - source["selected_invalid_received_dates"]
    accepted = split_total + r["june_excluded_n"]
    review_ci = rules["accuracy_when_auto_95_wilson"]
    story = [
        section("1　标题和项目信息"),
        p(TITLE, HERO),
        p("历史样本上的可学性、错分成本与人工复核", DECK),
        p("团队成员　杨俊炜、赵煜凡　｜　报告日期　2026 年 11 月 8 日", NOTE),
        p("课程阶段　阶段 2　数据与实验设计", NOTE),
        p(f"仓库 URL　{link(REPO)}", NOTE),
        p(f"提交标签　{link(REPO + '/tree/' + TAG, TAG)}", NOTE),
        gap(5), rule(),
        section("2　执行摘要"),
        p(f"本阶段检验投诉叙述中的英文词元能否支持六类产品分流。"
          f"从 {r['source_rows']:,} 条本地记录筛出六类非空叙述，按首次收件日期去重并划分训练、验证和测试集。"
          f"在 {n:,} 条五月投诉上，朴素贝叶斯宏平均 F1 为 {nb['macro_f1']:.3f}，比固定规则高 {delta:.3f}，"
          f"但自动处理正确率为 {pct(nb['accuracy_when_auto'])}，低于阶段一的 85% 门槛。"
          "公开叙述的覆盖率随产品变化，五月结果只用于回顾性分析。下一阶段将用四月验证集选择人工复核门槛，并用新封存样本核验。"),
        gap(2),
        panels([
            (f"{nb['macro_f1']:.3f}", "宏平均 F1", "朴素贝叶斯，五月历史测试"),
            (f"+{delta:.3f}", "配对宏 F1 差值", f"95% 区间 {score_ci(delta_ci)}"),
            (pct(nb["accuracy_when_auto"]), "自动处理正确率", "全覆盖，低于 85% 门槛"),
        ]),
        gap(15), section("3　修订后的项目背景"),
        p("使用者是受理环节的人工审核员。输入为一条投诉叙述，输出为六个产品队列之一，或交人工复核。"
          "监督标签取自投诉记录的 Product 字段，反映消费者当时的产品选择。实验只使用叙述，审核员保留改派权。"),
        p("阶段一使用固定词表试跑六月数据。阶段二冻结历史时间窗，加入训练多数类和朴素贝叶斯，并把转人工纳入统计。"
          "表 1 列出阶段一确定的验收门槛。本阶段用这些门槛判断能否减少人工分流。修订记录见第 10 节。"),
        caption("表 1　阶段一预先设定的三项门槛"),
        table([["指标", "门槛", "为何需要"],
               ["六类宏平均 F1", "≥ 0.65", "六类等权，关注少数队列能否被识别。"],
               ["自动处理正确率", "≥ 85%", "减少误路由引发的重复转派和受理延迟。"],
               ["自动覆盖率", "≥ 50%", "同时计量转人工负荷，防止大量弃权抬高正确率。"]],
              [.27, .17, .56]),
        PageBreak(),
    ]

    story += [section("4　特定阶段的技术工作")]
    story += heading("4.1　数据来源、样本与字段",
                     "以 CFPB 公开数据库的字段定义作对照，分析范围限于本地 CSV 前段。")
    story += [
        p("赵煜凡负责收集并提供 complaints.xlsx 和 complaints.csv.zip 两份本地文件。"
          "研究从 ZIP 中按文件顺序读取与工作簿容量对应的 CSV 前段，核对两份文件的表头及前两行。"
          "这个前段按文件位置截取，未进行随机抽样。"
          "CFPB 运营消费者投诉数据库，公开页面说明其发布的数据可供使用和分析 [1]。"
          "本地文件的原始下载日期、筛选条件和当时许可凭证尚无记录，因此保留 ZIP 校验值和实际读取边界。"
          "表 2 记录每一步保留的样本数。"),
        caption("表 2　样本筛选台账"),
        table([
            ["处理范围", "条数", "说明"],
            ["CSV 前段", f"{r['source_rows']:,}",
             f"{len(source['columns'])} 列，收件日期 {source['received_min']} 至 {source['received_max']}。"],
            ["叙述非空", f"{r['narrative_rows']:,}",
             f"占读取记录的 {pct(source['narrative_rate'], 2)}，其余叙述为空。"],
            ["属于六个目标产品且日期有效", f"{target_text:,}",
             f"非目标产品叙述 {r['narrative_rows'] - source['selected_six_narratives']:,} 条。六类日期无效 {source['selected_invalid_received_dates']:,} 条。"],
            ["按首次出现去重后", f"{accepted:,}", f"清洗减少 {target_text - accepted:,} 条，规则见第 4.2 节。"],
            ["进入训练、验证和测试", f"{split_total:,}",
             f"另有 {r['june_excluded_n']:,} 条处于阶段一已查看的六月，排除。"],
        ], [.34, .17, .49], spacing=4),
        gap(10), p("表 3 列出核心字段的缺失数和使用范围。", NOTE),
        caption("表 3　核心字段字典"),
        table([
            ["CSV 字段", "含义及数据类型", "缺失", "实验角色"],
            ["Consumer complaint narrative", "公开投诉叙述，文本", f"{r['field_missing']['Consumer complaint narrative']:,}", "唯一模型输入"],
            ["Product", "消费者选择的产品，类别", f"{r['field_missing']['Product']:,}", "六类监督标签"],
            ["Date received", "CFPB 收件日期，日期", f"{r['field_missing']['Date received']:,}", "去重排序、时间切分"],
            ["Complaint ID", "投诉编号，标识符", f"{r['field_missing']['Complaint ID']:,}", "同日同标签时排序"],
            ["Issue", "消费者选择的问题，类别", f"{r['field_missing']['Issue']:,}", "排除，避免依赖相关标注"],
            ["Company response to consumer", "企业处理结果，类别", f"{r['field_missing']['Company response to consumer']:,}", "排除，发生于受理之后"],
            ["State", "州，类别", f"{r['field_missing']['State']:,}", "仅供总体缺失审计"],
        ], [.30, .27, .15, .28], spacing=4),
        gap(6),
        p("观察单位为一条投诉记录。编号缺失时仍按叙述内容识别重复。"
          "主要证据覆盖快照前段有公开叙述的六类投诉。未公开叙述、其他产品和未进入 CFPB 公开数据库的投诉没有评估。"
          f"其余字段的定义和缺失统计见 {link(REPO + '/blob/' + TAG + '/stage2/DATA_CARD.md', '仓库数据卡')}。", NOTE),
        PageBreak(),
    ]

    credit_key = PRODUCTS[-1][0]
    credit_share = r["class_total"][credit_key] / r["source_rows"]
    credit_text_share = r["class_narratives"][credit_key] / source["selected_six_narratives"]
    length_stats = r["six_narrative_length_chars"]
    exploration = [section("5　证据与分析")] + heading(
        "5.1　数据覆盖、类别变化与文本长度",
        "同一快照中，叙述可见性随产品变化，产品构成也随月份变化。")
    exploration += [
        caption("图 2　各产品中公开叙述的可得率"),
        CoveragePlot(r), gap(3),
        p(f"图 2 的分母是对应产品在 CSV 前段的全部记录。征信占前段全部记录的 {pct(credit_share, 2)}，"
          f"却只占六类非空叙述的 {pct(credit_text_share, 2)}。因此模型成绩适用于有叙述的样本，"
          "空文本须进入人工队列。", NOTE),
        gap(8), caption("图 3　去重后各时间段的类别构成"),
        MixPlot(splits), gap(2),
        p(f"图 3 每列以该时间段的记录数为分母，条长的共同上限为 50%。债务催收占比从训练集"
          f"的 {pct(share(splits, 'train', PRODUCTS[0][0]))} 降至五月的 {pct(share(splits, 'test', PRODUCTS[0][0]))}，"
          f"信用卡从 {pct(share(splits, 'train', PRODUCTS[2][0]))} 升至 {pct(share(splits, 'test', PRODUCTS[2][0]))}。"
          "部署会遇到月份变化，因此用时间切分衡量这种变化下的表现，并保留逐类指标。", NOTE),
        gap(9), caption(f"图 4　去重前六类叙述的长度分组（横轴为字符数，n = {length_stats['n']:,}）"),
        LengthPlot(length_stats["bins"]), gap(2),
        p(f"图 4 使用归一化后的文本。中位数为 {length_stats['median']:,} 字符，第 95 百分位为 {length_stats['p95']:,}。"
          f"其中 {source['selected_redaction_marker_rows']:,} 条含遮盖标记，{source['selected_over_20000_chars']:,} 条超过旧规则的 20,000 字符限制。"
          f"朴素贝叶斯去除 x 遮盖词，每条最多保留 5,000 个英文词元。五月有 {data['model']['test_docs_over_token_cap']} 条超过这一上限。"
          "脚本未单独筛除非英语叙述。Product 由投诉者选择，混合产品叙述可能造成标注差异。", NOTE),
        PageBreak(),
    ]

    story += heading("4.2　数据清洗、切分与建模",
                     "同一标准化文本只能分到一个集合，词表和参数选择按时间隔离。")
    story += [
        caption("图 1　从历史 CSV 到评估结果"),
        table([
            ["01 读入与检查", "02 到件去重", "03 固定时间窗", "04 拟合与评价"],
            ["校验 ZIP 哈希、字段和日期。筛选六类非空叙述。", "大小写及空白归一化。按最早收件日决定保留与排除。",
             "截至三月训练。四月验证。五月测试。", "训练集拟合词袋。四月选平滑系数。汇总五月结果。"],
        ], [.25, .25, .25, .25]),
        gap(9), section("重复与冲突如何处理"),
        p("对叙述按大小写与空白归一化后计算哈希。同一个哈希以最早收件日为准。"
          "同日标签一致时保留一条，最早同日出现多个产品标签时隔离该组。后续日期出现的重复文本不会进入其他集合，"
          "其标签不会追溯改变早期记录。流程见图 1。"),
        p(f"六类候选中有 {dedup['duplicate_extra_rows']:,} 条超出每组一条的重复记录。"
          f"最早同日标签冲突而排除 {dedup['conflicting_label_groups_excluded']:,} 组。"
          f"有 {dedup['later_label_disagreement_rows_dropped']} 条较晚记录的标签不同，修订后保留了原来被删除的四月首条记录。"
          f"三个集合之间的标准化文本哈希重叠为 {check['hash_overlap_across_splits']}。"
          "近似改写及同一投诉者的多次投诉尚未识别。表 4 列出三个集合各自的日期、样本数与用途。"),
        caption("表 4　时间窗、观察范围与用途"),
        table([["集合", "实际日期范围", "条数", "用途"]] + [
            [display, f"{splits[key]['date_min']} 至 {splits[key]['date_max']}", f"{splits[key]['n']:,}", role]
            for key, display, role in (
                ("train", "训练", "拟合多数类与词袋模型"),
                ("validation", "验证", "以宏平均 F1 选择 α"),
                ("test", "历史测试", "同批记录比较三个基线"),
            )
        ], [.14, .40, .12, .34]),
        gap(10), section("特征、边界与运行验证"),
        p(f"词袋使用英文词元计数，文档频次至少为 2。词表仅在 {check['vocabulary_fit_rows']:,} 条训练记录上拟合，"
          f"得到 {data['model']['vocabulary_size']:,} 个词元。四月和五月仅用训练词表转换。"
          "五月数据没有参与 α 的选择。旧规则词表沿用阶段一版本。"),
        p("五月已用于前一版报告，因此本次采用相同月份作回顾性比较。"
          "下一阶段的模型和复核门槛仍用四月验证集探索，最终确认需要新的封存样本。"
          "阶段一已查看过的六月继续排除。"),
        p(f"运行环境为 Python {data['environment']['python']}。重采样种子为 {data['protocol']['seed']}。"
          "15 项合成测试通过，覆盖缺列校验、跨期重复、词表拟合边界、转人工计分及重采样。"
          f"实现见 {link(REPO + '/blob/' + TAG + '/stage2/stage2.py', 'stage2.py')}，执行命令见第 10 节。", NOTE),
        PageBreak(),
    ]
    story += exploration

    comparison = [["基线", "总体正确率", "宏 F1 / 95% 区间", "自动覆盖率", "自动正确率"]]
    for label, outcome in (("训练多数类", majority), ("阶段一固定规则", rules), ("词袋朴素贝叶斯", nb)):
        comparison.append([label, pct(outcome["accuracy"]),
                           f"{outcome['macro_f1']:.3f}<br/>{score_ci(outcome['macro_f1_95_bootstrap'])}",
                           pct(outcome["coverage"]), pct(outcome["accuracy_when_auto"])])
    story += heading("5.2　基线比较与不确定性",
                     "三个基线在同一批历史样本上比较，覆盖率和正确率同时报告。")
    story += [
        p("多数类基线始终预测训练集中最多的债务催收，衡量类别先验能达到的分数。"
          "固定规则匹配阶段一的关键词，冲突或无命中时可转人工。多项式朴素贝叶斯使用训练词袋，"
          "为衡量文本词频能否改善分流而设。"),
        caption(f"表 5　2026 年 5 月历史测试结果（n = {n:,}）"),
        table(comparison, [.24, .16, .28, .16, .16]),
        gap(6),
        p("宏平均 F1 是六个类别 F1 的等权平均。总体正确率以全部测试记录为分母，转人工计为未正确自动分流。"
          "自动正确率只用自动处理的记录作分母。两项指标并列，便于区分审核负荷与自动错分。", NOTE),
        gap(6), section("差值比两条单独区间更直接"),
        p(f"在表 5 的同一批投诉上，朴素贝叶斯的宏平均 F1 比固定规则高 {delta:.3f}。"
          f"每次对五月记录有放回抽样，并用相同的样本索引重算两个模型，所得差值的 95% 区间为 {score_ci(delta_ci)}。"
          "单模型宏 F1 也使用 500 次行级自助抽样。该区间描述当前样本的抽样波动，跨月份漂移另需验证。"),
        caption("表 6　只用四月验证集选择朴素贝叶斯平滑系数"),
        table([["候选 α", "验证宏 F1", "验证总体正确率", "选择"]] + [
            [f"{score['alpha']:g}", f"{score['macro_f1']:.4f}", pct(score["accuracy"]),
             "选用" if score["alpha"] == data["model"]["selected_alpha"] else "—"]
            for score in data["validation_alpha_scores"]
        ], [.19, .28, .29, .24], spacing=4),
        gap(4), p("表 6 的验证宏 F1 在 α = 1 时最高，与 α = 0.1 的差距约为 0.001。", NOTE),
        gap(8),
        p(f"规则把 {reviews:,} 条交人工，其中无命中 {review_reasons['no_rule_match']:,} 条、"
          f"命中冲突 {review_reasons['ambiguous']:,} 条、超长 {review_reasons['too_long']:,} 条。"
          f"规则自动误路由 {rule_errors:,} 条，"
          f"自动正确率的 Wilson 95% 区间为 {pct_ci(review_ci)}。"
          f"朴素贝叶斯全量自动分流，正确 {nb['correct']:,} 条、误路由 {nb_errors:,} 条，自动正确率区间为 "
          f"{pct_ci(nb['accuracy_when_auto_95_wilson'])}。朴素贝叶斯达到宏 F1 与覆盖率门槛，"
          "但增加了自动误路由的绝对数量。两种方法都未达到 85% 自动正确率门槛。"),
        PageBreak(),
    ]

    story += heading("5.3　逐类错分分析", "转账投诉最常被错分到存取款账户。")
    story += [
        caption(f"图 5　朴素贝叶斯的五月混淆矩阵（n = {n:,}，单位为条）"),
        ConfusionPlot(confusion),
        p(f"图 5 按行给出数据标签、按列给出预测标签。{transfer_total:,} 条转账类中，"
          f"{transferred[TRANSFER]:,} 条进入正确队列，召回率 {pct(transferred[TRANSFER] / transfer_total)}。"
          f"其中 {transferred[ACCOUNT]:,} 条被路由到存取款账户，占转账类的 "
          f"{pct(transferred[ACCOUNT] / transfer_total)}。仅凭聚合矩阵无法判定具体文本中的原因。", NOTE),
        gap(7), section("6　局限性与风险"),
        p("错分可能让正确队列迟收案件，错误接收的队列也要承担改派。用人工确认保留回退路径，"
          "在四月验证集上选择拒答门槛。五月结果描述历史分流表现，部署表现需要用新封存样本另行核验。"),
        p("投诉流程与发布条件造成样本选择偏差 [1], [2]。本地副本无法逐条核验公开同意，叙述也可能残留个人信息。"
          "原文留在本地，公开的数据证据只含汇总和合成示例。CFPB 于 2026 年 8 月宣布停止酌情公开叙述 [3]。"
          "后续验收需要先取得合适的新样本。"),
        section("7　下一阶段计划"),
        p("阶段二已完成时间切分和基线比较。表 7 列出后续任务、依赖和完成标准。", NOTE),
        caption("表 7　阶段三至五的交付计划"),
        table([
            ["阶段与任务", "负责人", "依赖", "完成标准"],
            ["3　方法比较", "杨俊炜建模，赵煜凡核查数据。", "四月验证集、阶段二基线、候选数据来源。",
             "比较线性模型与基线，冻结复核门槛并形成新样本方案。"],
            ["4　系统集成", "杨俊炜", "阶段三锁定的模型与门槛。",
             "本地命令输出队列建议或转人工，通过空文本和超长文本检查。"],
            ["5　复现与审计", "杨俊炜审计，赵煜凡跟进数据。", "新封存样本、阶段四工具。",
             "用新样本核验表 1，汇报转账召回率、覆盖率和误路由数。"],
        ], [.17, .21, .23, .39], spacing=4),
        gap(8), section("8　个人贡献"),
        p("表 8 将团队分工与本阶段可核对的工作对应起来。", NOTE),
        caption("表 8　阶段二成员分工"),
        table([
            ["成员", "责任及可核对产物"],
            ["赵煜凡", "负责数据采集，提供工作簿及 CSV 压缩包两份本地历史文件。"],
            ["杨俊炜", "研究设计、数据审计、去重与切分、基线评估、测试、制图、报告和仓库整理。"
                    "对应 stage2.py、test_stage2.py、results、数据卡和本报告。"],
        ], [.20, .80], spacing=4),
        gap(6),
        p("AI 使用披露。OpenAI Codex 协助修改代码、复核实验、生成图表和撰写报告。", NOTE),
        PageBreak(),
    ]

    commands = (
        "cd stage2",
        "python -m unittest -v test_stage2.py",
        'python stage2.py --data "本地路径/complaints.csv.zip" --output results/summary.json',
        "python make_charts.py",
        "python make_data_card.py",
        "python -m pip install -r requirements.txt",
        "python build_report.py",
    )
    story += [
        section("9　参考文献"),
        p("[1] Consumer Financial Protection Bureau, “Consumer Complaint Database.” [Online]. Available: " +
          link(CFPB + "/data-research/consumer-complaints/"), NOTE),
        p("[2] Consumer Financial Protection Bureau, “How we share complaint data.” [Online]. Available: " +
          link(CFPB + "/complaint/data-use/"), NOTE),
        p("[3] Consumer Financial Protection Bureau, “The CFPB to Cease Discretionary Publication of "
          "Complaint Narratives and Visualizations,” Aug. 14, 2026. [Online]. Available: " +
          link(CFPB + "/about-us/newsroom/the-cfpb-to-cease-discretionary-publication-of-complaint-narratives-and-visualizations/"), NOTE),
        gap(12), section("10　附录"), section("复现步骤"),
        p("解压仓库或检出提交标签。合成测试可直接执行。真实结果需要取得同一历史 ZIP 并按下列命令指定路径，"
          "官方当前导出文件可能属于不同版本。仓库结果只含汇总值。"),
        table([[p("<br/>".join(escape(command) for command in commands), CODE)]], [1], header=False, spacing=8),
        gap(7),
        p("输入 ZIP 的 SHA-256", HEAD),
        p(source["sha256"], NOTE),
        p(f"校验对象为 ZIP 文件本身。PDF 的复建需要 ReportLab 和 Windows 微软雅黑字体。"
          f"运行说明见 {link(REPO + '/blob/' + TAG + '/stage2/README.md', '阶段二 README')}。", NOTE),
        gap(13), section("反馈与修订记录"),
        p("针对阶段一成绩偏低的反馈，阶段二补齐数据来源、字段记录、时间切分和简单学习基线。"
          "随后按首次到件顺序修正去重，补上配对区间和错分分析，并标明五月结果是回顾性复评。"
          "根据格式要求，本版按标准章节顺序重排，统一字号和行距，补齐图表引用及正式提交标签。"
          "目前未收到教师的逐条评语。"),
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    Report(output).build(story)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    summary = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
    build(summary, args.output)
