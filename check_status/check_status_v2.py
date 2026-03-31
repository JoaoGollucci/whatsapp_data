import os
import requests
from datetime import datetime, timezone
from google.cloud import bigquery
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# --- Variáveis de ambiente ---
WAHA_URLS = os.getenv("WAHA_URLS", "")
PAGERDUTY_ROUTING_KEY = os.getenv("PAGERDUTY_ROUTING_KEY", "")
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "")
BQ_TABLE = os.getenv("BQ_TABLE", "projeto_meli.status_waha_services")

urls = [u.strip() for u in WAHA_URLS.split(",") if u.strip()]

if not urls:
    print("ERRO: Defina a variável de ambiente WAHA_URLS (URLs separadas por vírgula)")
    exit(1)

if not PAGERDUTY_ROUTING_KEY:
    print("ERRO: Defina a variável de ambiente PAGERDUTY_ROUTING_KEY")
    exit(1)

bq = bigquery.Client()


def get_endpoint_state(endpoint):
    """Lê o estado atual de um endpoint na tabela do BigQuery."""
    query = f"""
        SELECT last_status, starting_counter, incident_open, incident_key
        FROM `{BQ_TABLE}`
        WHERE endpoint = @endpoint
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("endpoint", "STRING", endpoint)]
    )
    rows = list(bq.query(query, job_config=job_config).result())
    if rows:
        row = rows[0]
        return {
            "last_status": row.last_status or "",
            "starting_counter": row.starting_counter or 0,
            "incident_open": row.incident_open or False,
            "incident_key": row.incident_key or "",
        }
    return {"last_status": "", "starting_counter": 0, "incident_open": False, "incident_key": ""}


def save_endpoint_state(endpoint, last_status, starting_counter, incident_open, incident_key):
    """Persiste o estado do endpoint no BigQuery via MERGE (upsert)."""
    query = f"""
        MERGE `{BQ_TABLE}` t
        USING (SELECT @endpoint AS endpoint) s
        ON t.endpoint = s.endpoint
        WHEN MATCHED THEN
            UPDATE SET
                last_status = @last_status,
                starting_counter = @starting_counter,
                incident_open = @incident_open,
                incident_key = @incident_key
        WHEN NOT MATCHED THEN
            INSERT (endpoint, last_status, starting_counter, incident_open, incident_key)
            VALUES (@endpoint, @last_status, @starting_counter, @incident_open, @incident_key)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("endpoint", "STRING", endpoint),
            bigquery.ScalarQueryParameter("last_status", "STRING", last_status),
            bigquery.ScalarQueryParameter("starting_counter", "INT64", starting_counter),
            bigquery.ScalarQueryParameter("incident_open", "BOOL", incident_open),
            bigquery.ScalarQueryParameter("incident_key", "STRING", incident_key or ""),
        ]
    )
    bq.query(query, job_config=job_config).result()


def check_waha_status(base_url):
    """Consulta o status da sessão WAHA no endpoint."""
    url = f"{base_url}/api/sessions/default"
    headers = {"Content-Type": "application/json"}

    if WAHA_API_KEY:
        headers["X-Api-Key"] = WAHA_API_KEY
    else:
        auth_req = Request()
        token = id_token.fetch_id_token(auth_req, base_url)
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        return "FAILED"

    return resp.json().get("status", "UNKNOWN").upper()


def start_waha_session(base_url):
    """Tenta iniciar uma sessão WAHA que está parada."""
    url = f"{base_url}/api/sessions/default/start"
    headers = {"Content-Type": "application/json"}

    if WAHA_API_KEY:
        headers["X-Api-Key"] = WAHA_API_KEY
    else:
        auth_req = Request()
        token = id_token.fetch_id_token(auth_req, base_url)
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.post(url, headers=headers, timeout=10)
    return resp.status_code in [200, 201]


