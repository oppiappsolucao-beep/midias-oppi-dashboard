Write-Host "Iniciando backend em http://localhost:8000"
Set-Location "$PSScriptRoot\..\backend"
if (-not (Test-Path ".venv")) {
  py -m venv .venv
}
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Arquivo .env criado. Edite backend/.env com as credenciais Google."
}
uvicorn main:app --reload --port 8000
