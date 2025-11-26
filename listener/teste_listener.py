import os, json, hashlib
from flask import Flask, request, abort
from google.api_core.exceptions import NotFound
from google.cloud import pubsub_v1

# Env vars esperadas:
# - GCP_PROJECT (ex.: "meu-projeto")
# - PUBSUB_TOPIC (ex.: "waha.events")
# - WAHA_TOKEN (opcional; valida header X-WAHA-Token)
# - PORT (Cloud Run define automaticamente)

PROJECT = os.getenv("GCP_PROJECT")
TOPIC = os.getenv("PUBSUB_TOPIC")
WAHA_TOKEN = os.getenv("WAHA_TOKEN", "")

if not PROJECT or not TOPIC:
    raise RuntimeError("Defina GCP_PROJECT e PUBSUB_TOPIC no ambiente.")

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
    return {"status": "healthy", "service": "waha-webhook-listener"}, 200

@app.route("/webhook/webhook", methods=["POST"])
def webhook():
    # (opcional) token simples no header
    token = request.headers.get("X-WAHA-Token")
    if WAHA_TOKEN and token != WAHA_TOKEN:
        print("[SECURITY] Token inválido recebido")
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
    except NotFound as e:
        # aqui vai aparecer o 404 completo nos logs
        print(f"[ERROR] Pub/Sub NOT FOUND - Topic: {topic_path} | Error: {e}")
        return {"ok": False, "error": "topic_not_found", "topic": topic_path}, 500
    except Exception as e:
        print(f"[ERROR] Pub/Sub falhou: {repr(e)}")
        return {"ok": False, "error": str(e)}, 500

    return {"ok": True}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5678"))
    app.run(host="0.0.0.0", port=port)