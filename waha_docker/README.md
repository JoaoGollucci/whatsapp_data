# waha_docker

Container WAHA customizado para captura de mensagens WhatsApp. Baseado na imagem oficial `devlikeapro/waha:latest` com configurações pré-definidas para o projeto.

## Configurações padrão

| Variável | Valor | Descrição |
|----------|-------|-----------|
| `WHATSAPP_HOOK_URL` | URL do listener | Webhook para onde os eventos são enviados |
| `WHATSAPP_DEFAULT_ENGINE` | `GOWS` | Engine de conexão (Go WebSocket) |
| `WHATSAPP_HOOK_EVENTS` | `message` | Eventos capturados |
| `WHATSAPP_RESTART_ALL_SESSIONS` | `True` | Reinicia sessões ao iniciar o container |
| `WAHA_SESSION_CONFIG_IGNORE_STATUS` | `True` | Ignora mensagens de status |
| `WAHA_SESSION_CONFIG_IGNORE_BROADCAST` | `True` | Ignora broadcasts |

## Volumes

| Path | Função |
|------|--------|
| `/app/.sessions` | Dados das sessões WhatsApp (manter persistente) |
| `/app/.media` | Mídia baixada |

## Execução com Docker

```bash
# Build
docker build -t waha-custom .

# Run
docker run -d \
  -p 3000:3000 \
  -e WHATSAPP_HOOK_URL="https://seu-listener.run.app/webhook/webhook" \
  -v waha_sessions:/app/.sessions \
  -v waha_media:/app/.media \
  waha-custom
```

## Porta

- `3000` — API REST e Dashboard do WAHA

## Observações

- Na primeira execução, acesse `http://localhost:3000` para escanear o QR Code e vincular a sessão WhatsApp
- Os volumes devem ser persistidos para não perder a sessão entre restarts
- Em produção (Cloud Run), os dados de sessão podem ser sincronizados com GCS
