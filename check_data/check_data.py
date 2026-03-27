import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from google.cloud import bigquery

# Variáveis de ambiente
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gauge-prod")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "joao.gollucci@gauge.haus")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "alertas.engenhariagauge@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "tloohwsxfgvdzfib")

if not ALERT_EMAIL_TO or not SMTP_USER or not SMTP_PASSWORD:
    print("ERRO: Defina ALERT_EMAIL_TO, SMTP_USER e SMTP_PASSWORD para envio de alertas")
    exit(1)

print(f"Iniciando verificação de dados no BigQuery...")
print(f"Tabela: {PROJECT_ID}.projeto_meli.gold_messages")
print(f"Verificando dados de D-1\n")

def send_alert_email(target_date, qtd_class, qtd_id):
    """Envia email de alerta quando os dados não atendem os requisitos"""
    try:
        msg = MIMEMultipart('alternative')
        
        has_issue = qtd_class < 4 or qtd_id == 0
        
        if has_issue:
            subject = f'🚨 ALERTA: Dados inconsistentes no BigQuery - {target_date}'
            title_color = '#d32f2f'
            status_message = f'qtd_class={qtd_class} (esperado >= 4), qtd_id={qtd_id} (esperado > 0)'
            status_color = '#d32f2f'
        else:
            subject = f'✓ Dados validados no BigQuery - {target_date}'
            title_color = '#4caf50'
            status_message = f'qtd_class={qtd_class}, qtd_id={qtd_id}'
            status_color = '#4caf50'
        
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL_TO
        
        # Corpo do email em HTML
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {title_color};">{'🚨 Alerta: Dados Inconsistentes' if has_issue else '✓ Verificação de Dados'}</h2>
            <p><strong>Data/Hora da Verificação:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Data Consultada:</strong> {target_date} (D-1)</p>
            
            <h3>Detalhes da Consulta:</h3>
            <ul>
              <li><strong>Projeto:</strong> {PROJECT_ID}</li>
              <li><strong>Tabela:</strong> projeto_meli.gold_messages</li>
              <li><strong>qtd_class:</strong> {qtd_class} (esperado >= 4)</li>
              <li><strong>qtd_id:</strong> {qtd_id} (esperado > 0)</li>
              <li><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{status_message}</span></li>
            </ul>
        """
        
        if has_issue:
            html_body += """
            <hr>
            <h3 style="color: #d32f2f;">⚠️ Ação Necessária:</h3>
            <p>Os dados não atendem os requisitos mínimos. Verifique:</p>
            <ul>
              <li>Se o pipeline de dados está funcionando corretamente</li>
              <li>Se houve alguma falha no processamento</li>
              <li>Se os jobs de ETL foram executados</li>
              <li>Logs do BigQuery e Cloud Run</li>
            </ul>
            """
        
        html_body += """
            <hr>
            <p style="color: #666; font-size: 12px;">
              Este é um alerta automático do sistema de monitoramento BigQuery.
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
        
        print(f"✓ Email enviado para {ALERT_EMAIL_TO}")
        return True
        
    except Exception as e:
        print(f"✗ ERRO ao enviar email: {e}")
        return False

def check_bigquery_data():
    """Verifica se há dados no BigQuery para a data especificada"""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        target_date = (datetime.now() - timedelta(days=1)).date()
        
        query = """
        SELECT count(distinct class) qtd_class, count(id) as qtd_id
        FROM `gauge-prod.projeto_meli.gold_messages`
        WHERE date = current_date()-1
        """
        
        print(f"Executando query no BigQuery...")
        print(f"Query: {query}\n")
        
        query_job = client.query(query)
        rows = list(query_job.result())
        
        qtd_class = rows[0].qtd_class if rows else 0
        qtd_id = rows[0].qtd_id if rows else 0
        
        print(f"Data alvo: {target_date}")
        print(f"qtd_class: {qtd_class}")
        print(f"qtd_id: {qtd_id}\n")
        
        return target_date, qtd_class, qtd_id
        
    except Exception as e:
        print(f"✗ ERRO ao consultar BigQuery: {e}")
        raise

# Executar verificação
try:
    target_date, qtd_class, qtd_id = check_bigquery_data()
    
    print("=" * 60)
    
    if qtd_class < 4 or qtd_id == 0:
        print(f"✗ ALERTA: Dados inconsistentes para {target_date}")
        print(f"  qtd_class={qtd_class} (esperado >= 4), qtd_id={qtd_id} (esperado > 0)")
        print("\nEnviando email de alerta...")
        
        if send_alert_email(target_date, qtd_class, qtd_id):
            print("✓ Alerta enviado com sucesso")
        else:
            print("✗ Falha ao enviar alerta")
        
        exit(1)
    else:
        print(f"✓ Dados validados para {target_date}: qtd_class={qtd_class}, qtd_id={qtd_id}")
        print("Nenhum alerta necessário.")
        exit(0)
        
except Exception as e:
    print(f"\n✗ ERRO CRÍTICO: {e}")
    
    # Tentar enviar email de erro crítico
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🚨 ERRO CRÍTICO: Falha na verificação BigQuery'
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL_TO
        
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d32f2f;">🚨 Erro Crítico no Monitoramento</h2>
            <p><strong>Data/Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Erro:</strong> {str(e)}</p>
            <p>O script de monitoramento encontrou um erro crítico durante a execução.</p>
            <p>Verifique os logs do Cloud Run para mais detalhes.</p>
          </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
            
        print("Email de erro crítico enviado")
    except:
        pass
    
    exit(1)
