# Prometheus Pushgateway

Pushgateway para receber métricas do listener WAHA.

## Como usar

### Usando Docker Compose (recomendado)

```bash
docker-compose up -d
```

### Usando Docker direto

```bash
# Build
docker build -t prometheus-pushgateway .

# Run
docker run -d \
  --name prometheus-pushgateway \
  -p 9091:9091 \
  -v pushgateway-data:/data \
  prometheus-pushgateway
```

## Acessar a interface

Após iniciar, acesse: http://localhost:9091

## Conectar o listener

No listener, configure a variável de ambiente:

```bash
PROMETHEUS_ENABLED=true
PROMETHEUS_PUSHGATEWAY_URL=http://prometheus-pushgateway:9091
```

Ou se estiver em hosts diferentes:

```bash
PROMETHEUS_PUSHGATEWAY_URL=http://<ip-do-servidor>:9091
```

## Características

- **Porta:** 9091
- **Persistência:** Métricas são salvas em `/data/pushgateway.data` a cada 5 minutos
- **Admin API:** Habilitada para facilitar gerenciamento
- **Lifecycle API:** Permite recarregar configurações sem restart

## Verificar métricas

```bash
curl http://localhost:9091/metrics
```

## Limpar métricas de um job específico

```bash
curl -X DELETE http://localhost:9091/metrics/job/waha_listener
```
