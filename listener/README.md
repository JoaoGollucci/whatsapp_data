# listener

Serviço web (Flask) que recebe webhooks do WAHA e publica os eventos no Google Pub/Sub. Roda como um serviço contínuo (Cloud Run).

## Endpoints

| Rota | Método | Função |
|------|--------|--------|
| `/` | GET | Health check |
| `/webhook/webhook` | POST | Recebe eventos do WAHA |

## Funcionalidades

- Validação opcional de token (`X-WAHA-Token`)
- Deduplicação de mensagens via hash SHA-256
- Métricas Prometheus (opcional) com push para Pushgateway
- Suporte a autenticação GCP para Pushgateway em Cloud Run

## Variáveis de ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `GCP_PROJECT` | Projeto GCP | — |
| `PUBSUB_TOPIC` | Nome do tópico Pub/Sub | — |
| `WAHA_TOKEN` | Token para validação do webhook (opcional) | — |
| `PORT` | Porta do servidor | `5678` |
| `PROMETHEUS_ENABLED` | Habilitar métricas Prometheus | `false` |
| `PROMETHEUS_PUSHGATEWAY_URL` | URL do Pushgateway | — |
| `PROMETHEUS_USE_GCP_AUTH` | Usar autenticação GCP no Pushgateway | `false` |

## Execução com Docker

```bash
# Build
docker build -t waha-listener .

# Run
docker run --rm -p 5678:5678 \
  -e GCP_PROJECT="meu-projeto" \
  -e PUBSUB_TOPIC="waha.events" \
  -e WAHA_TOKEN="token_secreto" \
  -v /path/to/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  waha-listener
```

## Dependências

- Flask 3.0.0
- google-cloud-pubsub 2.21.0
- gunicorn 21.2.0
- prometheus-client 0.19.0
- google-auth 2.25.2
- requests 2.31.0

## Observações

- Em produção, usar gunicorn como entrypoint para melhor performance
- O WAHA deve estar configurado com `WHATSAPP_HOOK_URL` apontando para este serviço
