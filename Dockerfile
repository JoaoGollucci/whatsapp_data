# Dockerfile para WAHA (WhatsApp HTTP API) - Configurado para Google Cloud Run
# Usando a imagem oficial mais recente do WAHA
FROM devlikeapro/waha:latest

# Instalar Google Cloud SDK e ferramentas necessárias
USER root
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    lsb-release \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add - \
    && echo "deb https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Definir variáveis de ambiente para Cloud Run
ENV WHATSAPP_HOOK_URL=${WHATSAPP_HOOK_URL:-}
ENV WHATSAPP_DEFAULT_ENGINE=GOWS
ENV WHATSAPP_HOOK_EVENTS=message
ENV WAHA_NO_API_KEY=true
ENV WAHA_DASHBOARD_NO_PASSWORD=true
ENV WHATSAPP_SWAGGER_NO_PASSWORD=true

# Configurações específicas para GCS
ENV GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-}
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/service-account-key.json
ENV WAHA_SESSION_STORE_TYPE=LOCAL
ENV WAHA_FILES_FOLDER=/app/.media
ENV WAHA_SESSIONS_FOLDER=/app/.sessions

# Porta configurável para Cloud Run (usa PORT do ambiente)
EXPOSE ${PORT:-3000}

# Criar diretórios para dados temporários (serão sincronizados com GCS)
RUN mkdir -p /app/.sessions /app/.media && \
    chmod 755 /app/.sessions /app/.media

# Script para sincronização com GCS
COPY <<'EOF' /app/sync-gcs.sh
#!/bin/bash
set -e

# Função para fazer download dos dados do GCS
sync_from_gcs() {
    if [ ! -z "$GCS_BUCKET_NAME" ]; then
        echo "Downloading session data from GCS bucket: $GCS_BUCKET_NAME"
        gsutil -m rsync -r -d gs://$GCS_BUCKET_NAME/sessions/ /app/.sessions/ || echo "No existing session data found"
        gsutil -m rsync -r -d gs://$GCS_BUCKET_NAME/media/ /app/.media/ || echo "No existing media data found"
    fi
}

# Função para fazer upload dos dados para o GCS
sync_to_gcs() {
    if [ ! -z "$GCS_BUCKET_NAME" ]; then
        echo "Uploading session data to GCS bucket: $GCS_BUCKET_NAME"
        gsutil -m rsync -r -d /app/.sessions/ gs://$GCS_BUCKET_NAME/sessions/
        gsutil -m rsync -r -d /app/.media/ gs://$GCS_BUCKET_NAME/media/
    fi
}

# Função para sincronização periódica
periodic_sync() {
    while true; do
        sleep 300  # Sincroniza a cada 5 minutos
        sync_to_gcs
    done
}

# Baixar dados existentes do GCS no início
sync_from_gcs

# Iniciar sincronização periódica em background
periodic_sync &

# Configurar trap para fazer upload final quando o container for encerrado
trap 'sync_to_gcs' EXIT TERM INT

# Aguardar o processo principal
wait
EOF

RUN chmod +x /app/sync-gcs.sh

# Script de inicialização
COPY <<'EOF' /app/start.sh
#!/bin/bash
set -e

# Configurar porta do Cloud Run
export PORT=${PORT:-3000}

# Iniciar sincronização com GCS em background
/app/sync-gcs.sh &

# Iniciar a aplicação WAHA
exec node dist/main.js
EOF

RUN chmod +x /app/start.sh

# Comando para iniciar com sincronização GCS
CMD ["/app/start.sh"]

# Labels para documentação
LABEL maintainer="seu-email@exemplo.com"
LABEL description="WAHA WhatsApp HTTP API - Configurado para Google Cloud Run com persistência GCS"
LABEL version="latest"
LABEL cloud.platform="google-cloud-run"
LABEL storage.backend="google-cloud-storage"