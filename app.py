import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Mídias - Oppi",
    page_icon="📱",
    layout="wide"
)

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
        padding-top: 3rem;
        padding-bottom: 2rem;
        max-width: 1450px;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    .logo-wrap {
        display: flex;
        justify-content: center;
        margin-bottom: 0.6rem;
    }

    .logo-wrap img {
        width: 80px;
        height: 80px;
        object-fit: cover;
        border-radius: 50%;
        padding: 6px;
        background: white;
        box-shadow: 0 6px 18px rgba(0,0,0,0.15);
    }

    .top-title {
        text-align: center;
        margin-bottom: 4px;
    }

    .top-title .text {
        font-size: 40px;
        font-weight: 800;
        color: #16233b;
    }

    .subtitle {
        color: #6b7280;
        font-size: 18px;
        margin-bottom: 26px;
        text-align: center;
    }

    .filter-card,
    .section-card,
    .table-card {
        background: #ffffff;
        border: 1px solid #e7ebf3;
        border-radius: 24px;
        padding: 18px;
        box-shadow: 0 6px 20px rgba(15, 23, 42, 0.04);
    }

    .metric-card {
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border-left: 6px solid #e11d48;
        border-radius: 20px;
        padding: 16px;
    }

    .metric-title {
        font-size: 14px;
        font-weight: 700;
        color: #334155;
    }

    .metric-value {
        font-size: 34px;
        font-weight: 900;
    }

    .metric-sub {
        font-size: 12px;
        color: #64748b;
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
    )

def ordenar_meses(lista):
    ordem = {mes: i for i, mes in enumerate(MESES_ORDEM)}
    return sorted(lista, key=lambda x: ordem.get(x, 999))

def metric_card(title, value, subtitle=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

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
    return client.open_by_key(SHEET_ID).get_worksheet(0)

@st.cache_data(ttl=60)
def load_data():
    return pd.DataFrame(connect_sheet().get_all_records())

df = load_data()

# ---------------------------------------------------
# TRATAMENTO
# ---------------------------------------------------

df["Valor"] = pd.to_numeric(normalizar_valor(df["Valor"]), errors="coerce").fillna(0)
df["Data Publicação"] = pd.to_datetime(df["Data Publicação"], dayfirst=True, errors="coerce")

# ---------------------------------------------------
# TOPO
# ---------------------------------------------------

if LOGO_PATH.exists():
    st.markdown('<div class="logo-wrap">', unsafe_allow_html=True)
    st.image(str(LOGO_PATH))
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="top-title">
    <div class="text">Dashboard — Mídias Oppi</div>
</div>
<div class="subtitle">Gestão de publicações e pagamentos</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

st.markdown('<div class="filter-card">', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    mes = st.selectbox("Mês", ["Todos"] + ordenar_meses(df["Mês"].dropna().unique()))

with c2:
    semana = st.selectbox("Semana", ["Todas"] + sorted(df["Semana"].dropna().unique()))

with c3:
    empresa = st.selectbox("Empresa", ["Todas"] + sorted(df["Empresa"].dropna().unique()))

st.markdown('</div>', unsafe_allow_html=True)

df_filtrado = df.copy()

if mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Mês"] == mes]

if semana != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Semana"] == semana]

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"] == empresa]

# ---------------------------------------------------
# KPIs
# ---------------------------------------------------

pagos = df_filtrado[df_filtrado["Status Pagamento"].str.lower() == "pago"]
a_pagar = df_filtrado[df_filtrado["Status Pagamento"].str.lower() == "a pagar"]

m1, m2, m3, m4 = st.columns(4)

with m1:
    metric_card("Posts", len(df_filtrado))
with m2:
    metric_card("Valor total", format_brl(df_filtrado["Valor"].sum()))
with m3:
    metric_card("Pagos", len(pagos))
with m4:
    metric_card("A pagar", len(a_pagar))

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------
# GRÁFICO
# ---------------------------------------------------

graf = df_filtrado.groupby("Empresa").size().reset_index(name="Total")

fig = px.bar(graf, x="Empresa", y="Total")
st.plotly_chart(fig, use_container_width=True)
