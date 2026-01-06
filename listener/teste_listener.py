import os, json, hashlib, time
from flask import Flask, request, abort
from google.api_core.exceptions import NotFound
from google.cloud import pubsub_v1
from prometheus_client import Counter, Histogram
import requests
try:
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

# Env vars esperadas:
# - GCP_PROJECT (ex.: "meu-projeto")
# - PUBSUB_TOPIC (ex.: "waha.events")
# - WAHA_TOKEN (opcional; valida header X-WAHA-Token)
# - PORT (Cloud Run define automaticamente)
# - PROMETHEUS_ENABLED (opcional; default "false")
# - PROMETHEUS_PUSHGATEWAY_URL (ex.: "https://pushgateway-xxxx.run.app")
# - PROMETHEUS_USE_GCP_AUTH (opcional; default "false", para Cloud Run com IAM)

PROJECT = os.getenv("GCP_PROJECT")
TOPIC = os.getenv("PUBSUB_TOPIC")
WAHA_TOKEN = os.getenv("WAHA_TOKEN", "")
PROMETHEUS_ENABLED = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
PROMETHEUS_PUSHGATEWAY_URL = os.getenv("PROMETHEUS_PUSHGATEWAY_URL", "")
PROMETHEUS_USE_GCP_AUTH = os.getenv("PROMETHEUS_USE_GCP_AUTH", "false").lower() == "true"

if not PROJECT or not TOPIC:
    raise RuntimeError("Defina GCP_PROJECT e PUBSUB_TOPIC no ambiente.")

if PROMETHEUS_ENABLED and not PROMETHEUS_PUSHGATEWAY_URL:
    raise RuntimeError("PROMETHEUS_ENABLED=true requer PROMETHEUS_PUSHGATEWAY_URL")

if PROMETHEUS_USE_GCP_AUTH and not GOOGLE_AUTH_AVAILABLE:
    raise RuntimeError("PROMETHEUS_USE_GCP_AUTH=true requer google-auth instalado")

# Métricas do Prometheus
webhook_requests_total = Counter(
    'waha_webhook_requests_total',
    'Total de requisições webhook recebidas',
    ['event_type', 'status']
)

pubsub_messages_published_total = Counter(
    'waha_pubsub_published_total',
    'Total de mensagens publicadas no Pub/Sub',
    ['status']
)

webhook_duration_seconds = Histogram(
    'waha_webhook_duration_seconds',
    'Duração do processamento de webhooks',
    ['event_type']
)

def get_gcp_id_token(audience: str) -> str:
    """Obtém token de identidade do Google para autenticação em Cloud Run"""
    if not GOOGLE_AUTH_AVAILABLE:
        raise RuntimeError("google-auth não está instalado")
    
    try:
        auth_req = Request()
        token = id_token.fetch_id_token(auth_req, audience)
        return token
    except Exception as e:
        print(f"[ERROR] Falha ao obter token GCP: {e}")
        raise

def push_metrics_to_prometheus():
    """Envia métricas para o Prometheus Pushgateway"""
    if not PROMETHEUS_ENABLED:
        return
    
    try:
        from prometheus_client import CollectorRegistry, generate_latest
        from prometheus_client.core import REGISTRY
        
        # Gera as métricas em formato Prometheus
        metrics_data = generate_latest(REGISTRY)
        
        # URL do pushgateway
        url = f"{PROMETHEUS_PUSHGATEWAY_URL.rstrip('/')}/metrics/job/waha_listener"
        
        headers = {'Content-Type': 'text/plain; charset=utf-8'}
        
        # Se usar autenticação GCP, adiciona o token
        if PROMETHEUS_USE_GCP_AUTH:
            try:
                token = get_gcp_id_token(PROMETHEUS_PUSHGATEWAY_URL)
                headers['Authorization'] = f'Bearer {token}'
            except Exception as e:
                print(f"[ERROR] Falha ao obter token de autenticação: {e}")
                return
        
        # Envia as métricas via HTTP POST
        response = requests.post(
            url,
            data=metrics_data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code not in (200, 201, 202):
            print(f"[WARN] Pushgateway retornou status {response.status_code}: {response.text}")
        
    except Exception as e:
        print(f"[WARN] Falha ao enviar métricas para Prometheus: {e}")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT, TOPIC)

app = Flask(__name__)

def stable_message_id(payload: dict) -> str:
    # ID estável se não vier no payload (evita duplicados)
    key = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

@app.route("/", methods=["GET"])
def health():
    """Health check para Cloud Run"""
    if PROMETHEUS_ENABLED:
        webhook_requests_total.labels(event_type='health', status='success').inc()
        push_metrics_to_prometheus()
    return {"status": "healthy", "service": "waha-webhook-listener", "prometheus_enabled": PROMETHEUS_ENABLED}, 200

@app.route("/webhook/webhook", methods=["POST"])
def webhook():
    start_time = time.time()
    
    # (opcional) token simples no header
    token = request.headers.get("X-WAHA-Token")
    if WAHA_TOKEN and token != WAHA_TOKEN:
        print("[SECURITY] Token inválido recebido")
        if PROMETHEUS_ENABLED:
            webhook_requests_total.labels(event_type='unknown', status='unauthorized').inc()
            push_metrics_to_prometheus()
        abort(401, "invalid token")

    body = request.get_json(silent=True) or {}
    event = body.get("event") or "message"
    payload = body.get("payload") or body

    msg_id = (
        payload.get("id")
        or payload.get("messageId")
        or stable_message_id(payload)
    )

    envelope = {
        "event": event,
        "message_id": msg_id,
        "payload": payload,
    }
    data = json.dumps(envelope, ensure_ascii=False).encode("utf-8")

    try:
        future = publisher.publish(topic_path, data=data)
        pubsub_msg_id = future.result(timeout=10)
        print(f"[SUCCESS] Publicado no Pub/Sub: {pubsub_msg_id} | Event: {event} | MsgID: {msg_id}")
        
        if PROMETHEUS_ENABLED:
            webhook_requests_total.labels(event_type=event, status='success').inc()
            pubsub_messages_published_total.labels(status='success').inc()
            webhook_duration_seconds.labels(event_type=event).observe(time.time() - start_time)
            push_metrics_to_prometheus()
            
    except NotFound as e:
        # aqui vai aparecer o 404 completo nos logs
        print(f"[ERROR] Pub/Sub NOT FOUND - Topic: {topic_path} | Error: {e}")
        if PROMETHEUS_ENABLED:
            webhook_requests_total.labels(event_type=event, status='error_not_found').inc()
            pubsub_messages_published_total.labels(status='error_not_found').inc()
            push_metrics_to_prometheus()
        return {"ok": False, "error": "topic_not_found", "topic": topic_path}, 500
    except Exception as e:
        print(f"[ERROR] Pub/Sub falhou: {repr(e)}")
        if PROMETHEUS_ENABLED:
            webhook_requests_total.labels(event_type=event, status='error').inc()
            pubsub_messages_published_total.labels(status='error').inc()
            push_metrics_to_prometheus()
        return {"ok": False, "error": str(e)}, 500

    return {"ok": True}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5678"))
    app.run(host="0.0.0.0", port=port)