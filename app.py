import base64
import calendar
import concurrent.futures
import html
import io
import textwrap
import os
import re
import time
from pathlib import Path
from datetime import date, timedelta

import gspread
import gspread.exceptions
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

OPERACAO_PASSWORD = "100316*"

APP_USERS = {
    "operacao": {"password": OPERACAO_PASSWORD, "role": "geral"},
    "geral": {"password": os.getenv("APP_PASS_GERAL", "100316"), "role": "geral"},
    "gestor": {"password": os.getenv("APP_PASS_GESTOR", "gestor@oppi"), "role": "gestor"},
    "designer": {"password": os.getenv("APP_PASS_DESIGNER", "designer@oppi"), "role": "designer"},
}
ROLE_LABELS = {
    "geral": "Geral",
    "gestor": "Gestor",
    "designer": "Designer",
}
NAV_MIDIAS = ["Empresas", "Publicações", "Nova Arte"]
NAV_ACESSOS = "Acessos"
ROLE_NAV_ACCESS = {
    "geral": ["Empresas", "Publicações", "Nova Arte", "Gestão de Tráfego", NAV_ACESSOS],
    "gestor": ["Gestão de Tráfego", NAV_ACESSOS],
    "designer": NAV_MIDIAS,
}
NAV_LABELS = {
    "Empresas": "🏢  Empresas",
    "Publicações": "📄  Publicações",
    "Nova Arte": "🎨  Nova Arte",
    "Gestão de Tráfego": "📊  Gestão de Tráfego",
    NAV_ACESSOS: "🔐  Acessos",
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_role" not in st.session_state:
    st.session_state.user_role = "geral"

if "area_dashboard" not in st.session_state:
    st.session_state.area_dashboard = "Publicações"


def ensure_auth_session():
    if not st.session_state.get("logged_in"):
        return

    role = st.session_state.get("user_role") or "geral"
    st.session_state.user_role = role

    if not st.session_state.get("user_permissions"):
        st.session_state.user_permissions = ROLE_NAV_ACCESS.get(
            role, ROLE_NAV_ACCESS["geral"]
        )

    if not st.session_state.get("logged_username"):
        st.session_state.logged_username = role


@st.fragment(run_every=timedelta(seconds=25))
def manter_conexao_viva():
    st.session_state["_sessao_keepalive"] = time.time()


NAV_OPTIONS = ["Empresas", "Publicações", "Nova Arte", "Gestão de Tráfego", NAV_ACESSOS]
TIPO_ARTE_OPTIONS = ["Vídeo", "Arte", "Carrossel"]
STATUS_ARTE_FORM_OPTIONS = ["Andamento", "Finalizado", "Pausado", "Pendente"]
SEMANA_OPTIONS = [
    "Primeira Semana",
    "Segunda Semana",
    "Terceira Semana",
    "Quarta Semana",
    "Quinta Semana",
]
SERVICO_OPTIONS = [
    "Post único",
    "Carrossel",
    "Vídeo",
    "Stories",
    "Reels",
    "Arte estática",
    "Banner",
    "Thumb",
]
STATUS_ARTE_SHEET_MAP = {
    "Andamento": "Em andamento",
    "Finalizado": "Pronto",
    "Pausado": "Pausado",
    "Pendente": "Pendente",
}
STATUS_PAGAMENTO_FORM_OPTIONS = ["Pago", "A Pagar"]
STATUS_PAGAMENTO_SHEET_MAP = {
    "Pago": "Pago",
    "A Pagar": "A pagar",
}
RECORRENCIA_OPTIONS = ["Não", "Sim"]
DIAS_SEMANA_RECORRENCIA = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]
DIA_SEMANA_FORM_OPTIONS = ["Seg", "Ter", "Qua", "Qui", "Sex"]
DIA_SEMANA_FORM_WEEKDAY = {
    "Seg": 0,
    "Ter": 1,
    "Qua": 2,
    "Qui": 3,
    "Sex": 4,
}
DIA_SEMANA_FORM_NOME = {
    "Seg": "segunda-feira",
    "Ter": "terça-feira",
    "Qua": "quarta-feira",
    "Qui": "quinta-feira",
    "Sex": "sexta-feira",
}
STATUS_ARTE_EDIT_OPTIONS = ["Pronto", "Em andamento", "Pausado", "Pendente"]
APP_UI_VERSION = "2026-07-13-colunas-planilha"

if "traffic_form_reset_token" not in st.session_state:
    st.session_state.traffic_form_reset_token = 0

SIDEBAR_TOGGLE_SCRIPT = """
<script>
(function () {
    const win = window.parent;
    const doc = win.document;
    const storage = win.localStorage;
    const KEY = "oppi_sidebar_collapsed";

    function setCollapsed(collapsed) {
        storage.setItem(KEY, collapsed ? "1" : "0");
        doc.querySelector(".stApp")?.classList.toggle("sidebar-collapsed", collapsed);
    }

    if (!win.__oppiSidebarToggleBound) {
        win.__oppiSidebarToggleBound = true;
        doc.addEventListener("click", function (event) {
            if (event.target.closest(".oppi-sidebar-hide")) {
                event.preventDefault();
                event.stopPropagation();
                setCollapsed(true);
                return;
            }
            if (event.target.closest(".oppi-sidebar-show")) {
                event.preventDefault();
                event.stopPropagation();
                setCollapsed(false);
            }
        }, true);
    }

    setCollapsed(storage.getItem(KEY) === "1");
})();
</script>
"""

# Garante migração para o menu lateral simplificado.
if st.session_state.get("nav_layout_version") != "flat_v3":
    area_atual = st.session_state.get("area_dashboard", "Publicações")
    submenu_antigo = st.session_state.get("midias_submenu", "Publicações")

    if area_atual == "Gestão de Tráfego":
        st.session_state.area_dashboard = "Gestão de Tráfego"
    elif area_atual in NAV_OPTIONS:
        st.session_state.area_dashboard = area_atual
    elif submenu_antigo in NAV_OPTIONS:
        st.session_state.area_dashboard = submenu_antigo
    elif area_atual == "Mídias":
        if submenu_antigo == "Nova Arte":
            st.session_state.area_dashboard = "Nova Arte"
        elif submenu_antigo == "Empresas":
            st.session_state.area_dashboard = "Empresas"
        else:
            st.session_state.area_dashboard = "Publicações"
    else:
        st.session_state.area_dashboard = "Publicações"

    st.session_state.nav_layout_version = "flat_v3"

# ---------------------------------------------------
# PLANILHA
# ---------------------------------------------------

SHEET_ID = "16l701e6FdfkXYQrCxknZRidTonR3f80SQcUq3tGNw5I"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

USERS_SHEET_NAME = os.getenv("USERS_SHEET_NAME", "Acessos")
USERS_HEADERS = [
    "Usuário",
    "Senha",
    "Perfil",
    "Ativo",
    "Empresas",
    "Publicações",
    "Nova Arte",
    "Gestão de Tráfego",
    NAV_ACESSOS,
]
PERMISSION_OPTIONS = ["Sim", "Não"]
ROLE_FORM_OPTIONS = ["geral", "gestor", "designer"]
CONTENT_AREAS = ["Empresas", "Publicações", "Nova Arte", "Gestão de Tráfego", NAV_ACESSOS]

MESES_ORDEM = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

LOGO_PATH = Path("logo-oppi.png")
if not LOGO_PATH.exists():
    LOGO_PATH = Path("LOGOS.png")

