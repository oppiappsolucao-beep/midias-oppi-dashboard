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
# LOGIN
# ---------------------------------------------------

if not st.session_state.logged_in:
    show_login()
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

if "Valor" in df.columns:
    df["Valor"] = pd.to_numeric(normalizar_valor(df["Valor"]), errors="coerce").fillna(0)
else:
    df["Valor"] = 0.0

if "Data Publicação" in df.columns:
    df["Data Publicação"] = pd.to_datetime(
        df["Data Publicação"],
        dayfirst=True,
        errors="coerce"
    )
else:
    df["Data Publicação"] = pd.NaT

for col in ["Mês", "Semana", "Empresa", "Tema", "Status Pagamento", "Status da arte", "Tipo de arte"]:
    if col not in df.columns:
        df[col] = ""

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
# TOPO COM LOGO
# ---------------------------------------------------

render_logo(LOGO_PATH)

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
    datas_disponiveis_dt = (
        df["Data Publicação"]
        .dropna()
        .dt.normalize()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )
    datas_disponiveis_str = [d.strftime("%d/%m/%Y") for d in datas_disponiveis_dt]
    datas_selecionadas_str = st.multiselect(
        "Datas publicação",
        options=datas_disponiveis_str,
        default=[]
    )
    datas_selecionadas_dt = {
        pd.to_datetime(d, dayfirst=True).normalize() for d in datas_selecionadas_str
    }

st.markdown('</div>', unsafe_allow_html=True)

df_filtrado = df.copy()

if mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["Mês"].astype(str) == mes]

if semana != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Semana"].astype(str) == semana]

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"].astype(str) == empresa]

if datas_selecionadas_dt:
    df_filtrado = df_filtrado[
        df_filtrado["Data Publicação"].dt.normalize().isin(datas_selecionadas_dt)
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
        data_txt = "-"

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
                st.cache_data.clear()import base64
import html
import mimetypes
import re
from pathlib import Path

import gspread
import pandas as pd
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="Gestão Financeira Oppi",
    page_icon="💸",
    layout="wide"
)

SHEET_ID = "1cQU5tNwSoiepTPHx_Qc7ZF1PcaER2gstW_dZQ0eCrB4"
WORKSHEET_NAME = "Página1"

