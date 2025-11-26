FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
RUN pip install --no-cache-dir requests google-auth

# Copiar o script
COPY test_endpoint.py .

# Variável de ambiente (pode ser sobrescrita no docker run)
ENV TEST_URLS="https://waha-meli-teste-180862637961.us-central1.run.app/api/sessions,https://waha-meli-2-180862637961.us-central1.run.app/api/sessions"

# Executar o script
CMD ["python", "test_endpoint.py"]