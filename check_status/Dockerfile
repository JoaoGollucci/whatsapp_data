FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir requests google-auth

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

# Executar o script
CMD ["python", "check_status.py"]
