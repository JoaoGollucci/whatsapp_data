# Configuração de Segurança no Cloud Run

Este guia explica como configurar Prometheus Pushgateway e o listener no Cloud Run com autenticação IAM do Google Cloud.

## Arquitetura Segura

```
Listener (Cloud Run) → [Token IAM] → Pushgateway (Cloud Run) → [Token IAM] → Prometheus (Cloud Run/GKE)
```

## 1. Deploy do Pushgateway no Cloud Run

### Build e Push da imagem

```bash
cd push_gateway

# Build
gcloud builds submit --tag gcr.io/SEU-PROJETO/pushgateway

# Deploy no Cloud Run COM autenticação IAM
gcloud run deploy pushgateway \
  --image gcr.io/SEU-PROJETO/pushgateway \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --no-allow-unauthenticated \
  --port 9091
```

**Importante**: Use `--no-allow-unauthenticated` para exigir autenticação IAM.

### Obter a URL do serviço

```bash
gcloud run services describe pushgateway --region us-central1 --format 'value(status.url)'
```

Exemplo: `https://pushgateway-xxxx-uc.a.run.app`

## 2. Deploy do Listener no Cloud Run

### Build e Push da imagem

```bash
cd listener

# Build
gcloud builds submit --tag gcr.io/SEU-PROJETO/waha-listener

# Deploy no Cloud Run
gcloud run deploy waha-listener \
  --image gcr.io/SEU-PROJETO/waha-listener \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --allow-unauthenticated \
  --port 5678 \
  --set-env-vars "GCP_PROJECT=SEU-PROJETO,PUBSUB_TOPIC=waha.events,PROMETHEUS_ENABLED=true,PROMETHEUS_USE_GCP_AUTH=true,PROMETHEUS_PUSHGATEWAY_URL=https://pushgateway-xxxx-uc.a.run.app"
```

**Nota**: O listener pode ser `--allow-unauthenticated` se for receber webhooks públicos, mas use `WAHA_TOKEN` para validação customizada.

## 3. Configurar Permissões IAM

O listener precisa de permissão para invocar o Pushgateway:

```bash
# Obter a service account do listener
LISTENER_SA=$(gcloud run services describe waha-listener \
  --region us-central1 \
  --format 'value(spec.template.spec.serviceAccountName)')

# Dar permissão de invoker no Pushgateway
gcloud run services add-iam-policy-binding pushgateway \
  --region us-central1 \
  --member="serviceAccount:${LISTENER_SA}" \
  --role="roles/run.invoker"
```

## 4. Deploy do Prometheus no Cloud Run (Opcional)

### Considerações importantes

- **Não é ideal**: Prometheus funciona melhor em GKE ou Compute Engine devido à necessidade de scraping contínuo
- **Alternativa recomendada**: Use Cloud Monitoring (Stackdriver) ou GKE com Prometheus Operator

Se ainda quiser usar Cloud Run:

```bash
cd prometheus

# Build
gcloud builds submit --tag gcr.io/SEU-PROJETO/prometheus

# Deploy
gcloud run deploy prometheus \
  --image gcr.io/SEU-PROJETO/prometheus \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2 \
  --no-allow-unauthenticated \
  --port 9090
```

**Problema**: Cloud Run scale-to-zero pode perder dados. Considere:
- Min instances: `--min-instances 1`
- Ou use GKE/Compute Engine para Prometheus

## 5. Configurar Prometheus para Scrape Seguro

Se o Pushgateway estiver no Cloud Run, o Prometheus precisa se autenticar. Atualize [prometheus.yml](prometheus/prometheus.yml):

```yaml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    scheme: https
    authorization:
      credentials_file: /var/run/secrets/gcp/token
    static_configs:
      - targets: ['pushgateway-xxxx-uc.a.run.app']
```

**Nota**: Isso requer configuração adicional de tokens no container do Prometheus, que é complexo no Cloud Run. **Recomendamos rodar Prometheus fora do Cloud Run** (GKE ou Compute Engine).

## Arquitetura Recomendada para Produção

### Opção 1: Cloud Run + GKE (Recomendado)

```
Listener (Cloud Run) → [IAM] → Pushgateway (Cloud Run) → Prometheus (GKE) → Grafana (GKE)
```

- Listener e Pushgateway no Cloud Run (serverless, escala automática)
- Prometheus e Grafana no GKE (sempre disponível, melhor para scraping)

