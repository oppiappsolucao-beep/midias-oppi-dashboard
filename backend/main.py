from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from auth import authenticate_user, create_access_token, get_current_user
from config import CORS_ORIGINS
from services.media import (
    apply_filters,
    compute_charts,
    compute_metrics,
    get_filter_options,
    load_prepared_dataframe,
    rows_to_list,
    update_row_status,
    update_row_tema,
)
from services.traffic import build_traffic_pdf, safe_filename, validate_traffic_form

app = FastAPI(title="Oppi Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StatusUpdateRequest(BaseModel):
    status: str


class TemaUpdateRequest(BaseModel):
    tema: str


class TrafficFormRequest(BaseModel):
    empresa: str = ""
    campanha: str = ""
    plataforma: str = ""
    periodo_inicio: str = ""
    periodo_fim: str = ""
    investimento: str = ""
    custo_dia: str = ""
    alcance: str = ""
    visualizacoes: str = ""
    contatos: str = ""
    custo_contato: str = ""


def _parse_filter_params(
    mes: str | None,
    semana: str | None,
    empresa: str | None,
    datas: list[str] | None,
    busca: str | None,
):
    df = load_prepared_dataframe()
    filtered = apply_filters(df, mes=mes, semana=semana, empresa=empresa, datas=datas, busca=busca)
    return df, filtered


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if not authenticate_user(body.username, body.password):
        raise HTTPException(status_code=401, detail="Usuário ou senha incorretos.")
    return LoginResponse(access_token=create_access_token())


@app.get("/media/filters")
def media_filters(_user: str = Depends(get_current_user)):
    df = load_prepared_dataframe()
    return get_filter_options(df)


@app.get("/media/dashboard")
def media_dashboard(
    mes: str | None = Query(None),
    semana: str | None = Query(None),
    empresa: str | None = Query(None),
    datas: list[str] | None = Query(None),
    busca: str | None = Query(None),
    _user: str = Depends(get_current_user),
):
    df, filtered = _parse_filter_params(mes, semana, empresa, datas, busca)
    return {
        "filters": get_filter_options(df),
        "metrics": compute_metrics(filtered),
        "charts": compute_charts(filtered),
        "rows": rows_to_list(filtered),
    }


@app.get("/media/metrics")
def media_metrics(
    mes: str | None = Query(None),
    semana: str | None = Query(None),
    empresa: str | None = Query(None),
    datas: list[str] | None = Query(None),
    _user: str = Depends(get_current_user),
):
    _, filtered = _parse_filter_params(mes, semana, empresa, datas, None)
    return compute_metrics(filtered)


@app.get("/media/charts")
def media_charts(
    mes: str | None = Query(None),
    semana: str | None = Query(None),
    empresa: str | None = Query(None),
    datas: list[str] | None = Query(None),
    _user: str = Depends(get_current_user),
):
    _, filtered = _parse_filter_params(mes, semana, empresa, datas, None)
    return compute_charts(filtered)


@app.get("/media/rows")
def media_rows(
    mes: str | None = Query(None),
    semana: str | None = Query(None),
    empresa: str | None = Query(None),
    datas: list[str] | None = Query(None),
    busca: str | None = Query(None),
    _user: str = Depends(get_current_user),
):
    _, filtered = _parse_filter_params(mes, semana, empresa, datas, busca)
    return {"rows": rows_to_list(filtered)}


@app.patch("/media/rows/{row_index}/status")
def update_status(row_index: int, body: StatusUpdateRequest, _user: str = Depends(get_current_user)):
    allowed = {"Pronto", "Em andamento", "Pausado", "Pendente", "Concluído"}
    if body.status not in allowed:
        raise HTTPException(status_code=400, detail="Status inválido.")
    try:
        update_row_status(row_index, body.status)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "row_index": row_index, "status": body.status}


@app.patch("/media/rows/{row_index}/tema")
def update_tema(row_index: int, body: TemaUpdateRequest, _user: str = Depends(get_current_user)):
    if not body.tema.strip():
        raise HTTPException(status_code=400, detail="Tema não pode ser vazio.")
    try:
        update_row_tema(row_index, body.tema.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True, "row_index": row_index, "tema": body.tema.strip()}


@app.post("/traffic/validate")
def traffic_validate(body: TrafficFormRequest, _user: str = Depends(get_current_user)):
    values = body.model_dump()
    return validate_traffic_form(values)


@app.post("/traffic/pdf")
def traffic_pdf(body: TrafficFormRequest, _user: str = Depends(get_current_user)):
    values = body.model_dump()
    validation = validate_traffic_form(values)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "missing": validation["missing"],
                "error": validation["error"],
            },
        )

    pdf_bytes = build_traffic_pdf(values)
    filename = f"resultados_{safe_filename(values['empresa'])}_{safe_filename(values['campanha'])}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
