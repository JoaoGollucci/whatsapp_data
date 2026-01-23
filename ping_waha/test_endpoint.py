import os
import requests
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Lê as URLs da variável de ambiente (separadas por vírgula)
urls_str = os.getenv("TEST_URLS")
pushgateway_url = os.getenv("PUSHGATEWAY_URL")

if not urls_str:
    print("ERRO: Defina a variável de ambiente TEST_URLS (URLs separadas por vírgula)")
    exit(1)

if not pushgateway_url:
    print("ERRO: Defina a variável de ambiente PUSHGATEWAY_URL")
    exit(1)

# Converter string em lista
urls = [url.strip() for url in urls_str.split(",")]
print(f"Testando {len(urls)} endpoint(s)...\n")

# Configurar Prometheus
registry = CollectorRegistry()
endpoint_status = Gauge('endpoint_status', 'Status do endpoint (1=OK, 0=FALHA)', ['url'], registry=registry)

failed_urls = []

for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] Testando: {url}")
    
    try:
        # Obter ID token específico para Cloud Run (usa audience)
        auth_req = Request()
        id_token_credential = id_token.fetch_id_token(auth_req, url)
        
        # Adicionar token no header Authorization
        headers = {
            "Authorization": f"Bearer {id_token_credential}"
        }
        
        print(f"  ✓ ID Token obtido")
        
        response = requests.get(url, headers=headers, timeout=10)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response: {response.text[:100]}...")
        
        if response.status_code != 200:
            print(f"  ✗ FALHOU: Status code inválido: {response.status_code}\n")
            failed_urls.append(url)
            endpoint_status.labels(url=url).set(0)
        else:
            print(f"  ✓ Requisição bem-sucedida!\n")
            endpoint_status.labels(url=url).set(1)
        
    except Exception as e:
        print(f"  ✗ ERRO: {e}\n")
        failed_urls.append(url)
        endpoint_status.labels(url=url).set(0)

# Enviar métricas para Pushgateway
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
