import base64
import html
import io
import textwrap
import os
import re
from pathlib import Path
from datetime import date

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Dashboard - Oppi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------
# LOGIN CONFIG
# ---------------------------------------------------

APP_USER = "operacao"
APP_PASS = "100316"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "area_dashboard" not in st.session_state:
    st.session_state.area_dashboard = "Gestão de Tráfego"

if "traffic_form_reset_token" not in st.session_state:
    st.session_state.traffic_form_reset_token = 0

# ---------------------------------------------------
# PLANILHA
# ---------------------------------------------------

SHEET_ID = "16l701e6FdfkXYQrCxknZRidTonR3f80SQcUq3tGNw5I"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

MESES_ORDEM = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

LOGO_PATH = Path("logo-oppi.png")
if not LOGO_PATH.exists():
    LOGO_PATH = Path("LOGOS.png")

# ---------------------------------------------------
# CSS
# ---------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background-color: #f5f7fb;
    }

    .block-container {
        padding-top: 2.6rem;
        padding-bottom: 2rem;
        max-width: 1450px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .logo-wrap {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 0.25rem;
        margin-bottom: 10px;
        overflow: visible;
    }

    .logo-shell {
        width: 78px;
        height: 78px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .logo-round {
        width: 74px;
        height: 74px;
        border-radius: 50%;
        object-fit: cover;
        object-position: 58% center;
        display: block;
    }

    .top-title {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        margin-bottom: 6px;
        text-align: center;
    }

    .top-title .text {
        font-size: 42px;
        font-weight: 800;
        color: #16233b;
        line-height: 1.1;
    }

    .subtitle {
        color: #6b7280;
        font-size: 20px;
        margin-bottom: 26px;
        text-align: center;
    }

    .filter-card,
    .section-card,
    .table-card,
    .login-card {
        background: #ffffff;
        border: 1px solid #e7ebf3;
        border-radius: 24px;
        padding: 18px 18px 16px 18px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
    }

    .metric-card {
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border: 1px solid #e7ebf3;
        border-left: 7px solid #e11d48;
        border-radius: 24px;
        padding: 18px 20px 18px 22px;
        height: 172px;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        overflow: hidden;
    }

    .metric-card-green {
        border-left-color: #10b981 !important;
    }

    .metric-card-orange {
        border-left-color: #f59e0b !important;
    }

    .metric-card-blue {
        border-left-color: #3b82f6 !important;
    }

    .metric-title {
        font-size: 15px;
        color: #334155;
        font-weight: 800;
        margin-bottom: 8px;
        letter-spacing: 0.1px;
    }

    .metric-value {
        font-size: 34px;
        color: #0f172a;
        font-weight: 900;
        line-height: 1.05;
        margin: 6px 0 10px 0;
        letter-spacing: -0.8px;
        word-break: break-word;
    }

    .metric-sub {
        font-size: 13px;
        color: #64748b;
        line-height: 1.45;
    }

    .section-title {
        font-size: 18px;
        font-weight: 800;
        color: #16233b;
        margin-bottom: 14px;
    }

    .small-note {
        color: #6b7280;
        font-size: 13px;
        margin-top: -4px;
        margin-bottom: 12px;
    }

    .status-pill {
        display: inline-block;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        white-space: nowrap;
    }

    .status-pago {
        background: #dcfce7;
        color: #166534;
    }

    .status-apagar {
        background: #fee2e2;
        color: #991b1b;
    }

    .status-outro {
        background: #e5e7eb;
        color: #374151;
    }

    .status-pronto {
        background: #dcfce7;
        color: #166534;
    }

    .status-andamento {
        background: #fef3c7;
        color: #92400e;
    }

    .status-concluido {
        background: #dbeafe;
        color: #1d4ed8;
    }

    .status-pausado {
        background: #fee2e2;
        color: #991b1b;
    }

    .status-pendente {
        background: #dbeafe;
        color: #1d4ed8;
    }

    .row-card {
        background: #fbfcfe;
        border: 1px solid #e8edf5;
        border-radius: 18px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }

    .row-main {
        font-size: 17px;
        font-weight: 700;
        color: #16233b;
        margin-bottom: 6px;
    }

    .row-meta {
        color: #667085;
        font-size: 13px;
        line-height: 1.5;
    }

    .row-valor {
        font-size: 24px;
        font-weight: 800;
        color: #111827;
        margin-top: 4px;
    }

    div[data-testid="stSelectbox"] > div,
    div[data-testid="stTextInput"] > div,
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] > div > div input,
    div[data-testid="stMultiSelect"] > div {
        border-radius: 14px !important;
    }

    .stButton {
        width: 100%;
    }

    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        height: 44px !important;
        min-height: 44px !important;
        max-height: 44px !important;
        width: 100% !important;
        min-width: 100% !important;
        padding: 0 10px !important;
        margin: 0 !important;
        white-space: nowrap !important;
        line-height: 1 !important;
        text-align: center !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }

    .login-top-blank {
        height: 58px;
        background: #ffffff;
        border-radius: 24px;
        margin-bottom: 14px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.03);
    }

    .login-wrap {
        width: min(1200px, 96vw);
        margin: 0 auto;
    }

    .login-head {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 14px;
        margin-bottom: 6px;
    }

    .login-logo {
        width: 46px;
        height: 46px;
        border-radius: 50%;
        object-fit: cover;
        object-position: 58% center;
        display: block;
    }

    .login-title {
        text-align: center;
        font-size: 34px;
        font-weight: 800;
        color: #0f2d63;
        margin: 0;
    }

    .login-subtitle {
        text-align: center;
        font-size: 16px;
        color: #60708a;
        margin-bottom: 24px;
    }

    .login-card {
        padding: 18px 16px 16px 16px;
    }

    .login-button .stButton > button {
        background: #0b1730 !important;
        color: #ffffff !important;
        border: none !important;
        min-height: 52px !important;
        height: 52px !important;
        border-radius: 14px !important;
        box-shadow: none !important;
    }

    .login-footer {
        text-align: center;
        color: #a7b0c2;
        font-size: 14px;
        margin-top: 28px;
    }

    hr {
        margin-top: 0.7rem !important;
        margin-bottom: 0.7rem !important;
    }

    .area-switch-card {
        background: #ffffff;
        border: 1px solid #e7ebf3;
        border-radius: 20px;
        padding: 14px 18px 8px 18px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
        margin-bottom: 18px;
    }

    .traffic-card {
        background: #ffffff;
        border: 1px solid #e7ebf3;
        border-radius: 26px;
        padding: 28px 30px 30px 30px;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
        max-width: 1180px;
        margin: 0 auto;
    }

    .traffic-greeting {
        color: #16233b;
        font-size: 28px;
        font-weight: 900;
        line-height: 1.25;
        margin-bottom: 24px;
        text-align: center;
    }

    .traffic-divider {
        height: 1px;
        background: #e7ebf3;
        margin: 4px 0 24px 0;
    }

    .sentence-piece {
        color: #334155;
        font-size: 18px;
        font-weight: 600;
        line-height: 1.35;
        padding-top: 10px;
    }

    .traffic-space {
        height: 8px;
    }

    .traffic-card div[data-testid="stTextInput"] input {
        background: #fbfcff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        font-size: 17px !important;
        font-weight: 700 !important;
        height: 44px !important;
        padding: 0 12px !important;
    }

    .traffic-card div[data-testid="stTextInput"] input:focus {
        border-color: #0f2d63 !important;
        box-shadow: 0 0 0 2px rgba(15, 45, 99, 0.10) !important;
    }



    /* ---------------------------------------------------
       APRESENTAÇÃO EM POP-UP
       --------------------------------------------------- */

    div[role="dialog"] {
        border-radius: 24px !important;
        overflow: hidden !important;
    }

    div[role="dialog"] > div {
        background: #ffffff !important;
    }

    @media (max-width: 768px) {
        div[role="dialog"] {
            width: calc(100vw - 18px) !important;
            max-width: calc(100vw - 18px) !important;
            padding: 10px !important;
            border-radius: 18px !important;
        }

        div[role="dialog"] > div {
            padding-left: 4px !important;
            padding-right: 4px !important;
        }

        div[role="dialog"] div[data-testid="stButton"] button,
        div[role="dialog"] div[data-testid="stDownloadButton"] button {
            font-size: 13px !important;
            min-height: 42px !important;
            height: 42px !important;
            padding: 0 8px !important;
        }
    }

    .presentation-popup {
        background: #ffffff;
        border-radius: 22px;
        padding: 4px 8px 8px 8px;
        color: #16233b;
        font-family: Inter, system-ui, -apple-system, Segoe UI, Arial, sans-serif;
    }

    .presentation-popup-kicker {
        color: #C026D3;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .presentation-popup-title {
        color: #16233b;
        font-size: 30px;
        font-weight: 900;
        line-height: 1.12;
        margin-bottom: 12px;
    }

    .presentation-popup-line {
        width: 72px;
        height: 5px;
        border-radius: 999px;
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%);
        margin-bottom: 22px;
    }

    .presentation-popup-text {
        color: #334155;
        font-size: 18px;
        line-height: 1.75;
        font-weight: 500;
    }

    .presentation-popup-text p {
        margin: 0 0 14px 0;
    }

    .presentation-popup-text strong {
        color: #16233b;
        font-weight: 900;
    }

    .traffic-action-wrap {
        margin-top: 22px;
        padding-top: 18px;
        border-top: 1px solid #e7ebf3;
    }

    .traffic-action-wrap .stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;
        min-height: 50px !important;
        height: 50px !important;
        font-size: 16px !important;
        font-weight: 900 !important;
        box-shadow: 0 10px 22px rgba(124, 58, 237, 0.20) !important;
    }

    .traffic-action-wrap .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 26px rgba(124, 58, 237, 0.26) !important;
    }


    /* ---------------------------------------------------
       FORMULÁRIO DE GESTÃO DE TRÁFEGO
       --------------------------------------------------- */

    .traffic-intro {
        color: #64748b;
        font-size: 15px;
        line-height: 1.5;
        text-align: center;
        margin-top: -10px;
        margin-bottom: 24px;
    }

    .traffic-section {
        background: #fbfcff;
        border: 1px solid #e7ebf3;
        border-radius: 18px;
        padding: 16px 18px 14px 18px;
        margin-bottom: 14px;
    }

    .traffic-section-title {
        color: #16233b;
        font-size: 16px;
        font-weight: 900;
        margin-bottom: 3px;
    }

    .traffic-section-subtitle {
        color: #64748b;
        font-size: 12px;
        line-height: 1.35;
        margin-bottom: 10px;
    }

    .traffic-field-label {
        color: #334155;
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 6px;
    }

    .traffic-card div[data-testid="stDateInput"] input {
        background: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        height: 44px !important;
        padding: 0 12px !important;
    }

    .traffic-card div[data-testid="stDateInput"] input:focus {
        border-color: #7C3AED !important;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.10) !important;
    }

    .traffic-card div[data-testid="stTextInput"] input {
        background: #ffffff !important;
    }

    @media (max-width: 768px) {
        .traffic-card {
            padding: 20px 16px 22px 16px !important;
        }

        .traffic-greeting {
            font-size: 24px !important;
        }

        .traffic-section {
            padding: 14px 12px 12px 12px !important;
        }
    }


    /* ---------------------------------------------------
       MENU LATERAL RECOLHÍVEL
       --------------------------------------------------- */

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0F172A 0%, #050816 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    section[data-testid="stSidebar"] > div {
        background: transparent !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-top: 18px !important;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 4px 16px 4px;
        margin-bottom: 14px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    }

    .sidebar-brand-logo {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        object-fit: cover;
        object-position: 58% center;
        display: block;
        border: 1px solid rgba(255, 255, 255, 0.16);
        background: #ffffff;
    }

    .sidebar-brand-title {
        color: #F8FAFC;
        font-size: 15px;
        font-weight: 900;
        line-height: 1.05;
        letter-spacing: 0.3px;
    }

    .sidebar-brand-subtitle {
        color: #C026D3;
        font-size: 10px;
        font-weight: 800;
        line-height: 1.2;
        margin-top: 3px;
        letter-spacing: 0.6px;
        text-transform: uppercase;
    }

    .sidebar-nav-label {
        color: #A1A1AA;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: 1.6px;
        margin: 2px 0 10px 2px;
        text-transform: uppercase;
    }

    .sidebar-help {
        color: #A1A1AA;
        font-size: 11px;
        line-height: 1.45;
        padding: 10px 4px 0 4px;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
        gap: 8px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        background: rgba(255, 255, 255, 0.055) !important;
        border: 1px solid rgba(255, 255, 255, 0.11) !important;
        border-radius: 12px !important;
        padding: 11px 10px !important;
        margin: 0 !important;
        min-height: 42px !important;
        width: 100% !important;
        box-sizing: border-box !important;
        transition: all 0.16s ease !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background: rgba(255, 255, 255, 0.10) !important;
        border-color: rgba(192, 38, 211, 0.60) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
        background: linear-gradient(90deg, rgba(124, 58, 237, 0.24) 0%, rgba(192, 38, 211, 0.16) 100%) !important;
        border-color: #C026D3 !important;
        box-shadow: 0 0 0 1px rgba(192, 38, 211, 0.14) inset !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label p {
        color: #f8fafc !important;
        font-size: 14px !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p {
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
        transform: scale(0.90);
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 12px !important;
        font-weight: 900 !important;
        min-height: 42px !important;
        height: 42px !important;
        margin-top: 16px !important;
        box-shadow: 0 8px 18px rgba(124, 58, 237, 0.28) !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: linear-gradient(90deg, #6D28D9 0%, #A21CAF 100%) !important;
        color: #ffffff !important;
    }

    button[data-testid="stSidebarCollapseButton"],
    button[data-testid="collapsedControl"] {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border-radius: 9px !important;
        border: none !important;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.18) !important;
    }

    button[data-testid="stSidebarCollapseButton"] svg,
    button[data-testid="collapsedControl"] svg {
        fill: #ffffff !important;
        color: #ffffff !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) > div:first-child > div {
        background-color: #C026D3 !important;
        border-color: #C026D3 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover > div:first-child > div {
        border-color: #C026D3 !important;
    }

    @media (max-width: 768px) {
        .top-title .text {
            font-size: 32px;
        }

        .subtitle {
            font-size: 17px;
        }

        .traffic-card {
            padding: 20px 16px 22px 16px;
        }

        .traffic-greeting {
            font-size: 23px;
        }

        .sentence-piece {
            font-size: 16px;
            padding-top: 7px;
        }
    }

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def format_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def normalizar_valor(coluna):
    return (
        coluna.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )

def ordenar_meses(lista):
    ordem = {mes: i for i, mes in enumerate(MESES_ORDEM)}
    return sorted(lista, key=lambda x: ordem.get(x, 999))

def parse_data_publicacao(valor):
    if pd.isna(valor):
        return pd.NaT

    texto = str(valor).strip()
    if not texto:
        return pd.NaT

    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y"):
        try:
            return pd.to_datetime(texto, format=fmt, errors="raise")
        except Exception:
            pass

    return pd.to_datetime(texto, dayfirst=True, errors="coerce")

def status_arte_badge(status):
    s = str(status).strip().lower()
    if s == "pronto":
        return '<span class="status-pill status-pronto">Pronto</span>'
    if s == "em andamento":
        return '<span class="status-pill status-andamento">Em andamento</span>'
    if s == "pausado":
        return '<span class="status-pill status-pausado">Pausado</span>'
    if s == "pendente":
        return '<span class="status-pill status-pendente">Pendente</span>'
    if s in ("concluído", "concluido"):
        return '<span class="status-pill status-concluido">Concluído</span>'
    return f'<span class="status-pill status-outro">{status if str(status).strip() else "-"}</span>'

def metric_card(title, value, subtitle="", extra_class=""):
    st.markdown(
        f"""
        <div class="metric-card {extra_class}">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def render_logo(path: Path):
    if not path.exists():
        return
    mime = "image/png"
    if path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    img_base64 = base64.b64encode(path.read_bytes()).decode()
    st.markdown(
        f'''
        <div class="logo-wrap">
            <div class="logo-shell">
                <img class="logo-round" src="data:{mime};base64,{img_base64}">
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )

def login_logo_html(path: Path):
    if not path.exists():
        return ""
    mime = "image/png"
    if path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    img_base64 = base64.b64encode(path.read_bytes()).decode()
    return f'<img class="login-logo" src="data:{mime};base64,{img_base64}">'

def show_login():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="login-top-blank"></div>', unsafe_allow_html=True)

    logo_html = login_logo_html(LOGO_PATH)
    st.markdown(
        f'''
        <div class="login-head">
            {logo_html}
            <div class="login-title">Oppi</div>
        </div>
        ''',
        unsafe_allow_html=True
    )

    st.markdown('<div class="login-subtitle">Acesse o dashboard</div>', unsafe_allow_html=True)

    st.markdown('<div class="login-card">', unsafe_allow_html=True)

    usuario = st.text_input("Usuário", placeholder="Digite seu usuário", key="login_usuario")
    senha = st.text_input("Senha", placeholder="Digite sua senha", type="password", key="login_senha")

    st.markdown('<div class="login-button">', unsafe_allow_html=True)
    entrar = st.button("Entrar", key="btn_login")
    st.markdown('</div>', unsafe_allow_html=True)

    if entrar:
        if usuario == APP_USER and senha == APP_PASS:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="login-footer">Acesso restrito</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def get_google_creds_dict():
    try:
        return dict(st.secrets["google"])
    except Exception:
        pass

    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n")

    env_creds = {
        "type": os.getenv("GOOGLE_TYPE", "service_account"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID", ""),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", ""),
        "private_key": private_key,
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL", ""),
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": os.getenv(
            "GOOGLE_AUTH_PROVIDER_X509_CERT_URL",
            "https://www.googleapis.com/oauth2/v1/certs"
        ),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL", ""),
        "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN", "googleapis.com"),
    }

    campos_obrigatorios = [
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id"
    ]

    faltando = [campo for campo in campos_obrigatorios if not env_creds.get(campo)]
    if faltando:
        raise ValueError(
            "Credenciais Google ausentes no EasyPanel. "
            f"Campos faltando: {', '.join(faltando)}"
        )

    return env_creds

# ---------------------------------------------------
# TOPO E NAVEGAÇÃO
# ---------------------------------------------------

def sidebar_logo_html(path: Path):
    if not path.exists():
        return ""

    mime = "image/png"
    if path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"

    img_base64 = base64.b64encode(path.read_bytes()).decode()
    return f'<img class="sidebar-brand-logo" src="data:{mime};base64,{img_base64}">'


def render_sidebar_navigation():
    logo_html = sidebar_logo_html(LOGO_PATH)

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-brand">
                {logo_html}
                <div>
                    <div class="sidebar-brand-title">OPPI TECH</div>
                    <div class="sidebar-brand-subtitle">Painel interno</div>
                </div>
            </div>
            <div class="sidebar-nav-label">Navegação</div>
            """,
            unsafe_allow_html=True
        )

        area = st.radio(
            "Navegação",
            options=["Mídias", "Gestão de Tráfego"],
            format_func=lambda opcao: (
                "📱  Mídias" if opcao == "Mídias" else "📊  Gestão de Tráfego"
            ),
            key="area_dashboard",
            label_visibility="collapsed"
        )

        sair = st.button("SAIR DA CONTA", key="btn_logout_sidebar")
        if sair:
            st.session_state.logged_in = False
            st.rerun()

        st.markdown(
            '<div class="sidebar-help">Use a seta na lateral para recolher ou abrir o menu.</div>',
            unsafe_allow_html=True
        )

    return area


def render_dashboard_top(area):
    render_logo(LOGO_PATH)

    subtitulo = "Resultados dos anúncios" if area == "Gestão de Tráfego" else "Gestão de publicações e pagamentos"

    st.markdown(
        f"""
        <div class="top-title">
            <div class="text">Dashboard — Oppi</div>
        </div>
        <div class="subtitle">{subtitulo}</div>
        """,
        unsafe_allow_html=True
    )


def traffic_input(key, placeholder):
    reset_token = st.session_state.get("traffic_form_reset_token", 0)
    widget_key = f"{key}_{reset_token}"

    value = st.text_input(
        label=key,
        value="",
        placeholder=placeholder,
        key=widget_key,
        label_visibility="collapsed"
    )

    st.session_state[key] = value
    return value


def traffic_date_input(key):
    reset_token = st.session_state.get("traffic_form_reset_token", 0)
    widget_key = f"{key}_{reset_token}"

    value = st.date_input(
        label=key,
        value=None,
        format="DD/MM/YYYY",
        key=widget_key,
        label_visibility="collapsed"
    )

    st.session_state[key] = value
    return value


def format_date_br(value):
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    return ""


def get_traffic_form_values():
    return {
        "empresa": str(st.session_state.get("trafego_empresa", "")).strip(),
        "campanha": str(st.session_state.get("trafego_campanha", "")).strip(),
        "plataforma": str(st.session_state.get("trafego_plataforma", "")).strip(),
        "periodo_inicio": format_date_br(st.session_state.get("trafego_periodo_inicio")),
        "periodo_fim": format_date_br(st.session_state.get("trafego_periodo_fim")),
        "investimento": str(st.session_state.get("trafego_investimento", "")).strip(),
        "custo_dia": str(st.session_state.get("trafego_custo_dia", "")).strip(),
        "alcance": str(st.session_state.get("trafego_alcance", "")).strip(),
        "visualizacoes": str(st.session_state.get("trafego_visualizacoes", "")).strip(),
        "contatos": str(st.session_state.get("trafego_contatos", "")).strip(),
        "custo_contato": str(st.session_state.get("trafego_custo_contato", "")).strip(),
    }


TRAFFIC_FORM_KEYS = [
    "trafego_empresa",
    "trafego_campanha",
    "trafego_plataforma",
    "trafego_periodo_inicio",
    "trafego_periodo_fim",
    "trafego_investimento",
    "trafego_custo_dia",
    "trafego_alcance",
    "trafego_visualizacoes",
    "trafego_contatos",
    "trafego_custo_contato",
]


def traffic_form_missing_fields(values):
    labels = {
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
    return [labels[key] for key, value in values.items() if not value]


def clear_traffic_form():
    reset_token = st.session_state.get("traffic_form_reset_token", 0)

    for key in TRAFFIC_FORM_KEYS:
        st.session_state.pop(key, None)
        st.session_state.pop(f"{key}_{reset_token}", None)

    st.session_state["traffic_form_reset_token"] = reset_token + 1


def safe_filename(value):
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value).strip())
    cleaned = cleaned.strip("_")
    return cleaned or "campanha"


def build_traffic_pdf(values):
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
        brand_table = Table(
            [[logo_element, brand_text]],
            colWidths=[22 * mm, 125 * mm],
        )
    else:
        brand_table = Table(
            [[brand_text]],
            colWidths=[147 * mm],
        )

    brand_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(brand_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("Apresentação de resultados", title_style))

    accent = Table([[""]], colWidths=[32 * mm], rowHeights=[2.4 * mm])
    accent.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#A855F7")),
                ("BOX", (0, 0), (-1, -1), 0, colors.HexColor("#A855F7")),
            ]
        )
    )
    story.append(accent)
    story.append(Spacer(1, 14))

    paragraphs = [
        "Bom dia, estes são os resultados dos anúncios.",
        (
            f'A empresa <b>{safe["empresa"]}</b> realizou uma campanha '
            f'na plataforma <b>{safe["plataforma"]}</b>.'
        ),
        f'A campanha apresentada é <b>{safe["campanha"]}</b>.',
        (
            f'O período analisado foi de <b>{safe["periodo_inicio"]}</b> '
            f'até <b>{safe["periodo_fim"]}</b>.'
        ),
        (
            f'Durante esse período, foram investidos '
            f'<b>R$ {safe["investimento"]}</b> em anúncios.'
        ),
        (
            f'O custo médio por dia foi de '
            f'<b>R$ {safe["custo_dia"]}</b>.'
        ),
        (
            f'A campanha alcançou <b>{safe["alcance"]}</b> pessoas '
            f'e recebeu <b>{safe["visualizacoes"]}</b> visualizações.'
        ),
        (
            f'Foram gerados <b>{safe["contatos"]}</b> contatos, '
            f'com um custo médio de <b>R$ {safe["custo_contato"]}</b> por contato.'
        ),
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
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("LINEABOVE", (0, 0), (-1, -1), 0.6, colors.HexColor("#E2E8F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(footer)
    document.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


@st.dialog("Apresentação de resultados", width="large")
def show_traffic_presentation(values):
    safe = {key: html.escape(value) for key, value in values.items()}

    popup_html = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                padding: 5px 8px 2px 8px;
                background: #ffffff;
                color: #16233b;
                font-family: Inter, Arial, sans-serif;
            }}

            .popup {{
                width: 100%;
                background: #ffffff;
                padding: 0;
            }}

            .kicker {{
                color: #C026D3;
                font-size: 11px;
                font-weight: 900;
                letter-spacing: 1.5px;
                text-transform: uppercase;
                margin-bottom: 8px;
            }}

            .title {{
                color: #16233b;
                font-size: 27px;
                font-weight: 900;
                line-height: 1.08;
                margin-bottom: 10px;
            }}

            .line {{
                width: 68px;
                height: 5px;
                border-radius: 999px;
                background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%);
                margin-bottom: 17px;
            }}

            .text {{
                color: #334155;
                font-size: 17px;
                line-height: 1.52;
                font-weight: 500;
            }}

            .text p {{
                margin: 0 0 11px 0;
            }}

            .text strong {{
                color: #16233b;
                font-weight: 900;
            }}

            @media (max-width: 600px) {{
                body {{
                    padding: 2px 3px 0 3px;
                }}

                .kicker {{
                    font-size: 10px;
                    margin-bottom: 6px;
                }}

                .title {{
                    font-size: 21px;
                    line-height: 1.05;
                    margin-bottom: 8px;
                }}

                .line {{
                    width: 54px;
                    height: 4px;
                    margin-bottom: 13px;
                }}

                .text {{
                    font-size: 15px;
                    line-height: 1.42;
                }}

                .text p {{
                    margin-bottom: 9px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="popup">
            <div class="kicker">Oppi Tech</div>
            <div class="title">Apresentação de resultados</div>
            <div class="line"></div>

            <div class="text">
                <p>Bom dia, estes são os resultados dos anúncios.</p>
                <p>A empresa <strong>{safe["empresa"]}</strong> realizou uma campanha na plataforma <strong>{safe["plataforma"]}</strong>.</p>
                <p>A campanha apresentada é <strong>{safe["campanha"]}</strong>.</p>
                <p>O período analisado foi de <strong>{safe["periodo_inicio"]}</strong> até <strong>{safe["periodo_fim"]}</strong>.</p>
                <p>Durante esse período, foram investidos <strong>R$ {safe["investimento"]}</strong> em anúncios.</p>
                <p>O custo médio por dia foi de <strong>R$ {safe["custo_dia"]}</strong>.</p>
                <p>A campanha alcançou <strong>{safe["alcance"]}</strong> pessoas e recebeu <strong>{safe["visualizacoes"]}</strong> visualizações.</p>
                <p>Foram gerados <strong>{safe["contatos"]}</strong> contatos, com um custo médio de <strong>R$ {safe["custo_contato"]}</strong> por contato.</p>
            </div>
        </div>
    </body>
    </html>
    """

    components.html(
        popup_html,
        height=650,
        scrolling=True
    )

    pdf_bytes = build_traffic_pdf(values)
    file_name = f"resultados_{safe_filename(values['empresa'])}_{safe_filename(values['campanha'])}.pdf"

    st.download_button(
        "Baixar PDF com a logo da Oppi",
        data=pdf_bytes,
        file_name=file_name,
        mime="application/pdf",
        use_container_width=True,
        key="btn_baixar_pdf_apresentacao",
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Voltar para editar", use_container_width=True, key="btn_voltar_editar"):
            st.rerun()

    with c2:
        if st.button("Nova apresentação", use_container_width=True, key="btn_nova_apresentacao"):
            clear_traffic_form()
            st.session_state["abrir_apresentacao"] = False
            st.rerun()


def render_gestao_trafego():
    st.markdown('<div class="traffic-card">', unsafe_allow_html=True)

    st.markdown(
        '<div class="traffic-greeting">Apresentação de resultados</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="traffic-intro">Preencha os dados da campanha e abra a apresentação para gerar uma tela pronta para print.</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="traffic-divider"></div>', unsafe_allow_html=True)

    # ---------------------------------------------------
    # IDENTIFICAÇÃO
    # ---------------------------------------------------
    st.markdown(
        """
        <div class="traffic-section">
            <div class="traffic-section-title">📌 Identificação da campanha</div>
            <div class="traffic-section-subtitle">Informe para qual cliente e campanha os resultados serão apresentados.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    i1, i2, i3 = st.columns(3, gap="medium")

    with i1:
        st.markdown('<div class="traffic-field-label">Empresa</div>', unsafe_allow_html=True)
        traffic_input("trafego_empresa", "Nome da empresa")

    with i2:
        st.markdown('<div class="traffic-field-label">Nome da campanha</div>', unsafe_allow_html=True)
        traffic_input("trafego_campanha", "Ex.: Campanha Junho")

    with i3:
        st.markdown('<div class="traffic-field-label">Plataforma</div>', unsafe_allow_html=True)
        traffic_input("trafego_plataforma", "Ex.: Meta Ads")

    # ---------------------------------------------------
    # PERÍODO
    # ---------------------------------------------------
    st.markdown(
        """
        <div class="traffic-section">
            <div class="traffic-section-title">📅 Período analisado</div>
            <div class="traffic-section-subtitle">Clique nos campos abaixo para selecionar as datas pelo calendário.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    p1, p2 = st.columns(2, gap="medium")

    with p1:
        st.markdown('<div class="traffic-field-label">Data inicial</div>', unsafe_allow_html=True)
        traffic_date_input("trafego_periodo_inicio")

    with p2:
        st.markdown('<div class="traffic-field-label">Data final</div>', unsafe_allow_html=True)
        traffic_date_input("trafego_periodo_fim")

    # ---------------------------------------------------
    # INVESTIMENTO
    # ---------------------------------------------------
    st.markdown(
        """
        <div class="traffic-section">
            <div class="traffic-section-title">💰 Investimento</div>
            <div class="traffic-section-subtitle">Preencha os valores da campanha no período selecionado.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    v1, v2 = st.columns(2, gap="medium")

    with v1:
        st.markdown('<div class="traffic-field-label">Valor investido em anúncios</div>', unsafe_allow_html=True)
        traffic_input("trafego_investimento", "Ex.: 2.500,00")

    with v2:
        st.markdown('<div class="traffic-field-label">Custo médio por dia</div>', unsafe_allow_html=True)
        traffic_input("trafego_custo_dia", "Ex.: 100,00")

    # ---------------------------------------------------
    # RESULTADOS
    # ---------------------------------------------------
    st.markdown(
        """
        <div class="traffic-section">
            <div class="traffic-section-title">📊 Resultados dos anúncios</div>
            <div class="traffic-section-subtitle">Informe os principais indicadores entregues pela campanha.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    r1, r2, r3, r4 = st.columns(4, gap="medium")

    with r1:
        st.markdown('<div class="traffic-field-label">Pessoas alcançadas</div>', unsafe_allow_html=True)
        traffic_input("trafego_alcance", "Ex.: 15.000")

    with r2:
        st.markdown('<div class="traffic-field-label">Visualizações</div>', unsafe_allow_html=True)
        traffic_input("trafego_visualizacoes", "Ex.: 25.000")

    with r3:
        st.markdown('<div class="traffic-field-label">Contatos gerados</div>', unsafe_allow_html=True)
        traffic_input("trafego_contatos", "Ex.: 120")

    with r4:
        st.markdown('<div class="traffic-field-label">Custo médio por contato</div>', unsafe_allow_html=True)
        traffic_input("trafego_custo_contato", "Ex.: 12,50")

    st.markdown('<div class="traffic-action-wrap">', unsafe_allow_html=True)

    abrir_apresentacao = st.button(
        "Abrir apresentação",
        use_container_width=True,
        key="btn_abrir_apresentacao"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    if abrir_apresentacao:
        values = get_traffic_form_values()
        missing = traffic_form_missing_fields(values)

        inicio = st.session_state.get("trafego_periodo_inicio")
        fim = st.session_state.get("trafego_periodo_fim")

        if missing:
            st.warning(
                "Preencha todos os campos antes de abrir a apresentação. "
                f"Faltando: {', '.join(missing)}."
            )
        elif isinstance(inicio, date) and isinstance(fim, date) and fim < inicio:
            st.warning("A data final não pode ser anterior à data inicial.")
        else:
            show_traffic_presentation(values)

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------

if not st.session_state.logged_in:
    show_login()
    st.stop()

area_dashboard = render_sidebar_navigation()
render_dashboard_top(area_dashboard)

if area_dashboard == "Gestão de Tráfego":
    render_gestao_trafego()
    st.stop()

# ---------------------------------------------------
# CONEXÃO GOOGLE
# ---------------------------------------------------

@st.cache_resource
def connect_sheet():
    try:
        creds_dict = get_google_creds_dict()
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        worksheet = sheet.get_worksheet(0)
        return worksheet
    except Exception as e:
        st.error("❌ Erro ao conectar com Google Sheets")
        st.write("Verifique:")
        st.write("- Se o SHEET_ID está correto")
        st.write("- Se a planilha foi compartilhada com a conta de serviço")
        st.write("- Se a Google Sheets API e a Google Drive API estão ativadas")
        st.write("- Se as credenciais foram cadastradas no EasyPanel > Ambiente")
        st.write(f"Erro técnico: {e}")
        st.stop()

# ---------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------

@st.cache_data(ttl=60)
def load_data():
    worksheet = connect_sheet()
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

df = load_data()

# ---------------------------------------------------
# TRATAMENTO
# ---------------------------------------------------

for col in ["Mês", "Semana", "Empresa", "Tema", "Status Pagamento", "Status da arte", "Tipo de arte", "Data Publicação"]:
    if col not in df.columns:
        df[col] = ""

df["Data Publicação Raw"] = df["Data Publicação"].astype(str).str.strip()

if "Valor" in df.columns:
    df["Valor"] = pd.to_numeric(normalizar_valor(df["Valor"]), errors="coerce").fillna(0)
else:
    df["Valor"] = 0.0

df["Data Publicação"] = df["Data Publicação Raw"].apply(parse_data_publicacao)

if "Mês" in df.columns:
    df["Mês"] = df["Mês"].astype(str).str.strip()
    mascara_mes_vazio = df["Mês"].eq("") & df["Data Publicação"].notna()
    if mascara_mes_vazio.any():
        mapa_meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        df.loc[mascara_mes_vazio, "Mês"] = df.loc[mascara_mes_vazio, "Data Publicação"].dt.month.map(mapa_meses)

# ---------------------------------------------------
# MÍDIAS
# ---------------------------------------------------

st.markdown(
    '<div class="section-title">📱 Gestão de publicações e pagamentos</div>',
    unsafe_allow_html=True
)

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

st.markdown('<div class="filter-card">', unsafe_allow_html=True)

f1, f2, f3, f4 = st.columns(4)

with f1:
    meses_disponiveis = [x for x in df["Mês"].dropna().astype(str).unique().tolist() if x.strip()]
    mes = st.selectbox("Mês", ["Todos"] + ordenar_meses(meses_disponiveis))

with f2:
    semanas_disponiveis = [x for x in df["Semana"].dropna().astype(str).unique().tolist() if str(x).strip()]
    semana = st.selectbox("Semana", ["Todas"] + sorted(semanas_disponiveis))

with f3:
    empresas_disponiveis = [x for x in df["Empresa"].dropna().astype(str).unique().tolist() if str(x).strip()]
    empresa = st.selectbox("Empresa", ["Todas"] + sorted(empresas_disponiveis))

with f4:
    datas_disponiveis_str = [
        x for x in df["Data Publicação Raw"].dropna().astype(str).unique().tolist()
        if str(x).strip() and str(x).strip().lower() != "nan"
    ]

    def chave_data(txt):
        dt = parse_data_publicacao(txt)
        return dt if pd.notna(dt) else pd.Timestamp.max

    datas_disponiveis_str = sorted(set(datas_disponiveis_str), key=chave_data)

    datas_selecionadas_str = st.multiselect(
        "Datas publicação",
        options=datas_disponiveis_str,
        default=[],
        placeholder="Selecione uma ou mais datas"
    )

st.markdown('</div>', unsafe_allow_html=True)

df_filtrado = df.copy()

if mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Mês"].astype(str) == mes]

if semana != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Semana"].astype(str) == semana]

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"].astype(str) == empresa]

if datas_selecionadas_str:
    df_filtrado = df_filtrado[
        df_filtrado["Data Publicação Raw"].isin(datas_selecionadas_str)
    ]

# ---------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------

status_pagamento_normalizado = df_filtrado["Status Pagamento"].astype(str).str.strip().str.lower()
status_arte_normalizado = df_filtrado["Status da arte"].astype(str).str.strip().str.lower()

pagos = df_filtrado[status_pagamento_normalizado == "pago"]
a_pagar = df_filtrado[status_pagamento_normalizado == "a pagar"]

linhas_com_conteudo = (
    df_filtrado["Empresa"].astype(str).str.strip().ne("")
    | df_filtrado["Tema"].astype(str).str.strip().ne("")
    | df_filtrado["Tipo de arte"].astype(str).str.strip().ne("")
    | df_filtrado["Valor"].fillna(0).gt(0)
    | df_filtrado["Data Publicação"].notna()
)

postagens_feitas = int(((status_arte_normalizado == "pronto") & linhas_com_conteudo).sum())
postagens_a_fazer = int(((status_arte_normalizado != "pronto") & linhas_com_conteudo).sum())
em_andamento_qtd = int(((status_arte_normalizado == "em andamento") & linhas_com_conteudo).sum())
concluido_qtd = int((((status_arte_normalizado == "concluído") | (status_arte_normalizado == "concluido")) & linhas_com_conteudo).sum())

total_posts = len(df_filtrado)
total_valor = float(df_filtrado["Valor"].sum())
valor_pago = float(pagos["Valor"].sum())
valor_pendente = float(a_pagar["Valor"].sum())

m1, m2, m3, m4, m5, m6 = st.columns(6)

with m1:
    metric_card("Posts", f"{total_posts}", "total de registros filtrados")
with m2:
    metric_card("Valor total", format_brl(total_valor), "soma de todas as mídias")
with m3:
    metric_card("Pagos", f"{len(pagos)}", "status pagamento = Pago")
with m4:
    metric_card("A pagar", f"{len(a_pagar)}", "status pagamento = A pagar")
with m5:
    metric_card("Valor pago", format_brl(valor_pago), "somatório dos pagos")
with m6:
    metric_card("Valor pendente", format_brl(valor_pendente), "somatório em aberto")

st.markdown("<br>", unsafe_allow_html=True)

pf1, pf2, pf3, pf4 = st.columns(4)

with pf1:
    metric_card("Postagens feitas", f"{postagens_feitas}", "status da arte = Pronto", "metric-card-green")
with pf2:
    metric_card("Postagens a fazer", f"{postagens_a_fazer}", "status diferente de Pronto", "metric-card-orange")
with pf3:
    metric_card("Em andamento", f"{em_andamento_qtd}", "status da arte = Em andamento", "metric-card-orange")
with pf4:
    metric_card("Concluído", f"{concluido_qtd}", "status da arte = Concluído", "metric-card-blue")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------
# GRÁFICOS
# ---------------------------------------------------

g1, g2 = st.columns(2)

with g1:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 Publicações por empresa</div>', unsafe_allow_html=True)

    graf_empresa = (
        df_filtrado.groupby("Empresa", dropna=False)
        .size()
        .reset_index(name="Total")
    )

    if not graf_empresa.empty:
        fig_empresa = px.bar(graf_empresa, x="Empresa", y="Total", text="Total")
        fig_empresa.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=380,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis_title="",
            yaxis_title="Quantidade"
        )
        fig_empresa.update_traces(textposition="outside")
        st.plotly_chart(fig_empresa, use_container_width=True)
    else:
        st.info("Sem dados para esse filtro.")
    st.markdown('</div>', unsafe_allow_html=True)

with g2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💳 Valor por status pagamento</div>', unsafe_allow_html=True)

    graf_status = (
        df_filtrado.groupby("Status Pagamento", dropna=False)["Valor"]
        .sum()
        .reset_index()
    )

    graf_status["Status Pagamento"] = graf_status["Status Pagamento"].astype(str).str.strip()
    graf_status = graf_status[
        (graf_status["Status Pagamento"] != "") &
        (graf_status["Valor"] > 0)
    ]

    if not graf_status.empty and graf_status["Valor"].sum() > 0:
        fig_status = px.pie(
            graf_status,
            values="Valor",
            names="Status Pagamento",
            hole=0.58
        )

        fig_status.update_traces(
            texttemplate="R$ %{value:,.2f}",
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>Valor: R$ %{value:,.2f}<extra></extra>"
        )

        fig_status.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            height=380,
            paper_bgcolor="white",
            showlegend=True
        )

        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("Sem valores para esse filtro.")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------
# ATUALIZAR STATUS DA ARTE
# ---------------------------------------------------

st.markdown('<div class="table-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">✏️ Atualizar status da arte</div>', unsafe_allow_html=True)
st.markdown('<div class="small-note">Atualize a coluna "Status da arte" diretamente pela interface abaixo.</div>', unsafe_allow_html=True)

busca = st.text_input("Buscar por empresa ou tema", placeholder="Ex.: Faiser, mulheres, internet...")

df_status = df_filtrado.copy()

if busca.strip():
    termo = busca.strip().lower()
    df_status = df_status[
        df_status["Empresa"].astype(str).str.lower().str.contains(termo, na=False)
        | df_status["Tema"].astype(str).str.lower().str.contains(termo, na=False)
    ]

worksheet = connect_sheet()

for index, row in df_status.iterrows():
    empresa_txt = str(row.get("Empresa", "")).strip() or "-"
    semana_txt = str(row.get("Semana", "")).strip() or "-"
    tema_txt = str(row.get("Tema", "")).strip() or "-"
    mes_txt = str(row.get("Mês", "")).strip() or "-"
    tipo_txt = str(row.get("Tipo de arte", "")).strip() or "-"
    status_arte_txt = str(row.get("Status da arte", "")).strip() or "-"
    valor_num = float(row.get("Valor", 0) or 0)

    if pd.notnull(row.get("Data Publicação")):
        data_txt = row["Data Publicação"].strftime("%d/%m/%Y")
    else:
        data_txt = str(row.get("Data Publicação Raw", "")).strip() or "-"

    st.markdown('<div class="row-card">', unsafe_allow_html=True)

    left, mid, right = st.columns([3.2, 1.2, 4.6])

    with left:
        st.markdown(f'<div class="row-main">{tema_txt}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="row-meta"><b>Empresa:</b> {empresa_txt} &nbsp;&nbsp; <b>Mês:</b> {mes_txt} &nbsp;&nbsp; <b>Semana:</b> {semana_txt}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="row-meta"><b>Tipo de arte:</b> {tipo_txt} &nbsp;&nbsp; <b>Data:</b> {data_txt}</div>',
            unsafe_allow_html=True
        )

        novo_tema = st.text_input(
            "Editar nome da atividade",
            value=tema_txt,
            key=f"tema_input_{index}"
        )

        if st.button("Salvar nome", key=f"salvar_tema_{index}"):
            worksheet.update_cell(index + 2, 4, novo_tema)
            st.cache_data.clear()
            st.rerun()

    with mid:
        st.markdown(f'<div class="row-meta"><b>Valor</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="row-valor">{format_brl(valor_num)}</div>', unsafe_allow_html=True)

    with right:
        info_col, buttons_col = st.columns([1.0, 4.0])

        with info_col:
            st.markdown("**Status atual**")
            st.markdown(status_arte_badge(status_arte_txt), unsafe_allow_html=True)

        with buttons_col:
            b1, b2, b3, b4 = st.columns([1.05, 1.55, 1.05, 1.15], gap="small")

            if b1.button("Pronto", key=f"pronto_{index}"):
                worksheet.update_cell(index + 2, 8, "Pronto")
                st.cache_data.clear()
                st.rerun()

            if b2.button("Em andamento", key=f"andamento_{index}"):
                worksheet.update_cell(index + 2, 8, "Em andamento")
                st.cache_data.clear()
                st.rerun()

            if b3.button("Pausado", key=f"pausado_{index}"):
                worksheet.update_cell(index + 2, 8, "Pausado")
                st.cache_data.clear()
                st.rerun()

            if b4.button("Pendente", key=f"pendente_{index}"):
                worksheet.update_cell(index + 2, 8, "Pendente")
                st.cache_data.clear()
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

if df_status.empty:
    st.info("Nenhum registro encontrado com esse filtro.")

st.markdown('</div>', unsafe_allow_html=True)
