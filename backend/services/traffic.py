import html
import io
import re
from datetime import date, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import LOGO_PATH

TRAFFIC_FIELD_LABELS = {
    "empresa": "nome da empresa",
    "campanha": "nome da campanha",
    "plataforma": "plataforma",
    "periodo_inicio": "data inicial",
    "periodo_fim": "data final",
    "investimento": "valor investido",
    "custo_dia": "custo médio por dia",
    "alcance": "alcance",
    "visualizacoes": "visualizações",
    "contatos": "contatos gerados",
    "custo_contato": "custo médio por contato",
}


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip())
    cleaned = cleaned.strip("_")
    return cleaned or "campanha"


def traffic_form_missing_fields(values: dict[str, str]) -> list[str]:
    return [TRAFFIC_FIELD_LABELS[key] for key, value in values.items() if not value]


def validate_traffic_form(values: dict[str, str]) -> dict[str, Any]:
    missing = traffic_form_missing_fields(values)
    if missing:
        return {"valid": False, "missing": missing, "error": None}

    try:
        inicio = datetime.strptime(values["periodo_inicio"], "%d/%m/%Y").date()
        fim = datetime.strptime(values["periodo_fim"], "%d/%m/%Y").date()
    except ValueError:
        return {"valid": False, "missing": [], "error": "Datas inválidas. Use o formato DD/MM/AAAA."}

    if fim < inicio:
        return {"valid": False, "missing": [], "error": "A data final não pode ser anterior à data inicial."}

    return {"valid": True, "missing": [], "error": None}


def build_traffic_pdf(values: dict[str, str]) -> bytes:
    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    brand_style = ParagraphStyle(
        "OppiBrand",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#C026D3"),
        spaceAfter=2,
    )

    title_style = ParagraphStyle(
        "OppiTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#16233B"),
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "OppiBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=12.5,
        leading=18,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10,
    )

    safe = {key: html.escape(str(value)) for key, value in values.items()}
    story = []

    logo_element = None
    if LOGO_PATH.exists():
        try:
            logo_element = RLImage(str(LOGO_PATH), width=18 * mm, height=18 * mm)
        except Exception:
            logo_element = None

    brand_text = Paragraph(
        '<font color="#C026D3"><b>OPPI TECH</b></font><br/>'
        '<font color="#64748B" size="8">GESTÃO DE TRÁFEGO</font>',
        brand_style,
    )

    if logo_element:
        brand_table = Table([[logo_element, brand_text]], colWidths=[22 * mm, 125 * mm])
    else:
        brand_table = Table([[brand_text]], colWidths=[147 * mm])

    brand_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    story.append(brand_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Apresentação de resultados", title_style))

    accent = Table([[""]], colWidths=[32 * mm], rowHeights=[2.4 * mm])
    accent.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#A855F7")),
            ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#A855F7")),
        ])
    )
    story.append(accent)
    story.append(Spacer(1, 14))

    paragraphs = [
        "Bom dia, estes são os resultados dos anúncios.",
        f'A empresa <b>{safe["empresa"]}</b> realizou uma campanha na plataforma <b>{safe["plataforma"]}</b>.',
        f'A campanha apresentada é <b>{safe["campanha"]}</b>.',
        f'O período analisado foi de <b>{safe["periodo_inicio"]}</b> até <b>{safe["periodo_fim"]}</b>.',
        f'Durante esse período, foram investidos <b>R$ {safe["investimento"]}</b> em anúncios.',
        f'O custo médio por dia foi de <b>R$ {safe["custo_dia"]}</b>.',
        f'A campanha alcançou <b>{safe["alcance"]}</b> pessoas e recebeu <b>{safe["visualizacoes"]}</b> visualizações.',
        f'Foram gerados <b>{safe["contatos"]}</b> contatos, com um custo médio de <b>R$ {safe["custo_contato"]}</b> por contato.',
    ]

    for paragraph in paragraphs:
        story.append(Paragraph(paragraph, body_style))

    story.append(Spacer(1, 12))

    footer = Table(
        [[Paragraph(
            '<font color="#64748B" size="8">Relatório gerado pelo painel interno da Oppi Tech.</font>',
            styles["Normal"],
        )]],
        colWidths=[170 * mm],
    )
    footer.setStyle(
        TableStyle([
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LINEABOVE", (0, 0), (-1, -1), 0.6, colors.HexColor("#E2E8F0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ])
    )
    story.append(footer)
    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
