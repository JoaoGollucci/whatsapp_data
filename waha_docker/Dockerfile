# Usa a imagem base do WAHA
FROM devlikeapro/waha:latest

# Define a arquitetura explicitamente (útil em algumas builds no Windows/WSL)
# Essa linha pode ser omitida se você fizer build em ambiente amd64 nativo
# PLATFORM linux/amd64

# Define variáveis de ambiente padrão (podem ser sobrescritas em runtime)
ENV WHATSAPP_HOOK_URL=https://waha-listener-180862637961.us-central1.run.app/webhook/webhook
ENV WHATSAPP_DEFAULT_ENGINE=GOWS
ENV WHATSAPP_HOOK_EVENTS=message
ENV WAHA_NO_API_KEY=True
ENV WAHA_DASHBOARD_NO_PASSWORD=True
ENV WHATSAPP_SWAGGER_NO_PASSWORD=True
ENV WHATSAPP_RESTART_ALL_SESSIONS=True
ENV WAHA_SESSION_CONFIG_IGNORE_STATUS=True
ENV WAHA_SESSION_CONFIG_IGNORE_BROADCAST=True

# Expõe a porta padrão
EXPOSE 3000

# Cria volumes para sessões e mídia
VOLUME ["/app/.sessions", "/app/.media"]

# Define o diretório de trabalho
WORKDIR /app
