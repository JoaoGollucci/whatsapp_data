import os
import requests
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Lê as URLs da variável de ambiente (separadas por vírgula)
urls_str = os.getenv("TEST_URLS")
pushgateway_url = os.getenv("PUSHGATEWAY_URL")
api_key = os.getenv("API_KEY")

if not urls_str:
    print("ERRO: Defina a variável de ambiente TEST_URLS (URLs separadas por vírgula)")
    exit(1)

if not api_key:
    print("AVISO: Variável de ambiente API_KEY não definida. Requisições serão feitas sem chave de API.")

# Converter string em lista
urls = [url.strip() for url in urls_str.split(",")]
print(f"Testando {len(urls)} endpoint(s)...\n")

# Configurar Prometheus (se Pushgateway estiver configurado)
if pushgateway_url:
    registry = CollectorRegistry()
    endpoint_status = Gauge('endpoint_status', 'Status do endpoint (1=OK, 0=FALHA)', ['url'], registry=registry)
else:
    print("AVISO: PUSHGATEWAY_URL não definida. Métricas não serão enviadas.\n")
    registry = None
    endpoint_status = None

failed_urls = []

for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] Testando: {url}")
    
    try:
        # Obter ID token específico para Cloud Run (usa audience)
        auth_req = Request()
        id_token_credential = id_token.fetch_id_token(auth_req, url)
        
        # Adicionar token no header Authorization e API Key
        headers = {
            "Authorization": f"Bearer {id_token_credential}"
        }
        
        if api_key:
            headers["X-Api-Key"] = api_key
        
        print(f"  ✓ ID Token obtido")
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:100]}...")
        
        if response.status_code != 200:
            print(f"  ✗ FALHOU: Status code inválido: {response.status_code}\n")
            failed_urls.append(url)
            if endpoint_status:
                endpoint_status.labels(url=url).set(0)
        else:
            print(f"  ✓ Requisição bem-sucedida!\n")
            if endpoint_status:
                endpoint_status.labels(url=url).set(1)
        
    except Exception as e:
        print(f"  ✗ ERRO: {e}\n")
        failed_urls.append(url)
        if endpoint_status:
            endpoint_status.labels(url=url).set(0)

# Enviar métricas para Pushgateway (se configurado)
if pushgateway_url and registry:
    try:
        push_to_gateway(pushgateway_url, job='ping_waha', registry=registry)
        print("✓ Métricas enviadas para Pushgateway\n")
    except Exception as e:
        print(f"✗ Erro ao enviar métricas para Pushgateway: {e}\n")

# Resumo final
print("=" * 60)
print(f"RESUMO: {len(urls) - len(failed_urls)}/{len(urls)} endpoints bem-sucedidos")

if failed_urls:
    print(f"\n✗ {len(failed_urls)} endpoint(s) falharam:")
    for url in failed_urls:
        print(f"  - {url}")
    print("\nVerifique se a service account tem a role 'roles/run.invoker' nos serviços de destino")
    exit(1)
else:
    print("✓ Todos os endpoints estão funcionando!")
    exit(0)