def trigger_pagerduty(endpoint, status):
    """Cria um incidente no PagerDuty via Events API v2. Retorna o dedup_key."""
    payload = {
        "routing_key": PAGERDUTY_ROUTING_KEY,
        "event_action": "trigger",
        "dedup_key": f"waha-{endpoint}",
        "payload": {
            "summary": f"WAHA endpoint com status {status}: {endpoint}",
            "severity": "critical",
            "source": "check_status_v2",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "custom_details": {"endpoint": endpoint, "status": status},
        },
    }
    resp = requests.post(
        "https://events.pagerduty.com/v2/enqueue", json=payload, timeout=10
    )
    if resp.status_code == 202:
        return resp.json().get("dedup_key", f"waha-{endpoint}")
    print(f"  Falha ao criar incidente PagerDuty: HTTP {resp.status_code}")
    return None


def resolve_pagerduty(dedup_key):
    """Resolve um incidente aberto no PagerDuty usando o dedup_key."""
    payload = {
        "routing_key": PAGERDUTY_ROUTING_KEY,
        "event_action": "resolve",
        "dedup_key": dedup_key,
    }
    resp = requests.post(
        "https://events.pagerduty.com/v2/enqueue", json=payload, timeout=10
    )
    return resp.status_code == 202


# --- Execução principal ---
print(f"Verificando {len(urls)} endpoint(s)...\n")

for endpoint_url in urls:
    print(f"Endpoint: {endpoint_url}")

    try:
        status = check_waha_status(endpoint_url)
    except Exception as e:
        print(f"  Erro na verificação: {e}")
        status = "FAILED"

    print(f"  Status: {status}")

    state = get_endpoint_state(endpoint_url)
    counter = state["starting_counter"]
    incident_open = state["incident_open"]
    incident_key = state["incident_key"]

    if status == "WORKING":
        counter = 0
        if incident_open and incident_key:
            print("  Resolvendo incidente PagerDuty...")
            if resolve_pagerduty(incident_key):
                print("  Incidente resolvido.")
            else:
                print("  Falha ao resolver incidente.")
            incident_open = False
            incident_key = ""
        print("  OK")

    elif status == "FAILED":
        counter = 0
        if not incident_open:
            print("  Criando incidente PagerDuty (FAILED)...")
            key = trigger_pagerduty(endpoint_url, status)
            if key:
                incident_open = True
                incident_key = key
                print(f"  Incidente criado: {key}")
        else:
            print("  Incidente já aberto, sem novos alertas.")

    elif status == "STARTING":
        counter += 1
        print(f"  Starting counter: {counter}/3")
        if counter >= 3 and not incident_open:
            print("  Criando incidente PagerDuty (STARTING persistente)...")
            key = trigger_pagerduty(endpoint_url, status)
            if key:
                incident_open = True
                incident_key = key
                print(f"  Incidente criado: {key}")
        elif incident_open:
            print("  Incidente já aberto, sem novos alertas.")

    elif status == "STOPPED":
        counter = 0
        print("  Status STOPPED - tentando reiniciar sessão...")
        try:
            if start_waha_session(endpoint_url):
                print("  Sessão reiniciada com sucesso.")
            else:
                print("  Falha ao reiniciar sessão.")
        except Exception as e:
            print(f"  Erro ao tentar reiniciar: {e}")
        print("  Nenhum chamado gerado.")

    else:
        # Status desconhecido - tratar como FAILED
        counter = 0
        if not incident_open:
            print(f"  Status inesperado ({status}). Criando incidente PagerDuty...")
            key = trigger_pagerduty(endpoint_url, status)
            if key:
                incident_open = True
                incident_key = key
                print(f"  Incidente criado: {key}")
        else:
            print("  Incidente já aberto, sem novos alertas.")

    save_endpoint_state(endpoint_url, status, counter, incident_open, incident_key)
    print(f"  Estado salvo no BigQuery.\n")

print("=" * 60)
print("Verificação concluída.")
