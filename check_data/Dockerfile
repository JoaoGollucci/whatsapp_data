FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir google-cloud-bigquery

# Copiar o script
COPY check_data.py .

# Variáveis de ambiente
ENV GCP_PROJECT_ID="gauge-prod"
ENV BQ_DATASET_TABLE="projeto_meli.vw_aff_quantity"
ENV BQ_DATE_COLUMN="date"
ENV DAYS_BACK="1"
ENV ALERT_EMAIL_TO="joao.gollucci@gauge.haus"
ENV SMTP_SERVER="smtp.gmail.com"
ENV SMTP_PORT="587"
ENV SMTP_USER=""
ENV SMTP_PASSWORD=""

# Executar o script
CMD ["python", "check_data.py"]
