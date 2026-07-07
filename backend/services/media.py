import re
from typing import Any

import pandas as pd

from config import EXPECTED_MEDIA_HEADERS, MESES_ORDEM, SHEET_COL_STATUS_ARTE, SHEET_COL_TEMA
from services.sheets import fetch_sheet_rows, update_sheet_cell

HEADER_ALIASES = {
    "Mês": ["mes", "mês"],
    "Semana": ["semana"],
    "Empresa": ["empresa", "cliente"],
    "Tema": ["tema", "atividade", "nome da atividade"],
    "Valor": ["valor", "preco", "preço"],
    "Status Pagamento": ["status pagamento", "status de pagamento", "pagamento"],
    "Tipo de arte": ["tipo de arte", "tipo arte", "formato"],
    "Status da arte": ["status da arte", "status arte", "status"],
    "Data Publicação": [
        "data publicacao", "data de publicacao", "data publicação",
        "data de publicação", "publicacao", "publicação", "data",
    ],
}


def format_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def normalizar_valor(coluna: pd.Series) -> pd.Series:
    return (
        coluna.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )


def ordenar_meses(lista: list[str]) -> list[str]:
    ordem = {mes: i for i, mes in enumerate(MESES_ORDEM)}
    return sorted(lista, key=lambda x: ordem.get(x, 999))


def normalize_header_name(value: str) -> str:
    return str(value).replace("\u00a0", " ").strip()


def normalize_header_key(value: str) -> str:
    text_value = normalize_header_name(value).lower()
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "ê": "e", "í": "i",
        "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ç": "c",
    }
    for old, new in replacements.items():
        text_value = text_value.replace(old, new)
    return re.sub(r"\s+", " ", text_value).strip()


def parse_data_publicacao(valor) -> pd.Timestamp:
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


def count_non_empty_column(rows: list[list[str]], column_index: int) -> int:
    total = 0
    for row in rows:
        if column_index < len(row) and str(row[column_index]).strip():
            total += 1
    return total


def count_parseable_dates(rows: list[list[str]], column_index: int) -> int:
    total = 0
    for row in rows:
        if column_index >= len(row):
            continue
        value = str(row[column_index]).strip()
        if not value:
            continue
        if pd.notna(parse_data_publicacao(value)):
            total += 1
    return total


def find_header_candidates(raw_headers: list[str], expected_header: str) -> list[int]:
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


def detect_date_column(raw_headers: list[str], data_rows: list[list[str]], already_selected: set[int]):
    candidates = find_header_candidates(raw_headers, "Data Publicação")
    if candidates:
        return max(
            candidates,
            key=lambda index: (
                count_parseable_dates(data_rows, index),
                count_non_empty_column(data_rows, index),
            ),
        )
    available_indexes = [index for index in range(len(raw_headers)) if index not in already_selected]
    if not available_indexes:
        return None
    scored_columns = [
        (count_parseable_dates(data_rows, index), count_non_empty_column(data_rows, index), index)
        for index in available_indexes
    ]
    best_dates, _, best_index = max(scored_columns)
    if best_dates > 0:
        return best_index
    return None


