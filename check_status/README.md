# check_status

Monitoramento de saúde dos endpoints WAHA. Verifica o status das sessões e cria incidentes no PagerDuty quando há falhas persistentes.

## Lógica de monitoramento

| Status | Ação |
|--------|------|
| `WORKING` | OK — resolve incidentes abertos |
| `FAILED` | Cria incidente PagerDuty imediatamente |
| `STARTING` | Incrementa contador; abre incidente após N verificações consecutivas |
| `STOPPED` | Tenta reiniciar a sessão; abre incidente após N tentativas |

O estado de cada endpoint (contadores, incidentes) é persistido no BigQuery para manter contexto entre execuções.

## Variáveis de ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `WAHA_URLS` | URLs dos endpoints WAHA (separadas por vírgula) | — |
| `WAHA_API_KEY` | Chave de API do WAHA (se não usar IAM) | — |
| `PAGERDUTY_ROUTING_KEY` | Routing key do PagerDuty Events API v2 | — |
| `BQ_TABLE` | Tabela de estado no BigQuery | `projeto_meli.status_waha_services` |
| `STARTING_THRESHOLD` | Nº de checks em STARTING antes de alertar | `3` |
| `STOPPED_THRESHOLD` | Nº de checks em STOPPED antes de alertar | `3` |

## Execução com Docker

```bash
# Build
docker build -t check-status .

# Run
docker run --rm \
  -e WAHA_URLS="https://waha-1.run.app,https://waha-2.run.app" \
  -e WAHA_API_KEY="sua_chave" \
  -e PAGERDUTY_ROUTING_KEY="sua_routing_key" \
  -v /path/to/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  check-status
```

## Frequência recomendada

Executar a cada 5-10 minutos (Cloud Scheduler + Cloud Run Job).
