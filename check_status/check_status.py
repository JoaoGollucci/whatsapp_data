import os
import json
import requests
import smtplib
import subprocess
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Variáveis de ambiente
URLS_STR = os.getenv("WAHA_URLS", "https://waha-meli-teste-180862637961.us-central1.run.app,https://waha-meli-2-180862637961.us-central1.run.app")  # URLs separadas por vírgula
EXPECTED_STATUS = os.getenv("EXPECTED_STATUS", "WORKING")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "joao.gollucci@gauge.haus")  # Email para enviar alertas
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "alertas.engenhariagauge@gmail.com")  # seu-email@gmail.com
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "tloohwsxfgvdzfib")  # sua-senha-ou-app-password
pushgateway_url = os.getenv("PUSHGATEWAY_URL")
PAGERDUTY_API_KEY = os.getenv("PAGERDUTY_API_KEY")
API_KEY = os.getenv("WAHA_API_KEY")  # Chave de API para autenticação nos endpoints monitorados

if not URLS_STR:
    print("ERRO: Defina a variável de ambiente WAHA_URLS (URLs separadas por vírgula)")
    exit(1)

if not ALERT_EMAIL_TO or not SMTP_USER or not SMTP_PASSWORD:
    print("ERRO: Defina ALERT_EMAIL_TO, SMTP_USER e SMTP_PASSWORD para envio de alertas")
    exit(1)

if not pushgateway_url:
    print("AVISO: Variável de ambiente PUSHGATEWAY_URL não configurada. Métricas Prometheus serão desabilitadas.")

if not PAGERDUTY_API_KEY:
    print("AVISO: Variável de ambiente PAGERDUTY_API_KEY não configurada. Alertas PagerDuty serão desabilitados.")

# Converter string em lista de URLs
urls = [url.strip() for url in URLS_STR.split(",")]
print(f"Verificando status de {len(urls)} endpoint(s)...\n")

# Configurar Prometheus
registry = CollectorRegistry()
waha_session_status = Gauge('waha_session_status', 'Status da sessão WAHA (1=WORKING, 0=outros status)', ['url', 'status'], registry=registry)
waha_endpoint_available = Gauge('waha_endpoint_available', 'Disponibilidade do endpoint WAHA (1=disponível, 0=erro)', ['url'], registry=registry)

def extract_cloud_run_info(base_url):
    """Extrai o nome do serviço, região e project do URL do Cloud Run"""
    # Formato esperado: https://service-name-project-id.region.run.app
    pattern = r'https://([^-]+(?:-[^-]+)*?)-([0-9]+)\.([^.]+)\.run\.app'
    match = re.match(pattern, base_url)
    
    if match:
        service_name = match.group(1)
        project_id = match.group(2)
        region = match.group(3)
        return {
            'service_name': service_name,
            'project_id': project_id,
            'region': region
        }
    return None

def redeploy_cloud_run(base_url):
    """Faz o redeploy de um serviço Cloud Run"""
    info = extract_cloud_run_info(base_url)
    
    if not info:
        print(f"  ✗ Não foi possível extrair informações do Cloud Run da URL: {base_url}")
        return False
    
    service_name = info['service_name']
    project_id = info['project_id']
    region = info['region']
    
    print(f"  🔄 Iniciando redeploy do Cloud Run: {service_name} (região: {region})")
    
    try:
        # Comando para fazer redeploy sem alterar parâmetros
        cmd = [
            'gcloud', 'run', 'services', 'update', service_name,
            '--region', region,
            '--project', project_id,
            '--platform', 'managed'
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos de timeout
        )
        
        if result.returncode == 0:
            print(f"  ✓ Redeploy concluído com sucesso")
            return True
        else:
            print(f"  ✗ Falha no redeploy: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout ao fazer redeploy (>5min)")
        return False
    except FileNotFoundError:
        print(f"  ✗ Comando gcloud não encontrado. Instale o Google Cloud SDK.")
        return False
    except Exception as e:
        print(f"  ✗ Erro ao fazer redeploy: {e}")
        return False

