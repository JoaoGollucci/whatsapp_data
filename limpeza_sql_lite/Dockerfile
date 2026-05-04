FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir google-cloud-storage pandas pyarrow

COPY limpeza_sqlite.py .

ENV GCS_BUCKET_NAME=""
ENV GCS_ORIGIN_PATH=""
ENV GCS_OUTPUT_PATH=""
ENV PYTHONUNBUFFERED=1

CMD ["python", "-u", "limpeza_sqlite.py"]
