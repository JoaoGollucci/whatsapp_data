import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from google.cloud import bigquery

# Variáveis de ambiente
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gauge-prod")
DATASET_TABLE = os.getenv("BQ_DATASET_TABLE", "projeto_meli.vw_aff_quantity")
DATE_COLUMN = os.getenv("BQ_DATE_COLUMN", "date")
DAYS_BACK = int(os.getenv("DAYS_BACK", "1"))  # Quantos dias atrás verificar
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "joao.gollucci@gauge.haus")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "alertas.engenhariagauge@gmail.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "tloohwsxfgvdzfib")

if not ALERT_EMAIL_TO or not SMTP_USER or not SMTP_PASSWORD:
    print("ERRO: Defina ALERT_EMAIL_TO, SMTP_USER e SMTP_PASSWORD para envio de alertas")
    exit(1)

print(f"Iniciando verificação de dados no BigQuery...")
print(f"Dataset/Tabela: {DATASET_TABLE}")
print(f"Verificando dados de D-{DAYS_BACK}\n")

def send_alert_email(target_date, row_count):
    """Envia email de alerta quando não há dados"""
    try:
        msg = MIMEMultipart('alternative')
        
        if row_count == 0:
            subject = f'🚨 ALERTA: Dados ausentes no BigQuery - {target_date}'
            title_color = '#d32f2f'
            status_message = 'Nenhum dado encontrado'
            status_color = '#d32f2f'
        else:
            subject = f'✓ Dados encontrados no BigQuery - {target_date}'
            title_color = '#4caf50'
            status_message = f'{row_count} registro(s) encontrado(s)'
            status_color = '#4caf50'
        
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL_TO
        
        # Corpo do email em HTML
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif;">
            <h2 style="color: {title_color};">{'🚨 Alerta: Dados Ausentes' if row_count == 0 else '✓ Verificação de Dados'}</h2>
            <p><strong>Data/Hora da Verificação:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p><strong>Data Consultada:</strong> {target_date} (D-{DAYS_BACK})</p>
            
            <h3>Detalhes da Consulta:</h3>
            <ul>
              <li><strong>Projeto:</strong> {PROJECT_ID}</li>
              <li><strong>Dataset/Tabela:</strong> {DATASET_TABLE}</li>
              <li><strong>Coluna de Data:</strong> {DATE_COLUMN}</li>
              <li><strong>Status:</strong> <span style="color: {status_color}; font-weight: bold;">{status_message}</span></li>
            </ul>
        """
        
        if row_count == 0:
            html_body += """
            <hr>
            <h3 style="color: #d32f2f;">⚠️ Ação Necessária:</h3>
            <p>Nenhum dado foi encontrado para a data especificada. Verifique:</p>
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
        # Criar cliente BigQuery (usa credenciais do ambiente Cloud Run)
        client = bigquery.Client(project=PROJECT_ID)
        
        # Calcular a data alvo (D-N)
        target_date = (datetime.now() - timedelta(days=DAYS_BACK)).date()
        
        # Construir query
        query = f"""
        SELECT {DATE_COLUMN}
        FROM `{PROJECT_ID}.{DATASET_TABLE}`
        WHERE {DATE_COLUMN} = DATE_SUB(CURRENT_DATE(), INTERVAL {DAYS_BACK} DAY)
        """
        
        print(f"Executando query no BigQuery...")
        print(f"Query: {query}\n")
        
        # Executar query
        query_job = client.query(query)
        results = query_job.result()
        
        # Contar registros
        row_count = results.total_rows
        
        print(f"Data alvo: {target_date}")
        print(f"Registros encontrados: {row_count}\n")
        
        return target_date, row_count
        
    except Exception as e:
        print(f"✗ ERRO ao consultar BigQuery: {e}")
        raise

# Executar verificação
try:
    target_date, row_count = check_bigquery_data()
    
    print("=" * 60)
    
    if row_count == 0:
        print(f"✗ ALERTA: Nenhum dado encontrado para {target_date}")
        print("\nEnviando email de alerta...")
        
        if send_alert_email(target_date, row_count):
            print("✓ Alerta enviado com sucesso")
        else:
            print("✗ Falha ao enviar alerta")
        
        exit(1)
    else:
        print(f"✓ Dados encontrados para {target_date}: {row_count} registro(s)")
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