### Opção 2: Cloud Monitoring (Nativo GCP)

```
Listener (Cloud Run) → Cloud Monitoring API (direto)
```

Use a biblioteca `google-cloud-monitoring` ao invés de Prometheus:

```python
from google.cloud import monitoring_v3

client = monitoring_v3.MetricServiceClient()
# Enviar métricas customizadas diretamente
```

## Variáveis de Ambiente do Listener

Para usar autenticação GCP:

```bash
# Obrigatórias
GCP_PROJECT=seu-projeto
PUBSUB_TOPIC=waha.events

# Prometheus com autenticação
PROMETHEUS_ENABLED=true
PROMETHEUS_USE_GCP_AUTH=true
PROMETHEUS_PUSHGATEWAY_URL=https://pushgateway-xxxx-uc.a.run.app

# Opcional: token customizado para webhooks
WAHA_TOKEN=seu-token-secreto
```

## Testar Autenticação

### Testar acesso ao Pushgateway (deve falhar sem token)

```bash
curl https://pushgateway-xxxx-uc.a.run.app/metrics
# Resposta: 403 Forbidden
```

### Testar com token

```bash
# Obter token
TOKEN=$(gcloud auth print-identity-token \
  --audiences=https://pushgateway-xxxx-uc.a.run.app)

# Testar
curl -H "Authorization: Bearer $TOKEN" \
  https://pushgateway-xxxx-uc.a.run.app/metrics
```

## Monitoramento e Logs

### Ver logs do listener

```bash
gcloud run logs read waha-listener --region us-central1 --limit 50
```

### Ver logs do pushgateway

```bash
gcloud run logs read pushgateway --region us-central1 --limit 50
```

### Métricas do Cloud Run

Acesse no Console: Cloud Run > Seu Serviço > Metrics

Ou via gcloud:

```bash
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"'
```

## Custos Estimados

- **Listener**: ~$5-20/mês (depende do tráfego)
- **Pushgateway**: ~$5-10/mês (poucas requisições)
- **Prometheus no GKE**: ~$50-100/mês (cluster pequeno)

Cloud Run cobra por:
- Requisições: $0.40 por 1M requisições
- CPU/Memória: $0.00002400 por vCPU-segundo
- Rede: $0.12 por GB

## Troubleshooting

### Erro 403 no Pushgateway

```
[ERROR] Pushgateway retornou status 403
```

**Solução**: Verifique as permissões IAM:

```bash
gcloud run services get-iam-policy pushgateway --region us-central1
```

### Erro ao obter token

```
[ERROR] Falha ao obter token GCP
```

**Solução**: Verifique se o listener tem permissão para gerar tokens:

```bash
gcloud projects add-iam-policy-binding SEU-PROJETO \
  --member="serviceAccount:${LISTENER_SA}" \
  --role="roles/iam.serviceAccountTokenCreator"
```

### Métricas não aparecem

1. Verifique logs do listener: `gcloud run logs read waha-listener`
2. Verifique se o Pushgateway está recebendo: `curl -H "Authorization: Bearer $TOKEN" https://pushgateway-xxxx.run.app/metrics`
3. Verifique se `PROMETHEUS_ENABLED=true` está configurado

## Segurança Adicional

### 1. VPC Connector (Acesso privado)

Configure VPC para comunicação privada entre serviços:

```bash
gcloud compute networks vpc-access connectors create prometheus-connector \
  --region us-central1 \
  --range 10.8.0.0/28

gcloud run services update pushgateway \
  --vpc-connector prometheus-connector \
  --vpc-egress private-ranges-only
```

### 2. Secret Manager

Use Secret Manager para tokens sensíveis:

```bash
echo -n "seu-token-secreto" | gcloud secrets create waha-token --data-file=-

gcloud run services update waha-listener \
  --update-secrets WAHA_TOKEN=waha-token:latest
```

### 3. Cloud Armor (WAF)

Proteja endpoints públicos com Cloud Armor (requer Load Balancer).

## Referências

- [Cloud Run Authentication](https://cloud.google.com/run/docs/authenticating/overview)
- [IAM Roles for Cloud Run](https://cloud.google.com/run/docs/reference/iam/roles)
- [Cloud Monitoring](https://cloud.google.com/monitoring/docs)
