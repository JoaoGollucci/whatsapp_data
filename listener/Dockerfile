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

# Executa o listener
CMD ["python", "teste_listener.py"]
