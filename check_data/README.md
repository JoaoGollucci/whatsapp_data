# check_data

Validação diária dos dados na tabela `gold_messages` do BigQuery. Verifica se os dados de D-1 estão consistentes e envia alertas por email em caso de problemas.

## O que verifica

- `qtd_class` >= 4 (quantidade de classificações distintas)
- `qtd_id` > 0 (pelo menos um registro presente)

Se alguma condição falhar, um email de alerta é disparado.

## Variáveis de ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `GCP_PROJECT_ID` | Projeto GCP | `gauge-prod` |
| `ALERT_EMAIL_TO` | Email destinatário do alerta | — |
| `SMTP_SERVER` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_PORT` | Porta SMTP | `587` |
| `SMTP_USER` | Usuário SMTP (email remetente) | — |
| `SMTP_PASSWORD` | Senha/app password do SMTP | — |

## Execução com Docker

```bash
# Build
docker build -t check-data .

# Run
docker run --rm \
  -e SMTP_USER="alertas@gmail.com" \
  -e SMTP_PASSWORD="sua_app_password" \
  -e ALERT_EMAIL_TO="destino@email.com" \
  -v /path/to/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  check-data
```

## Frequência recomendada

Executar diariamente pela manhã (ex: Cloud Scheduler + Cloud Run Job).
