FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema necessárias para o gcloud SDK
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | \
    tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg && \
    apt-get update && apt-get install -y google-cloud-cli && \
    rm -rf /var/lib/apt/lists/*

# Instalar dependências Python
RUN pip install --no-cache-dir requests google-auth prometheus-client

# Copiar o script
COPY check_status.py .

# Variáveis de ambiente
ENV WAHA_URLS="https://waha-meli-teste-180862637961.us-central1.run.app,https://waha-meli-2-180862637961.us-central1.run.app"
ENV EXPECTED_STATUS="WORKING"
ENV ALERT_EMAIL_TO="joao.gollucci@gauge.haus"
ENV SMTP_SERVER="smtp.gmail.com"
ENV SMTP_PORT="587"
ENV SMTP_USER="alertas.engenhariagauge@gmail.com"
ENV SMTP_PASSWORD="tloohwsxfgvdzfib"
ENV PUSHGATEWAY_URL="http://pushgateway:9091"
ENV PAGERDUTY_API_KEY=""
ENV WAHA_API_KEY=""

# Executar o script
CMD ["python", "check_status.py"]
