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

def send_alert_email(failed_endpoints):
    """Envia email de alerta quando endpoints falham"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🚨 ALERTA: {len(failed_endpoints)} endpoint(s) WAHA com problema'
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL_TO
        
        # Corpo do email em HTML
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">⚠️ Alerta de Status WAHA</h2>
            <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Status Esperado:</strong> {EXPECTED_STATUS}</p>
            
            <h3>Endpoints com Problema:</h3>
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
        
        html_body += """
            </ul>
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
        
        if status != EXPECTED_STATUS:
            return {
                "url": base_url,
                "status": status,
                "error": f"Status diferente do esperado ({EXPECTED_STATUS})"
            }
        
        return None  # Tudo OK
        
    except Exception as e:
        return {
            "url": base_url,
            "status": "ERROR",
            "error": str(e)
        }

# Verificar todos os endpoints
failed_endpoints = []

for i, url in enumerate(urls, 1):
    print(f"[{i}/{len(urls)}] Verificando: {url}")
    
    result = check_waha_status(url)
    
    if result:
        print(f"  ✗ FALHOU: {result['status']} - {result['error']}\n")
        failed_endpoints.append(result)
    else:
        print(f"  ✓ Status OK: {EXPECTED_STATUS}\n")

# Resumo e envio de alerta
print("=" * 60)
print(f"RESUMO: {len(urls) - len(failed_endpoints)}/{len(urls)} endpoints funcionando corretamente")

if failed_endpoints:
    print(f"\n✗ {len(failed_endpoints)} endpoint(s) com problema!")
    print("\nEnviando email de alerta...")
    
    if send_alert_email(failed_endpoints):
        print("✓ Alerta enviado com sucesso")
    else:
        print("✗ Falha ao enviar alerta")
    
    exit(1)
else:
    print("✓ Todos os endpoints estão funcionando corretamente!")
    exit(0)