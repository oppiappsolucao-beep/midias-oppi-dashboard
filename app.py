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

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------------------------------------------
# CONEXÃO GOOGLE
# ---------------------------------------------------

@st.cache_resource
def connect_sheet():
    try:
        creds_dict = st.secrets["google"]

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

        client = gspread.authorize(creds)

        sheet = client.open_by_key(SHEET_ID)

        worksheet = sheet.sheet1

        return worksheet

    except Exception as e:
        st.error("❌ Erro ao conectar com Google Sheets")
        st.write("Verifique:")
        st.write("- Se o SHEET_ID está correto")
        st.write("- Se a planilha foi compartilhada com a conta de serviço")
        st.write("- Se a API do Google Sheets está ativada")
        st.write(f"Erro técnico: {e}")
        st.stop()

# ---------------------------------------------------
# CARREGAR DADOS
# ---------------------------------------------------

@st.cache_data(ttl=60)
def load_data():
    worksheet = connect_sheet()

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    return df

df = load_data()

# ---------------------------------------------------
# TRATAMENTO
# ---------------------------------------------------

if "Valor" in df.columns:
    df["Valor"] = (
        df["Valor"]
        .astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
else:
    df["Valor"] = 0

if "Data Publicação" in df.columns:
    df["Data Publicação"] = pd.to_datetime(
        df["Data Publicação"],
        dayfirst=True,
        errors="coerce"
    )

# ---------------------------------------------------
# FILTROS
# ---------------------------------------------------

col1, col2, col3 = st.columns(3)

with col1:
    semana = st.selectbox(
        "Semana",
        ["Todas"] + sorted(df["Semana"].dropna().unique().tolist())
    )

with col2:
    empresa = st.selectbox(
        "Empresa",
        ["Todas"] + sorted(df["Empresa"].dropna().unique().tolist())
    )

with col3:
    data = st.date_input("Data publicação", value=None)

df_filtrado = df.copy()

if semana != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Semana"] == semana]

if empresa != "Todas":
    df_filtrado = df_filtrado[df_filtrado["Empresa"] == empresa]

if data:
    df_filtrado = df_filtrado[df_filtrado["Data Publicação"].dt.date == data]

# ---------------------------------------------------
# MÉTRICAS
# ---------------------------------------------------

total_posts = len(df_filtrado)
total_valor = df_filtrado["Valor"].sum()

pagos = df_filtrado[df_filtrado["Status Pagamento"] == "Pago"]
a_pagar = df_filtrado[df_filtrado["Status Pagamento"] == "A Pagar"]

valor_pago = pagos["Valor"].sum()
valor_pendente = a_pagar["Valor"].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Posts", total_posts)
c2.metric("Valor total", f"R$ {total_valor:,.2f}")
c3.metric("Pagos", len(pagos))
c4.metric("A pagar", len(a_pagar))
c5.metric("Valor pago", f"R$ {valor_pago:,.2f}")
c6.metric("Valor pendente", f"R$ {valor_pendente:,.2f}")

st.divider()

# ---------------------------------------------------
# GRÁFICOS
# ---------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    graf_empresa = df_filtrado.groupby("Empresa").size().reset_index(name="Total")

    fig = px.bar(
        graf_empresa,
        x="Empresa",
        y="Total",
        title="Posts por empresa"
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    graf_semana = df_filtrado.groupby("Semana").size().reset_index(name="Total")

    fig = px.pie(
        graf_semana,
        values="Total",
        names="Semana",
        title="Posts por semana"
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------
# ATUALIZAR STATUS
# ---------------------------------------------------

st.subheader("📋 Atualizar status pagamento")

worksheet = connect_sheet()

for index, row in df_filtrado.iterrows():

    c1, c2, c3, c4, c5, c6, c7 = st.columns([2,3,1,1,1,1,2])

    c1.write(row.get("Empresa", ""))
    c2.write(row.get("Tema", ""))
    c3.write(row.get("Semana", ""))

    if pd.notnull(row.get("Data Publicação")):
        c4.write(row["Data Publicação"].strftime("%d/%m/%Y"))
    else:
        c4.write("-")

    c5.write(f"R$ {row.get('Valor', 0):.2f}")
    c6.write(row.get("Status Pagamento", "-"))

    if c7.button("✔ Pago", key=f"pago{index}"):
        worksheet.update_cell(index + 2, 9, "Pago")
        st.cache_data.clear()
        st.rerun()

    if c7.button("⚠ A pagar", key=f"apagar{index}"):
        worksheet.update_cell(index + 2, 9, "A Pagar")
        st.cache_data.clear()
        st.rerun()
