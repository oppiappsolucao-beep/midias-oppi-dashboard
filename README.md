# Mídias - Oppi Dashboard

Dashboard interno da Oppi Tech conectado ao Google Sheets.

**Site publicado:** [midias.oppitech.com.br](https://midias.oppitech.com.br)

## Como o site está publicado hoje

| Item | Situação |
|------|----------|
| **Plataforma** | **Streamlit** (`app.py`) |
| **Hospedagem** | EasyPanel (servidor responde via uvicorn/proxy) |
| **Repositório** | `github.com/oppiappsolucao-beep/midias-oppi-dashboard` |
| **Domínio** | `midias.oppitech.com.br` |

O HTML do site em produção ainda é Streamlit (copyright Snowflake/Streamlit no código-fonte da página).

As pastas `backend/` e `frontend/` (Next.js + FastAPI) existem no repositório, mas **não estão publicadas** nesse domínio hoje.

---

## Como publicar alterações no site atual (Streamlit)

Para mudar layout, login, filtros, etc. **sem trocar o link**:

1. Edite o arquivo [`app.py`](app.py)
2. No **GitHub Desktop**: commit + **Push origin**
3. O EasyPanel detecta o push e rebuilda automaticamente (leva 1–5 min)
4. Atualize a página com **Ctrl+F5** (limpa cache)

### Credenciais em produção (EasyPanel)

No painel EasyPanel → **Ambiente**, confirme que existem:

- `GOOGLE_PRIVATE_KEY`, `GOOGLE_CLIENT_EMAIL`, `GOOGLE_CLIENT_ID`, etc.
- Ou o JSON da service account (`GOOGLE_SERVICE_ACCOUNT_JSON`)

O `SHEET_ID` está no `app.py` (variável `SHEET_ID`).

### Comando que o EasyPanel deve usar

```bash
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

Arquivo de dependências: [`requirements.txt`](requirements.txt) na raiz.

---

## Testar localmente antes de publicar

```powershell
cd C:\Users\orchi\OneDrive\Documentos\GitHub\midias-oppi-dashboard
py -m pip install -r requirements.txt
streamlit run app.py
```

Abra `http://localhost:8501` e valide o layout antes do push.

---

## Se quiser sair do Streamlit (mesmo domínio)

Isso **não se faz só editando código** — exige acesso ao **EasyPanel** e ao **DNS**:

1. Publicar `backend/` (FastAPI) e `frontend/` (Next.js) no EasyPanel ou Vercel
2. Apontar `midias.oppitech.com.br` para o novo serviço
3. Desativar o app Streamlit antigo no EasyPanel

Enquanto isso não for feito, **todas as mudanças visíveis no site passam pelo `app.py`**.

---

## Arquivos principais

| Arquivo | Função |
|---------|--------|
| [`app.py`](app.py) | **App em produção hoje** (Streamlit) |
| [`requirements.txt`](requirements.txt) | Dependências do Streamlit |
| `backend/` | API FastAPI (futuro / dev local) |
| `frontend/` | Next.js (futuro / dev local) |
