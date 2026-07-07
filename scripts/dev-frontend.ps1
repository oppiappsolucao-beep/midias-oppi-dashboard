Write-Host "Iniciando frontend em http://localhost:3000"
Set-Location "$PSScriptRoot\..\frontend"
if (-not (Test-Path ".env.local")) {
  Copy-Item ".env.local.example" ".env.local"
}
npm install
npm run dev