LOGO_CANDIDATES = [
    "logo_oppi.png",
    "logo_oppi.jpg",
    "logo_oppi.jpeg",
    "logo_oppi.webp",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =========================================================
# ESTILO
# =========================================================
st.markdown("""
<style>
    .stApp {
        background: #f6f7fb;
    }

    .block-container {
        max-width: 1450px;
        padding-top: 3.6rem !important;
        padding-bottom: 2rem;
    }

    .logo-wrap {
        display: flex;
        justify-content: center;
        margin-top: 0.35rem;
        margin-bottom: 0.8rem;
    }

    .logo-circle {
        width: 142px;
        height: 142px;
        border-radius: 50%;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.12);
    }

    .logo-circle img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center center;
        display: block;
    }

    .main-title {
        text-align: center;
        font-size: 2.6rem;
        font-weight: 800;
        color: #14213d;
        margin-bottom: 0.2rem;
        line-height: 1.1;
    }

    .main-subtitle {
        text-align: center;
        font-size: 1.08rem;
        color: #667085;
        margin-bottom: 1.6rem;
    }

    .top-divider, .section-divider {
        width: 100%;
        height: 18px;
        background: #ffffff;
        border: 1px solid #ececf3;
        border-radius: 999px;
        margin: 0.8rem 0 1.35rem 0;
    }

    .filter-label {
        font-size: 0.94rem;
        color: #2f3552;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }

    .kpi-card {
        background: #ffffff;
        border: 1px solid #ececf3;
        border-left: 6px solid #e91e63;
        border-radius: 22px;
        padding: 1.05rem 1.15rem 0.95rem 1.15rem;
        box-shadow: 0 6px 18px rgba(20, 20, 43, 0.05);
        min-height: 150px;
    }

    .kpi-card.roxo { border-left-color: #7c3aed; }
    .kpi-card.rosa { border-left-color: #e91e63; }
    .kpi-card.verde { border-left-color: #10b981; }
    .kpi-card.azul { border-left-color: #3b82f6; }
    .kpi-card.laranja { border-left-color: #f59e0b; }

    .kpi-title {
        font-size: 1rem;
        font-weight: 700;
        color: #28314f;
        margin-bottom: 0.8rem;
    }

    .kpi-value {
        font-size: 2rem;
        font-weight: 800;
        color: #081b4b;
        line-height: 1.05;
        margin-bottom: 0.72rem;
    }

    .kpi-caption {
        font-size: 0.92rem;
        color: #667085;
    }

    .status-triplet-wrap {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        width: 100%;
        height: 100%;
    }

    .status-mini-wrap {
        position: relative;
        min-width: 0;
    }

    .status-mini-card {
        background: #ffffff;
        border: 1px solid #ececf3;
        border-radius: 16px;
        padding: 0.8rem 0.85rem;
        min-height: 150px;
        box-shadow: 0 6px 18px rgba(20, 20, 43, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        cursor: default;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .status-mini-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(20, 20, 43, 0.09);
    }

    .status-mini-card.pago {
        border-left: 5px solid #10b981;
    }

    .status-mini-card.apagar {
        border-left: 5px solid #f59e0b;
    }

    .status-mini-card.areceber {
        border-left: 5px solid #7c3aed;
    }

    .status-mini-title {
        font-size: 0.88rem;
        font-weight: 700;
        color: #28314f;
        margin-bottom: 0.45rem;
        line-height: 1.1;
    }

    .status-mini-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: #081b4b;
        line-height: 1.05;
        margin-bottom: 0.4rem;
    }

    .status-mini-caption {
        font-size: 0.78rem;
        color: #667085;
        line-height: 1.2;
    }

    .status-hover-box {
        position: absolute;
        left: 0;
        top: calc(100% + 8px);
        width: 260px;
        max-width: 320px;
        background: #ffffff;
        border: 1px solid #e8eaf2;
        border-radius: 16px;
        box-shadow: 0 14px 28px rgba(20, 20, 43, 0.12);
        padding: 0.9rem 1rem;
        z-index: 50;
        opacity: 0;
        visibility: hidden;
        transform: translateY(6px);
        transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s ease;
        pointer-events: none;
    }

    .status-mini-wrap:hover .status-hover-box {
        opacity: 1;
        visibility: visible;
        transform: translateY(0);
    }

    .status-hover-title {
        font-size: 0.95rem;
        font-weight: 800;
        color: #14213d;
        margin-bottom: 0.45rem;
    }

    .status-hover-line {
        font-size: 0.87rem;
        color: #5f6b7a;
        margin-bottom: 0.15rem;
    }

    .status-hover-subtitle {
        font-size: 0.88rem;
        font-weight: 700;
        color: #28314f;
        margin-top: 0.55rem;
        margin-bottom: 0.3rem;
    }

    .status-hover-item {
        font-size: 0.84rem;
        color: #667085;
        margin-bottom: 0.14rem;
    }

    .section-title {
        font-size: 1.38rem;
        font-weight: 800;
        color: #14213d;
        margin-bottom: 0.3rem;
    }

    .section-text {
        color: #677185;
        font-size: 0.96rem;
        margin-bottom: 1rem;
    }

    .update-card {
        background: #ffffff;
        border: 1px solid #ececf3;
        border-radius: 24px;
        padding: 1.15rem;
        box-shadow: 0 6px 18px rgba(20, 20, 43, 0.05);
        margin-bottom: 1rem;
    }

    .item-title {
        font-size: 1.35rem;
        font-weight: 800;
        color: #0b1d4d;
        margin-bottom: 0.35rem;
    }

    .item-meta {
        color: #64748b;
        font-size: 0.96rem;
        line-height: 1.65;
    }

    .item-meta b {
        color: #344054;
    }

    .item-value-label {
        color: #64748b;
        font-size: 0.95rem;
        font-weight: 600;
    }

    .item-value {
        font-size: 1.28rem;
        font-weight: 800;
        color: #081b4b;
    }

    .status-pill {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 999px;
        font-size: 0.86rem;
        font-weight: 700;
    }

    .status-pago {
        background: #dff7e8;
        color: #118a43;
    }

    .status-apagar {
        background: #fde6e6;
        color: #c62828;
    }

    .status-areceber {
        background: #efe3ff;
        color: #6d28d9;
    }

    .small-note {
        font-size: 0.88rem;
        color: #6b7280;
        margin-top: 0.45rem;
    }

    .stButton > button {
        border-radius: 14px;
        border: 1px solid #d6d9e5;
        font-weight: 600;
        min-height: 44px;
        background: white;
    }

    .stButton > button:hover {
        border-color: #7c3aed;
        color: #7c3aed;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
def normalizar_coluna(col):
    col = str(col or "")
    col = col.replace("\ufeff", "").replace("\xa0", " ").strip()
    return col

def slug_coluna(col):
    col = normalizar_coluna(col).lower()
    col = (
        col.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    col = re.sub(r"[^a-z0-9]+", "", col)
    return col

def encontrar_coluna(df, candidatos):
    mapa = {slug_coluna(c): c for c in df.columns}
    for cand in candidatos:
        slug = slug_coluna(cand)
        if slug in mapa:
            return mapa[slug]
    return None

def parse_brl(valor):
    if pd.isna(valor):
        return 0.0
    s = str(valor).strip()
    if not s:
        return 0.0

    s = s.replace("R$", "").replace("r$", "").strip()
    s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)

    try:
        return float(s)
    except Exception:
        return 0.0

def formatar_brl(v):
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def parse_data_br(valor):
    if pd.isna(valor):
        return pd.NaT
    s = str(valor).strip()
    if not s:
        return pd.NaT
    try:
        return pd.to_datetime(s, dayfirst=True, errors="coerce")
    except Exception:
        return pd.NaT

def extrair_mes_label(data):
    if pd.isna(data):
        return "Sem data"
    meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    return f"{meses[data.month - 1]}/{data.year}"

def status_class(status):
    s = str(status or "").strip().lower()
    if s == "pago":
        return "status-pill status-pago"
    if s == "a pagar":
        return "status-pill status-apagar"
    if s == "a receber":
        return "status-pill status-areceber"
    return "status-pill"

def encontrar_logo():
    for nome in LOGO_CANDIDATES:
        p = Path(nome)
        if p.exists() and p.is_file():
            return p
    return None

def render_logo():
    logo_path = encontrar_logo()
    if not logo_path:
        return

    try:
        img_bytes = logo_path.read_bytes()
        mime_type = mimetypes.guess_type(str(logo_path))[0] or "image/png"
        img_base64 = base64.b64encode(img_bytes).decode("utf-8")
        st.markdown(
            f"""
            <div class="logo-wrap">
                <div class="logo-circle">
                    <img src="data:{mime_type};base64,{img_base64}" alt="Logo Oppi">
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    except Exception:
        pass

def montar_detalhes_status_html(df_base, status_nome):
    base = df_base[df_base["_status"].str.lower() == status_nome.lower()].copy()

    if base.empty:
        return """
        <div class="status-hover-title">Sem registros</div>
        <div class="status-hover-line">Nenhum item encontrado nesse status.</div>
        """

    qtd = len(base)
    valor_total = formatar_brl(base["_valor_num"].sum())

    top = (
        base.groupby("_estabelecimento", dropna=False)["_valor_num"]
        .sum()
        .reset_index()
        .sort_values("_valor_num", ascending=False)
        .head(5)
    )

    itens_html = ""
    for _, r in top.iterrows():
        nome = html.escape(str(r["_estabelecimento"]).strip() or "-")
        valor = formatar_brl(r["_valor_num"])
        itens_html += f'<div class="status-hover-item">• {nome}: {valor}</div>'

    return f"""
    <div class="status-hover-title">{html.escape(status_nome)}</div>
    <div class="status-hover-line">Qtd: {qtd}</div>
    <div class="status-hover-line">Valor total: {valor_total}</div>
    <div class="status-hover-subtitle">Principais:</div>
    {itens_html}
    """

# =========================================================
# GOOGLE SHEETS
# =========================================================
@st.cache_resource(show_spinner=False)
def conectar():
    creds = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client

@st.cache_data(ttl=30, show_spinner=False)
def carregar():
    client = conectar()
    ws = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)

    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(), {}

    headers = [normalizar_coluna(h) for h in values[0]]
    rows = values[1:]

    rows_pad = []
    for row in rows:
        if len(row) < len(headers):
            row = row + [""] * (len(headers) - len(row))
        elif len(row) > len(headers):
            row = row[:len(headers)]
        rows_pad.append(row)

    df = pd.DataFrame(rows_pad, columns=headers)

    for c in df.columns:
        df[c] = df[c].astype(str).apply(lambda x: x.strip())

    col_mes = encontrar_coluna(df, ["Mês", "Mes", "Data", "Data do mês", "Data do mes"])
    col_estabelecimento = encontrar_coluna(df, ["Estabelecimento", "Empresa", "Nome"])
    col_valor = encontrar_coluna(df, ["Valor", "Valor total", "Preço", "Preco"])
    col_entrada = encontrar_coluna(df, ["Entrada", "Tipo", "Movimento"])
    col_categoria = encontrar_coluna(df, ["Categoria", "Grupo"])
    col_status = encontrar_coluna(df, ["Status", "Situação", "Situacao"])
    col_detalhes = encontrar_coluna(df, ["Detalhes", "Descrição", "Descricao", "Observação", "Observacao"])
    col_whatsapp = encontrar_coluna(df, ["Whatsapp", "WhatsApp", "Telefone"])

    df["_mes_raw"] = df[col_mes] if col_mes else ""
    df["_data_mes"] = df["_mes_raw"].apply(parse_data_br) if col_mes else pd.NaT
    df["_mes_label"] = df["_data_mes"].apply(extrair_mes_label) if col_mes else "Sem data"

    df["_estabelecimento"] = df[col_estabelecimento] if col_estabelecimento else ""
    df["_valor_num"] = df[col_valor].apply(parse_brl) if col_valor else 0.0
    df["_entrada"] = df[col_entrada].astype(str).str.strip() if col_entrada else ""
    df["_categoria"] = df[col_categoria].astype(str).str.strip() if col_categoria else ""
    df["_status"] = df[col_status].astype(str).str.strip() if col_status else ""
    df["_detalhes"] = df[col_detalhes].astype(str).str.strip() if col_detalhes else ""
    df["_whatsapp"] = df[col_whatsapp].astype(str).str.strip() if col_whatsapp else ""

    df["_sheet_row"] = range(2, len(df) + 2)

    meta = {
        "status_col_name": col_status,
    }
    return df, meta

def atualizar_status(sheet_row, novo_status):
    client = conectar()
    ws = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
    headers = [normalizar_coluna(h) for h in ws.row_values(1)]

    status_col_name = None
    for h in headers:
        if slug_coluna(h) in [slug_coluna("Status"), slug_coluna("Situação"), slug_coluna("Situacao")]:
            status_col_name = h
            break

    if not status_col_name:
        raise ValueError("Coluna 'Status' não encontrada na planilha.")

    status_col_idx = headers.index(status_col_name) + 1
    ws.update_cell(sheet_row, status_col_idx, novo_status)
    st.cache_data.clear()

# =========================================================
# HEADER
# =========================================================
render_logo()

st.markdown('<div class="main-title">Gestão Financeira Oppi</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="main-subtitle">Gestão financeira de receitas, despesas e status de pagamento</div>',
    unsafe_allow_html=True
)
st.markdown('<div class="top-divider"></div>', unsafe_allow_html=True)

# =========================================================
# LOAD
# =========================================================
try:
    df, meta = carregar()
except Exception as e:
    st.error("Erro ao conectar com a planilha do Google Sheets.")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("A planilha está vazia.")
    st.stop()

if not meta.get("status_col_name"):
    st.error("A coluna 'Status' não foi encontrada na planilha. Confira o cabeçalho.")
    st.stop()

# =========================================================
# FILTROS
# =========================================================
meses_opcoes = ["Todos"] + sorted(
    [m for m in df["_mes_label"].dropna().unique().tolist() if m != "Sem data"]
)

estab_opcoes = ["Todos"] + sorted([x for x in df["_estabelecimento"].unique().tolist() if str(x).strip()])
categoria_opcoes = ["Todas"] + sorted([x for x in df["_categoria"].unique().tolist() if str(x).strip()])
entrada_opcoes = ["Todas"] + sorted([x for x in df["_entrada"].unique().tolist() if str(x).strip()])

f1, f2, f3, f4 = st.columns(4)

with f1:
    st.markdown('<div class="filter-label">Mês</div>', unsafe_allow_html=True)
    filtro_mes = st.selectbox("Mês", meses_opcoes, label_visibility="collapsed")

with f2:
    st.markdown('<div class="filter-label">Estabelecimento</div>', unsafe_allow_html=True)
    filtro_estab = st.selectbox("Estabelecimento", estab_opcoes, label_visibility="collapsed")

with f3:
    st.markdown('<div class="filter-label">Categoria</div>', unsafe_allow_html=True)
    filtro_categoria = st.selectbox("Categoria", categoria_opcoes, label_visibility="collapsed")

with f4:
    st.markdown('<div class="filter-label">Entrada</div>', unsafe_allow_html=True)
    filtro_entrada = st.selectbox("Entrada", entrada_opcoes, label_visibility="collapsed")

df_filtrado = df.copy()

if filtro_mes != "Todos":
    df_filtrado = df_filtrado[df_filtrado["_mes_label"] == filtro_mes]

if filtro_estab != "Todos":
    df_filtrado = df_filtrado[df_filtrado["_estabelecimento"] == filtro_estab]

if filtro_categoria != "Todas":
    df_filtrado = df_filtrado[df_filtrado["_categoria"] == filtro_categoria]

if filtro_entrada != "Todas":
    df_filtrado = df_filtrado[df_filtrado["_entrada"] == filtro_entrada]

# =========================================================
# KPIs
# =========================================================
total_registros = len(df_filtrado)

total_receitas = df_filtrado.loc[
    df_filtrado["_entrada"].str.lower() == "receita", "_valor_num"
].sum()

total_despesas = df_filtrado.loc[
    df_filtrado["_entrada"].str.lower() == "despesa", "_valor_num"
].sum()

saldo = total_receitas - total_despesas

total_pago = df_filtrado.loc[
    df_filtrado["_status"].str.lower() == "pago", "_valor_num"
].sum()

total_apagar = df_filtrado.loc[
    df_filtrado["_status"].str.lower() == "a pagar", "_valor_num"
].sum()

total_areceber = df_filtrado.loc[
    df_filtrado["_status"].str.lower() == "a receber", "_valor_num"
].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)