EMPRESAS_LOGOS_DIR = Path("logos-empresas")
EMPRESA_LOGO_MAP = {
    "skoob": EMPRESAS_LOGOS_DIR / "logo-skoob.png",
    "skoobpet": EMPRESAS_LOGOS_DIR / "logo-skoob.png",
    "casa das essencias": EMPRESAS_LOGOS_DIR / "logo-casa-essencias.png",
    "faiser": EMPRESAS_LOGOS_DIR / "logo-faiser.png",
    "faiser telecomunicacoes": EMPRESAS_LOGOS_DIR / "logo-faiser.png",
    "oppi tech": LOGO_PATH,
    "oppi": LOGO_PATH,
}

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

    .filter-card .form-field-label,
    .form-field-label {
        color: #0f172a !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        margin: 0 0 6px 2px !important;
    }

    .stApp:has(#empresas-page) section.main [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(#publicacoes-page) section.main [data-testid="stVerticalBlockBorderWrapper"],
    .stApp:has(#acessos-page) section.main [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #e7ebf3 !important;
        border-radius: 24px !important;
        padding: 18px 18px 16px 18px !important;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04) !important;
    }

    .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #e7ebf3 !important;
        border-radius: 26px !important;
        padding: 28px 30px 30px 30px !important;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06) !important;
        max-width: 1180px !important;
        margin: 0 auto !important;
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

    .filter-card [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    .stApp:has(#nova-arte-page) section.main label[data-testid="stWidgetLabel"] p,
    .stApp:has(#nova-arte-page) section.main div[data-testid="stTextInput"] label p,
    .stApp:has(#nova-arte-page) section.main div[data-testid="stSelectbox"] label p,
    .stApp:has(#publicacoes-filtros) section.main label[data-testid="stWidgetLabel"] p,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stTextInput"] label p,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stSelectbox"] label p,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stMultiSelect"] label p,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stDateInput"] label p {
        color: #0f172a !important;
        font-size: 14px !important;
        font-weight: 700 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stTextInput"] input,
    .stApp:has(#nova-arte-page) section.main div[data-testid="stTextInput"] [data-baseweb="input"],
    .stApp:has(#nova-arte-page) section.main div[data-testid="stTextInput"] [data-baseweb="input"] > div,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stTextInput"] input,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stTextInput"] [data-baseweb="input"],
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stTextInput"] [data-baseweb="input"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stTextInput"] input::placeholder,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stTextInput"] input::placeholder {
        color: #94a3b8 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        min-height: 44px !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
    .stApp:has(#nova-arte-page) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] input,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] input,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stMultiSelect"] div[data-baseweb="select"] span,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stMultiSelect"] div[data-baseweb="select"] input {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stSelectbox"] svg,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stDateInput"] input {
        background: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        min-height: 44px !important;
        padding: 0 12px !important;
    }

    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stDateInput"] input:focus {
        border-color: #7C3AED !important;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.10) !important;
    }

    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stSelectbox"] svg,
    .stApp:has(#publicacoes-filtros) section.main div[data-testid="stMultiSelect"] svg {
        fill: #0f172a !important;
    }

    .stApp:has(#acessos-page) section.main div[data-testid="stTextInput"] input,
    .stApp:has(#acessos-page) section.main div[data-testid="stTextInput"] [data-baseweb="input"],
    .stApp:has(#acessos-page) section.main div[data-testid="stTextInput"] [data-baseweb="input"] > div,
    .stApp:has(#acessos-page) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        min-height: 44px !important;
    }

    .stApp:has(#acessos-page) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] span,
    .stApp:has(#acessos-page) section.main div[data-testid="stSelectbox"] div[data-baseweb="select"] input {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    .stApp:has(#acessos-page) section.main label[data-testid="stWidgetLabel"] p,
    .stApp:has(#acessos-page) section.main div[data-testid="stSelectbox"] label p,
    .stApp:has(#acessos-page) section.main div[data-testid="stRadio"] label p {
        color: #0f172a !important;
        font-size: 14px !important;
        font-weight: 700 !important;
    }

    .stApp:has(#acessos-page) section.main .stButton > button {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #d9e0eb !important;
    }

    .stApp:has(#acessos-page) section.main .stButton > button:hover {
        background: #f8fafc !important;
        border-color: #cbd5e1 !important;
    }

    .stApp:has(#acessos-page) [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #e7ebf3 !important;
        border-radius: 18px !important;
        padding: 16px !important;
    }

    .stApp:has(#acessos-page) section.main div[data-testid="stMarkdownContainer"] p,
    .stApp:has(#acessos-page) section.main div[data-testid="stMarkdownContainer"] strong {
        color: #0f172a !important;
    }

    .stApp:has(#acessos-page) section.main .acessos-block-title {
        color: #0f172a !important;
        font-size: 15px !important;
        font-weight: 800 !important;
        margin: 0 0 12px 2px !important;
    }

    .stApp:has(#acessos-page) section.main [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    .stApp:has(#acessos-page) section.main [data-testid="stFormSubmitButton"] > button p {
        color: #ffffff !important;
    }

    .acessos-user-list {
        background: #f8fafc;
        border: 1px solid #e7ebf3;
        border-radius: 14px;
        padding: 8px 10px;
        margin-bottom: 12px;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stFormSubmitButton"] > button,
    .stApp:has(#nova-arte-page) section.main [data-testid="stFormSubmitButton"] > button p {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    .stApp:has(#nova-arte-page) [data-testid="stVerticalBlockBorderWrapper"] {
        background: #ffffff !important;
        border: 1px solid #e7ebf3 !important;
        border-radius: 24px !important;
        padding: 18px !important;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04) !important;
    }

    .form-field-label {
        color: #0f172a !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        margin: 0 0 6px 2px !important;
        line-height: 1.2 !important;
    }

    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_empresa_opcao [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_mes [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_recorrencia [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_padrao_recorrencia [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_padrao_recorrencia_Janeiro [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main [class*="st-key-nova_arte_padrao_recorrencia_"] [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_semana [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_tipo [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_status [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_status_pagamento [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_servico [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_empresa_outra [data-baseweb="input"],
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_empresa_outra [data-baseweb="input"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_valor [data-baseweb="input"],
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_valor [data-baseweb="input"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_dia [data-baseweb="select"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_dia [data-baseweb="input"],
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_dia [data-baseweb="input"] > div,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_tema [data-baseweb="input"],
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_tema [data-baseweb="input"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #d9e0eb !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        min-height: 44px !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stSelectbox"] div[data-baseweb="select"] span,
    .stApp:has(#nova-arte-page) section.main [data-testid="stSelectbox"] div[data-baseweb="select"] input {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;
        font-size: 15px !important;
        font-weight: 600 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stRadio"] label p {
        color: #0f172a !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
        background-color: #ffffff !important;
        border-color: #d9e0eb !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stFormSubmitButton"] > button,
    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_cadastrar .stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        margin-top: 8px !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stHorizontalBlock"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        gap: 0.75rem !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stVerticalBlock"] > div {
        margin-bottom: 0 !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stVerticalBlockBorderWrapper"] > div {
        gap: 0.5rem !important;
    }

    .stApp:has(#nova-arte-page) section.main .st-key-nova_arte_dia:has(input[disabled]) {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    .stApp:has(#nova-arte-page) section.main .nova-arte-hide-dia {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stForm"] {
        margin-top: 0 !important;
        padding-top: 0 !important;
        border: none !important;
    }

    .stApp:has(#nova-arte-page) section.main [data-testid="stForm"] > div {
        gap: 0.35rem !important;
    }

    .stApp:has(#nova-arte-page) section.main .nova-arte-recorrencia-extra {
        margin: 0 0 8px 0 !important;
        padding: 0 !important;
    }

    .stApp:has(#nova-arte-page) section.main div[data-testid="stRadio"] > div {
        gap: 0.35rem !important;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }

    .metric-card {
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border: 1px solid #e7ebf3;
        border-left: 6px solid #e11d48;
        border-radius: 18px;
        padding: 14px 16px 12px 16px;
        min-height: 118px;
        height: auto;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.05);
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
        font-size: 13px;
        color: #334155;
        font-weight: 800;
        margin-bottom: 4px;
        letter-spacing: 0.1px;
        line-height: 1.2;
    }

    .metric-value {
        font-size: 26px;
        color: #0f172a;
        font-weight: 900;
        line-height: 1.1;
        margin: 4px 0 6px 0;
        letter-spacing: -0.4px;
        word-break: keep-all;
        overflow-wrap: normal;
        white-space: nowrap;
    }

    .metric-sub {
        font-size: 11px;
        color: #64748b;
        line-height: 1.35;
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

    .row-edit-label {
        color: #334155;
        font-size: 13px;
        font-weight: 800;
        margin: 0 0 6px 2px;
    }

    .stApp:has(#publicacoes-page) [class*="st-key-row_card_"] {
        background: #ffffff !important;
        border: 1px solid #e8edf5 !important;
        border-radius: 16px !important;
        padding: 16px 18px !important;
        margin-bottom: 10px !important;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
        position: relative !important;
    }

    .stApp:has(#publicacoes-page) [class*="st-key-row_card_"] > [data-testid="stVerticalBlock"] {
        gap: 0 !important;
    }

    .stApp:has(#publicacoes-page) [class*="st-key-row_card_"] [data-testid="stHorizontalBlock"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        gap: 0.75rem !important;
        align-items: center !important;
    }

    .row-card div[data-testid="stSelectbox"] label p,
    .row-card div[data-testid="stTextInput"] label p,
    [class*="st-key-row_card_"] div[data-testid="stSelectbox"] label p,
    [class*="st-key-row_card_"] div[data-testid="stTextInput"] label p {
        color: #334155 !important;
        font-size: 13px !important;
        font-weight: 800 !important;
    }

    .row-main {
        font-size: 17px;
        font-weight: 700;
        color: #16233b;
        margin-bottom: 6px;
    }

    .row-empresa-title {
        font-size: 17px;
        font-weight: 800;
        color: #16233b;
        margin: 0 0 2px 0;
        line-height: 1.2;
        text-align: left;
    }

    .row-tema-subtitle {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        margin: 0 0 8px 0;
        line-height: 1.35;
        text-align: left;
    }

    .pub-card-avatar {
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background: #f3e8ff;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        margin: 0 auto;
    }

    .pub-card-avatar img {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        object-fit: contain;
        background: #ffffff;
        padding: 2px;
    }

    .pub-card-avatar-fallback {
        font-size: 18px;
        font-weight: 800;
        color: #7c3aed;
    }

    .pub-card-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        font-size: 12px;
        color: #94a3b8;
        line-height: 1.4;
    }

    .pub-card-meta-item {
        white-space: nowrap;
    }

    .pub-card-valor {
        font-size: 20px;
        font-weight: 800;
        color: #111827;
        text-align: right;
        white-space: nowrap;
        line-height: 1.1;
        padding-top: 4px;
    }

    [class*="st-key-row_card_"] [class*="st-key-status_inline_"] div[data-testid="stSelectbox"],
    [class*="st-key-row_card_"] [class*="st-key-pagamento_inline_"] div[data-testid="stSelectbox"] {
        margin: 0 !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-status_inline_"] div[data-baseweb="select"] > div,
    [class*="st-key-row_card_"] [class*="st-key-pagamento_inline_"] div[data-baseweb="select"] > div {
        min-height: 34px !important;
        height: 34px !important;
        border-radius: 999px !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        border-width: 1px !important;
        box-shadow: none !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-status_inline_"] div[data-baseweb="select"] > div {
        background: #eff6ff !important;
        border-color: #bfdbfe !important;
        color: #1d4ed8 !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-pagamento_inline_"] div[data-baseweb="select"] > div {
        background: #eff6ff !important;
        border-color: #bfdbfe !important;
        color: #1d4ed8 !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-status_inline_"] div[data-baseweb="select"] svg,
    [class*="st-key-row_card_"] [class*="st-key-pagamento_inline_"] div[data-baseweb="select"] svg {
        width: 14px !important;
        height: 14px !important;
    }

    .pub-activity-heading {
        margin: 0;
        padding: 0;
    }

    .pub-activity-card-view {
        width: 100%;
    }

    .row-meta {
        color: #667085;
        font-size: 13px;
        line-height: 1.55;
        margin-bottom: 4px;
    }

    .row-meta-line {
        margin-bottom: 6px;
    }

    .row-valor {
        font-size: 22px;
        font-weight: 800;
        color: #111827;
        margin: 0;
        text-align: center;
        line-height: 1.1;
    }

    .row-valor-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 100%;
        padding-top: 2px;
    }

    .row-valor-label {
        font-size: 11px;
        font-weight: 700;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 4px;
    }

    .stApp:has(#publicacoes-page) [class*="st-key-row_card_"] div[data-testid="stMarkdownContainer"] {
        width: 100% !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    .stApp:has(#publicacoes-page) [class*="st-key-row_card_"] [data-testid="stHorizontalBlock"] {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        gap: 0.5rem !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-edit_atividade_"] .stButton > button,
    .row-card [class*="st-key-edit_atividade_"] .stButton > button {
        width: 44px !important;
        min-width: 44px !important;
        max-width: 44px !important;
        height: 44px !important;
        min-height: 44px !important;
        max-height: 44px !important;
        padding: 0 !important;
        margin: 0 !important;
        font-size: 18px !important;
        line-height: 1 !important;
        background: #f5f3ff !important;
        border: 1px solid #ddd6fe !important;
        color: #7C3AED !important;
        box-shadow: none !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-edit_atividade_"] .stButton > button:hover,
    .row-card [class*="st-key-edit_atividade_"] .stButton > button:hover {
        background: #ede9fe !important;
        border-color: #c4b5fd !important;
        color: #6d28d9 !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-salvar_alteracoes_"] .stButton > button,
    .row-card [class*="st-key-salvar_alteracoes_"] .stButton > button {
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        font-size: 14px !important;
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-cancelar_edicao_"] .stButton > button,
    .row-card [class*="st-key-cancelar_edicao_"] .stButton > button {
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        font-size: 14px !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-excluir_atividade_"] .stButton > button,
    .row-card [class*="st-key-excluir_atividade_"] .stButton > button {
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        font-size: 14px !important;
        background: #fef2f2 !important;
        color: #dc2626 !important;
        border: 1px solid #fecaca !important;
    }

    [class*="st-key-row_card_"] [class*="st-key-confirmar_exclusao_"] .stButton > button,
    .row-card [class*="st-key-confirmar_exclusao_"] .stButton > button {
        height: 40px !important;
        min-height: 40px !important;
        max-height: 40px !important;
        font-size: 14px !important;
        background: #dc2626 !important;
        color: #ffffff !important;
        border: none !important;
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
        display: none;
    }

    .login-wrap {
        width: min(1200px, 96vw);
        margin: 0 auto;
    }

    .stApp:has(#login-page) [data-testid="stStatusWidget"],
    .stApp:has(#login-page) [data-testid="stElementToolbar"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
    }

    .stApp:has(#login-page) section[data-testid="stSidebar"],
    .stApp:has(#login-page) [data-testid="collapsedControl"],
    .stApp:has(#login-page) [data-testid="stSidebarCollapsedControl"] {
        display: none !important;
    }

    .stApp:has(#login-page) .block-container {
        max-width: 520px;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-top: 3.5rem;
    }

    .stApp:has(#login-page) div[data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }

    .stApp:has(#login-page) div[data-testid="stForm"] {
        background: #ffffff;
        border: 1px solid #e7ebf3;
        border-radius: 28px;
        padding: 32px 28px 26px 28px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
        width: 100%;
        box-sizing: border-box;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"],
    .stApp:has(#login-page) div[data-testid="stTextInput"] > div,
    .stApp:has(#login-page) div[data-testid="stTextInput"] > div > div,
    .stApp:has(#login-page) div[data-testid="stTextInput"] > div > div > div {
        width: 100% !important;
        max-width: 100% !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] label p {
        color: #334155 !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        margin-bottom: 6px !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] input {
        background: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 16px !important;
        color: #0f172a !important;
        font-size: 16px !important;
        font-weight: 500 !important;
        height: 52px !important;
        min-height: 52px !important;
        width: 100% !important;
        padding: 0 16px !important;
        box-sizing: border-box !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] input:focus {
        border-color: #7C3AED !important;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.12) !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] input::placeholder {
        color: #94a3b8 !important;
        font-size: 16px !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] [data-baseweb="input"] {
        background: #ffffff !important;
        border-radius: 16px !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] .stButton {
        width: auto !important;
        min-width: 48px !important;
        max-width: 48px !important;
        flex: 0 0 48px !important;
    }

    .stApp:has(#login-page) div[data-testid="stTextInput"] .stButton > button {
        width: 48px !important;
        min-width: 48px !important;
        max-width: 48px !important;
        height: 48px !important;
        min-height: 48px !important;
        max-height: 48px !important;
        padding: 0 !important;
        margin: 0 !important;
        background: #f8fafc !important;
        color: #64748b !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        box-shadow: none !important;
    }

    .stApp:has(#login-page) [data-testid="stFormSubmitButton"] {
        width: 100% !important;
    }

    .stApp:has(#login-page) [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
        color: #ffffff !important;
        border: none !important;
        min-height: 56px !important;
        height: 56px !important;
        font-size: 17px !important;
        border-radius: 16px !important;
        box-shadow: none !important;
        margin-top: 12px !important;
        width: 100% !important;
        white-space: nowrap !important;
    }

    .stApp:has(#login-page) [data-testid="stFormSubmitButton"] > button:hover {
        opacity: 0.92 !important;
    }

    .login-head {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        margin-bottom: 10px;
    }

    .login-logo {
        width: 56px;
        height: 56px;
        border-radius: 50%;
        object-fit: cover;
        object-position: 58% center;
        display: block;
    }

    .login-title {
        text-align: center;
        font-size: 40px;
        font-weight: 800;
        color: #0f2d63;
        margin: 0;
    }

    .login-subtitle {
        text-align: center;
        font-size: 18px;
        color: #60708a;
        margin-bottom: 28px;
    }

    .login-card {
        padding: 18px 16px 16px 16px;
    }

    .login-button .stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #C026D3 100%) !important;
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

    .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stTextInput"] input {
        background: #fbfcff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        font-size: 17px !important;
        font-weight: 700 !important;
        height: 44px !important;
        padding: 0 12px !important;
    }

    .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stTextInput"] input:focus {
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

    .stApp:has(#trafego-page) [class*="st-key-btn_abrir_apresentacao"] .stButton > button {
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

    .stApp:has(#trafego-page) [class*="st-key-btn_abrir_apresentacao"] .stButton > button:hover {
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

    .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stDateInput"] input {
        background: #ffffff !important;
        border: 1px solid #d9e0eb !important;
        border-radius: 12px !important;
        color: #0f172a !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        height: 44px !important;
        padding: 0 12px !important;
    }

    .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stDateInput"] input:focus {
        border-color: #7C3AED !important;
        box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.10) !important;
    }

    @media (max-width: 768px) {
        .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] {
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
        position: relative !important;
        background: linear-gradient(180deg, #2A2342 0%, #1A1630 100%) !important;
        border-right: 1px solid rgba(167, 139, 250, 0.12) !important;
    }

    section[data-testid="stSidebar"] > div {
        background: transparent !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
        padding-top: 18px !important;
    }

    .sidebar-top-row {
        display: flex;
        justify-content: flex-end;
        align-items: center;
        min-height: 40px;
        margin: 0 0 2px 0;
        padding: 0 4px 0 0;
    }

    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 4px 16px 4px;
        margin-bottom: 14px;
        border-bottom: 1px solid rgba(167, 139, 250, 0.14);
    }

    .sidebar-brand-logo {
        width: 42px;
        height: 42px;
        border-radius: 50%;
        object-fit: cover;
        object-position: 58% center;
        display: block;
        border: 1px solid rgba(196, 181, 253, 0.35);
        background: #ffffff;
    }

    .sidebar-brand-title {
        color: #F5F3FF;
        font-size: 15px;
        font-weight: 700;
        line-height: 1.05;
        letter-spacing: 0.2px;
    }

    .sidebar-brand-subtitle {
        color: #A78BFA;
        font-size: 10px;
        font-weight: 600;
        line-height: 1.2;
        margin-top: 3px;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        opacity: 0.85;
    }

    .sidebar-nav-label {
        color: #8B7FA8;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1.2px;
        margin: 2px 0 10px 2px;
        text-transform: uppercase;
    }

    .sidebar-role {
        color: #C4B5FD;
        font-size: 11px;
        font-weight: 700;
        margin: -4px 0 12px 4px;
        letter-spacing: 0.3px;
    }

    .sidebar-help {
        color: #9F94C9;
        font-size: 11px;
        line-height: 1.45;
        padding: 10px 4px 0 4px;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] > div {
        gap: 8px !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label {
        background: rgba(167, 139, 250, 0.06) !important;
        border: 1px solid rgba(167, 139, 250, 0.10) !important;
        border-radius: 10px !important;
        padding: 10px 12px !important;
        margin: 0 !important;
        min-height: 40px !important;
        width: 100% !important;
        box-sizing: border-box !important;
        transition: background 0.15s ease, border-color 0.15s ease !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover {
        background: rgba(167, 139, 250, 0.10) !important;
        border-color: rgba(167, 139, 250, 0.18) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
        background: rgba(167, 139, 250, 0.14) !important;
        border-color: rgba(167, 139, 250, 0.28) !important;
        box-shadow: inset 3px 0 0 #A78BFA !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label p {
        color: #C4B5FD !important;
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) p {
        color: #F5F3FF !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label > div:first-child {
        transform: scale(0.90);
    }

    .sidebar-submenu-label {
        color: #A78BFA;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin: 2px 0 8px 4px;
    }

    section[data-testid="stSidebar"] .st-key-midias_submenu {
        margin: 0 0 12px 0;
        padding: 2px 0 2px 10px;
        border-left: 2px solid rgba(167, 139, 250, 0.35);
    }

    section[data-testid="stSidebar"] .st-key-midias_submenu div[data-testid="stRadio"] > div {
        gap: 6px !important;
    }

    section[data-testid="stSidebar"] .st-key-midias_submenu div[data-testid="stRadio"] label {
        min-height: 36px !important;
        padding: 8px 10px !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] .st-key-midias_submenu div[data-testid="stRadio"] label p {
        font-size: 13px !important;
        font-weight: 700 !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(167, 139, 250, 0.08) !important;
        color: #EDE9FE !important;
        border: 1px solid rgba(167, 139, 250, 0.22) !important;
        border-radius: 10px !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        min-height: 42px !important;
        height: 42px !important;
        margin-top: 16px !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(167, 139, 250, 0.16) !important;
        border-color: rgba(167, 139, 250, 0.35) !important;
        color: #F5F3FF !important;
    }

    /* Desliga header nativo da sidebar (seta + texto "Esconder menu lateral") */
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"],
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] *,
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    button[data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
    }

    .stApp.sidebar-collapsed section[data-testid="stSidebar"] {
        display: none !important;
    }

    .stApp.sidebar-collapsed [data-testid="stAppViewContainer"] > section.main {
        margin-left: 0 !important;
        max-width: 100% !important;
    }

    /* Seta BRANCA — esconder menu (topo direito da sidebar) */
    section[data-testid="stSidebar"] .oppi-sidebar-hide {
        position: static !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: transparent !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 32px !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        min-height: 40px !important;
        height: 40px !important;
        width: 40px !important;
        min-width: 40px !important;
        max-width: 40px !important;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
        pointer-events: auto !important;
        z-index: 20 !important;
    }

    section[data-testid="stSidebar"] .oppi-sidebar-hide:hover {
        background: rgba(167, 139, 250, 0.18) !important;
        border-radius: 8px !important;
    }

    /* Seta PRETA — abrir menu (fora, menu fechado) */
    .oppi-sidebar-show {
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 999999 !important;
        display: none !important;
        align-items: center !important;
        justify-content: center !important;
        background: transparent !important;
        color: #000000 !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 36px !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        min-height: 52px !important;
        height: 52px !important;
        width: 52px !important;
        min-width: 52px !important;
        max-width: 52px !important;
        margin: 0 !important;
        padding: 0 !important;
        cursor: pointer !important;
    }

    .oppi-sidebar-show:hover {
        background: rgba(0, 0, 0, 0.06) !important;
        border-radius: 8px !important;
    }

    .stApp.sidebar-collapsed .oppi-sidebar-show {
        display: flex !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) > div:first-child > div {
        background-color: #A78BFA !important;
        border-color: #A78BFA !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stRadio"] label:hover > div:first-child > div {
        border-color: rgba(196, 181, 253, 0.55) !important;
    }

    @media (max-width: 768px) {
        .top-title .text {
            font-size: 32px;
        }

        .subtitle {
            font-size: 17px;
        }

        .stApp:has(#trafego-page) section.main [data-testid="stVerticalBlockBorderWrapper"] {
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

def format_valor_input(valor):
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_valor_texto(valor):
    if valor is None:
        return 0.0

    if isinstance(valor, (int, float)):
        if pd.isna(valor):
            return 0.0
        return float(valor)

    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "-"}:
        return 0.0

    texto = re.sub(r"[R$r$\s]", "", texto)
    if not texto:
        return 0.0

    if re.search(r",\d{1,2}$", texto):
        texto = texto.replace(".", "").replace(",", ".")
    else:
        texto = texto.replace(",", "")

    numero = pd.to_numeric(texto, errors="coerce")
    if pd.isna(numero):
        return 0.0
    return float(numero)


def normalizar_valor(coluna):
    return coluna.apply(parse_valor_texto)


def normalizar_status_pagamento_coluna(coluna):
    def map_status(valor):
        texto = str(valor).strip().lower()
        if texto in {"", "nan", "none"}:
            return "a pagar"
        if texto == "pago":
            return "pago"
        if texto in {"a pagar", "apagar"}:
            return "a pagar"
        return "a pagar"

    return coluna.map(map_status)

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

def status_pagamento_badge(status):
    s = str(status).strip().lower()
    if s == "pago":
        return '<span class="status-pill status-pronto">Pago</span>'
    if s == "a pagar":
        return '<span class="status-pill status-pendente">A pagar</span>'
    return f'<span class="status-pill status-outro">{status if str(status).strip() else "-"}</span>'

def status_arte_para_edicao(valor):
    mapa = {
        "pronto": "Pronto",
        "em andamento": "Em andamento",
        "pausado": "Pausado",
        "pendente": "Pendente",
        "concluído": "Pronto",
        "concluido": "Pronto",
    }
    return mapa.get(str(valor).strip().lower(), "Pendente")

def status_pagamento_para_edicao(valor):
    if str(valor).strip().lower() == "pago":
        return "Pago"
    return "A Pagar"

def indice_select(opcoes, valor):
    try:
        return opcoes.index(valor)
    except ValueError:
        return 0


def resolver_indices_colunas_midias(rows):
    if not rows:
        return {}

    raw_headers = [normalize_header_name(header) for header in rows[0]]
    data_rows = rows[1:]
    selected_indexes = {}
    used_indexes = set()

    for expected_header in EXPECTED_MEDIA_HEADERS:
        if expected_header in ("Data Publicação", "Status Pagamento"):
            continue

        candidates = find_header_candidates(raw_headers, expected_header)
        if not candidates:
            continue

        best_index = max(
            candidates,
            key=lambda index: count_non_empty_column(data_rows, index),
        )
        selected_indexes[expected_header] = best_index
        used_indexes.add(best_index)

    date_index = detect_date_column(raw_headers, data_rows, used_indexes)
    if date_index is not None:
        selected_indexes["Data Publicação"] = date_index
        used_indexes.add(date_index)

    payment_index = detect_payment_column(raw_headers, data_rows, used_indexes)
    if payment_index is not None:
        selected_indexes["Status Pagamento"] = payment_index
        used_indexes.add(payment_index)

    valor_index = detect_valor_column(raw_headers, data_rows, selected_indexes, used_indexes)
    if valor_index is not None:
        previous_valor_index = selected_indexes.get("Valor")
        if previous_valor_index in used_indexes:
            used_indexes.discard(previous_valor_index)
        selected_indexes["Valor"] = valor_index
        used_indexes.add(valor_index)

    return selected_indexes


def mapa_colunas_midias_por_nome(rows):
    indices = resolver_indices_colunas_midias(rows)
    return {nome: indice + 1 for nome, indice in indices.items()}


def atualizar_mapa_colunas_midias(rows):
    st.session_state["_media_col_map"] = mapa_colunas_midias_por_nome(rows)


def get_media_column_map():
    cached = st.session_state.get("_media_col_map")
    if cached:
        return cached

    rows = load_raw_rows()
    atualizar_mapa_colunas_midias(rows)
    return st.session_state.get("_media_col_map") or {}


def validar_colunas_gravacao(col_map, campos_obrigatorios):
    faltando = [campo for campo in campos_obrigatorios if not col_map.get(campo)]
    if faltando:
        raise ValueError(
            "Não foi possível localizar na planilha as colunas: "
            + ", ".join(faltando)
            + ". Confira os cabeçalhos da primeira linha."
        )


def montar_linha_para_gravacao(col_map, valores_por_campo):
    validar_colunas_gravacao(col_map, list(valores_por_campo.keys()))
    max_col = max(col_map.values())
    linha = [""] * max_col

    for campo, valor in valores_por_campo.items():
        col = col_map[campo]
        if col > len(linha):
            linha.extend([""] * (col - len(linha)))
        linha[col - 1] = valor

    return linha


def atualizar_celula_midia(row_index, campo, valor):
    col_map = get_media_column_map()
    col_num = col_map.get(campo)
    if not col_num:
        raise ValueError(f"Coluna '{campo}' não encontrada na planilha.")

    sheet_row = row_index + 2

    def gravar():
        worksheet = connect_media_worksheet()
        worksheet.update_cell(sheet_row, col_num, valor)

    executar_operacao_planilha(gravar)


def salvar_atividade_planilha(row_index, tema, valor_txt, pagamento, status_arte):
    valor_txt = str(valor_txt).strip()
    if not valor_txt:
        return False, "Informe um valor."

    valor_parsed = parse_valor_texto(valor_txt)
    if valor_parsed < 0:
        return False, "Informe um valor válido."

    campos_valores = [
        ("Tema", str(tema).strip()),
        ("Valor", valor_parsed),
        (
            "Status Pagamento",
            STATUS_PAGAMENTO_SHEET_MAP.get(pagamento, pagamento),
        ),
        ("Status da arte", status_arte),
    ]

    try:
        col_map = get_media_column_map()

        def gravar():
            worksheet = connect_media_worksheet()
            sheet_row = row_index + 2
            for campo, valor_campo in campos_valores:
                col_num = col_map.get(campo)
                if not col_num:
                    raise ValueError(f"Coluna '{campo}' não encontrada na planilha.")
                worksheet.update_cell(sheet_row, col_num, valor_campo)

        executar_operacao_planilha(gravar)
    except Exception as exc:
        return False, mensagem_erro_planilha(exc)
    return True, ""


def salvar_status_arte_inline(row_index):
    novo_status = st.session_state.get(f"status_inline_{row_index}")
    if novo_status:
        try:
            atualizar_celula_midia(row_index, "Status da arte", novo_status)
            invalidar_cache_midias()
        except Exception as exc:
            st.error(mensagem_erro_planilha(exc))


def salvar_pagamento_inline(row_index):
    novo_pagamento = st.session_state.get(f"pagamento_inline_{row_index}")
    if novo_pagamento:
        try:
            atualizar_celula_midia(
                row_index,
                "Status Pagamento",
                STATUS_PAGAMENTO_SHEET_MAP.get(novo_pagamento, novo_pagamento),
            )
            invalidar_cache_midias()
        except Exception as exc:
            st.error(mensagem_erro_planilha(exc))


def excluir_atividade_planilha(row_index):
    def gravar():
        worksheet = connect_media_worksheet()
        worksheet.delete_rows(row_index + 2)

    executar_operacao_planilha(gravar)
    return True, ""


def format_status_pill_option(opcao):
    icones = {
        "Pronto": "🟢",
        "Pendente": "🔵",
        "Em andamento": "🟡",
        "Pausado": "⏸️",
    }
    return f"{icones.get(opcao, '●')} {opcao}"


def format_pagamento_pill_option(opcao):
    return f"💳 {opcao}"


def normalize_empresa_key(nome):
    texto = str(nome).strip().lower()
    substituicoes = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)
    return re.sub(r"\s+", " ", texto).strip()


def logo_empresa_path(empresa_nome):
    chave = normalize_empresa_key(empresa_nome)

    if chave in EMPRESA_LOGO_MAP:
        caminho = EMPRESA_LOGO_MAP[chave]
        if caminho.exists():
            return caminho

    for alias, caminho in EMPRESA_LOGO_MAP.items():
        if alias in chave or chave in alias:
            if caminho.exists():
                return caminho

    if LOGO_PATH.exists():
        return LOGO_PATH

    return None


def card_logo_html(empresa_nome):
    path = logo_empresa_path(empresa_nome)
    if path is None or not path.exists():
        inicial = str(empresa_nome).strip()[:1].upper() or "E"
        return f'<div class="pub-card-avatar pub-card-avatar-fallback">{html.escape(inicial)}</div>'

    mime = "image/png"
    if path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"
    img_base64 = base64.b64encode(path.read_bytes()).decode()
    return (
        f'<div class="pub-card-avatar">'
        f'<img src="data:{mime};base64,{img_base64}" alt="{html.escape(str(empresa_nome))}">'
        f'</div>'
    )


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

def imagem_base64_cached(path_str):
    path = Path(path_str)
    if not path.exists():
        return "", ""

    mime = "image/png"
    if path.suffix.lower() in [".jpg", ".jpeg"]:
        mime = "image/jpeg"

    return mime, base64.b64encode(path.read_bytes()).decode()


imagem_base64_cached = st.cache_data(show_spinner=False)(imagem_base64_cached)


def render_logo(path: Path):
    mime, img_base64 = imagem_base64_cached(str(path))
    if not img_base64:
        return
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
    mime, img_base64 = imagem_base64_cached(str(path))
    if not img_base64:
        return ""
    return f'<img class="login-logo" src="data:{mime};base64,{img_base64}">'


def operacao_user_fallback():
    return {
        "row_number": None,
        "username": "operacao",
        "password": OPERACAO_PASSWORD,
        "role": "geral",
        "active": True,
        "permissions": default_permissions_for_role("geral"),
        "source": "padrão",
    }


def authenticate_user(usuario, senha):
    user_key = normalize_username(usuario)
    senha_informada = str(senha).strip()

    if user_key == "operacao":
        if senha_informada != OPERACAO_PASSWORD:
            return None

        try:
            for user in load_users_sheet_rows():
                if user["username"] != "operacao":
                    continue
                if not user["active"]:
                    return "blocked"
                user = dict(user)
                user["password"] = OPERACAO_PASSWORD
                return user
        except Exception:
            pass

        return operacao_user_fallback()

    try:
        for user in load_users_sheet_rows():
            if user["username"] == user_key and user["password"] == senha_informada:
                if not user["active"]:
                    return "blocked"
                return user
    except Exception:
        return None

    return None


def get_user_role():
    return st.session_state.get("user_role", "geral")


def get_user_permissions():
    permissions = st.session_state.get("user_permissions")
    if permissions:
        return permissions
    return nav_options_for_role(get_user_role())


def nav_options_for_role(role):
    return ROLE_NAV_ACCESS.get(role, ROLE_NAV_ACCESS["geral"])


def default_area_for_permissions(permissions):
    return permissions[0] if permissions else "Publicações"


def default_area_for_role(role):
    return default_area_for_permissions(nav_options_for_role(role))


def enforce_area_access(area):
    allowed = get_user_permissions()
    if area in allowed:
        return area
    return default_area_for_permissions(allowed)


def show_login():
    st.markdown('<div id="login-page"></div>', unsafe_allow_html=True)

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

    with st.form("login_form", clear_on_submit=False):
        usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("Senha", placeholder="Digite sua senha", type="password")
        entrar = st.form_submit_button("Entrar", width="stretch")

    if entrar:
        erro_planilha = False
        try:
            auth_result = authenticate_user(usuario, senha)
        except Exception:
            erro_planilha = True
            auth_result = None
            st.error(
                "Não foi possível validar o login agora. "
                "A planilha está temporariamente sobrecarregada — tente novamente em 1 minuto."
            )

        if auth_result == "blocked":
            st.error("Usuário bloqueado. Fale com o administrador do painel.")
        elif auth_result:
            st.session_state.logged_in = True
            st.session_state.user_role = auth_result["role"]
            st.session_state.logged_username = auth_result["username"]
            st.session_state.user_permissions = permissions_to_nav_list(auth_result["permissions"])
            st.session_state.area_dashboard = default_area_for_permissions(
                st.session_state.user_permissions
            )
            st.rerun()
        elif not erro_planilha:
            st.error("Usuário ou senha incorretos.")

    st.markdown(
        f'<div class="login-footer">Acesso restrito · v{APP_UI_VERSION}</div>',
        unsafe_allow_html=True,
    )

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


@st.cache_resource(show_spinner=False)
def connect_gspread_client():
    creds_dict = get_google_creds_dict()
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def connect_spreadsheet():
    return connect_gspread_client().open_by_key(SHEET_ID)


def connect_media_worksheet():
    return connect_spreadsheet().get_worksheet(0)


def connect_sheet():
    try:
        return connect_media_worksheet()
    except Exception as e:
        raise ConnectionError(f"Erro ao conectar com Google Sheets: {e}") from e


def invalidar_conexao_planilha():
    connect_gspread_client.clear()
    connect_spreadsheet.clear()


def erro_planilha_recuperavel(exc):
    texto = str(exc).lower()
    if "429" in texto or "quota" in texto or "rate limit" in texto:
        return True
    if isinstance(exc, gspread.exceptions.APIError):
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status in (429, 500, 502, 503):
            return True
    return isinstance(
        exc,
        (
            gspread.exceptions.GSpreadException,
            ConnectionError,
            TimeoutError,
        ),
    )


def executar_operacao_planilha(operacao, *args, **kwargs):
    ultimo_erro = None
    for tentativa in range(3):
        try:
            return operacao(*args, **kwargs)
        except Exception as exc:
            ultimo_erro = exc
            if tentativa >= 2 or not erro_planilha_recuperavel(exc):
                raise
            invalidar_conexao_planilha()
            time.sleep(1.5 * (tentativa + 1))
    raise ultimo_erro


def append_linhas_midia(linhas):
    if not linhas:
        return

    def gravar():
        worksheet = connect_media_worksheet()
        col_map = get_media_column_map()
        campos_ordem = [
            "Mês",
            "Semana",
            "Empresa",
            "Tema",
            "Valor",
            "Status Pagamento",
            "Tipo de arte",
            "Status da arte",
            "Data Publicação",
            "Serviços",
            "Recorrência",
        ]
        campos_obrigatorios = [
            "Mês",
            "Empresa",
            "Tema",
            "Semana",
            "Data Publicação",
            "Valor",
            "Status da arte",
            "Status Pagamento",
        ]
        validar_colunas_gravacao(col_map, campos_obrigatorios)

        for linha_valores in linhas:
            valores = dict(zip(campos_ordem, linha_valores))
            valores_gravar = {}
            for campo in campos_ordem:
                if campo not in col_map:
                    continue
                valor = valores.get(campo, "")
                if campo in campos_obrigatorios or str(valor).strip() != "":
                    valores_gravar[campo] = valor
            linha_planilha = montar_linha_para_gravacao(col_map, valores_gravar)
            worksheet.append_row(linha_planilha, value_input_option="USER_ENTERED")

    executar_operacao_planilha(gravar)


def executar_com_timeout(operacao, timeout_segundos=25):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(operacao)
        try:
            return future.result(timeout=timeout_segundos)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutError(
                "A planilha Google demorou demais para responder. "
                "Tente novamente em cerca de 1 minuto."
            ) from exc


def get_all_values_com_timeout(worksheet, timeout_segundos=90):
    return executar_com_timeout(worksheet.get_all_values, timeout_segundos)


def mensagem_erro_carregamento_midias(exc):
    if isinstance(exc, TimeoutError):
        return str(exc)
    if isinstance(exc, ConnectionError):
        return (
            "Não foi possível conectar com a planilha Google. "
            "Verifique as credenciais no EasyPanel e tente novamente."
        )
    texto = str(exc).lower()
    if "429" in texto or "quota" in texto or "rate limit" in texto:
        return (
            "A planilha está temporariamente sobrecarregada. "
            "Aguarde cerca de 1 minuto e atualize a página."
        )
    return (
        "Não foi possível carregar os dados da planilha agora. "
        "Tente atualizar a página em alguns segundos."
    )


def mensagem_erro_planilha(exc):
    texto = str(exc).lower()
    if "429" in texto or "quota" in texto or "rate limit" in texto:
        return (
            "A planilha está temporariamente sobrecarregada. "
            "Aguarde cerca de 1 minuto e tente salvar novamente."
        )
    return (
        "Não foi possível salvar na planilha agora. "
        "Verifique a conexão e tente de novo em alguns segundos."
    )


def connect_users_worksheet():
    sheet = connect_spreadsheet()
    try:
        worksheet = sheet.worksheet(USERS_SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=USERS_SHEET_NAME, rows=200, cols=len(USERS_HEADERS))
        worksheet.append_row(USERS_HEADERS)
        return worksheet
    ensure_users_headers(worksheet)
    return worksheet


def ensure_users_headers(worksheet):
    current = [str(item).strip() for item in worksheet.row_values(1) if str(item).strip()]
    if not current:
        worksheet.update("A1", [USERS_HEADERS])
        return

    updated = list(current)
    changed = False
    for header in USERS_HEADERS:
        if header not in updated:
            updated.append(header)
            changed = True

    if changed:
        worksheet.update("A1", [updated])


def get_users_header_map(worksheet):
    ensure_users_headers(worksheet)
    headers = worksheet.row_values(1)
    return {str(name).strip(): idx + 1 for idx, name in enumerate(headers) if str(name).strip()}


def normalize_username(value):
    texto = str(value).strip().lower()
    substituicoes = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    for antigo, novo in substituicoes.items():
        texto = texto.replace(antigo, novo)
    return texto


def normalize_role(value):
    role = str(value).strip().lower()
    if role in ROLE_LABELS:
        return role
    for key, label in ROLE_LABELS.items():
        if str(label).strip().lower() == role:
            return key
    return ""


def sim_nao_value(value, default="Não"):
    texto = str(value).strip().lower()
    if texto in ("sim", "s", "yes", "1", "true"):
        return "Sim"
    if texto in ("não", "nao", "n", "0", "false"):
        return "Não"
    return default


def is_user_active(value):
    return sim_nao_value(value, "Sim") == "Sim"


def default_permissions_for_role(role):
    allowed = nav_options_for_role(role)
    return {area: ("Sim" if area in allowed else "Não") for area in CONTENT_AREAS}


def permissions_to_nav_list(permissions):
    return [area for area in CONTENT_AREAS if permissions.get(area) == "Sim"]


def parse_user_row(row, row_number):
    username = normalize_username(row.get("Usuário", ""))
    password = str(row.get("Senha", "")).strip()
    role = normalize_role(row.get("Perfil", ""))
    if not username or not password or not role:
        return None

    defaults = default_permissions_for_role(role)
    permissions = {
        area: sim_nao_value(row.get(area, ""), defaults.get(area, "Não"))
        for area in CONTENT_AREAS
    }

    return {
        "row_number": row_number,
        "username": username,
        "password": password,
        "role": role,
        "active": is_user_active(row.get("Ativo", "Sim")),
        "permissions": permissions,
        "source": "planilha",
    }


def sync_operacao_password_in_sheet():
    try:
        worksheet = connect_users_worksheet()
        header_map = get_users_header_map(worksheet)
        senha_col = header_map.get("Senha", 2)
        records = worksheet.get_all_records()
        atualizou = False

        for index, row in enumerate(records, start=2):
            username = normalize_username(row.get("Usuário", ""))
            if username != "operacao":
                continue

            senha_atual = str(row.get("Senha", "")).strip()
            if senha_atual != OPERACAO_PASSWORD:
                worksheet.update_cell(index, senha_col, OPERACAO_PASSWORD)
                atualizou = True

        if atualizou:
            clear_users_cache()

        return atualizou
    except Exception:
        return False


def sync_operacao_password_once():
    if st.session_state.get("_operacao_password_synced"):
        return

    sync_operacao_password_in_sheet()
    st.session_state["_operacao_password_synced"] = True


def apply_operacao_password_override(users):
    for user in users:
        if user["username"] == "operacao":
            user["password"] = OPERACAO_PASSWORD
    return users


def ensure_default_users_in_sheet():
    if st.session_state.get("users_sheet_initialized"):
        return

    try:
        worksheet = connect_users_worksheet()
        records = worksheet.get_all_records()
        existing = {
            normalize_username(row.get("Usuário", ""))
            for row in records
        }

        for username, data in APP_USERS.items():
            username = normalize_username(username)
            if username in existing:
                continue

            permissions = default_permissions_for_role(data["role"])
            worksheet.append_row([
                username,
                data["password"],
                data["role"],
                "Sim",
                permissions["Empresas"],
                permissions["Publicações"],
                permissions["Nova Arte"],
                permissions["Gestão de Tráfego"],
                permissions[NAV_ACESSOS],
            ])

        sync_operacao_password_once()
        st.session_state["users_sheet_initialized"] = True
    except Exception:
        return


def load_users_sheet_rows_impl():
    worksheet = connect_users_worksheet()
    records = worksheet.get_all_records()
    users = []
    for index, row in enumerate(records, start=2):
        parsed = parse_user_row(row, index)
        if parsed:
            users.append(parsed)
    return apply_operacao_password_override(users)


def load_users_sheet_rows_fallback():
    users = []
    for username, data in APP_USERS.items():
        username = normalize_username(username)
        users.append(
            {
                "row_number": None,
                "username": username,
                "password": data["password"],
                "role": data["role"],
                "active": True,
                "permissions": default_permissions_for_role(data["role"]),
                "source": "padrão",
            }
        )
    return apply_operacao_password_override(users)


@st.cache_data(ttl=300, show_spinner=False)
def load_users_sheet_rows():
    try:
        return load_users_sheet_rows_impl()
    except Exception:
        return load_users_sheet_rows_fallback()


def clear_users_cache():
    load_users_sheet_rows.clear()


def roles_criaveis_por(perfil_atual):
    if perfil_atual == "geral":
        return ROLE_FORM_OPTIONS
    if perfil_atual == "gestor":
        return ["gestor", "designer"]
    return []


def can_manage_user(manager_role, target_user):
    if manager_role == "geral":
        return True
    if manager_role == "gestor":
        return target_user["role"] in ("gestor", "designer")
    return False


def update_user_permissions(row_number, permissions):
    worksheet = connect_users_worksheet()
    header_map = get_users_header_map(worksheet)
    for area in CONTENT_AREAS:
        worksheet.update_cell(row_number, header_map[area], permissions[area])
    clear_users_cache()


def set_user_active(row_number, active):
    worksheet = connect_users_worksheet()
    header_map = get_users_header_map(worksheet)
    worksheet.update_cell(row_number, header_map["Ativo"], "Sim" if active else "Não")
    clear_users_cache()


def username_is_valid(username):
    username = normalize_username(username)
    if len(username) < 3:
        return False
    return re.fullmatch(r"[a-z0-9_.-]+", username) is not None


def register_user(username, password, role, creator_role):
    username = normalize_username(username)
    role = normalize_role(role)

    if creator_role not in ("geral", "gestor"):
        return False, "Seu perfil não pode cadastrar usuários."

    if role not in roles_criaveis_por(creator_role):
        return False, "Seu perfil não pode criar esse tipo de acesso."

    if not username_is_valid(username):
        return False, "Use um usuário válido com pelo menos 3 caracteres."

    if len(password.strip()) < 4:
        return False, "A senha precisa ter pelo menos 4 caracteres."

    if any(user["username"] == username for user in load_users_sheet_rows()):
        return False, "Esse usuário já está cadastrado."

    permissions = default_permissions_for_role(role)
    worksheet = connect_users_worksheet()
    worksheet.append_row([
        username,
        password.strip(),
        role,
        "Sim",
        permissions["Empresas"],
        permissions["Publicações"],
        permissions["Nova Arte"],
        permissions["Gestão de Tráfego"],
        permissions[NAV_ACESSOS],
    ])
    clear_users_cache()
    return True, "Usuário cadastrado com sucesso!"


# ---------------------------------------------------
# TOPO E NAVEGAÇÃO
# ---------------------------------------------------

def sidebar_logo_html(path: Path):
    mime, img_base64 = imagem_base64_cached(str(path))
    if not img_base64:
        return ""
    return f'<img class="sidebar-brand-logo" src="data:{mime};base64,{img_base64}">'


def render_sidebar_show_button():
    st.markdown(
        '<button type="button" class="oppi-sidebar-show" aria-label="Abrir menu lateral">»</button>',
        unsafe_allow_html=True,
    )


def sync_sidebar_toggle_state():
    components.html(SIDEBAR_TOGGLE_SCRIPT, height=0)


def reset_sidebar_toggle_state():
    components.html(
        """
        <script>
        window.parent.localStorage.setItem("oppi_sidebar_collapsed", "0");
        window.parent.document.querySelector(".stApp")?.classList.remove("sidebar-collapsed");
        </script>
        """,
        height=0,
    )


def render_sidebar_navigation():
    logo_html = sidebar_logo_html(LOGO_PATH)
    role = get_user_role()
    nav_options = get_user_permissions()
    role_label = ROLE_LABELS.get(role, role.title())

    if not nav_options:
        nav_options = [default_area_for_role(role)]

    if st.session_state.get("area_dashboard") not in nav_options:
        st.session_state.area_dashboard = default_area_for_permissions(nav_options)

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-top-row">
                <button type="button" class="oppi-sidebar-hide" aria-label="Esconder menu lateral">«</button>
            </div>
            <div class="sidebar-brand">
                {logo_html}
                <div>
                    <div class="sidebar-brand-title">OPPI TECH</div>
                    <div class="sidebar-brand-subtitle">Painel interno</div>
                </div>
            </div>
            <div class="sidebar-nav-label">Navegação</div>
            <div class="sidebar-role">Perfil: {html.escape(role_label)}</div>
            """,
            unsafe_allow_html=True
        )

        area = st.radio(
            "Navegação",
            options=nav_options,
            format_func=lambda opcao: NAV_LABELS[opcao],
            key="area_dashboard",
            label_visibility="collapsed",
        )

        sair = st.button("SAIR DA CONTA", key="btn_logout_sidebar")
        if sair:
            st.session_state.logged_in = False
            st.session_state.pop("user_role", None)
            st.session_state.pop("logged_username", None)
            st.session_state.pop("user_permissions", None)
            st.session_state.pop("df_midias_processado", None)
            st.session_state.pop("_sessao_keepalive", None)
            reset_sidebar_toggle_state()
            st.rerun()

        st.markdown(
            '<div class="sidebar-help">Seta branca no topo direito esconde o menu. Seta preta no canto esquerdo abre de novo.</div>',
            unsafe_allow_html=True
        )

    return area


def render_dashboard_top(area):
    render_logo(LOGO_PATH)

    subtitulos = {
        "Gestão de Tráfego": "Resultados dos anúncios",
        "Empresas": "Visão por empresa",
        "Publicações": "Gestão de publicações e pagamentos",
        "Nova Arte": "Cadastro de nova arte",
        NAV_ACESSOS: "Perfis e permissões do painel",
    }
    subtitulo = subtitulos.get(area, "Gestão de publicações e pagamentos")

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
        width="stretch",
        key="btn_baixar_pdf_apresentacao",
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Voltar para editar", width="stretch", key="btn_voltar_editar"):
            st.rerun()

    with c2:
        if st.button("Nova apresentação", width="stretch", key="btn_nova_apresentacao"):
            clear_traffic_form()
            st.session_state["abrir_apresentacao"] = False
            st.rerun()


def linhas_com_conteudo_mask(df_frame):
    return (
        df_frame["Empresa"].astype(str).str.strip().ne("")
        | df_frame["Tema"].astype(str).str.strip().ne("")
        | df_frame["Tipo de arte"].astype(str).str.strip().ne("")
        | df_frame["Valor"].fillna(0).gt(0)
        | df_frame["Data Publicação"].notna()
    )


def chave_filtros_publicacoes(mes, data_inicio, data_fim, empresa):
    empresa_slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(empresa)).strip("_")
    return f"{mes}_{data_inicio.isoformat()}_{data_fim.isoformat()}_{empresa_slug}"


def calcular_metricas_empresa(df_empresa):
    status_pagamento_normalizado = normalizar_status_pagamento_coluna(
        df_empresa["Status Pagamento"]
    )
    status_arte_normalizado = df_empresa["Status da arte"].astype(str).str.strip().str.lower()

    pagos = df_empresa[status_pagamento_normalizado == "pago"]
    a_pagar = df_empresa[status_pagamento_normalizado == "a pagar"]

    linhas_com_conteudo = linhas_com_conteudo_mask(df_empresa)

    postagens_feitas = int(((status_arte_normalizado == "pronto") & linhas_com_conteudo).sum())
    postagens_a_fazer = int(((status_arte_normalizado != "pronto") & linhas_com_conteudo).sum())
    valor_pago = float(pagos["Valor"].sum())
    valor_a_pagar = float(a_pagar["Valor"].sum())

    return postagens_feitas, postagens_a_fazer, valor_pago, valor_a_pagar


def aplicar_estilo_grafico_legivel(fig):
    cor_texto = "#1e293b"
    cor_grade = "#e2e8f0"

    fig.update_layout(
        font=dict(color=cor_texto, size=13),
        xaxis=dict(
            tickfont=dict(color=cor_texto, size=12),
            title_font=dict(color=cor_texto, size=13),
            linecolor=cor_grade,
            gridcolor=cor_grade,
        ),
        yaxis=dict(
            tickfont=dict(color=cor_texto, size=12),
            title_font=dict(color=cor_texto, size=13),
            linecolor=cor_grade,
            gridcolor=cor_grade,
        ),
    )
    fig.update_traces(
        textfont=dict(color=cor_texto, size=13),
        selector=dict(type="bar"),
    )


def render_grafico_valores_pagamento(valor_pago, valor_a_pagar, chart_key=None):
    graf_pagamento = pd.DataFrame(
        {
            "Status": ["Pago", "A pagar"],
            "Valor": [valor_pago, valor_a_pagar],
        }
    )
    graf_pagamento["Rotulo"] = graf_pagamento["Valor"].map(format_brl)

    fig_pagamento = px.bar(
        graf_pagamento,
        x="Status",
        y="Valor",
        color="Status",
        text="Rotulo",
        color_discrete_map={"Pago": "#22c55e", "A pagar": "#f97316"},
    )
    fig_pagamento.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=380,
        paper_bgcolor="white",
        plot_bgcolor="white",
        xaxis_title="",
        yaxis_title="Valor (R$)",
        showlegend=False,
    )
    aplicar_estilo_grafico_legivel(fig_pagamento)
    fig_pagamento.update_traces(textposition="outside")
    fig_pagamento.update_yaxes(tickformat=",.2f")

    st.plotly_chart(fig_pagamento, width="stretch", key=chart_key)


def render_midias_empresas(df):
    st.markdown(
        '<div class="section-title">🏢 Empresas</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div id="empresas-page"></div>', unsafe_allow_html=True)

    df_empresas = df[df["Empresa"].astype(str).str.strip().ne("")].copy()

    if df_empresas.empty:
        st.info("Nenhuma empresa encontrada na planilha.")
        return

    empresas_disponiveis = sorted(df_empresas["Empresa"].astype(str).str.strip().unique())

    with st.container(border=True):
        empresa_selecionada = st.selectbox(
            "Empresa",
            options=empresas_disponiveis,
            key="empresa_selecionada_midias",
        )

    df_selecionado = df_empresas[
        df_empresas["Empresa"].astype(str).str.strip() == empresa_selecionada
    ]

    postagens_feitas, postagens_a_fazer, valor_pago, valor_a_pagar = calcular_metricas_empresa(
        df_selecionado
    )

    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    with c1:
        metric_card(
            "Publicações feitas",
            f"{postagens_feitas}",
            "status da arte = Pronto",
            "metric-card-green",
        )
    with c2:
        metric_card(
            "Publicações a fazer",
            f"{postagens_a_fazer}",
            "status diferente de Pronto",
            "metric-card-orange",
        )
    with c3:
        metric_card(
            "Valor pago",
            format_brl(valor_pago),
            "status pagamento = Pago",
            "metric-card-green",
        )
    with c4:
        metric_card(
            "Valor a pagar",
            format_brl(valor_a_pagar),
            "status pagamento = A pagar",
            "metric-card-orange",
        )


def form_field_label(text):
    st.markdown(
        f'<div class="form-field-label">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def acessos_block_title(text):
    st.markdown(
        f'<div class="form-field-label acessos-block-title">{html.escape(text)}</div>',
        unsafe_allow_html=True,
    )


def montar_data_publicacao(mes_nome, dia_txt):
    dia = str(dia_txt).strip()
    if not dia or not mes_nome:
        return ""

    try:
        dia_int = int(dia)
        mes_int = MESES_ORDEM.index(mes_nome) + 1
        ano = date.today().year
        return f"{dia_int:02d}/{mes_int:02d}/{ano}"
    except (ValueError, IndexError):
        return dia


def opcoes_padrao_recorrencia(mes_nome=None):
    if mes_nome:
        return [
            f"Toda {dia} no mês de {mes_nome}"
            for dia in DIAS_SEMANA_RECORRENCIA
        ]
    return [f"Toda {dia}" for dia in DIAS_SEMANA_RECORRENCIA]


def padrao_recorrencia_completo(padrao, mes_nome):
    texto = str(padrao or "").strip()
    if not texto or not mes_nome:
        return texto
    if "no mês de" in texto.lower():
        return texto
    dia_encontrado = next(
        (dia for dia in DIAS_SEMANA_RECORRENCIA if dia in texto.lower()),
        None,
    )
    if dia_encontrado:
        return f"Toda {dia_encontrado} no mês de {mes_nome}"
    return texto


def datas_dia_semana_form_mes(mes_nome, dia_abrev, ano=None):
    weekday = DIA_SEMANA_FORM_WEEKDAY.get(str(dia_abrev).strip())
    if weekday is None or not mes_nome:
        return []

    ano = ano or date.today().year
    mes_int = MESES_ORDEM.index(mes_nome) + 1
    ultimo_dia = calendar.monthrange(ano, mes_int)[1]
    return [
        date(ano, mes_int, dia)
        for dia in range(1, ultimo_dia + 1)
        if date(ano, mes_int, dia).weekday() == weekday
    ]


def data_publicacao_por_dia_form(mes_nome, dia_abrev, ano=None):
    datas = datas_dia_semana_form_mes(mes_nome, dia_abrev, ano)
    if not datas:
        return None

    hoje = date.today()
    ano_ref = ano or hoje.year
    mes_int = MESES_ORDEM.index(mes_nome) + 1

    if hoje.year == ano_ref and hoje.month == mes_int:
        proximas = [item for item in datas if item >= hoje]
        if proximas:
            return proximas[0]

    return datas[0]


def montar_linha_nova_arte(
    mes,
    semana_linha,
    empresa_final,
    tema,
    valor_num_val,
    status_pagamento_planilha,
    tipo_arte,
    status_arte_planilha,
    data_linha,
    servico,
    recorrencia_linha,
):
    return [
        mes,
        semana_linha,
        empresa_final,
        tema.strip(),
        float(valor_num_val),
        status_pagamento_planilha,
        tipo_arte,
        status_arte_planilha,
        data_linha,
        servico,
        recorrencia_linha,
    ]


def weekday_do_padrao_recorrencia(padrao):
    texto = str(padrao).strip().lower()
    for idx, dia in enumerate(DIAS_SEMANA_RECORRENCIA):
        if dia in texto:
            return idx
    return None


def datas_recorrencia_mes(mes_nome, padrao, ano=None):
    weekday = weekday_do_padrao_recorrencia(padrao)
    if weekday is None or not mes_nome:
        return []

    ano = ano or date.today().year
    mes_int = MESES_ORDEM.index(mes_nome) + 1
    ultimo_dia = calendar.monthrange(ano, mes_int)[1]
    return [
        date(ano, mes_int, dia)
        for dia in range(1, ultimo_dia + 1)
        if date(ano, mes_int, dia).weekday() == weekday
    ]


def indice_semana_por_dia(dia: int) -> int:
    if dia <= 7:
        return 0
    if dia <= 14:
        return 1
    if dia <= 21:
        return 2
    if dia <= 28:
        return 3
    return 4


def indice_semana_valor(valor) -> int | None:
    texto = str(valor).strip().lower()
    if not texto or texto == "nan":
        return None

    termos_por_semana = [
        ("primeira", "1ª", "1a"),
        ("segunda", "2ª", "2a"),
        ("terceira", "3ª", "3a"),
        ("quarta", "4ª", "4a"),
        ("quinta", "5ª", "5a"),
    ]

    for idx, termos in enumerate(termos_por_semana):
        if any(termo in texto for termo in termos):
            return idx
        if texto in (str(idx + 1), f"{idx + 1}ª"):
            return idx

    return None


def mes_atual_nome():
    return MESES_ORDEM[date.today().month - 1]


def semana_atual_rotulo():
    return SEMANA_OPTIONS[indice_semana_por_dia(date.today().day)]


def intervalo_semana_atual(ref=None):
    ref = ref or date.today()
    limites = [(1, 7), (8, 14), (15, 21), (22, 28), (29, 31)]
    inicio_dia, fim_dia = limites[indice_semana_por_dia(ref.day)]
    ultimo_dia_mes = calendar.monthrange(ref.year, ref.month)[1]
    fim_dia = min(fim_dia, ultimo_dia_mes)
    return date(ref.year, ref.month, inicio_dia), date(ref.year, ref.month, fim_dia)


def intervalo_mes(mes_nome, ref_year=None):
    ref_year = ref_year or date.today().year
    mes_int = MESES_ORDEM.index(mes_nome) + 1
    ultimo_dia = calendar.monthrange(ref_year, mes_int)[1]
    return date(ref_year, mes_int, 1), date(ref_year, mes_int, ultimo_dia)


def alinhar_filtro_publicacoes_apos_cadastro(data_ref, mes_nome):
    if not data_ref:
        return

    inicio, fim = intervalo_semana_atual(data_ref)
    st.session_state["pub_data_inicio"] = inicio
    st.session_state["pub_data_fim"] = fim
    if mes_nome and mes_nome in MESES_ORDEM:
        st.session_state["pub_mes_select"] = mes_nome
    st.session_state["pub_destaque_tema"] = ""


def atualizar_datas_por_mes_selecionado():
    mes_sel = st.session_state.get("pub_mes_select", "Todos")
    if mes_sel and mes_sel != "Todos":
        data_ini, data_fim_mes = intervalo_mes(mes_sel)
        st.session_state["pub_data_inicio"] = data_ini
        st.session_state["pub_data_fim"] = data_fim_mes


def semana_atual_em_opcoes(semanas_disponiveis):
    idx_atual = indice_semana_por_dia(date.today().day)
    for semana in semanas_disponiveis:
        if indice_semana_valor(semana) == idx_atual:
            return semana
    return SEMANA_OPTIONS[idx_atual]


def semana_por_dia_mes(mes_nome, dia_txt):
    dia = str(dia_txt).strip()
    if not dia:
        return None, "Informe o dia."

    try:
        dia_int = int(dia)
    except ValueError:
        return None, "Informe um dia válido."

    if dia_int < 1 or dia_int > 31:
        return None, "Informe um dia entre 1 e 31."

    if mes_nome:
        mes_int = MESES_ORDEM.index(mes_nome) + 1
        ultimo_dia = calendar.monthrange(date.today().year, mes_int)[1]
        if dia_int > ultimo_dia:
            return None, f"O mês de {mes_nome} tem apenas {ultimo_dia} dias."

    return SEMANA_OPTIONS[indice_semana_por_dia(dia_int)], ""


def indice_semana_linha(row) -> int | None:
    idx = indice_semana_valor(row.get("Semana"))
    if idx is not None:
        return idx

    data_pub = row.get("Data Publicação")
    if pd.notna(data_pub):
        return indice_semana_por_dia(int(data_pub.day))

    return None


def render_midias_nova_arte(df):
    st.markdown(
        f'<div class="section-title">🎨 Nova Arte <span style="font-size:12px;color:#64748b;font-weight:600;">({APP_UI_VERSION})</span></div>',
        unsafe_allow_html=True
    )
    st.markdown('<div id="nova-arte-page"></div>', unsafe_allow_html=True)

    if st.session_state.get("nova_arte_msg_sucesso"):
        st.success(st.session_state.pop("nova_arte_msg_sucesso"))

    empresas_planilha = sorted(
        {
            str(item).strip()
            for item in df["Empresa"].dropna().astype(str).tolist()
            if str(item).strip()
        }
    )
    opcoes_empresa = empresas_planilha + ["Outra"]

    with st.container(border=True):
        form_field_label("Empresas")
        empresa_opcao = st.selectbox(
            "Empresas",
            options=opcoes_empresa,
            index=None,
            placeholder="Selecione a empresa",
            key="nova_arte_empresa_opcao",
            label_visibility="collapsed",
        )

        empresa_outra = ""
        if empresa_opcao == "Outra":
            form_field_label("Nome da nova empresa")
            empresa_outra = st.text_input(
                "Nome da nova empresa",
                placeholder="Digite o nome da empresa",
                key="nova_arte_empresa_outra",
                label_visibility="collapsed",
            )

        form_field_label("Serviços")
        servico = st.selectbox(
            "Serviços",
            SERVICO_OPTIONS,
            index=None,
            placeholder="Selecione o serviço",
            key="nova_arte_servico",
            label_visibility="collapsed",
        )

        col_mes, col_rec = st.columns(2)
        with col_mes:
            form_field_label("Mês")
            mes = st.selectbox(
                "Mês",
                MESES_ORDEM,
                index=None,
                placeholder="Selecione o mês",
                key="nova_arte_mes",
                label_visibility="collapsed",
            )
        with col_rec:
            form_field_label("Recorrência")
            recorrencia = st.selectbox(
                "Recorrência",
                RECORRENCIA_OPTIONS,
                index=None,
                placeholder="Selecione Sim ou Não",
                key="nova_arte_recorrencia",
                label_visibility="collapsed",
            )

        padrao_recorrencia = None
        if recorrencia == "Sim":
            form_field_label("Padrão de recorrência")
            padrao_recorrencia = st.selectbox(
                "Padrão de recorrência",
                options=opcoes_padrao_recorrencia(mes),
                index=None,
                placeholder="Selecione o dia da semana",
                key="nova_arte_padrao_recorrencia",
                label_visibility="collapsed",
            )
            if not mes:
                st.caption("Selecione também o **mês** para aplicar a recorrência.")

        c1, c2 = st.columns(2)

        with c1:
            form_field_label("Tema")
            tema = st.text_input(
                "Tema",
                placeholder="Descrição da publicação",
                key="nova_arte_tema",
                label_visibility="collapsed",
            )
            form_field_label("Tipo")
            tipo_arte = st.selectbox(
                "Tipo",
                TIPO_ARTE_OPTIONS,
                index=None,
                placeholder="Selecione o tipo",
                key="nova_arte_tipo",
                label_visibility="collapsed",
            )
            form_field_label("Dia")
            dia = st.selectbox(
                "Dia",
                DIA_SEMANA_FORM_OPTIONS,
                index=None,
                placeholder="Selecione o dia",
                key="nova_arte_dia",
                label_visibility="collapsed",
            )

        with c2:
            form_field_label("Status")
            status_arte = st.selectbox(
                "Status",
                STATUS_ARTE_FORM_OPTIONS,
                index=None,
                placeholder="Selecione o status",
                key="nova_arte_status",
                label_visibility="collapsed",
            )
            form_field_label("Status pagamento")
            status_pagamento = st.selectbox(
                "Status pagamento",
                STATUS_PAGAMENTO_FORM_OPTIONS,
                index=None,
                placeholder="Pago ou A Pagar",
                key="nova_arte_status_pagamento",
                label_visibility="collapsed",
            )
            form_field_label("Valor da arte")
            valor_arte = st.text_input(
                "Valor da arte",
                placeholder="Ex.: 38,00",
                key="nova_arte_valor",
                label_visibility="collapsed",
            )

        cadastrar = st.button("Cadastrar nova arte", width="stretch", key="nova_arte_cadastrar")

    if cadastrar:
        if not empresa_opcao:
            st.warning("Selecione uma empresa.")
            return

        if empresa_opcao == "Outra":
            empresa_final = empresa_outra.strip()
        else:
            empresa_final = empresa_opcao

        if not empresa_final:
            st.warning('Escolha "Outra" e informe o nome da nova empresa.')
            return

        if not mes:
            st.warning("Selecione o mês.")
            return

        if not recorrencia:
            st.warning("Selecione se a arte tem recorrência (Sim ou Não).")
            return

        if recorrencia == "Sim":
            if not mes:
                st.warning("Selecione o mês para aplicar a recorrência.")
                return
            if not padrao_recorrencia:
                st.warning("Selecione o padrão de recorrência.")
                return
            padrao_recorrencia = padrao_recorrencia_completo(padrao_recorrencia, mes)
        else:
            if not dia:
                st.warning("Selecione o dia da semana.")
                return
            data_ref = data_publicacao_por_dia_form(mes, dia)
            if not data_ref:
                st.warning("Não foi possível encontrar essa data no mês selecionado.")
                return

        if not servico:
            st.warning("Selecione um serviço.")
            return

        if not tema.strip():
            st.warning("Preencha o campo Tema.")
            return

        if not tipo_arte:
            st.warning("Selecione o tipo.")
            return

        if not status_arte:
            st.warning("Selecione o status.")
            return

        if not status_pagamento:
            st.warning("Selecione o status de pagamento.")
            return

        valor_txt = str(valor_arte).strip()
        if not valor_txt:
            st.warning("Informe o valor da arte.")
            return

        valor_num_val = parse_valor_texto(valor_txt)
        if valor_num_val < 0:
            st.warning("Informe um valor válido para a arte.")
            return

        data_publicacao = ""
        status_arte_planilha = STATUS_ARTE_SHEET_MAP.get(status_arte, status_arte)
        status_pagamento_planilha = STATUS_PAGAMENTO_SHEET_MAP.get(
            status_pagamento,
            status_pagamento,
        )

        def montar_linha_planilha(semana_linha, data_linha, recorrencia_linha):
            return montar_linha_nova_arte(
                mes,
                semana_linha,
                empresa_final,
                tema,
                valor_num_val,
                status_pagamento_planilha,
                tipo_arte,
                status_arte_planilha,
                data_linha,
                servico,
                recorrencia_linha,
            )

        linhas_novas = []
        if recorrencia == "Sim":
            datas_recorrencia = datas_recorrencia_mes(mes, padrao_recorrencia)
            if not datas_recorrencia:
                st.warning("Não foi possível gerar as datas para o padrão selecionado.")
                return

            for data_item in datas_recorrencia:
                semana_linha = SEMANA_OPTIONS[indice_semana_por_dia(data_item.day)]
                data_linha = data_item.strftime("%d/%m/%Y")
                linhas_novas.append(
                    montar_linha_planilha(semana_linha, data_linha, padrao_recorrencia)
                )
        else:
            semana = SEMANA_OPTIONS[indice_semana_por_dia(data_ref.day)]
            data_publicacao = data_ref.strftime("%d/%m/%Y")
            linhas_novas.append(montar_linha_planilha(semana, data_publicacao, "Não"))

        try:
            with st.spinner("Salvando atividade na planilha..."):
                append_linhas_midia(linhas_novas)
        except ConnectionError as exc:
            st.error("❌ Não foi possível conectar com a planilha Google.")
            st.caption(f"Detalhe técnico: {exc}")
            return
        except Exception as exc:
            st.error(mensagem_erro_planilha(exc))
            st.caption(f"Detalhe técnico: {exc}")
            return

        invalidar_cache_midias()
        if recorrencia == "Sim" and datas_recorrencia:
            data_ini, data_fim_mes = intervalo_mes(mes)
            st.session_state["pub_data_inicio"] = data_ini
            st.session_state["pub_data_fim"] = data_fim_mes
            if mes in MESES_ORDEM:
                st.session_state["pub_mes_select"] = mes
        else:
            alinhar_filtro_publicacoes_apos_cadastro(data_ref, mes)
            st.session_state["pub_destaque_tema"] = tema.strip().lower()

        for key in [
            "nova_arte_empresa_opcao",
            "nova_arte_empresa_outra",
            "nova_arte_servico",
            "nova_arte_mes",
            "nova_arte_recorrencia",
            "nova_arte_tema",
            "nova_arte_tipo",
            "nova_arte_dia",
            "nova_arte_status",
            "nova_arte_status_pagamento",
            "nova_arte_valor",
            "nova_arte_padrao_recorrencia",
        ]:
            st.session_state.pop(key, None)
        if recorrencia == "Sim":
            st.session_state["nova_arte_msg_sucesso"] = (
                f"Nova arte cadastrada com sucesso! "
                f"{len(linhas_novas)} publicação(ões) recorrente(s) criada(s)."
            )
        else:
            st.session_state["nova_arte_msg_sucesso"] = (
                f"Nova arte cadastrada para {data_publicacao}! "
                f"Vá em **Publicações** — o filtro já foi ajustado para essa data."
            )
        st.rerun()


def _render_gestao_trafego_form():
    st.markdown(
        '<div class="traffic-greeting">Apresentação de resultados</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="traffic-intro">Preencha os dados da campanha e abra a apresentação para gerar uma tela pronta para print.</div>',
        unsafe_allow_html=True
    )

    st.markdown('<div class="traffic-divider"></div>', unsafe_allow_html=True)

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

    st.divider()

    abrir_apresentacao = st.button(
        "Abrir apresentação",
        width="stretch",
        key="btn_abrir_apresentacao"
    )

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


def render_gestao_trafego():
    st.markdown('<div id="trafego-page"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        _render_gestao_trafego_form()


def render_user_access_detail(user, usuario_logado):
    status_txt = "Ativo" if user["active"] else "Bloqueado"
    status_class = "status-pronto" if user["active"] else "status-pausado"
    st.markdown(
        f'<div class="row-meta"><b>Usuário:</b> {html.escape(user["username"])} &nbsp;&nbsp; '
        f'<b>Perfil:</b> {html.escape(ROLE_LABELS.get(user["role"], user["role"]))} &nbsp;&nbsp; '
        f'<b>Status:</b> <span class="status-pill {status_class}">{status_txt}</span></div>',
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
    st.markdown("**Permissões de acesso**")

    novas_permissoes = {}
    perm_row1 = st.columns(3)
    perm_row2 = st.columns(2)

    for col, area in zip(perm_row1, CONTENT_AREAS[:3]):
        with col:
            form_field_label(area)
            valor_atual = user["permissions"].get(area, "Não")
            if valor_atual not in PERMISSION_OPTIONS:
                valor_atual = "Não"
            novas_permissoes[area] = st.selectbox(
                area,
                PERMISSION_OPTIONS,
                index=PERMISSION_OPTIONS.index(valor_atual),
                key=f"perm_{user['row_number']}_{area}",
                label_visibility="collapsed",
            )

    for col, area in zip(perm_row2, CONTENT_AREAS[3:]):
        with col:
            form_field_label(area)
            valor_atual = user["permissions"].get(area, "Não")
            if valor_atual not in PERMISSION_OPTIONS:
                valor_atual = "Não"
            novas_permissoes[area] = st.selectbox(
                area,
                PERMISSION_OPTIONS,
                index=PERMISSION_OPTIONS.index(valor_atual),
                key=f"perm_{user['row_number']}_{area}",
                label_visibility="collapsed",
            )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    action1, action2 = st.columns(2)
    with action1:
        if st.button(
            "Salvar permissões",
            key=f"salvar_perm_{user['row_number']}",
            width="stretch",
        ):
            update_user_permissions(user["row_number"], novas_permissoes)
            if user["username"] == usuario_logado:
                st.session_state.user_permissions = permissions_to_nav_list(novas_permissoes)
            st.success("Permissões atualizadas.")
            st.rerun()

    with action2:
        if user["active"]:
            if st.button(
                "Bloquear usuário",
                key=f"bloquear_{user['row_number']}",
                width="stretch",
            ):
                if user["username"] == usuario_logado:
                    st.warning("Você não pode bloquear seu próprio acesso.")
                else:
                    set_user_active(user["row_number"], False)
                    st.success("Usuário bloqueado.")
                    st.rerun()
        elif st.button(
            "Desbloquear usuário",
            key=f"desbloquear_{user['row_number']}",
            width="stretch",
        ):
            set_user_active(user["row_number"], True)
            st.success("Usuário desbloqueado.")
            st.rerun()


def render_acessos():
    ensure_default_users_in_sheet()
    st.markdown(
        '<div class="section-title">🔐 Acessos do painel</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div id="acessos-page"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="small-note">Selecione um usuário na lista para ver e editar os acessos. '
        "Marque <b>Sim</b> ou <b>Não</b> em cada conteúdo e use <b>Bloquear</b> ou <b>Desbloquear</b> quando necessário.</div>",
        unsafe_allow_html=True,
    )

    perfil_atual = get_user_role()
    usuarios = load_users_sheet_rows()
    usuario_logado = st.session_state.get("logged_username", "")

    if not usuarios:
        st.info("Não foi possível carregar os usuários da planilha.")
        return

    usuarios_gerenciaveis = [
        user
        for user in usuarios
        if user["row_number"] is not None and can_manage_user(perfil_atual, user)
    ]

    with st.container(border=True):
        acessos_block_title("Usuários")

        if not usuarios_gerenciaveis:
            st.info("Nenhum usuário disponível para gerenciar.")
        else:
            opcoes_usuarios = {
                user["username"]: user for user in sorted(usuarios_gerenciaveis, key=lambda item: item["username"])
            }

            def formatar_usuario_lista(username):
                user = opcoes_usuarios[username]
                status = "Ativo" if user["active"] else "Bloqueado"
                perfil = ROLE_LABELS.get(user["role"], user["role"])
                return f"{username} — {perfil} — {status}"

            form_field_label("Selecione o usuário")
            usuario_selecionado = st.selectbox(
                "Selecione o usuário",
                options=list(opcoes_usuarios.keys()),
                format_func=formatar_usuario_lista,
                key="acesso_usuario_selecionado",
                label_visibility="collapsed",
            )

            with st.container(border=True):
                acessos_block_title("Acessos do usuário selecionado")
                render_user_access_detail(opcoes_usuarios[usuario_selecionado], usuario_logado)

    roles_permitidos = roles_criaveis_por(perfil_atual)
    if not roles_permitidos:
        return

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        acessos_block_title("Cadastrar novo usuário")

        with st.form("cadastro_acesso_form", clear_on_submit=True):
            c1, c2 = st.columns(2)

            with c1:
                form_field_label("Usuário")
                novo_usuario = st.text_input(
                    "Usuário",
                    placeholder="Ex.: maria.designer",
                    key="acesso_novo_usuario",
                    label_visibility="collapsed",
                )
                form_field_label("Perfil de acesso")
                perfil_novo = st.selectbox(
                    "Perfil de acesso",
                    options=roles_permitidos,
                    format_func=lambda role: ROLE_LABELS.get(role, role.title()),
                    key="acesso_novo_perfil",
                    label_visibility="collapsed",
                )

            with c2:
                form_field_label("Senha")
                nova_senha = st.text_input(
                    "Senha",
                    placeholder="Digite a senha",
                    type="password",
                    key="acesso_nova_senha",
                    label_visibility="collapsed",
                )
                form_field_label("Confirmar senha")
                confirmar_senha = st.text_input(
                    "Confirmar senha",
                    placeholder="Repita a senha",
                    type="password",
                    key="acesso_confirmar_senha",
                    label_visibility="collapsed",
                )

            cadastrar = st.form_submit_button("Cadastrar usuário", width="stretch")

        if cadastrar:
            if nova_senha.strip() != confirmar_senha.strip():
                st.warning("As senhas informadas não conferem.")
            else:
                ok, mensagem = register_user(
                    novo_usuario,
                    nova_senha,
                    perfil_novo,
                    perfil_atual,
                )
                if ok:
                    st.success(mensagem)
                    st.rerun()
                else:
                    st.warning(mensagem)


# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------

if not st.session_state.logged_in:
    show_login()
    st.stop()

ensure_auth_session()
manter_conexao_viva()

user_role = get_user_role()
area_dashboard = enforce_area_access(
    st.session_state.get("area_dashboard", default_area_for_role(user_role)),
)
st.session_state.area_dashboard = area_dashboard
area_dashboard = render_sidebar_navigation()
render_sidebar_show_button()
sync_sidebar_toggle_state()
render_dashboard_top(area_dashboard)

if area_dashboard == "Gestão de Tráfego":
    render_gestao_trafego()
    st.stop()

if area_dashboard == NAV_ACESSOS:
    render_acessos()
    st.stop()

# ---------------------------------------------------
# CONEXÃO GOOGLE
# ---------------------------------------------------

# connect_sheet() definido junto de connect_media_worksheet()

# ---------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------

EXPECTED_MEDIA_HEADERS = [
    "Mês",
    "Semana",
    "Empresa",
    "Tema",
    "Valor",
    "Status Pagamento",
    "Tipo de arte",
    "Status da arte",
    "Data Publicação",
    "Serviços",
    "Recorrência",
]


def normalize_header_name(value):
    return str(value).replace("\u00a0", " ").strip()


def normalize_header_key(value):
    text_value = normalize_header_name(value).lower()

    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e",
        "í": "i",
        "ó": "o", "ô": "o", "õ": "o",
        "ú": "u",
        "ç": "c",
    }

    for old, new in replacements.items():
        text_value = text_value.replace(old, new)

    text_value = re.sub(r"\s+", " ", text_value)
    return text_value.strip()


HEADER_ALIASES = {
    "Mês": ["mes", "mês"],
    "Semana": ["semana"],
    "Empresa": ["empresa", "cliente"],
    "Tema": ["tema", "atividade", "nome da atividade"],
    "Valor": ["valor", "preco", "preço", "valor da arte", "valor arte", "preco da arte"],
    "Status Pagamento": [
        "status pagamento",
        "status de pagamento",
        "pagamento",
    ],
    "Tipo de arte": [
        "tipo de arte",
        "tipo arte",
        "formato",
    ],
    "Status da arte": [
        "status da arte",
        "status arte",
    ],
    "Data Publicação": [
        "data publicacao",
        "data de publicacao",
        "data publicação",
        "data de publicação",
        "publicacao",
        "publicação",
        "data",
    ],
    "Serviços": [
        "servicos",
        "serviços",
        "servico",
        "serviço",
    ],
    "Recorrência": [
        "recorrencia",
        "recorrência",
        "padrao recorrencia",
        "padrão recorrência",
    ],
}


def count_non_empty_column(rows, column_index):
    total = 0

    for row in rows:
        if column_index < len(row) and str(row[column_index]).strip():
            total += 1

    return total


def count_parseable_dates(rows, column_index):
    total = 0

    for row in rows:
        if column_index >= len(row):
            continue

        value = str(row[column_index]).strip()

        if not value:
            continue

        parsed = parse_data_publicacao(value)

        if pd.notna(parsed):
            total += 1

    return total


def count_parseable_valores(rows, column_index):
    total = 0

    for row in rows:
        if column_index >= len(row):
            continue

        if parse_valor_texto(row[column_index]) > 0:
            total += 1

    return total


def count_payment_status_values(rows, column_index):
    total = 0

    for row in rows:
        if column_index >= len(row):
            continue

        texto = str(row[column_index]).strip().lower()
        if texto in ("pago", "a pagar", "a pagar"):
            total += 1
        elif "pagar" in texto and "data" not in texto:
            total += 1

    return total


def detect_payment_column(raw_headers, data_rows, used_indexes):
    candidates = find_header_candidates(raw_headers, "Status Pagamento")
    if candidates:
        return max(
            candidates,
            key=lambda index: count_payment_status_values(data_rows, index),
        )

    best_index = None
    best_score = 0

    for index in range(len(raw_headers)):
        if index in used_indexes:
            continue

        score = count_payment_status_values(data_rows, index)
        if score > best_score:
            best_score = score
            best_index = index

    return best_index if best_score > 0 else None


def detect_valor_column(raw_headers, data_rows, selected_indexes, used_indexes):
    current_index = selected_indexes.get("Valor")
    if current_index is not None and count_parseable_valores(data_rows, current_index) > 0:
        return current_index

    header_candidates = find_header_candidates(raw_headers, "Valor")
    best_header_index = None
    best_header_score = 0

    for index in header_candidates:
        score = count_parseable_valores(data_rows, index)
        if score > best_header_score:
            best_header_score = score
            best_header_index = index

    if best_header_index is not None:
        return best_header_index

    if count_parseable_valores(data_rows, 4) > 0:
        return 4

    best_index = None
    best_score = 0

    for index in range(len(raw_headers)):
        if index in used_indexes and index != current_index:
            continue

        score = count_parseable_valores(data_rows, index)
        if score > best_score:
            best_score = score
            best_index = index

    return best_index if best_index is not None else current_index


def find_header_candidates(raw_headers, expected_header):
    accepted = {
        normalize_header_key(alias)
        for alias in HEADER_ALIASES.get(expected_header, [expected_header])
    }

    accepted.add(normalize_header_key(expected_header))

    return [
        index
        for index, header in enumerate(raw_headers)
        if normalize_header_key(header) in accepted
    ]


def converter_linha_midia_para_planilha(headers, linha_valores):
    campos = [
        "Mês",
        "Semana",
        "Empresa",
        "Tema",
        "Valor",
        "Status Pagamento",
        "Tipo de arte",
        "Status da arte",
        "Data Publicação",
        "Serviços",
        "Recorrência",
    ]
    valores = dict(zip(campos, linha_valores))
    largura = max(len(headers), 11)
    linha_planilha = [""] * largura

    for campo, valor in valores.items():
        candidatos = find_header_candidates(headers, campo)
        if not candidatos:
            indice_fallback = campos.index(campo)
            if indice_fallback < largura:
                linha_planilha[indice_fallback] = valor
            continue

        indice = candidatos[0]
        if indice >= len(linha_planilha):
            linha_planilha.extend([""] * (indice - len(linha_planilha) + 1))
        linha_planilha[indice] = valor

    return linha_planilha


def detect_date_column(raw_headers, data_rows, already_selected):
    candidates = find_header_candidates(raw_headers, "Data Publicação")

    if candidates:
        valid_candidates = [
            index
            for index in candidates
            if count_payment_status_values(data_rows, index)
            <= count_parseable_dates(data_rows, index)
        ]
        pool = valid_candidates or candidates
        return max(
            pool,
            key=lambda index: (
                count_parseable_dates(data_rows, index),
                count_non_empty_column(data_rows, index),
            ),
        )

    available_indexes = [
        index
        for index in range(len(raw_headers))
        if index not in already_selected
    ]

    if not available_indexes:
        return None

    scored_columns = []
    for index in available_indexes:
        dates = count_parseable_dates(data_rows, index)
        payments = count_payment_status_values(data_rows, index)
        if payments > dates:
            continue
        scored_columns.append(
            (
                dates,
                count_non_empty_column(data_rows, index),
                index,
            )
        )

    if not scored_columns:
        return None

    best_dates, _, best_index = max(scored_columns)

    if best_dates > 0:
        return best_index

    return None


def build_media_dataframe(rows):
    """
    Preserva os nomes usados pelo dashboard de Mídias e localiza
    automaticamente a coluna correta de cada informação.
    """
    if not rows:
        return pd.DataFrame(columns=EXPECTED_MEDIA_HEADERS)

    selected_indexes = resolver_indices_colunas_midias(rows)
    data_rows = rows[1:]
    records = []

    for row in data_rows:
        record = {}

        for expected_header in EXPECTED_MEDIA_HEADERS:
            selected_index = selected_indexes.get(expected_header)

            if selected_index is None:
                record[expected_header] = ""
            elif selected_index < len(row):
                record[expected_header] = row[selected_index]
            else:
                record[expected_header] = ""

        records.append(record)

    return pd.DataFrame(records, columns=EXPECTED_MEDIA_HEADERS)


@st.cache_data(ttl=3600, show_spinner=False)
def load_raw_rows():
    worksheet = connect_media_worksheet()
    return executar_operacao_planilha(
        lambda: get_all_values_com_timeout(worksheet)
    )


@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    return build_media_dataframe(load_raw_rows())


def invalidar_cache_midias():
    load_data.clear()
    load_raw_rows.clear()
    st.session_state.pop("df_midias_processado", None)
    st.session_state.pop("_media_col_map", None)


def processar_dataframe_midias(df):
    df = df.copy()

    for col in [
        "Mês",
        "Semana",
        "Empresa",
        "Tema",
        "Status Pagamento",
        "Status da arte",
        "Tipo de arte",
        "Data Publicação",
        "Serviços",
        "Recorrência",
    ]:
        if col not in df.columns:
            df[col] = ""

    df["Data Publicação Raw"] = df["Data Publicação"].astype(str).str.strip()

    if "Valor" in df.columns:
        df["Valor"] = normalizar_valor(df["Valor"]).fillna(0)
    else:
        df["Valor"] = 0.0

    df["Data Publicação"] = df["Data Publicação Raw"].apply(parse_data_publicacao)

    if "Mês" in df.columns:
        df["Mês"] = df["Mês"].astype(str).str.strip()
        mascara_mes_vazio = df["Mês"].eq("") & df["Data Publicação"].notna()
        if mascara_mes_vazio.any():
            mapa_meses = {
                1: "Janeiro",
                2: "Fevereiro",
                3: "Março",
                4: "Abril",
                5: "Maio",
                6: "Junho",
                7: "Julho",
                8: "Agosto",
                9: "Setembro",
                10: "Outubro",
                11: "Novembro",
                12: "Dezembro",
            }
            df.loc[mascara_mes_vazio, "Mês"] = df.loc[
                mascara_mes_vazio, "Data Publicação"
            ].dt.month.map(mapa_meses)

    return df


def carregar_dataframe_midias():
    cache_key = "df_midias_processado"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    try:
        with st.spinner("Carregando dados da planilha..."):
            rows = load_raw_rows()
            atualizar_mapa_colunas_midias(rows)
            df_processado = processar_dataframe_midias(build_media_dataframe(rows))
    except Exception as exc:
        st.error(f"❌ {mensagem_erro_carregamento_midias(exc)}")
        st.caption(f"Detalhe técnico: {exc}")
        if st.button("🔄 Tentar novamente", key="retry_carregar_planilha"):
            invalidar_cache_midias()
            st.rerun()
        st.stop()

    st.session_state[cache_key] = df_processado
    return df_processado


df = carregar_dataframe_midias()

# ---------------------------------------------------
# MÍDIAS
# ---------------------------------------------------

if area_dashboard == "Empresas":
    render_midias_empresas(df)
    st.stop()

if area_dashboard == "Nova Arte":
    render_midias_nova_arte(df)
    st.stop()

st.markdown(
    '<div class="section-title">📱 Gestão de publicações e pagamentos</div>',
    unsafe_allow_html=True
)
st.markdown('<div id="publicacoes-page"></div>', unsafe_allow_html=True)

hoje = date.today()
mes_corrente = mes_atual_nome()
data_inicio_default, data_fim_default = intervalo_semana_atual(hoje)

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

st.markdown('<div id="publicacoes-filtros"></div>', unsafe_allow_html=True)

meses_disponiveis = [x for x in df["Mês"].dropna().astype(str).unique().tolist() if x.strip()]
mes_opcoes = ["Todos"] + ordenar_meses(meses_disponiveis)
if mes_corrente not in mes_opcoes:
    mes_opcoes.insert(1, mes_corrente)

empresas_disponiveis = [x for x in df["Empresa"].dropna().astype(str).unique().tolist() if str(x).strip()]

with st.container(border=True):
    f1, f2, f3, f4 = st.columns(4)

    with f1:
        form_field_label("Mês")
        mes = st.selectbox(
            "Mês",
            mes_opcoes,
            index=mes_opcoes.index(mes_corrente),
            key="pub_mes_select",
            on_change=atualizar_datas_por_mes_selecionado,
            label_visibility="collapsed",
        )

    with f2:
        form_field_label("De")
        data_inicio = st.date_input(
            "De",
            value=data_inicio_default,
            format="DD/MM/YYYY",
            key="pub_data_inicio",
            label_visibility="collapsed",
        )

    with f3:
        form_field_label("Até")
        data_fim = st.date_input(
            "Até",
            value=data_fim_default,
            format="DD/MM/YYYY",
            key="pub_data_fim",
            label_visibility="collapsed",
        )

    with f4:
        form_field_label("Empresa")
        empresa = st.selectbox(
            "Empresa",
            ["Todas"] + sorted(empresas_disponiveis),
            label_visibility="collapsed",
        )

periodo_txt = f"{format_date_br(data_inicio)} até {format_date_br(data_fim)}"
if mes != "Todos":
    periodo_txt = f"{mes} — {periodo_txt}"

st.markdown(
    f'<div class="small-note">Mostrando atividades de <b>{periodo_txt}</b>.</div>',
    unsafe_allow_html=True,
)

df_filtrado = df.copy()

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"].astype(str) == empresa]

if data_fim < data_inicio:
    st.warning("A data final deve ser igual ou posterior à data inicial.")
    df_filtrado = df_filtrado.iloc[0:0]
else:
    df_filtrado = df_filtrado[df_filtrado["Data Publicação"].notna()]
    df_filtrado = df_filtrado[
        (df_filtrado["Data Publicação"].dt.date >= data_inicio)
        & (df_filtrado["Data Publicação"].dt.date <= data_fim)
    ]

# ---------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------

postagens_feitas, postagens_a_fazer, valor_pago, valor_a_pagar = calcular_metricas_empresa(
    df_filtrado
)

c1, c2 = st.columns(2)
c3, c4 = st.columns(2)

with c1:
    metric_card(
        "Publicações Feitas",
        f"{postagens_feitas}",
        "status da arte = Pronto",
        "metric-card-green",
    )
with c2:
    metric_card(
        "Publicações A Fazer",
        f"{postagens_a_fazer}",
        "status diferente de Pronto",
        "metric-card-orange",
    )
with c3:
    metric_card(
        "Valor Pago",
        format_brl(valor_pago),
        "status pagamento = Pago",
        "metric-card-green",
    )
with c4:
    metric_card(
        "Valor A Pagar",
        format_brl(valor_a_pagar),
        "status pagamento = A pagar",
        "metric-card-orange",
    )

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------
# GRÁFICOS
# ---------------------------------------------------

filtro_key = chave_filtros_publicacoes(mes, data_inicio, data_fim, empresa)
df_graficos = df_filtrado[linhas_com_conteudo_mask(df_filtrado)].copy()

g1, g2 = st.columns(2)

with g1:
    with st.container(border=True):
        st.markdown('<div class="section-title">📊 Publicações por empresa</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="small-note">Período: <b>{periodo_txt}</b></div>',
            unsafe_allow_html=True,
        )

        graf_empresa = (
            df_graficos.groupby("Empresa", dropna=False)
            .size()
            .reset_index(name="Total")
            .sort_values("Total", ascending=False)
        )

        if not graf_empresa.empty:
            total_grafico = int(graf_empresa["Total"].sum())
            fig_empresa = px.bar(graf_empresa, x="Empresa", y="Total", text="Total")
            fig_empresa.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=380,
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis_title="",
                yaxis_title="Quantidade",
            )
            aplicar_estilo_grafico_legivel(fig_empresa)
            fig_empresa.update_traces(textposition="outside")
            st.plotly_chart(
                fig_empresa,
                width="stretch",
                key=f"graf_empresa_{filtro_key}",
            )
            st.caption(f"Total no período: {total_grafico} publicações")
        else:
            st.info("Sem dados para esse filtro.")

with g2:
    with st.container(border=True):
        st.markdown('<div class="section-title">💳 Valor por status pagamento</div>', unsafe_allow_html=True)
        render_grafico_valores_pagamento(
            valor_pago,
            valor_a_pagar,
            chart_key=f"graf_pagamento_{filtro_key}",
        )

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------
# ATUALIZAR STATUS DA ARTE
# ---------------------------------------------------

with st.container(border=True):
    st.markdown(
        f'<div class="section-title">✏️ Atualizar status da arte <span style="font-size:12px;color:#64748b;font-weight:600;">({APP_UI_VERSION})</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="small-note">Clique nos badges de <b>status</b> e <b>pagamento</b> para alterar. Use o <b>✏️</b> para editar nome, valor ou excluir.</div>',
        unsafe_allow_html=True,
    )

    busca = st.text_input("Buscar por empresa ou tema", placeholder="Ex.: Faiser, mulheres, internet...")

    df_status = df_filtrado.copy()
    df_status = df_status.sort_values(
        by="Data Publicação",
        ascending=False,
        na_position="last",
    )

    destaque_tema = str(st.session_state.get("pub_destaque_tema", "")).strip().lower()

    if busca.strip():
        termo = busca.strip().lower()
        df_status = df_status[
            df_status["Empresa"].astype(str).str.lower().str.contains(termo, na=False)
            | df_status["Tema"].astype(str).str.lower().str.contains(termo, na=False)
        ]

    for index, row in df_status.iterrows():
        empresa_txt = str(row.get("Empresa", "")).strip() or "-"
        tema_txt = str(row.get("Tema", "")).strip() or "-"
        mes_txt = str(row.get("Mês", "")).strip() or "-"
        tipo_txt = str(row.get("Tipo de arte", "")).strip() or "-"
        servico_txt = str(row.get("Serviços", "")).strip() or "-"
        status_arte_txt = str(row.get("Status da arte", "")).strip() or "-"
        status_pagamento_txt = str(row.get("Status Pagamento", "")).strip() or "A pagar"
        valor_num = float(row.get("Valor", 0) or 0)

        if pd.notnull(row.get("Data Publicação")):
            data_txt = row["Data Publicação"].strftime("%d/%m/%Y")
        else:
            data_txt = str(row.get("Data Publicação Raw", "")).strip() or "-"

        edit_key = f"pub_edit_{index}"
        delete_confirm_key = f"pub_delete_confirm_{index}"
        edit_ativo = st.session_state.get(edit_key, False)
        pagamento_atual = status_pagamento_para_edicao(status_pagamento_txt)
        status_atual = status_arte_para_edicao(status_arte_txt)
        empresa_exibicao = empresa_txt if empresa_txt != "-" else "Empresa não informada"
        tema_exibicao = tema_txt if tema_txt != "-" else "Sem tema definido"
        tipo_exibicao = tipo_txt if tipo_txt != "-" else "-"

        with st.container(border=True, key=f"row_card_{index}"):
            if edit_ativo:
                st.markdown(
                    f'<div class="row-empresa-title">Editando: {html.escape(empresa_exibicao)}</div>',
                    unsafe_allow_html=True,
                )
                form_field_label("Nome da atividade")
                novo_tema = st.text_input(
                    "Nome da atividade",
                    value=tema_txt if tema_txt != "-" else "",
                    key=f"tema_input_{index}",
                    label_visibility="collapsed",
                )
                form_field_label("Valor")
                novo_valor = st.text_input(
                    "Valor",
                    value=format_valor_input(valor_num),
                    placeholder="Ex.: 38,00",
                    key=f"valor_input_{index}",
                    label_visibility="collapsed",
                )

                if st.session_state.get(delete_confirm_key):
                    st.warning("Tem certeza que deseja excluir esta atividade? Essa ação não pode ser desfeita.")
                    conf1, conf2 = st.columns(2)
                    with conf1:
                        if st.button("Sim, excluir", key=f"confirmar_exclusao_{index}"):
                            excluir_atividade_planilha(index)
                            st.session_state.pop(edit_key, None)
                            st.session_state.pop(delete_confirm_key, None)
                            invalidar_cache_midias()
                            st.rerun()
                    with conf2:
                        if st.button("Não excluir", key=f"cancelar_exclusao_{index}"):
                            st.session_state.pop(delete_confirm_key, None)
                            st.rerun()
                else:
                    ac1, ac2, ac3 = st.columns(3)
                    with ac1:
                        if st.button("Salvar alterações", key=f"salvar_alteracoes_{index}"):
                            pagamento_salvar = st.session_state.get(
                                f"pagamento_inline_{index}",
                                pagamento_atual,
                            )
                            status_salvar = st.session_state.get(
                                f"status_inline_{index}",
                                status_atual,
                            )
                            ok, msg = salvar_atividade_planilha(
                                index,
                                novo_tema,
                                novo_valor,
                                pagamento_salvar,
                                status_salvar,
                            )
                            if ok:
                                st.session_state[edit_key] = False
                                invalidar_cache_midias()
                                st.rerun()
                            else:
                                st.warning(msg)
                    with ac2:
                        if st.button("Cancelar", key=f"cancelar_edicao_{index}"):
                            st.session_state[edit_key] = False
                            st.rerun()
                    with ac3:
                        if st.button("🗑️ Excluir", key=f"excluir_atividade_{index}"):
                            st.session_state[delete_confirm_key] = True
                            st.rerun()
            else:
                c_logo, c_info, c_status, c_pag, c_valor, c_edit = st.columns(
                    [0.7, 3.6, 1.3, 1.3, 1.1, 0.5],
                    vertical_alignment="center",
                )

                with c_logo:
                    st.markdown(card_logo_html(empresa_exibicao), unsafe_allow_html=True)

                with c_info:
                    st.markdown(
                        f'<div class="pub-activity-heading">'
                        f'<div class="row-empresa-title">{html.escape(empresa_exibicao)}</div>'
                        f'<div class="row-tema-subtitle">{html.escape(tema_exibicao)}</div>'
                        f'<div class="pub-card-meta">'
                        f'<span class="pub-card-meta-item">📅 {html.escape(mes_txt)}</span>'
                        f'<span class="pub-card-meta-item">📅 {html.escape(data_txt)}</span>'
                        f'<span class="pub-card-meta-item">🎬 {html.escape(tipo_exibicao)}</span>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                with c_status:
                    st.selectbox(
                        "Status da arte",
                        STATUS_ARTE_EDIT_OPTIONS,
                        index=indice_select(STATUS_ARTE_EDIT_OPTIONS, status_atual),
                        format_func=format_status_pill_option,
                        key=f"status_inline_{index}",
                        label_visibility="collapsed",
                        on_change=salvar_status_arte_inline,
                        args=(index,),
                    )

                with c_pag:
                    st.selectbox(
                        "Pagamento",
                        STATUS_PAGAMENTO_FORM_OPTIONS,
                        index=indice_select(STATUS_PAGAMENTO_FORM_OPTIONS, pagamento_atual),
                        format_func=format_pagamento_pill_option,
                        key=f"pagamento_inline_{index}",
                        label_visibility="collapsed",
                        on_change=salvar_pagamento_inline,
                        args=(index,),
                    )

                with c_valor:
                    st.markdown(
                        f'<div class="pub-card-valor">{format_brl(valor_num)}</div>',
                        unsafe_allow_html=True,
                    )

                with c_edit:
                    if st.button(
                        "✏️",
                        key=f"edit_atividade_{index}",
                        help="Editar atividade",
                    ):
                        st.session_state[edit_key] = True
                        st.rerun()

    if df_status.empty:
        st.info(
            "Nenhum registro encontrado com esse filtro. "
            "Confira o período **De/Até** acima — a atividade pode estar em outra data."
        )
