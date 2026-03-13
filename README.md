# Mídias - Oppi Dashboard

Dashboard em Streamlit conectado ao Google Sheets para acompanhar publicações e atualizar o status de pagamento.

## Arquivos
- `app.py`
- `requirements.txt`

## Antes de publicar
1. Coloque o ID da planilha na variável `SHEET_ID` dentro do `app.py`.
2. Adicione os dados da service account em `Secrets` no Streamlit Cloud.

## Secrets esperados no Streamlit
Use a chave `google` com o JSON da sua conta de serviço.
