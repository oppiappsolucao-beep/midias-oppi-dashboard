# Deploy Streamlit no EasyPanel — midias.oppitech.com.br

## Configuração do serviço "midias"

| Campo | Valor |
|-------|-------|
| **Tipo** | App / GitHub |
| **Repositório** | `oppiappsolucao-beep/midias-oppi-dashboard` |
| **Branch** | `main` |
| **Porta** | `8501` |
| **Comando de start** | `streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.enableXsrfProtection=false --browser.gatherUsageStats=false` |

Ou use o [`Dockerfile.streamlit`](Dockerfile.streamlit) se o EasyPanel deployar via Docker.

## Variáveis de ambiente (EasyPanel → Ambiente)

```
GOOGLE_TYPE=service_account
GOOGLE_PROJECT_ID=...
GOOGLE_PRIVATE_KEY_ID=...
GOOGLE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n
GOOGLE_CLIENT_EMAIL=...@....iam.gserviceaccount.com
GOOGLE_CLIENT_ID=...
```

> A chave privada deve ter `\n` nos quebras de linha, ou colar o JSON inteiro se o painel suportar.

## Logs normais

```
Uvicorn running on http://0.0.0.0:8501
You can now view your Streamlit app in your browser.
```

Isso é **esperado** — versões recentes do Streamlit usam Uvicorn internamente.

## Publicar mudanças

1. Edite `app.py` localmente
2. GitHub Desktop → Commit → **Push**
3. No EasyPanel, clique **Implantar** (ou aguarde auto-deploy)
4. Acompanhe os **Logs** até aparecer "running on 0.0.0.0:8501"
5. Abra `midias.oppitech.com.br` com **Ctrl+F5**

## Se aparecer erro 502 depois de usar o painel

O EasyPanel (proxy/nginx) pode cortar conexões ociosas do Streamlit. No serviço **midias**, aumente o timeout do proxy se houver opção, ou adicione no nginx:

```
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

Depois **Implantar** de novo e testar com **Ctrl+F5**.

## Se aparecer "Stopping..." nos logs

- Normal durante redeploy (para e sobe de novo)
- Se ficar parado: clique **Implantar** de novo
- Verifique se `requirements.txt` na raiz está sendo instalado no build
