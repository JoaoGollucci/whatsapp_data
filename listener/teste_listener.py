import os, json, hashlib
from flask import Flask, request, abort
from google.cloud import pubsub_v1

# Env vars esperadas:
# - GCP_PROJECT (ex.: "meu-projeto")
# - PUBSUB_TOPIC (ex.: "waha.events")
# - WAHA_TOKEN (opcional; valida header X-WAHA-Token)
# - WEBHOOK_HOST (ex.: "https://seu-servico.run.app")

PROJECT = os.getenv("GCP_PROJECT", "projeto-exemplo-gce")
TOPIC = os.getenv("PUBSUB_TOPIC", "waha.events")
WAHA_TOKEN = os.getenv("WAHA_TOKEN", "")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "http://localhost:5678")

if not PROJECT or not TOPIC:
    raise RuntimeError("Defina GCP_PROJECT e PUBSUB_TOPIC no ambiente.")

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT, TOPIC)

app = Flask(__name__)

def stable_message_id(payload: dict) -> str:
    # ID estável se não vier no payload (evita duplicados)
    key = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(key.encode("utf-8")).hexdigest()

@app.route("/webhook/webhook", methods=["POST"])
def webhook():
    # (opcional) token simples no header
    token = request.headers.get("X-WAHA-Token")
    if WAHA_TOKEN and token != WAHA_TOKEN:
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

    # publica e não espera o future (resposta 200 rápida)
    publisher.publish(topic_path, data=data, message_id=msg_id)
    return {"ok": True}, 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5678"))
    app.run(host="0.0.0.0", port=port)