cards = [
    (c1, "Registros", str(total_registros), "total de lançamentos filtrados", "roxo"),
    (c2, "Receitas", formatar_brl(total_receitas), "soma das receitas", "verde"),
    (c3, "Despesas", formatar_brl(total_despesas), "soma das despesas", "rosa"),
    (c4, "Saldo", formatar_brl(saldo), "receitas menos despesas", "azul"),
    (c5, "A pagar", formatar_brl(total_apagar), "somatório do status A Pagar", "laranja"),
    (c6, "A receber", formatar_brl(total_areceber), "somatório do status A Receber", "roxo"),
]

for col, titulo, valor, legenda, cor in cards:
    with col:
        st.markdown(
            f"""
            <div class="kpi-card {cor}">
                <div class="kpi-title">{titulo}</div>
                <div class="kpi-value">{valor}</div>
                <div class="kpi-caption">{legenda}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("<br>", unsafe_allow_html=True)

# =========================================================
# PAGO + RESUMO DE STATUS (3 QUADRADINHOS)
# =========================================================
c7, c8 = st.columns([1.1, 1])

qtd_pago = int((df_filtrado["_status"].str.lower() == "pago").sum())
qtd_apagar = int((df_filtrado["_status"].str.lower() == "a pagar").sum())
qtd_areceber = int((df_filtrado["_status"].str.lower() == "a receber").sum())

hover_pago = montar_detalhes_status_html(df_filtrado, "Pago")
hover_apagar = montar_detalhes_status_html(df_filtrado, "A Pagar")
hover_areceber = montar_detalhes_status_html(df_filtrado, "A Receber")

with c7:
    st.markdown(
        f"""
        <div class="kpi-card verde">
            <div class="kpi-title">Pago</div>
            <div class="kpi-value">{formatar_brl(total_pago)}</div>
            <div class="kpi-caption">somatório do status Pago</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c8:
    st.markdown(
        f"""
        <div class="kpi-card rosa">
            <div class="kpi-title">Resumo de status</div>
            <div class="status-triplet-wrap">
                <div class="status-mini-wrap">
                    <div class="status-mini-card pago">
                        <div class="status-mini-title">Pago</div>
                        <div class="status-mini-value">{qtd_pago}</div>
                        <div class="status-mini-caption">Passe o mouse</div>
                    </div>
                    <div class="status-hover-box">
                        {hover_pago}
                    </div>
                </div>

                <div class="status-mini-wrap">
                    <div class="status-mini-card apagar">
                        <div class="status-mini-title">A Pagar</div>
                        <div class="status-mini-value">{qtd_apagar}</div>
                        <div class="status-mini-caption">Passe o mouse</div>
                    </div>
                    <div class="status-hover-box">
                        {hover_apagar}
                    </div>
                </div>

                <div class="status-mini-wrap">
                    <div class="status-mini-card areceber">
                        <div class="status-mini-title">A Receber</div>
                        <div class="status-mini-value">{qtd_areceber}</div>
                        <div class="status-mini-caption">Passe o mouse</div>
                    </div>
                    <div class="status-hover-box">
                        {hover_areceber}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================================================
# GRÁFICOS
# =========================================================
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

g1, g2 = st.columns(2)

with g1:
    st.markdown('<div class="section-title">📊 Valor por categoria</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-text">Soma dos valores agrupados por categoria.</div>', unsafe_allow_html=True)

    base_categoria = (
        df_filtrado.groupby("_categoria", dropna=False)["_valor_num"]
        .sum()
        .reset_index()
        .rename(columns={"_categoria": "Categoria", "_valor_num": "Valor"})
    )
    base_categoria = base_categoria[base_categoria["Categoria"].astype(str).str.strip() != ""]

    if not base_categoria.empty:
        fig_cat = px.bar(
            base_categoria.sort_values("Valor", ascending=False),
            x="Categoria",
            y="Valor",
            text="Valor"
        )
        fig_cat.update_traces(texttemplate="R$ %{y:,.2f}", textposition="outside")
        fig_cat.update_layout(
            height=420,
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="",
            yaxis_title="Valor"
        )
        fig_cat.update_yaxes(tickprefix="R$ ")
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico de categoria.")

with g2:
    st.markdown('<div class="section-title">💰 Valor por status</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-text">Distribuição financeira por status atual.</div>', unsafe_allow_html=True)

    base_status = (
        df_filtrado.groupby("_status", dropna=False)["_valor_num"]
        .sum()
        .reset_index()
        .rename(columns={"_status": "Status", "_valor_num": "Valor"})
    )
    base_status = base_status[base_status["Status"].astype(str).str.strip() != ""]

    if not base_status.empty:
        fig_status = px.pie(
            base_status,
            names="Status",
            values="Valor",
            hole=0.62
        )
        fig_status.update_traces(
            textinfo="label+value",
            texttemplate="%{label}<br>R$ %{value:,.2f}"
        )
        fig_status.update_layout(
            height=420,
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=20, r=20, t=20, b=20),
            legend_title=""
        )
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("Sem dados para o gráfico de status.")

# =========================================================
# ATUALIZAR STATUS
# =========================================================
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="section-title">✏️ Atualizar status</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-text">Altere o campo <b>Status</b> diretamente pelo dashboard. Use a busca para localizar por estabelecimento, categoria, detalhes ou whatsapp.</div>',
    unsafe_allow_html=True
)

busca = st.text_input(
    "Buscar lançamento",
    placeholder="Ex.: Valeria, OpenAI, internet, mídia...",
    label_visibility="collapsed"
)

df_update = df.copy()

if filtro_mes != "Todos":
    df_update = df_update[df_update["_mes_label"] == filtro_mes]
if filtro_estab != "Todos":
    df_update = df_update[df_update["_estabelecimento"] == filtro_estab]
if filtro_categoria != "Todas":
    df_update = df_update[df_update["_categoria"] == filtro_categoria]
if filtro_entrada != "Todas":
    df_update = df_update[df_update["_entrada"] == filtro_entrada]

if busca.strip():
    termo = busca.strip().lower()
    mask = (
        df_update["_estabelecimento"].astype(str).str.lower().str.contains(termo, na=False) |
        df_update["_categoria"].astype(str).str.lower().str.contains(termo, na=False) |
        df_update["_detalhes"].astype(str).str.lower().str.contains(termo, na=False) |
        df_update["_whatsapp"].astype(str).str.lower().str.contains(termo, na=False)
    )
    df_update = df_update[mask]

df_update = df_update.head(40)

if df_update.empty:
    st.info("Nenhum lançamento encontrado para atualização.")
else:
    for _, row in df_update.iterrows():
        estabelecimento = row["_estabelecimento"] if str(row["_estabelecimento"]).strip() else "-"
        valor_txt = formatar_brl(row["_valor_num"])
        entrada = row["_entrada"] if str(row["_entrada"]).strip() else "-"
        categoria = row["_categoria"] if str(row["_categoria"]).strip() else "-"
        status_atual = row["_status"] if str(row["_status"]).strip() else "Sem status"
        detalhes = row["_detalhes"] if str(row["_detalhes"]).strip() else "-"
        whatsapp = row["_whatsapp"] if str(row["_whatsapp"]).strip() else "-"
        mes_txt = row["_mes_raw"] if str(row["_mes_raw"]).strip() else "-"
        sheet_row = int(row["_sheet_row"])

        st.markdown('<div class="update-card">', unsafe_allow_html=True)

        info1, info2, info3, b1, b2, b3 = st.columns([3.3, 1.2, 1.2, 1.1, 1.1, 1.1])

        with info1:
            st.markdown(f'<div class="item-title">{estabelecimento}</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="item-meta">
                    <b>Mês:</b> {mes_txt}&nbsp;&nbsp;&nbsp;
                    <b>Entrada:</b> {entrada}&nbsp;&nbsp;&nbsp;
                    <b>Categoria:</b> {categoria}<br>
                    <b>Detalhes:</b> {detalhes}<br>
                    <b>Whatsapp:</b> {whatsapp}
                </div>
                """,
                unsafe_allow_html=True
            )

        with info2:
            st.markdown('<div class="item-value-label">Valor</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="item-value">{valor_txt}</div>', unsafe_allow_html=True)

        with info3:
            st.markdown('<div class="item-value-label">Status atual</div>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="{status_class(status_atual)}">{status_atual}</span>',
                unsafe_allow_html=True
            )

        with b1:
            if st.button("Pago", key=f"pago_{sheet_row}", use_container_width=True):
                try:
                    atualizar_status(sheet_row, "Pago")
                    st.success(f"Status da linha {sheet_row} atualizado para Pago.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar para Pago: {e}")

        with b2:
            if st.button("A Pagar", key=f"apagar_{sheet_row}", use_container_width=True):
                try:
                    atualizar_status(sheet_row, "A Pagar")
                    st.success(f"Status da linha {sheet_row} atualizado para A Pagar.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar para A Pagar: {e}")

        with b3:
            if st.button("A Receber", key=f"areceber_{sheet_row}", use_container_width=True):
                try:
                    atualizar_status(sheet_row, "A Receber")
                    st.success(f"Status da linha {sheet_row} atualizado para A Receber.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar para A Receber: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

st.markdown(
    '<div class="small-note">Se algo não carregar, confira se a planilha continua compartilhada com o e-mail da service account como Editor.</div>',
    unsafe_allow_html=True
)
