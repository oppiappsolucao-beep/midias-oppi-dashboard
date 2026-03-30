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

    /* BOTÕES GERAIS */
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

    left, mid, right = st.columns([3.3, 1.3, 4.2])

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
        info_col, buttons_col = st.columns([1.0, 3.0])

        with info_col:
            st.markdown("**Status atual**")
            st.markdown(status_arte_badge(status_arte_txt), unsafe_allow_html=True)

        with buttons_col:
            b1, b2, b3, b4 = st.columns([1, 1, 1, 1], gap="small")

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
