"""Build the stage-1 PDF report with ReportLab.

The report content is a course-project draft. Replace pending team/repository
fields before submission and keep the evidence numbers tied to the supplied
data version.
"""

from __future__ import annotations

from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "阶段一开题报告_提交版.pdf"
FONT = Path(r"C:\Windows\Fonts\msyh.ttc")
FONT_BOLD = Path(r"C:\Windows\Fonts\msyhbd.ttc")
pdfmetrics.registerFont(TTFont("MSYH", str(FONT), subfontIndex=0))
pdfmetrics.registerFont(TTFont("MSYH-Bold", str(FONT_BOLD), subfontIndex=0))

NAVY = colors.HexColor("#14263D")
BLUE = colors.HexColor("#2463A6")
TEAL = colors.HexColor("#137C83")
LIGHT = colors.HexColor("#EDF3F8")
PALE = colors.HexColor("#F7FAFC")
GRAY = colors.HexColor("#526071")


class Report(BaseDocTemplate):
    def __init__(self, filename):
        super().__init__(str(filename), pagesize=A4,
                         leftMargin=20*mm, rightMargin=20*mm,
                         topMargin=20*mm, bottomMargin=20*mm,
                         title="金融投诉叙述文本的六类自动分流与人工复核系统——阶段一开题报告",
                         author="Course project team")
        frame = Frame(self.leftMargin, self.bottomMargin,
                      self.width, self.height, leftPadding=0, rightPadding=0,
                      topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self.decorate))

    def decorate(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setStrokeColor(BLUE)
        canvas.setLineWidth(0.8)
        canvas.line(20*mm, h-13*mm, w-20*mm, h-13*mm)
        canvas.setFont("MSYH", 8)
        canvas.setFillColor(GRAY)
        canvas.drawString(20*mm, 12*mm, "Python 与人工智能课程 · 阶段一开题报告")
        canvas.drawRightString(w-20*mm, 12*mm, f"{doc.page} / 5")
        canvas.restoreState()


title = ParagraphStyle("title", fontName="MSYH-Bold", fontSize=20, leading=29,
                       textColor=NAVY, alignment=TA_CENTER, wordWrap="CJK", spaceAfter=8)
subtitle = ParagraphStyle("subtitle", fontName="MSYH", fontSize=11, leading=17,
                          textColor=TEAL, alignment=TA_CENTER, spaceAfter=16)
h1 = ParagraphStyle("h1", fontName="MSYH-Bold", fontSize=14, leading=20,
                    textColor=NAVY, wordWrap="CJK", spaceBefore=13, spaceAfter=7)
h2 = ParagraphStyle("h2", fontName="MSYH-Bold", fontSize=11.5, leading=16,
                    textColor=BLUE, wordWrap="CJK", spaceBefore=9, spaceAfter=4)
body = ParagraphStyle("body", fontName="MSYH", fontSize=10.5, leading=17,
                      textColor=NAVY, wordWrap="CJK", spaceAfter=5)
small = ParagraphStyle("small", parent=body, fontSize=9.2, leading=14, textColor=GRAY)
tiny = ParagraphStyle("tiny", parent=body, fontSize=8.2, leading=12)
tablehead = ParagraphStyle("tablehead", parent=body, fontName="MSYH-Bold", fontSize=10,
                           leading=14.5, textColor=colors.white, spaceAfter=0)
tablecell = ParagraphStyle("tablecell", parent=body, fontSize=10, leading=14.5, spaceAfter=0)
callout = ParagraphStyle("callout", parent=body, fontName="MSYH-Bold", fontSize=10,
                         leading=15, textColor=TEAL)


def P(text, style=body):
    return Paragraph(text, style)


def section(number, label):
    return P(f"{number}　{label}", h1)


def sub(label):
    return P(label, h2)


def tbl(rows, widths, header=True, font_size=8.3):
    contents = []
    for i, row in enumerate(rows):
        contents.append([P(str(x), tablehead if header and i == 0 else tablecell) for x in row])
    t = Table(contents, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY if header else LIGHT),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E3EC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


class Flow(Flowable):
    def __init__(self, width=170*mm, height=26*mm):
        super().__init__()
        self.width, self.height = width, height

    def draw(self):
        labels = ["英文投诉叙述", "校验与标准化", "六类规则计分", "自动分流／人工复核"]
        box_w = 37*mm
        gap = (self.width - 4*box_w) / 3
        c = self.canv
        for i, label in enumerate(labels):
            x = i*(box_w+gap)
            c.setFillColor(LIGHT if i != 3 else colors.HexColor("#E4F4F1"))
            c.setStrokeColor(BLUE if i != 3 else TEAL)
            c.roundRect(x, 6*mm, box_w, 13*mm, 3*mm, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont("MSYH", 8.2)
            c.drawCentredString(x+box_w/2, 11*mm, label)
            if i < 3:
                c.setStrokeColor(BLUE)
                sx = x+box_w+1.5*mm
                ex = x+box_w+gap-2*mm
                c.line(sx, 12.5*mm, ex, 12.5*mm)
                c.line(ex-2*mm, 14*mm, ex, 12.5*mm)
                c.line(ex-2*mm, 11*mm, ex, 12.5*mm)


story = []

# Page 1: framing and abstract.
story += [Spacer(1, 11*mm), P("金融投诉叙述文本的六类自动分流<br/>与人工复核系统", title),
          P("阶段一开题报告｜问题定义与计算原型", subtitle)]
story += [tbl([
    ["项目", "提交信息"],
    ["课程 / 阶段", "Python 与人工智能 / 阶段一"],
    ["团队 / 成员", "杨俊炜、赵煜凡"],
    ["日期", "2026 年 10 月 12 日"],
], [42*mm, 128*mm]), Spacer(1, 6*mm)]
story += [P("执行摘要", h1)]
story += [P("本项目面向金融投诉受理人员，研究如何仅根据英文投诉叙述，将案件初步分流至六个常见金融产品类别；无法可靠判断时交由人工复核。提供的工作簿有 1,048,575 条记录，但仅 17,093 条含公开叙述，其中六类目标共有 14,919 条。阶段一完成了数据流式核查、规则分流原型与 15 项自动化测试。以去重后的 2026 年 6 月 946 条六类样本作初步检查，规则自动覆盖 61.31%，被自动处理样本的准确率为 72.93%；这些数值不代表最终模型表现。后续将比较多数类、TF-IDF 线性模型与带拒答的系统，采用时间切分、错误分析和鲁棒性测试，限制系统用途为辅助分流。")]
story += [section("1", "问题定义与范围")]
story += [P("<b>问题：</b>给定一条首次提交的英文投诉叙述，系统输出六个产品类别中的一个，或输出“需人工复核”；同时返回可检查的依据或拒答原因。目标用户是受理和分流人员，决策任务是辅助路由，而非判断投诉真伪、违法性、责任或赔偿。")]
story += [P("<b>输入：</b>单条纯文本叙述（字符串）。<b>输出：</b>JSON：status=auto/review、product、reason、evidence。只用叙述作为预测特征；Product 是监督标签，Issue、Sub-issue、公司处理结果等字段不进入推理，以免发生信息泄漏。")]
story += [P("<b>范围：</b>首期仅支持债务催收、存取款账户、信用卡、汇款／虚拟货币、按揭、征信六类；空文本、过短、过长、无规则匹配和并列命中均转人工。对其他产品及非英文投诉不作自动分类。")]

story += [PageBreak()]

# Page 2: data and related work.
story += [section("2", "数据可行性与相关工作")]
story += [sub("2.1 本地数据审计")]
story += [P("提供的 Excel 工作簿含 16 列、1,048,575 条数据，已达 Excel 单表行数上限；同目录压缩 CSV 可流式读取，原型只读取其前 1,048,575 条，并核对了工作簿行数和非空叙述数。下表是这段数据中的六类目标样本。")]
story += [tbl([
    ["产品类别", "总记录", "有叙述", "叙述覆盖率"],
    ["债务催收", "53,835", "5,566", "10.34%"],
    ["存取款账户", "13,191", "3,020", "22.89%"],
    ["信用卡", "13,509", "3,009", "22.27%"],
    ["汇款／虚拟货币", "5,706", "1,328", "23.27%"],
    ["按揭", "5,139", "1,082", "21.05%"],
    ["征信", "946,029", "914", "0.10%"],
], [64*mm, 32*mm, 32*mm, 42*mm])]
story += [Spacer(1, 2*mm), P("表 1　六类产品的文本可用性。全部 1,048,575 条中仅 17,093 条（1.63%）有叙述；六类合计 14,919 条。征信占全部记录约 90.2%，但文本覆盖率极低，因此不能把文本模型评估推广到全部投诉。", small)]
story += [P("<b>来源与标签：</b>本地文件为 complaints.xlsx 和 complaints.csv.zip；字段形式与 CFPB 投诉数据库一致，但原始下载日期和许可适用细节尚待团队核实。[1] 说明 Product 是投诉人识别的类别，故它是可用的代理标签，不等于经专家裁定的客观正确分类。")]
story += [P("SHA-256（xlsx）：12CEDEB7B886B8DEA2DF2580A5FA05888ECA9DC61463FA4EF5F8222E14CF7455<br/>SHA-256（CSV ZIP）：850D5D220285ABECB4D4B94AE4C92A8F318476CE14BD0460C3D6361C79AE9694", small)]
story += [sub("2.2 初步相关工作（非完整文献综述）")]
story += [P("[1] CFPB 数据库提供投诉产品、议题、处理等结构化字段，并提醒公开投诉不是消费者经历的统计代表样本。本项目据此限定目标总体为“可获取叙述的六类投诉”。[2] TF-IDF 可将文本转成稀疏特征，适合后续与线性分类器组成可复现的学习基线。[3] 选择性分类研究提出以拒答率换取更低的自动处理错误率，启发本项目同时报告覆盖率与自动处理准确率。")]
story += [P("<b>项目差距：</b>本项目不追求新算法；重点在明确输入时点、限制标签含义、处理文本缺失与重复、将分类和人工复核接成可运行流程，并用真实的时间切分和失败案例检验其可信度。", small)]

story += [PageBreak()]

# Page 3: modeling and prototype.
story += [section("3", "计算建模与 Python 原型")]
story += [sub("3.1 形式化表示")]
story += [P("令 x 为英文叙述字符串，y 属于六类产品集合 Y。分类器 f(x) 给出候选类别，选择函数 g(x)∈{0,1} 决定是否自动分流；g(x)=0 时输出 review。阶段一以透明规则构造 f 和 g；后续将用训练数据学习 f，并仅在验证集上确定拒答阈值。")]
story += [Flow(), P("图 1　阶段一原型流程。数据审计独立于在线推理；推理端仅接收文本。", small)]
story += [sub("3.2 模块、假设与复杂度")]
story += [tbl([
    ["函数", "职责与边界"],
    ["normalize / route", "标准化空白与大小写；按六类关键词计分；并列、无匹配及无效长度转人工。规则命中词仅是线索，不是校准概率。"],
    ["iter_workbook_segment / audit", "从压缩 CSV 流式读取与 Excel 行数相同的前段，核对类别与文本覆盖率；不将整个 8.9 GB 原始 CSV 解压到磁盘。"],
    ["evaluation_rows / score", "以标准化叙述散列去重，剔除同一文本跨类别冲突组，给出多数类及规则的基本评价。"],
], [55*mm, 115*mm])]
story += [Spacer(1, 2*mm), P("规则数固定时，单条推理时间约 O(L×K)，L 为文本长度、K 为关键词数；推理内存约 O(L)。数据审计单次顺序扫描 N 条记录，时间 O(N)、额外统计内存随类别数增长。评估需保存约 1.5 万条目标文本以跨月份去重，机器内存负担可控。", small)]
story += [sub("3.3 可复现演示与自动化测试")]
story += [P("执行 <font color='#2463A6'>python prototype.py demo --text \"A debt collector keeps calling about a debt I do not owe.\"</font>，输出 status=auto、product=Debt collection，并列出命中词。空文本、过短文本、过长文本、没有命中和并列命中均转人工。<font color='#2463A6'>python -m unittest -v</font> 已运行 15 项测试并全部通过，覆盖输入类型、归一化、词边界、六类中的代表性预测和空评估集。")]
story += [P("阶段一原型是可运行的规则基线；下一阶段训练 TF-IDF 线性模型前，不把这些规则当作已校准的 AI 概率系统。", callout)]

story += [PageBreak()]

# Page 4: measurements, evaluation plan and risk.
story += [section("4", "初步证据与后续评估方案")]
story += [sub("4.1 阶段一试运行")]
story += [P("从六类叙述中按标准化文本去重、去除跨类冲突，再选取首次出现在 2026 年 6 月的 946 条作原型检查。多数类根据此前月份确定为“债务催收”。规则方法没有用该月样本训练；这仍是开发阶段的试运行，不作为后续最终测试集。")]
story += [tbl([
    ["方法 / 指标", "结果", "解释"],
    ["多数类：整体准确率", "27.38%", "所有样本均给出债务催收类别。"],
    ["多数类：宏平均 F1", "0.0716", "反映六类不平衡下的差表现。"],
    ["规则：自动覆盖率", "61.31%", "约四成转人工；312 条无命中，54 条并列。"],
    ["规则：自动处理准确率", "72.93%", "仅在自动处理的样本上计算，不能与整体准确率直接等同。"],
    ["规则：宏平均 F1", "0.5042", "将转人工视为未正确分类，在全部 946 条上计算。"],
], [54*mm, 29*mm, 87*mm])]
story += [Spacer(1, 2*mm), P("表 2　初步规则基线。六月测试片段的征信类仅 18 条，类别指标不稳定；没有给出最终模型的泛化保证或显著性结论。", small)]
story += [sub("4.2 固定评估方案与成功标准")]
story += [P("阶段二先冻结数据字典和去重规则：同一标准化叙述若跨类冲突则剔除；其余按首次出现日期归组，确保相同文本不跨集合。计划用 2026 年 4 月及以前作训练／内部验证，2026 年 5 月作独立最终测试；6 月的阶段一试运行样本不参与后续模型选择或正式成绩。仅在训练集拟合词表和 IDF。")]
story += [P("主指标为六类宏平均 F1；同时报告每类召回率、混淆矩阵、覆盖率—自动处理准确率曲线及运行时延。目标是相对多数类和规则基线有稳定改进；预设探索性门槛为宏平均 F1≥0.65、自动处理准确率≥0.85 且覆盖率≥0.50，若未达到须解释失败原因而非修改测试集。正式报告将加入置信区间。")]
story += [sub("4.3 主要风险与约束")]
story += [P("<b>选择偏差：</b>叙述仅覆盖 1.63%，征信文本覆盖率约 0.10%。<b>标签噪声：</b>Product 是投诉人选择，不等于专家结论。[1] <b>时间与格式漂移：</b>公开文本的政策可能变化；CFPB 已于 2026 年 8 月停止在数据库中继续发布叙述，必须明确本项目只评估现有静态副本。[4] <b>误分流成本：</b>错误路由可能延误处理，故保留人工复核和审计记录。")]

story += [PageBreak()]

# Page 5: milestones, responsible AI, references and handoff.
story += [section("5", "阶段计划、责任与参考资料")]
story += [tbl([
    ["阶段", "具体工作与可交付证据"],
    ["阶段 2：数据与实验", "固定划分与数据卡片；清洗及防泄漏脚本；多数类、规则、TF-IDF＋逻辑回归基线；缺失和类别偏差图。"],
    ["阶段 3：模型比较", "在同一划分上比较线性模型、字符 n-gram 或轻量预训练模型；给出重复运行、错误分类及运行成本。"],
    ["阶段 4：集成系统", "提供 CLI 或本地网页：文本输入、类别／转人工输出、日志与异常处理；端到端及集成测试。"],
    ["阶段 5：扩展与审计", "加入验证集确定的拒答阈值、置信度校准、扰动与分组评估、数据漂移与回滚计划；形成最终报告草案。"],
], [39*mm, 131*mm])]
story += [Spacer(1, 2*mm), P("<b>分工：</b>成员为杨俊炜、赵煜凡，具体分工尚未提供。建议分配数据审计、模型与评估、系统集成、文档与演示四项职责；提交前必须填写各成员实际工作、仓库 URL 与 phase-1-submission 的真实 commit/tag。下一阶段完成标准：可重跑同一划分和基线表，并保留失败案例。", small)]
story += [sub("负责任 AI 与使用声明")]
story += [P("原始叙述可能仍有隐私风险，示例使用人工编写文本，不在日志或报告中展示完整原文。模型只为人工分流提供建议；对拒答、错误分流保留人工纠正路径。不以类别预测推断投诉真伪、公司违法或消费者权益。报告初稿、原型与测试由 OpenAI Codex（GPT-6）辅助生成；数据统计和测试由本地脚本实际执行，团队提交前须逐项复核、理解并按课程政策披露。", small)]
story += [sub("参考资料（初步）")]
story += [P("[1] Consumer Financial Protection Bureau, “Consumer Complaint Database” 与 “How we share complaint data,” 2026. <link href='https://www.consumerfinance.gov/data-research/consumer-complaints/' color='#2463A6'>consumerfinance.gov/data-research/consumer-complaints/</link>；<link href='https://www.consumerfinance.gov/complaint/data-use/' color='#2463A6'>consumerfinance.gov/complaint/data-use/</link>。", tiny)]
story += [P("[2] scikit-learn, “TfidfVectorizer” 官方文档. <link href='https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html' color='#2463A6'>scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html</link>。", tiny)]
story += [P("[3] Y. Geifman and R. El-Yaniv, “Selective Classification for Deep Neural Networks,” NeurIPS 2017. <link href='https://arxiv.org/abs/1705.08500' color='#2463A6'>arxiv.org/abs/1705.08500</link>。", tiny)]
story += [P("[4] CFPB, “The CFPB to Cease Discretionary Publication of Complaint Narratives and Visualizations,” 2026-08-14. <link href='https://www.consumerfinance.gov/about-us/newsroom/the-cfpb-to-cease-discretionary-publication-of-complaint-narratives-and-visualizations/' color='#2463A6'>CFPB 官方公告</link>。", tiny)]
story += [P("本地数据：complaints.xlsx 与 complaints.csv.zip（用户提供；文件哈希见第 2 页）。课程要求：作业指导.pdf，第 1–4 页。", tiny)]


if __name__ == "__main__":
    Report(OUT).build(story)
    print(OUT)
