import base64
import os
from pathlib import Path

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Mídias - Oppi",
    page_icon="📱",
    layout="wide"
)

# ---------------------------------------------------
# LOGIN CONFIG
# ---------------------------------------------------

APP_USER = "operacao"
APP_PASS = "100316"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

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
# CSS (AJUSTE DOS CARDS AQUI)
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
    }

    .logo-round {
        width: 74px;
        height: 74px;
        border-radius: 50%;
        object-fit: cover;
    }

    .top-title {
        text-align: center;
    }

    .top-title .text {
        font-size: 42px;
        font-weight: 800;
        color: #16233b;
    }

    .subtitle {
        text-align: center;
        color: #6b7280;
        font-size: 20px;
        margin-bottom: 26px;
    }

    .filter-card,
    .section-card,
    .table-card,
    .login-card {
        background: #ffffff;
        border-radius: 24px;
        padding: 18px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
    }

    /* 🔥 CORREÇÃO DOS CARDS */
    .metric-card {
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border-left: 7px solid #e11d48;
        border-radius: 24px;
        padding: 18px 20px;
        height: 170px;
        width: 100%;
        box-sizing: border-box;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .metric-title {
        font-size: 15px;
        font-weight: 800;
    }

    .metric-value {
        font-size: 38px;
        font-weight: 900;
    }

    .metric-sub {
        font-size: 13px;
        color: #64748b;
    }

    .stButton > button {
        border-radius: 12px !important;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def format_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def metric_card(title, value, subtitle=""):
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------
# LOGIN
# ---------------------------------------------------

if not st.session_state.logged_in:
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario == APP_USER and senha == APP_PASS:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Erro")

    st.stop()

# ---------------------------------------------------
# GOOGLE
# ---------------------------------------------------

@st.cache_resource
def connect_sheet():
    creds = Credentials.from_service_account_info(
        dict(st.secrets["google"]),
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

@st.cache_data(ttl=60)
def load_data():
    return pd.DataFrame(connect_sheet().get_all_records())

df = load_data()

# ---------------------------------------------------
# TRATAMENTO
# ---------------------------------------------------

df["Valor"] = pd.to_numeric(
    df["Valor"].astype(str)
    .str.replace("R$", "")
    .str.replace(".", "")
    .str.replace(",", "."),
    errors="coerce"
).fillna(0)

df["Data Publicação"] = pd.to_datetime(df["Data Publicação"], dayfirst=True, errors="coerce")

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

st.markdown('<div class="filter-card">', unsafe_allow_html=True)

f1, f2, f3 = st.columns(3)

mes = f1.selectbox("Mês", ["Todos"] + sorted(df["Mês"].dropna().unique()))
semana = f2.selectbox("Semana", ["Todas"] + sorted(df["Semana"].dropna().unique()))
empresa = f3.selectbox("Empresa", ["Todas"] + sorted(df["Empresa"].dropna().unique()))

st.markdown('</div>', unsafe_allow_html=True)

df_filtrado = df.copy()

if mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Mês"] == mes]

if semana != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Semana"] == semana]

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"] == empresa]

# ---------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------

total_posts = len(df_filtrado)
total_valor = df_filtrado["Valor"].sum()

m1, m2, m3, m4, m5, m6 = st.columns(6)

with m1: metric_card("Posts", total_posts)
with m2: metric_card("Valor total", format_brl(total_valor))
with m3: metric_card("Pagos", len(df_filtrado[df_filtrado["Status Pagamento"]=="Pago"]))
with m4: metric_card("A pagar", len(df_filtrado[df_filtrado["Status Pagamento"]=="A pagar"]))
with m5: metric_card("Valor pago", format_brl(df_filtrado[df_filtrado["Status Pagamento"]=="Pago"]["Valor"].sum()))
with m6: metric_card("Valor pendente", format_brl(df_filtrado[df_filtrado["Status Pagamento"]=="A pagar"]["Valor"].sum()))
