# WhatsApp Pipeline

Pipeline de coleta, processamento e monitoramento de mensagens WhatsApp via WAHA, com integração ao GCP (BigQuery, Pub/Sub, GCS).

## Arquitetura

```
WAHA (WhatsApp) → Listener (webhook) → Pub/Sub → Pipeline de dados → BigQuery
```

## Componentes

| Pasta | Função |
|-------|--------|
| `waha_docker/` | Container WAHA customizado para captura de mensagens |
| `listener/` | Webhook que recebe eventos do WAHA e publica no Pub/Sub |
| `limpeza_sql_lite/` | Processamento manual do banco SQLite (extrai parquet, limpa registros antigos) |
| `check_status/` | Monitoramento de saúde dos endpoints WAHA com alertas PagerDuty |
| `check_data/` | Validação diária dos dados no BigQuery com alertas por email |
| `ping_waha/` | Teste de conectividade dos endpoints WAHA com métricas Prometheus |

## Estrutura de dados (GCS/BigQuery)

- `landing/` — Dados brutos
- `bronze/` — Primeira camada de processamento
- `silver/` — Dados tratados
- `gold/` — Dados prontos para consumo

## Pré-requisitos

- Docker
- Conta GCP com acesso a BigQuery, Pub/Sub e GCS
- Service Account com permissões adequadas
- Credenciais configuradas via variáveis de ambiente ou mounted secrets
