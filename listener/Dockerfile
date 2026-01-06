FROM python:3.11-slim

WORKDIR /app

# Copia e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do listener
COPY teste_listener.py .

# Variáveis de ambiente padrão
ENV PORT=5678
ENV GCP_PROJECT=gauge-prod
ENV PUBSUB_TOPIC=waha.events
ENV PROMETHEUS_ENABLED=false
ENV PROMETHEUS_USE_GCP_AUTH=false
# ENV PROMETHEUS_PUSHGATEWAY_URL=http://prometheus-pushgateway:9091
# Para Cloud Run com IAM: ENV PROMETHEUS_PUSHGATEWAY_URL=https://pushgateway-xxxx.run.app

# Executa o listener
CMD ["python", "teste_listener.py"]
