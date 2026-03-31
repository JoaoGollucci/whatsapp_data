FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests google-auth google-cloud-bigquery

COPY check_status_v2.py .

ENV WAHA_URLS=""
ENV WAHA_API_KEY=""
ENV PAGERDUTY_ROUTING_KEY=""
ENV BQ_TABLE="projeto_meli.status_waha_services"

CMD ["python", "check_status_v2.py"]