def create_pagerduty_incident(failed_endpoints):
    """Cria um incidente no PagerDuty quando há endpoints com falha"""
    if not PAGERDUTY_API_KEY:
        return False
    
    try:
        url = "https://events.pagerduty.com/v2/enqueue"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Construir detalhes do incidente
        failed_urls = [ep['url'] for ep in failed_endpoints]
        failed_details = []
        
        for ep in failed_endpoints:
            failed_details.append({
                "url": ep['url'],
                "status": ep['status'],
                "error": ep.get('error', 'N/A')
            })
        
        payload = {
            "routing_key": PAGERDUTY_API_KEY,
            "event_action": "trigger",
            "payload": {
                "summary": f"WAHA: {len(failed_endpoints)} endpoint(s) com falha",
                "severity": "error",
                "source": "check_waha_status",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "custom_details": {
                    "failed_count": len(failed_endpoints),
                    "failed_urls": failed_urls,
                    "details": failed_details,
                    "expected_status": EXPECTED_STATUS
                }
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 202:
            print(f"✓ Incidente criado no PagerDuty")
            return True
        else:
            print(f"✗ Falha ao criar incidente no PagerDuty: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Erro ao criar incidente no PagerDuty: {e}")
        return False

def send_alert_email(failed_endpoints, restarted_endpoints=None, redeployed_endpoints=None):
    """Envia email de alerta quando endpoints falham, são reiniciados ou reimplantados"""
    try:
        restarted_endpoints = restarted_endpoints or []
        redeployed_endpoints = redeployed_endpoints or []
        
        if (restarted_endpoints or redeployed_endpoints) and not failed_endpoints:
            total_actions = len(restarted_endpoints) + len(redeployed_endpoints)
            subject = f'⚠️ AVISO: {total_actions} endpoint(s) WAHA foram recuperados'
            title_color = '#ff9800'
            title = '⚠️ Aviso: Serviços WAHA Recuperados'
        else:
            subject = f'🚨 ALERTA: {len(failed_endpoints)} endpoint(s) WAHA com problema'
            title_color = '#d32f2f'
            title = '⚠️ Alerta de Status WAHA'
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL_TO
        
        # Corpo do email em HTML
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {title_color};">{title}</h2>
            <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Status Esperado:</strong> {EXPECTED_STATUS}</p>
        """
        
        # Adicionar seção de serviços reiniciados
        if restarted_endpoints:
            html_body += """
            <h3 style="color: #ff9800;">🔄 Serviços Reiniciados Automaticamente:</h3>
            <ul>
            """
            for endpoint in restarted_endpoints:
                html_body += f"""
                  <li>
                    <strong>URL:</strong> {endpoint['url']}<br>
                    <strong>Status Anterior:</strong> <span style="color: #ff9800;">STOPPED</span><br>
                    <strong>Ação:</strong> <span style="color: #4caf50;">Serviço foi reiniciado automaticamente</span>
                  </li>
                  <br>
                """
            html_body += "</ul>"
        
        # Adicionar seção de serviços reimplantados
        if redeployed_endpoints:
            html_body += """
            <h3 style="color: #2196f3;">🔄 Serviços Reimplantados Automaticamente:</h3>
            <ul>
            """
            for endpoint in redeployed_endpoints:
                html_body += f"""
                  <li>
                    <strong>URL:</strong> {endpoint['url']}<br>
                    <strong>Status Anterior:</strong> <span style="color: #ff9800;">{endpoint.get('previous_status', 'UNKNOWN')}</span><br>
                    <strong>Ação:</strong> <span style="color: #4caf50;">Serviço foi reimplantado e reiniciado automaticamente</span>
                  </li>
                  <br>
                """
            html_body += "</ul>"
        
        # Adicionar seção de falhas
        if failed_endpoints:
            html_body += """
            <h3 style="color: #d32f2f;">❌ Endpoints com Problema:</h3>
            <ul>
            """
            for endpoint in failed_endpoints:
                html_body += f"""
                  <li>
                    <strong>URL:</strong> {endpoint['url']}<br>
                    <strong>Status Obtido:</strong> <span style="color: #d32f2f;">{endpoint['status']}</span><br>
                    <strong>Erro:</strong> {endpoint.get('error', 'N/A')}
                  </li>
                  <br>
                """
            html_body += "</ul>"
        
        html_body += """
            <hr>
            <p style="color: #666; font-size: 12px;">
              Este é um alerta automático do sistema de monitoramento WAHA.
            </p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Enviar email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Email de alerta enviado para {ALERT_EMAIL_TO}")
        return True
        
    except Exception as e:
        print(f"✗ ERRO ao enviar email: {e}")
        return False

def start_waha_session(base_url):
    """Inicia uma sessão WAHA que está parada"""
    url = f"{base_url}/api/sessions/default/start"
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        # Priorizar X-Api-Key se disponível, caso contrário usar Bearer token
        if API_KEY:
            headers["X-Api-Key"] = API_KEY
        else:
            # Obter ID token para autenticação Cloud Run
            auth_req = Request()
            id_token_credential = id_token.fetch_id_token(auth_req, base_url)
            headers["Authorization"] = f"Bearer {id_token_credential}"
        
        response = requests.post(url, headers=headers, timeout=10)
        
        if response.status_code in [200, 201]:
            print(f"  ✓ Serviço reiniciado com sucesso")
            return True
        else:
            print(f"  ✗ Falha ao reiniciar: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ✗ Erro ao tentar reiniciar: {e}")
        return False

def check_waha_status(base_url):
    """Verifica o status de um endpoint WAHA"""
    url = f"{base_url}/api/sessions/default"
    
    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        # Priorizar X-Api-Key se disponível, caso contrário usar Bearer token
        if API_KEY:
            headers["X-Api-Key"] = API_KEY
        else:
            # Obter ID token para autenticação Cloud Run
            auth_req = Request()
            id_token_credential = id_token.fetch_id_token(auth_req, base_url)
            headers["Authorization"] = f"Bearer {id_token_credential}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                "url": base_url,
                "status": f"HTTP {response.status_code}",
                "error": f"Falha na requisição: {response.text[:100]}",
                "available": False
            }
        
        data = response.json()
        status = data.get('status', 'UNKNOWN')
        
        if status == 'STOPPED':
            # Serviço está parado, tentar reiniciar
            return {
                "url": base_url,
                "status": status,
                "needs_restart": True,
                "available": True
            }
        
        if status != EXPECTED_STATUS:
            return {
                "url": base_url,
                "status": status,
                "error": f"Status diferente do esperado ({EXPECTED_STATUS})",
                "needs_restart": False,
                "available": True
            }
        
        return None  # Tudo OK
        
    except Exception as e:
        return {
            "url": base_url,
            "status": "ERROR",
            "error": str(e),
            "needs_restart": False,
            "available": False
        }

# Verificar todos os endpoints
failed_endpoints = []
restarted_endpoints = []
redeployed_endpoints = []

for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] Verificando: {url}")
    
    result = check_waha_status(url)
    
    if result:
        # Enviar métricas para Prometheus
        status = result.get('status', 'UNKNOWN')
        available = result.get('available', False)
        
        if pushgateway_url:
            waha_endpoint_available.labels(url=url).set(1 if available else 0)
            waha_session_status.labels(url=url, status=status).set(0)
        
        # Verificar se precisa reiniciar
        if result.get('needs_restart'):
            print(f"  ⚠️ Status STOPPED detectado - Tentando reiniciar...")
            if start_waha_session(url):
                restarted_endpoints.append(result)
                print(f"  ✓ Serviço reiniciado com sucesso!\n")
                # Atualizar métrica após reinicialização
                if pushgateway_url:
                    waha_session_status.labels(url=url, status='WORKING').set(1)
            else:
                result['error'] = 'Falha ao tentar reiniciar o serviço'
                result['needs_restart'] = False
                failed_endpoints.append(result)
                print(f"  ✗ Não foi possível reiniciar o serviço\n")
        else:
            # Status diferente de STOPPED ou WORKING - fazer redeploy
            status = result.get('status', '')
            if status not in ['STOPPED', 'WORKING', 'HTTP 401', 'HTTP 403', 'HTTP 404', 'ERROR']:
                print(f"  ⚠️ Status inesperado detectado: {status}")
                print(f"  🔄 Tentando reimplantar o serviço...")
                
                if redeploy_cloud_run(url):
                    print(f"  ⏳ Aguardando 2 minutos após redeploy...")
                    import time
                    time.sleep(120)
                    
                    print(f"  🔄 Tentando iniciar a sessão WAHA...")
                    if start_waha_session(url):
                        result['previous_status'] = status
                        redeployed_endpoints.append(result)
                        print(f"  ✓ Serviço reimplantado e reiniciado com sucesso!\n")
                        # Atualizar métrica após redeploy
                        if pushgateway_url:
                            waha_session_status.labels(url=url, status='WORKING').set(1)
                    else:
                        result['error'] = f'Redeploy OK, mas falha ao iniciar sessão (status anterior: {status})'
                        failed_endpoints.append(result)
                        print(f"  ✗ Redeploy OK, mas não foi possível iniciar a sessão\n")
                else:
                    result['error'] = f'Falha ao reimplantar o serviço (status: {status})'
                    failed_endpoints.append(result)
                    print(f"  ✗ Não foi possível reimplantar o serviço\n")
            else:
                print(f"  ✗ FALHOU: {result['status']} - {result.get('error', 'N/A')}\n")
                failed_endpoints.append(result)
    else:
        print(f"  ✓ Status OK: {EXPECTED_STATUS}\n")
        # Enviar métrica de sucesso
        if pushgateway_url:
            waha_endpoint_available.labels(url=url).set(1)
            waha_session_status.labels(url=url, status=EXPECTED_STATUS).set(1)