def build_media_dataframe(rows: list[list[str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=EXPECTED_MEDIA_HEADERS)

    raw_headers = [normalize_header_name(header) for header in rows[0]]
    data_rows = rows[1:]
    selected_indexes: dict[str, int] = {}
    used_indexes: set[int] = set()

    for expected_header in EXPECTED_MEDIA_HEADERS:
        if expected_header == "Data Publicação":
            continue
        candidates = find_header_candidates(raw_headers, expected_header)
        if not candidates:
            continue
        best_index = max(candidates, key=lambda index: count_non_empty_column(data_rows, index))
        selected_indexes[expected_header] = best_index
        used_indexes.add(best_index)

    date_index = detect_date_column(raw_headers, data_rows, used_indexes)
    if date_index is not None:
        selected_indexes["Data Publicação"] = date_index

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


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
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
                9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
            }
            df.loc[mascara_mes_vazio, "Mês"] = (
                df.loc[mascara_mes_vazio, "Data Publicação"].dt.month.map(mapa_meses)
            )

    return df


def load_prepared_dataframe() -> pd.DataFrame:
    rows = fetch_sheet_rows()
    df = build_media_dataframe(rows)
    return prepare_dataframe(df)


def _date_sort_key(txt: str):
    dt = parse_data_publicacao(txt)
    return dt if pd.notna(dt) else pd.Timestamp.max


def get_filter_options(df: pd.DataFrame) -> dict[str, Any]:
    meses = [x for x in df["Mês"].dropna().astype(str).unique().tolist() if x.strip()]
    semanas = [x for x in df["Semana"].dropna().astype(str).unique().tolist() if str(x).strip()]
    empresas = [x for x in df["Empresa"].dropna().astype(str).unique().tolist() if str(x).strip()]
    datas = [
        x for x in df["Data Publicação Raw"].dropna().astype(str).unique().tolist()
        if str(x).strip() and str(x).strip().lower() != "nan"
    ]
    datas = sorted(set(datas), key=_date_sort_key)

    return {
        "meses": ordenar_meses(meses),
        "semanas": sorted(semanas),
        "empresas": sorted(empresas),
        "datas": datas,
    }


def apply_filters(
    df: pd.DataFrame,
    mes: str | None = None,
    semana: str | None = None,
        empresa: str | None = None,
    datas: list[str] | None = None,
    busca: str | None = None,
) -> pd.DataFrame:
    filtered = df.copy()

    if mes and mes != "Todos":
        filtered = filtered[filtered["Mês"].astype(str) == mes]
    if semana and semana != "Todas":
        filtered = filtered[filtered["Semana"].astype(str) == semana]
    if empresa and empresa != "Todas":
        filtered = filtered[filtered["Empresa"].astype(str) == empresa]
    if datas:
        filtered = filtered[filtered["Data Publicação Raw"].isin(datas)]
    if busca and busca.strip():
        termo = busca.strip().lower()
        filtered = filtered[
            filtered["Empresa"].astype(str).str.lower().str.contains(termo, na=False)
            | filtered["Tema"].astype(str).str.lower().str.contains(termo, na=False)
        ]

    return filtered


def compute_metrics(df_filtrado: pd.DataFrame) -> dict[str, Any]:
    status_pagamento = df_filtrado["Status Pagamento"].astype(str).str.strip().str.lower()
    status_arte = df_filtrado["Status da arte"].astype(str).str.strip().str.lower()

    pagos = df_filtrado[status_pagamento == "pago"]
    a_pagar = df_filtrado[status_pagamento == "a pagar"]

    linhas_com_conteudo = (
        df_filtrado["Empresa"].astype(str).str.strip().ne("")
        | df_filtrado["Tema"].astype(str).str.strip().ne("")
        | df_filtrado["Tipo de arte"].astype(str).str.strip().ne("")
        | df_filtrado["Valor"].fillna(0).gt(0)
        | df_filtrado["Data Publicação"].notna()
    )

    total_valor = float(df_filtrado["Valor"].sum())
    valor_pago = float(pagos["Valor"].sum())
    valor_pendente = float(a_pagar["Valor"].sum())

    return {
        "total_posts": len(df_filtrado),
        "total_valor": total_valor,
        "total_valor_fmt": format_brl(total_valor),
        "pagos_count": len(pagos),
        "a_pagar_count": len(a_pagar),
        "valor_pago": valor_pago,
        "valor_pago_fmt": format_brl(valor_pago),
        "valor_pendente": valor_pendente,
        "valor_pendente_fmt": format_brl(valor_pendente),
        "postagens_feitas": int(((status_arte == "pronto") & linhas_com_conteudo).sum()),
        "postagens_a_fazer": int(((status_arte != "pronto") & linhas_com_conteudo).sum()),
        "em_andamento": int(((status_arte == "em andamento") & linhas_com_conteudo).sum()),
        "concluido": int(
            (((status_arte == "concluído") | (status_arte == "concluido")) & linhas_com_conteudo).sum()
        ),
    }


def compute_charts(df_filtrado: pd.DataFrame) -> dict[str, Any]:
    graf_empresa = (
        df_filtrado.groupby("Empresa", dropna=False)
        .size()
        .reset_index(name="Total")
    )

    graf_status = (
        df_filtrado.groupby("Status Pagamento", dropna=False)["Valor"]
        .sum()
        .reset_index()
    )
    graf_status["Status Pagamento"] = graf_status["Status Pagamento"].astype(str).str.strip()
    graf_status = graf_status[
        (graf_status["Status Pagamento"] != "") & (graf_status["Valor"] > 0)
    ]

    return {
        "por_empresa": graf_empresa.to_dict(orient="records"),
        "por_status_pagamento": graf_status.to_dict(orient="records"),
    }


def row_to_dict(index: int, row: pd.Series) -> dict[str, Any]:
    if pd.notnull(row.get("Data Publicação")):
        data_txt = row["Data Publicação"].strftime("%d/%m/%Y")
    else:
        data_txt = str(row.get("Data Publicação Raw", "")).strip() or "-"

    return {
        "row_index": int(index),
        "empresa": str(row.get("Empresa", "")).strip() or "-",
        "semana": str(row.get("Semana", "")).strip() or "-",
        "tema": str(row.get("Tema", "")).strip() or "-",
        "mes": str(row.get("Mês", "")).strip() or "-",
        "tipo_arte": str(row.get("Tipo de arte", "")).strip() or "-",
        "status_arte": str(row.get("Status da arte", "")).strip() or "-",
        "status_pagamento": str(row.get("Status Pagamento", "")).strip() or "-",
        "valor": float(row.get("Valor", 0) or 0),
        "valor_fmt": format_brl(float(row.get("Valor", 0) or 0)),
        "data": data_txt,
    }


def rows_to_list(df_filtrado: pd.DataFrame) -> list[dict[str, Any]]:
    return [row_to_dict(index, row) for index, row in df_filtrado.iterrows()]


def update_row_status(row_index: int, status: str) -> None:
    update_sheet_cell(row_index, SHEET_COL_STATUS_ARTE, status)


def update_row_tema(row_index: int, tema: str) -> None:
    update_sheet_cell(row_index, SHEET_COL_TEMA, tema)
