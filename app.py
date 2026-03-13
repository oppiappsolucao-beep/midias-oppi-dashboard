import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="Mídias - Oppi",
    page_icon="📱",
    layout="wide"
)

st.title("📱 Dashboard — Mídias - Oppi")
st.caption("Gestão de publicações e pagamentos")

SHEET_ID = "COLOQUE_O_ID_DA_PLANILHA"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def connect_sheet():
    creds_dict = dict(st.secrets["google"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    worksheet = sheet.sheet1
    return worksheet

@st.cache_data(ttl=60)
def load_data():
    worksheet = connect_sheet()
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def parse_valor(series):
    s = series.astype(str).str.replace("R$", "", regex=False).str.strip()
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce").fillna(0)

def format_brl(v):
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

df = load_data()

if not df.empty:
    if "Valor" in df.columns:
        df["Valor"] = parse_valor(df["Valor"])
    else:
        df["Valor"] = 0.0

    if "Data Publicação" in df.columns:
        df["Data Publicação"] = pd.to_datetime(df["Data Publicação"], dayfirst=True, errors="coerce")

    if "Status Pagamento" not in df.columns:
        df["Status Pagamento"] = ""

    if "Semana" not in df.columns:
        df["Semana"] = ""

    if "Empresa" not in df.columns:
        df["Empresa"] = ""

    col1, col2, col3 = st.columns(3)

    with col1:
        semana_opcoes = ["Todas"] + sorted([x for x in df["Semana"].dropna().astype(str).unique().tolist() if x.strip()])
        semana = st.selectbox("Semana", semana_opcoes)

    with col2:
        empresa_opcoes = ["Todas"] + sorted([x for x in df["Empresa"].dropna().astype(str).unique().tolist() if x.strip()])
        empresa = st.selectbox("Empresa", empresa_opcoes)

    with col3:
        data_publicacao = st.date_input("Data publicação", value=None)

    df_filtrado = df.copy()

    if semana != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Semana"].astype(str) == semana]

    if empresa != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Empresa"].astype(str) == empresa]

    if data_publicacao:
        df_filtrado = df_filtrado[df_filtrado["Data Publicação"].dt.date == data_publicacao]

    pagos_mask = df_filtrado["Status Pagamento"].astype(str).str.strip().str.lower() == "pago"
    apagar_mask = df_filtrado["Status Pagamento"].astype(str).str.strip().str.lower().isin(["a pagar", "apagar"])

    total_posts = len(df_filtrado)
    total_valor = float(df_filtrado["Valor"].sum())
    qtd_pagos = int(pagos_mask.sum())
    qtd_apagar = int(apagar_mask.sum())
    valor_pago = float(df_filtrado.loc[pagos_mask, "Valor"].sum())
    valor_pendente = float(df_filtrado.loc[apagar_mask, "Valor"].sum())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Posts", total_posts)
    c2.metric("Valor total", format_brl(total_valor))
    c3.metric("Pagos", qtd_pagos)
    c4.metric("A pagar", qtd_apagar)
    c5.metric("Valor pago", format_brl(valor_pago))
    c6.metric("Valor pendente", format_brl(valor_pendente))

    st.divider()

    g1, g2 = st.columns(2)

    with g1:
        graf_empresa = df_filtrado.groupby("Empresa", dropna=False).size().reset_index(name="Total")
        fig_empresa = px.bar(graf_empresa, x="Empresa", y="Total", title="Posts por empresa")
        st.plotly_chart(fig_empresa, use_container_width=True)

    with g2:
        graf_status = df_filtrado.groupby("Status Pagamento", dropna=False)["Valor"].sum().reset_index()
        fig_status = px.pie(graf_status, values="Valor", names="Status Pagamento", title="Valor por status de pagamento")
        st.plotly_chart(fig_status, use_container_width=True)

    st.subheader("📋 Atualizar status pagamento")

    worksheet = connect_sheet()

    for index, row in df_filtrado.iterrows():
        empresa_nome = row.get("Empresa", "")
        tema = row.get("Tema", "")
        semana_txt = row.get("Semana", "")
        valor = float(row.get("Valor", 0))
        data_txt = row["Data Publicação"].strftime("%d/%m/%Y") if pd.notnull(row.get("Data Publicação")) else "-"
        status_atual = str(row.get("Status Pagamento", "")).strip() or "-"

        box1, box2, box3, box4, box5, box6, box7 = st.columns([1.4, 2.5, 1.2, 1.2, 1.1, 1.1, 1.2])
        box1.write(empresa_nome)
        box2.write(tema)
        box3.write(semana_txt)
        box4.write(data_txt)
        box5.write(format_brl(valor))
        box6.write(status_atual)

        if box7.button("✔ Pago", key=f"pago_{index}"):
            worksheet.update_cell(index + 2, 9, "Pago")
            st.cache_data.clear()
            st.rerun()

        if box7.button("⚠ A pagar", key=f"apagar_{index}"):
            worksheet.update_cell(index + 2, 9, "A Pagar")
            st.cache_data.clear()
            st.rerun()
else:
    st.warning("Nenhum dado encontrado na planilha.")