# Enviar métricas para Pushgateway (apenas se configurado)
if pushgateway_url:
    try:
        push_to_gateway(pushgateway_url, job='check_waha_status', registry=registry)
        print("✓ Métricas enviadas para Pushgateway\n")
    except Exception as e:
        print(f"✗ Erro ao enviar métricas para Pushgateway: {e}\n")
else:
    print("⊘ Pushgateway desabilitado (PUSHGATEWAY_URL não configurada)\n")

# Resumo e envio de alerta
print("=" * 60)
total_ok = len(urls) - len(failed_endpoints) - len(restarted_endpoints) - len(redeployed_endpoints)
print(f"RESUMO:")
print(f"  ✓ {total_ok} endpoint(s) funcionando normalmente")
if restarted_endpoints:
    print(f"  🔄 {len(restarted_endpoints)} endpoint(s) reiniciados automaticamente")
if redeployed_endpoints:
    print(f"  🔄 {len(redeployed_endpoints)} endpoint(s) reimplantados automaticamente")
if failed_endpoints:
    print(f"  ✗ {len(failed_endpoints)} endpoint(s) com falha")

# Enviar email se houve problemas ou reinicializações
if failed_endpoints or restarted_endpoints or redeployed_endpoints:
    if failed_endpoints:
        print(f"\n✗ {len(failed_endpoints)} endpoint(s) com problema que não pôde ser resolvido!")
    if restarted_endpoints:
        print(f"\n⚠️ {len(restarted_endpoints)} endpoint(s) foram reiniciados automaticamente")
    if redeployed_endpoints:
        print(f"\n⚠️ {len(redeployed_endpoints)} endpoint(s) foram reimplantados automaticamente")
    
    print("\nEnviando alertas...")
    
    # Enviar email
    if send_alert_email(failed_endpoints, restarted_endpoints, redeployed_endpoints):
        print("✓ Email de alerta enviado com sucesso")
    else:
        print("✗ Falha ao enviar email de alerta")
    
    # Criar incidente no PagerDuty apenas se houver falhas reais (não reinicializações)
    if failed_endpoints and PAGERDUTY_API_KEY:
        if create_pagerduty_incident(failed_endpoints):
            print("✓ Incidente PagerDuty criado com sucesso")
        else:
            print("✗ Falha ao criar incidente PagerDuty")
    elif failed_endpoints and not PAGERDUTY_API_KEY:
        print("⊘ PagerDuty desabilitado (PAGERDUTY_API_KEY não configurada)")
    
    # Sair com erro apenas se houver falhas reais (não reinicializações bem-sucedidas)
    if failed_endpoints:
        exit(1)
    else:
        exit(0)
else:
    print("\n✓ Todos os endpoints estão funcionando corretamente!")
    exit(0)
