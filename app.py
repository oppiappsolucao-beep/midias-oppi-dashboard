import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------
# CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="Mídias - Oppi",
    page_icon="📱",
    layout="wide"
)

st.title("📱 Dashboard — Mídias Oppi")
st.caption("Gestão de publicações e pagamentos")

# ---------------------------------------------------
# PLANILHA
# ---------------------------------------------------

SHEET_ID = "16I701e6FdfkXYQrCxknZRidTonR3f80SQcUq3tGNw5I"
SHEET_URL = "https://docs.google.com/spreadsheets/d/16I701e6FdfkXYQrCxknZRidTonR3f80SQcUq3tGNw5I/edit?gid=0#gid=0"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

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

# ---------------------------------------------------
# CONEXÃO GOOGLE
# ---------------------------------------------------

@st.cache_resource
def connect_sheet():
    try:
        creds_dict = dict(st.secrets["google"])

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

        client = gspread.authorize(creds)

        # diagnóstico
        st.write("SHEET_ID usado:", SHEET_ID)
        st.write("client_email usado:", creds_dict.get("client_email", "não encontrado"))

        try:
            arquivos = client.list_spreadsheet_files()
            st.write("Quantidade de planilhas visíveis para essa conta:", len(arquivos))
            if len(arquivos) > 0:
                st.write("Primeiras planilhas visíveis:", arquivos[:5])
        except Exception as e:
            st.warning(f"Não foi possível listar planilhas visíveis: {e}")

        # tenta abrir pela URL completa
        sheet = client.open_by_url(SHEET_URL)
        worksheet = sheet.get_worksheet(0)

        return worksheet

    except Exception as e:
        st.error("❌ Erro ao conectar com Google Sheets")
        st.write("Verifique:")
        st.write("- Se o app está com o código atualizado no GitHub")
        st.write("- Se a planilha foi compartilhada com a conta de serviço mostrada acima")
        st.write("- Se a Google Sheets API e a Google Drive API estão ativadas")
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

for col in ["Semana", "Empresa", "Tema", "Status Pagamento", "Status da arte"]:
    if col not in df.columns:
        df[col] = ""

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    semana_opcoes = ["Todas"] + sorted(
        [x for x in df["Semana"].dropna().astype(str).unique().tolist() if x.strip()]
    )
    semana = st.selectbox("Semana", semana_opcoes)

with col2:
    empresa_opcoes = ["Todas"] + sorted(
        [x for x in df["Empresa"].dropna().astype(str).unique().tolist() if x.strip()]
    )
    empresa = st.selectbox("Empresa", empresa_opcoes)

with col3:
    data = st.date_input("Data publicação", value=None)

df_filtrado = df.copy()

if semana != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Semana"].astype(str) == semana]

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"].astype(str) == empresa]

if data:
    df_filtrado = df_filtrado[df_filtrado["Data Publicação"].dt.date == data]

# ---------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------

status_normalizado = df_filtrado["Status Pagamento"].astype(str).str.strip().str.lower()

pagos = df_filtrado[status_normalizado == "pago"]
a_pagar = df_filtrado[status_normalizado == "a pagar"]

total_posts = len(df_filtrado)
total_valor = df_filtrado["Valor"].sum()
valor_pago = pagos["Valor"].sum()
valor_pendente = a_pagar["Valor"].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Posts", total_posts)
c2.metric("Valor total", format_brl(total_valor))
c3.metric("Pagos", len(pagos))
c4.metric("A pagar", len(a_pagar))
c5.metric("Valor pago", format_brl(valor_pago))
c6.metric("Valor pendente", format_brl(valor_pendente))

st.divider()

# ---------------------------------------------------
# GRÁFICOS
# ---------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    graf_empresa = (
        df_filtrado.groupby("Empresa", dropna=False)
        .size()
        .reset_index(name="Total")
    )

    fig_empresa = px.bar(
        graf_empresa,
        x="Empresa",
        y="Total",
        title="Posts por empresa"
    )

    st.plotly_chart(fig_empresa, use_container_width=True)

with col2:
    graf_semana = (
        df_filtrado.groupby("Semana", dropna=False)
        .size()
        .reset_index(name="Total")
    )

    fig_semana = px.pie(
        graf_semana,
        values="Total",
        names="Semana",
        title="Posts por semana"
    )

    st.plotly_chart(fig_semana, use_container_width=True)

# ---------------------------------------------------
# ATUALIZAR STATUS PAGAMENTO
# ---------------------------------------------------

st.subheader("📋 Atualizar status pagamento")
st.caption("Clique no botão para atualizar a coluna 'Status Pagamento' na planilha.")

worksheet = connect_sheet()

header = st.columns([2, 3, 1.2, 1.2, 1.2, 1.4, 2.4])
header[0].write("**Empresa**")
header[1].write("**Tema**")
header[2].write("**Semana**")
header[3].write("**Data**")
header[4].write("**Valor**")
header[5].write("**Status**")
header[6].write("**Ações**")

for index, row in df_filtrado.iterrows():
    c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 3, 1.2, 1.2, 1.2, 1.4, 2.4])

    empresa_txt = str(row.get("Empresa", "")).strip()
    tema_txt = str(row.get("Tema", "")).strip()
    semana_txt = str(row.get("Semana", "")).strip()
    status_txt = str(row.get("Status Pagamento", "")).strip() or "-"
    valor_num = float(row.get("Valor", 0) or 0)

    if pd.notnull(row.get("Data Publicação")):
        data_txt = row["Data Publicação"].strftime("%d/%m/%Y")
    else:
        data_txt = "-"

    c1.write(empresa_txt)
    c2.write(tema_txt)
    c3.write(semana_txt)
    c4.write(data_txt)
    c5.write(format_brl(valor_num))
    c6.write(status_txt)

    a1, a2 = c7.columns(2)

    if a1.button("✔ Pago", key=f"pago_{index}"):
        worksheet.update_cell(index + 2, 9, "Pago")
        st.cache_data.clear()
        st.rerun()

    if a2.button("⚠ A pagar", key=f"apagar_{index}"):
        worksheet.update_cell(index + 2, 9, "A Pagar")
        st.cache_data.clear()
        st.rerun()
