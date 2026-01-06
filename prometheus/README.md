# Prometheus

Stack completa de monitoramento com Prometheus e Pushgateway para o listener WAHA.

## Arquitetura

```
Listener (WAHA) → Pushgateway (9091) → Prometheus (9090) → Grafana (opcional)
```

## Como usar

### Subir a stack completa (Prometheus + Pushgateway)

```bash
cd prometheus
docker-compose up -d
```

Isso vai subir:
- **Prometheus** na porta 9090
- **Pushgateway** na porta 9091

### Usar apenas o Prometheus

```bash
docker build -t prometheus-waha .
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v prometheus-data:/prometheus \
  prometheus-waha
```

## Acessar interfaces

- **Prometheus**: http://localhost:9090
- **Pushgateway**: http://localhost:9091

## Configurar o listener

No listener, defina as variáveis de ambiente:

```bash
PROMETHEUS_ENABLED=true
PROMETHEUS_PUSHGATEWAY_URL=http://pushgateway:9091
```

Se os serviços estiverem em hosts diferentes:

```bash
PROMETHEUS_PUSHGATEWAY_URL=http://<ip-do-servidor>:9091
```

## Consultar métricas

### Via interface web
Acesse http://localhost:9090/graph e use queries como:

```promql
# Total de webhooks recebidos
waha_webhook_requests_total

# Taxa de webhooks por segundo
rate(waha_webhook_requests_total[5m])

# Webhooks com erro
waha_webhook_requests_total{status="error"}

# Latência média de processamento
rate(waha_webhook_duration_seconds_sum[5m]) / rate(waha_webhook_duration_seconds_count[5m])

# Total de mensagens publicadas no Pub/Sub
waha_pubsub_published_total
```

### Via API
```bash
curl 'http://localhost:9090/api/v1/query?query=waha_webhook_requests_total'
```

## Configuração

O arquivo [prometheus.yml](prometheus.yml) está configurado para:
- Coletar métricas do Pushgateway a cada 15 segundos
- Preservar labels originais (`honor_labels: true`)
- Retenção de dados: 30 dias
- Filtrar apenas métricas que começam com `waha_`

## Recarregar configuração

Sem restart:
```bash
curl -X POST http://localhost:9090/-/reload
```

## Verificar status dos targets

http://localhost:9090/targets

## Métricas disponíveis

- `waha_webhook_requests_total`: Total de requisições webhook (com labels: event_type, status)
- `waha_pubsub_published_total`: Total de mensagens publicadas (com label: status)
- `waha_webhook_duration_seconds`: Histograma de latência de processamento

## Próximos passos

Para visualização avançada, considere adicionar o Grafana:

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - grafana-data:/var/lib/grafana
```

## Troubleshooting

### Métricas não aparecem
1. Verifique se o Pushgateway está recebendo dados: http://localhost:9091/metrics
2. Verifique os targets no Prometheus: http://localhost:9090/targets
3. Confirme que o listener está com `PROMETHEUS_ENABLED=true`

### Erro de conexão
Certifique-se que todos os serviços estão na mesma rede Docker ou use IPs/hostnames acessíveis.
