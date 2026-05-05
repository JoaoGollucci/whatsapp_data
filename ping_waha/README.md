# ping_waha

Teste de conectividade dos endpoints WAHA. Faz requisições autenticadas (IAM) e reporta métricas de disponibilidade para o Prometheus Pushgateway.

## O que faz

1. Itera sobre os endpoints configurados
2. Obtém um ID Token GCP para autenticação no Cloud Run
3. Faz um GET com header `Authorization` e `X-Api-Key`
4. Reporta status (1=OK, 0=FALHA) no Prometheus
5. Retorna exit code 1 se algum endpoint falhar

## Variáveis de ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `TEST_URLS` | URLs dos endpoints para testar (separadas por vírgula) | — |
| `PUSHGATEWAY_URL` | URL do Prometheus Pushgateway | — |
| `API_KEY` | Chave de API do WAHA (header `X-Api-Key`) | — |

## Execução com Docker

```bash
# Build
docker build -t ping-waha .

# Run
docker run --rm \
  -e TEST_URLS="https://waha-1.run.app/api/sessions,https://waha-2.run.app/api/sessions" \
  -e PUSHGATEWAY_URL="http://pushgateway:9091" \
  -e API_KEY="sua_chave" \
  -v /path/to/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  ping-waha
```

## Pré-requisitos

- A Service Account usada precisa ter a role `roles/run.invoker` nos serviços WAHA de destino.

## Frequência recomendada

Executar a cada 5 minutos para monitoramento contínuo.
