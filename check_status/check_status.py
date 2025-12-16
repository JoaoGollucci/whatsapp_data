import os
import json
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2 import id_token

# Variáveis de ambiente
URLS_STR = os.getenv("WAHA_URLS", "https://waha-meli-teste-180862637961.us-central1.run.app,https://waha-meli-2-180862637961.us-central1.run.app")  # URLs separadas por vírgula
EXPECTED_STATUS = os.getenv("EXPECTED_STATUS", "WORKING")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "joao.gollucci@gauge.haus")  # Email para enviar alertas
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "alertas.engenhariagauge@gmail.com")  # seu-email@gmail.com
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "tloohwsxfgvdzfib")  # sua-senha-ou-app-password

if not URLS_STR:
    print("ERRO: Defina a variável de ambiente WAHA_URLS (URLs separadas por vírgula)")
    exit(1)

if not ALERT_EMAIL_TO or not SMTP_USER or not SMTP_PASSWORD:
    print("ERRO: Defina ALERT_EMAIL_TO, SMTP_USER e SMTP_PASSWORD para envio de alertas")
    exit(1)

# Converter string em lista de URLs
urls = [url.strip() for url in URLS_STR.split(",")]
print(f"Verificando status de {len(urls)} endpoint(s)...\n")

def send_alert_email(failed_endpoints, restarted_endpoints=None):
    """Envia email de alerta quando endpoints falham ou são reiniciados"""
    try:
        restarted_endpoints = restarted_endpoints or []
        
        if restarted_endpoints and not failed_endpoints:
            subject = f'⚠️ AVISO: {len(restarted_endpoints)} endpoint(s) WAHA foram reiniciados'
            title_color = '#ff9800'
            title = '⚠️ Aviso: Serviços WAHA Reiniciados'
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
        # Obter ID token para autenticação Cloud Run
        auth_req = Request()
        id_token_credential = id_token.fetch_id_token(auth_req, base_url)
        
        headers = {
            "Authorization": f"Bearer {id_token_credential}",
            "Content-Type": "application/json"
        }
        
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
        # Obter ID token para autenticação Cloud Run
        auth_req = Request()
        id_token_credential = id_token.fetch_id_token(auth_req, base_url)
        
        headers = {
            "Authorization": f"Bearer {id_token_credential}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return {
                "url": base_url,
                "status": f"HTTP {response.status_code}",
                "error": f"Falha na requisição: {response.text[:100]}"
            }
        
        data = response.json()
        status = data.get('status', 'UNKNOWN')
        
        if status == 'STOPPED':
            # Serviço está parado, tentar reiniciar
            return {
                "url": base_url,
                "status": status,
                "needs_restart": True
            }
        
        if status != EXPECTED_STATUS:
            return {
                "url": base_url,
                "status": status,
                "error": f"Status diferente do esperado ({EXPECTED_STATUS})",
                "needs_restart": False
            }
        
        return None  # Tudo OK
        
    except Exception as e:
        return {
            "url": base_url,
            "status": "ERROR",
            "error": str(e),
            "needs_restart": False
        }

# Verificar todos os endpoints
failed_endpoints = []
restarted_endpoints = []

for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] Verificando: {url}")
    
    result = check_waha_status(url)
    
    if result:
        # Verificar se precisa reiniciar
        if result.get('needs_restart'):
            print(f"  ⚠️ Status STOPPED detectado - Tentando reiniciar...")
            if start_waha_session(url):
                restarted_endpoints.append(result)
                print(f"  ✓ Serviço reiniciado com sucesso!\n")
            else:
                result['error'] = 'Falha ao tentar reiniciar o serviço'
                result['needs_restart'] = False
                failed_endpoints.append(result)
                print(f"  ✗ Não foi possível reiniciar o serviço\n")
        else:
            print(f"  ✗ FALHOU: {result['status']} - {result.get('error', 'N/A')}\n")
            failed_endpoints.append(result)
    else:
        print(f"  ✓ Status OK: {EXPECTED_STATUS}\n")

# Resumo e envio de alerta
print("=" * 60)
total_ok = len(urls) - len(failed_endpoints) - len(restarted_endpoints)
print(f"RESUMO:")
print(f"  ✓ {total_ok} endpoint(s) funcionando normalmente")
if restarted_endpoints:
    print(f"  🔄 {len(restarted_endpoints)} endpoint(s) reiniciados automaticamente")
if failed_endpoints:
    print(f"  ✗ {len(failed_endpoints)} endpoint(s) com falha")

# Enviar email se houve problemas ou reinicializações
if failed_endpoints or restarted_endpoints:
    if failed_endpoints:
        print(f"\n✗ {len(failed_endpoints)} endpoint(s) com problema que não pôde ser resolvido!")
    if restarted_endpoints:
        print(f"\n⚠️ {len(restarted_endpoints)} endpoint(s) foram reiniciados automaticamente")
    
    print("\nEnviando email de alerta...")
    
    if send_alert_email(failed_endpoints, restarted_endpoints):
        print("✓ Alerta enviado com sucesso")
    else:
        print("✗ Falha ao enviar alerta")
    
    # Sair com erro apenas se houver falhas reais (não reinicializações bem-sucedidas)
    if failed_endpoints:
        exit(1)
    else:
        exit(0)
else:
    print("\n✓ Todos os endpoints estão funcionando corretamente!")
    exit(0)