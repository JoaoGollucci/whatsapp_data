# BigQuery Data Monitor - Cloud Run Job

Monitor de dados no BigQuery com alertas por email quando dados estão ausentes.

## 🚀 Deploy no Cloud Run Job

```bash
gcloud run jobs deploy bq-data-monitor \
  --source . \
  --region us-central1 \
  --set-env-vars "GCP_PROJECT_ID=gauge-prod" \
  --set-env-vars "BQ_DATASET_TABLE=projeto_meli.vw_aff_quantity" \
  --set-env-vars "BQ_DATE_COLUMN=date" \
  --set-env-vars "DAYS_BACK=1" \
  --set-env-vars "ALERT_EMAIL_TO=seu-email@exemplo.com" \
  --set-env-vars "SMTP_USER=seu-email@gmail.com" \
  --set-env-vars "SMTP_PASSWORD=sua-senha-app" \
  --max-retries 0 \
  --task-timeout 300
```

## 📋 Variáveis de Ambiente Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `GCP_PROJECT_ID` | ID do projeto GCP | `gauge-prod` |
| `BQ_DATASET_TABLE` | Dataset.Tabela no BigQuery | `projeto_meli.vw_aff_quantity` |
| `BQ_DATE_COLUMN` | Nome da coluna de data | `date` |
| `DAYS_BACK` | Quantos dias atrás verificar (D-N) | `1` |
| `ALERT_EMAIL_TO` | Email para receber alertas | `alerta@exemplo.com` |
| `SMTP_USER` | Usuário SMTP (email remetente) | `monitor@gmail.com` |
| `SMTP_PASSWORD` | Senha ou App Password do SMTP | `xxxx xxxx xxxx xxxx` |

## 📋 Variáveis Opcionais

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `SMTP_SERVER` | Servidor SMTP | `smtp.gmail.com` |
| `SMTP_PORT` | Porta SMTP | `587` |

## 🔍 Como Funciona

1. **Conecta ao BigQuery** usando as credenciais da service account do Cloud Run
2. **Executa a query** verificando dados de D-N (ex: D-1 = ontem)
3. **Verifica resultados**:
   - ✅ Dados encontrados → Script termina com sucesso (exit 0)
   - ❌ Dados ausentes → Envia email de alerta (exit 1)
   - 💥 Erro crítico → Envia email de erro (exit 1)

## 🔧 Permissões Necessárias

A service account do Cloud Run Job precisa de permissões no BigQuery:

```bash
# Dar permissão de leitura no dataset
gcloud projects add-iam-policy-binding gauge-prod \
  --member='serviceAccount:PROJECT-NUMBER-compute@developer.gserviceaccount.com' \
  --role='roles/bigquery.dataViewer'

# Dar permissão para executar jobs
gcloud projects add-iam-policy-binding gauge-prod \
  --member='serviceAccount:PROJECT-NUMBER-compute@developer.gserviceaccount.com' \
  --role='roles/bigquery.jobUser'
```

## 📧 Configurar Gmail (recomendado)

1. **Ativar verificação em 2 etapas** na sua conta Google
2. **Gerar App Password**:
   - Acesse: https://myaccount.google.com/apppasswords
   - Crie uma senha de app para "Mail"
   - Use essa senha em `SMTP_PASSWORD`

## ⏰ Agendar Execução (Cloud Scheduler)

```bash
# Criar scheduler para executar diariamente às 8h
gcloud scheduler jobs create http bq-data-check \
  --location us-central1 \
  --schedule="0 8 * * *" \
  --time-zone="America/Sao_Paulo" \
  --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/gauge-prod/jobs/bq-data-monitor:run" \
  --http-method POST \
  --oauth-service-account-email PROJECT-NUMBER-compute@developer.gserviceaccount.com
```

### Exemplos de Schedule (Cron):
- `0 8 * * *` - Todo dia às 8h
- `0 */6 * * *` - A cada 6 horas
- `0 8,18 * * *` - Às 8h e 18h
- `0 8 * * 1-5` - Dias úteis às 8h

## 🧪 Testar Localmente

```bash
# Instalar dependências
pip install google-cloud-bigquery

# Autenticar com GCP
gcloud auth application-default login

# Configurar variáveis
export GCP_PROJECT_ID="gauge-prod"
export BQ_DATASET_TABLE="projeto_meli.vw_aff_quantity"
export BQ_DATE_COLUMN="date"
export DAYS_BACK="1"
export ALERT_EMAIL_TO="seu-email@exemplo.com"
export SMTP_USER="seu-email@gmail.com"
export SMTP_PASSWORD="sua-senha-app"

# Executar
python check_data.py
```

## 📊 Email de Alerta

### Quando há dados ausentes:
- 🚨 Assunto: "ALERTA: Dados ausentes no BigQuery - YYYY-MM-DD"
- Detalhes da query executada
- Sugestões de verificação

### Quando há erro crítico:
- 💥 Assunto: "ERRO CRÍTICO: Falha na verificação BigQuery"
- Mensagem de erro detalhada

## 🔍 Monitorar Execuções

```bash
# Ver logs
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=bq-data-monitor" --limit 50

# Ver execuções
gcloud run jobs executions list --job=bq-data-monitor --region=us-central1

# Executar manualmente
gcloud run jobs execute bq-data-monitor --region=us-central1
```

## 💡 Casos de Uso

- **Monitoramento de Pipeline ETL** - Verificar se dados foram processados
- **Validação de Carga Diária** - Garantir que dados do dia anterior existem
- **Alertas de Falha de Ingestão** - Detectar problemas no pipeline de dados
- **SLA de Dados** - Garantir disponibilidade de dados para stakeholders

## 💰 Custos Estimados

- **Cloud Run Jobs**: ~$0.10/mês (1 execução/dia)
- **BigQuery**: Incluído no free tier (queries < 1TB/mês)
- **Cloud Scheduler**: ~$0.10/mês
- **Total**: ~$0.20/mês
