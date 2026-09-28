"""Shartnoma PDF generatori (reportlab). Til — shartnoma tuzilgan til (6 tildan biri)."""
import io
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .contract_texts import texts
from .translit import pick

FONT_DIR = Path(__file__).resolve().parent / "fonts"
_registered = False


def _fonts():
    global _registered
    if not _registered:
        pdfmetrics.registerFont(TTFont("DV", str(FONT_DIR / "DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("DVB", str(FONT_DIR / "DejaVuSans-Bold.ttf")))
        _registered = True


def money(v) -> str:
    v = Decimal(v or 0).quantize(Decimal("0.01"))
    whole, frac = f"{v:.2f}".split(".")
    whole = f"{int(whole):,}".replace(",", " ")
    return whole if frac == "00" else f"{whole},{frac}"


class QR(Flowable):
    def __init__(self, value, size=28 * mm):
        super().__init__()
        self.value, self.size = value, size
        self.width = self.height = size

    def draw(self):
        w = QrCodeWidget(self.value)
        b = w.getBounds()
        d = Drawing(self.size, self.size, transform=[self.size / (b[2] - b[0]), 0, 0, self.size / (b[3] - b[1]), 0, 0])
        d.add(w)
        renderPDF.draw(d, self.canv, 0, 0)


def build_pdf(contract) -> bytes:
    _fonts()
    app = contract.application
    lang = contract.lang
    T = texts(lang)
    seller = contract.seller
    platform = settings.BRAND_NAME
    styles = {
        "title": ParagraphStyle("t", fontName="DVB", fontSize=13, alignment=TA_CENTER, spaceAfter=4),
        "center": ParagraphStyle("c", fontName="DV", fontSize=9, alignment=TA_CENTER),
        "h": ParagraphStyle("h", fontName="DVB", fontSize=9.5, spaceBefore=7, spaceAfter=2),
        "p": ParagraphStyle("p", fontName="DV", fontSize=9, leading=12.2, alignment=TA_JUSTIFY),
        "small": ParagraphStyle("s", fontName="DV", fontSize=7.5, leading=9.5),
        "cell": ParagraphStyle("cell", fontName="DV", fontSize=8, leading=10),
        "cellb": ParagraphStyle("cellb", fontName="DVB", fontSize=8, leading=10),
        "note": ParagraphStyle("n", fontName="DV", fontSize=8.2, leading=11, textColor=colors.HexColor("#555555"),
                               alignment=TA_JUSTIFY),
    }
    P = lambda t, s="p": Paragraph(t, styles[s])  # noqa: E731

    seller_name = seller.full_name or pick(seller.name, lang)
    city = pick(seller.district_i18n, lang) or pick(seller.region_i18n, lang)
    fmt = {
        "number": contract.number,
        "date": contract.date.strftime("%d.%m.%Y"),
        "city": city,
        "seller": f"<b>{seller_name}</b>",
        "seller_director": seller.director or "________________",
        "buyer": f"<b>{app.buyer_name}</b>",
        "buyer_director": app.buyer_director or "________________",
        "pinfl": app.buyer_pinfl or "______________",
        "passport": app.buyer_passport or "________",
        "agent": pick(contract.agent.name, lang) if contract.agent else "",
        "platform": platform,
        "total": money(contract.grand_total),
        "delivery": money(contract.delivery_cost),
        "prepay": contract.prepayment_percent,
        "pay_days": contract.payment_days,
        "del_days": contract.delivery_days,
        "address": app.delivery_address or app.buyer_address or "—",
        "method": T.get(f"pay_{contract.payment_method}", contract.payment_method),
        "court": T["court_b2b"] if contract.buyer_type == "b2b" else T["court_b2c"],
    }
    f = lambda key: T[key].format(**fmt)  # noqa: E731

    story = [P(f("title"), "title"), P(f("city_date"), "center"), Spacer(1, 6)]
    story.append(P(f("pre_b2b") if contract.buyer_type == "b2b" else f("pre_b2c")))
    if contract.agent:
        story += [Spacer(1, 3), P("<i>" + f("agent_note") + "</i>", "note")]
    body = [
        ("s1", ["s1_1", "s1_2"]),
        ("s2", ["s2_1", "s2_2"]),
        ("s3", ["s3_bank" if contract.payment_method == "bank" else "s3_online", "s3_2"]),
        ("s4", ["s4_delivery" if app.delivery_required else "s4_pickup", "s4_2"]),
        ("s5", ["s5_1", "s5_2"]),
        ("s6", ["s6_b2b" if contract.buyer_type == "b2b" else "s6_b2c"]),
        ("s7", ["s7_1"]),
        ("s8", ["s8_1"]),
        ("s9", ["s9_1", "s9_2", "s9_3"]),
    ]
    for head, paras in body:
        story.append(P(f(head), "h"))
        for key in paras:
            story.append(P(f(key)))

    # Spetsifikatsiya
    story += [Spacer(1, 8), P(T["spec"], "h")]
    from .i18n_meta import unit_label

    rows = [[P(T[c], "cellb") for c in ("col_no", "col_name", "col_unit", "col_qty", "col_price", "col_sum")]]
    for i, it in enumerate(app.items.select_related("product").all(), 1):
        name = pick(it.name, lang)
        spec = pick(it.spec, lang)
        label = f"{name}<br/><font size=7 color='#666666'>{spec} · {it.product.sku}</font>" if spec else f"{name}<br/><font size=7 color='#666666'>{it.product.sku}</font>"
        rows.append([
            P(str(i), "cell"), P(label, "cell"), P(unit_label(it.unit, lang), "cell"),
            P(str(it.qty), "cell"), P(money(it.price), "cell"), P(money(it.amount), "cell"),
        ])
    rows.append(["", P(T["items_total"], "cellb"), "", "", "", P(money(contract.total), "cellb")])
    if contract.delivery_cost:
        rows.append(["", P(T["delivery"], "cell"), "", "", "", P(money(contract.delivery_cost), "cell")])
    rows.append(["", P(T["grand"], "cellb"), "", "", "", P(money(contract.grand_total), "cellb")])
    tbl = Table(rows, colWidths=[8 * mm, 75 * mm, 15 * mm, 19 * mm, 28 * mm, 30 * mm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2F7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(tbl)

    # Rekvizitlar
    story += [Spacer(1, 8), P(T["req"], "h")]

    def party(title, lines):
        out = [P(f"<b>{title}</b>", "cell")]
        out += [P(line, "cell") for line in lines if line]
        return out

    s_lines = [
        f"<b>{seller_name}</b>",
        f"{T['inn']}: {seller.inn or T['not_set']}",
        f"{T['address']}: {seller.address or (pick(seller.region_i18n, lang) + ', ' + pick(seller.district_i18n, lang))}",
        f"{T['bank']}: {seller.bank_name or T['not_set']}",
        f"{T['account']}: {seller.treasury_account or seller.bank_account or T['not_set']}",
        f"{T['mfo']}: {seller.bank_mfo or T['not_set']}",
        f"{T['phone']}: {seller.phone or T['not_set']}",
        f"{T['director']}: {seller.director or '________________'}",
        f"{T['sign']}: ________________",
    ]
    if contract.buyer_type == "b2b":
        b_lines = [
            f"<b>{app.buyer_name}</b>",
            f"{T['inn']}: {app.buyer_inn or T['not_set']}",
            f"{T['address']}: {app.buyer_address or T['not_set']}",
            f"{T['bank']}: {app.buyer_bank_name or T['not_set']}",
            f"{T['account']}: {app.buyer_bank_account or T['not_set']}",
            f"{T['mfo']}: {app.buyer_bank_mfo or T['not_set']}",
            f"{T['phone']}: {app.buyer_phone}",
            f"{T['director']}: {app.buyer_director or '________________'}",
            f"{T['sign']}: ________________",
        ]
    else:
        b_lines = [
            f"<b>{app.buyer_name}</b>",
            f"{T['pinfl']}: {app.buyer_pinfl or T['not_set']}",
            f"{T['passport']}: {app.buyer_passport or T['not_set']}",
            f"{T['address']}: {app.buyer_address or T['not_set']}",
            f"{T['phone']}: {app.buyer_phone}",
            f"{T['sign']}: ________________",
        ]
    req = Table([[party(T["seller"], s_lines), party(T["buyer"], b_lines)]], colWidths=[87.5 * mm, 87.5 * mm])
    req.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOX", (0, 0), (0, 0), 0.4, colors.grey),
                             ("BOX", (1, 0), (1, 0), 0.4, colors.grey)]))
    story.append(req)

    verify_url = f"{settings.SITE_URL.rstrip('/')}/verify/{contract.token}"
    qr_tbl = Table([[QR(verify_url), P(f"{T['verify']}: {verify_url}<br/>{platform} · {contract.number}", "small")]],
                   colWidths=[32 * mm, 143 * mm])
    qr_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [Spacer(1, 8), qr_tbl]

    buf = io.BytesIO()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("DV", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawString(18 * mm, 10 * mm, f"{platform} · {contract.number}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=17 * mm, topMargin=15 * mm,
                            bottomMargin=16 * mm, title=contract.number, author=platform)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def render_contract(contract, save=True):
    data = build_pdf(contract)
    if save:
        fname = contract.number.replace("/", "_") + ".pdf"
        if contract.pdf:
            contract.pdf.delete(save=False)
        contract.pdf.save(fname, ContentFile(data), save=True)
    return data
