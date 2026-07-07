# Mídias - Oppi Dashboard

Dashboard interno da Oppi Tech com **Next.js** (frontend) + **FastAPI** (backend), conectado ao Google Sheets.

## Estrutura

```
backend/     API Python (Google Sheets, métricas, PDF)
frontend/    Interface Next.js + Tailwind
app.py       Versão antiga em Streamlit (pode ser desativada após validação)
```

## Rodar localmente (Windows)

### 1. Backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
copy .env.example .env
# Edite .env com credenciais Google e login
uvicorn main:app --reload --port 8000
```

> **Windows:** use `py` em vez de `python`. O comando `python` pode apontar para a Microsoft Store e dar erro. O ambiente virtual fica em `.venv` (com ponto).

API disponível em `http://localhost:8000`

### 2. Frontend

Em outro terminal:

```powershell
cd frontend
copy .env.local.example .env.local
npm install
npm run dev
```

Interface em `http://localhost:3000`

## Variáveis de ambiente

### Backend (`backend/.env`)

| Variável | Descrição |
|----------|-----------|
| `SHEET_ID` | ID da planilha Google |
| `APP_USER` / `APP_PASS` | Login do painel |
| `JWT_SECRET` | Chave para tokens de sessão |
| `CORS_ORIGIN` | URL do frontend (ex.: `http://localhost:3000`) |
| `GOOGLE_*` | Credenciais da service account |

### Frontend (`frontend/.env.local`)

| Variável | Descrição |
|----------|-----------|
| `NEXT_PUBLIC_API_URL` | URL do backend (ex.: `http://localhost:8000`) |

## Publicar

### Frontend — Vercel

1. Conecte o repositório GitHub na Vercel
2. Root directory: `frontend`
3. Adicione `NEXT_PUBLIC_API_URL` apontando para o backend em produção

### Backend — EasyPanel

1. Use o `Dockerfile` na raiz do repositório
2. Configure as mesmas variáveis de ambiente Google do Streamlit/EasyPanel
3. Exponha a porta `8000`
4. Atualize `CORS_ORIGIN` com a URL da Vercel

### Logo

Coloque `logo-oppi.png` na raiz do repositório e em `frontend/public/logo-oppi.png`.

## Endpoints principais

- `POST /auth/login`
- `GET /media/dashboard`
- `PATCH /media/rows/{id}/status`
- `PATCH /media/rows/{id}/tema`
- `POST /traffic/pdf`

## Versão Streamlit (legado)

O arquivo `app.py` continua disponível. Para rodar:

```powershell
streamlit run app.py
```

Desative no Streamlit Cloud após validar a nova versão.
