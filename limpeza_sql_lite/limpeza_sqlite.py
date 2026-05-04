import os
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from google.cloud import storage

# Variáveis de ambiente
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
ORIGIN_PATH = os.getenv("GCS_ORIGIN_PATH", "").strip("/")
OUTPUT_PATH = os.getenv("GCS_OUTPUT_PATH", "").strip("/")

DB_PREFIX = "gows.db"
DB_FILES = ["gows.db", "gows.db-shm", "gows.db-wal"]
LOCAL_DIR = "/tmp/sqlite_work"


def get_client():
    return storage.Client()


def download_from_origin(client):
    """Baixa os arquivos do banco diretamente da origem para o diretório local."""
    os.makedirs(LOCAL_DIR, exist_ok=True)
    bucket = client.bucket(BUCKET_NAME)
    for fname in DB_FILES:
        blob = bucket.blob(f"{ORIGIN_PATH}/{fname}")
        local_path = os.path.join(LOCAL_DIR, fname)
        blob.download_to_filename(local_path)
        print(f"Baixado {ORIGIN_PATH}/{fname} -> {local_path}")


def process_sqlite():
    """Executa o tratamento do banco SQLite: consulta D-1, salva parquet, deleta registros antigos."""
    db_path = os.path.join(LOCAL_DIR, "gows.db")
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"\nDatas de referência: consulta={yesterday}, delete != {today}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Checkpoint WAL antes de iniciar
    cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    print(f"WAL checkpoint inicial: {cursor.fetchall()}")

    # Consulta D-1
    query = (
        "SELECT jid as id,"
        "date(timestamp) as date,"
        "time(timestamp) as time,"
        "coalesce(json_extract(data, '$.Info.SenderAlt'), 'N/A') as sender,"
        "coalesce(json_extract(data, '$.Info.Chat'), 'N/A') as sender2,"
        "coalesce(json_extract(data, '$.RawMessage.extendedTextMessage.text'), 'N/A') as body,"
        "coalesce(json_extract(data, '$.Message.imageMessage.caption'), 'N/A') as caption,"
        "'to_process' as category "
        "FROM gows_messages "
        f"WHERE date(timestamp) = '{yesterday}' "
        "AND substr(jid, instr(jid, '@') + 1) in ('g.us', 'newsletter', 'lid')"
    )

    df = pd.read_sql_query(query, conn)
    print(f"Registros encontrados para {yesterday}: {len(df)}")

    parquet_path = None
    if len(df) > 0:
        parquet_name = f"messages_{yesterday}.parquet"
        parquet_path = os.path.join(LOCAL_DIR, parquet_name)
        df.to_parquet(parquet_path, index=False)
        print(f"Parquet salvo localmente: {parquet_path}")
    else:
        print("Nenhum registro encontrado para D-1, parquet não será gerado.")

    # Delete registros com data diferente de hoje
    try:
        cursor.execute(f"DELETE FROM gows_messages WHERE date(timestamp) != '{today}'")
        conn.commit()
        print(f"DELETE executado (mantidos apenas registros de {today})")
    except Exception as e:
        print(f"ALERTA: Falha no DELETE de mensagens antigas: {e}")

    # Checkpoint WAL pós-delete
    try:
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        print(f"WAL checkpoint pós-delete: {cursor.fetchall()}")
    except Exception as e:
        print(f"ALERTA: Falha no WAL checkpoint pós-delete: {e}")

    # Remover duplicatas na whatsmeow_lid_map para evitar UNIQUE constraint em pn
    try:
        cursor.execute("""
            DELETE FROM whatsmeow_lid_map
            WHERE rowid NOT IN (
                SELECT MIN(rowid) FROM whatsmeow_lid_map GROUP BY pn
            )
        """)
        deleted_lids = cursor.rowcount
        conn.commit()
        if deleted_lids > 0:
            print(f"Removidas {deleted_lids} duplicatas de whatsmeow_lid_map.pn")
    except Exception as e:
        print(f"ALERTA: Falha ao remover duplicatas de whatsmeow_lid_map: {e}")

    # VACUUM para recuperar espaço
    try:
        cursor.execute("VACUUM;")
        print("VACUUM executado")
    except Exception as e:
        print(f"ALERTA: Falha no VACUUM: {e}")

    # Reindexar para corrigir possíveis problemas de autoindex
    try:
        cursor.execute("REINDEX;")
        print("REINDEX executado")
    except Exception as e:
        print(f"ALERTA: Falha no REINDEX: {e}")

    # Verificação de integridade
    try:
        cursor.execute("PRAGMA integrity_check;")
        integrity = cursor.fetchall()
        print(f"Integrity check: {integrity}")
        if integrity[0][0] != "ok":
            print(f"ALERTA: Integrity check retornou problemas: {integrity}")
    except Exception as e:
        print(f"ALERTA: Falha no integrity check: {e}")

    # Checkpoint WAL final
    try:
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        print(f"WAL checkpoint final: {cursor.fetchall()}")
    except Exception as e:
        print(f"ALERTA: Falha no WAL checkpoint final: {e}")

    conn.close()
    return parquet_path


def upload_parquet(client, parquet_path):
    """Faz upload do parquet para a pasta de saída no GCS."""
    if not parquet_path:
        return
    bucket = client.bucket(BUCKET_NAME)
    parquet_name = os.path.basename(parquet_path)
    blob = bucket.blob(f"{OUTPUT_PATH}/{parquet_name}")
    blob.upload_from_filename(parquet_path)
    print(f"Parquet enviado para {OUTPUT_PATH}/{parquet_name}")


def return_files_to_origin(client):
    """Retorna os arquivos do banco para a pasta de origem."""
    bucket = client.bucket(BUCKET_NAME)
    if not os.path.exists(LOCAL_DIR):
        print("Diretório local não existe, nada a devolver.")
        return
    for fname in DB_FILES:
        local_path = os.path.join(LOCAL_DIR, fname)
        if not os.path.exists(local_path):
            continue
        dest_blob = bucket.blob(f"{ORIGIN_PATH}/{fname}")
        dest_blob.upload_from_filename(local_path)
        print(f"Enviado {local_path} -> {ORIGIN_PATH}/{fname}")


def cleanup_local():
    """Remove os arquivos locais temporários."""
    import shutil
    if os.path.exists(LOCAL_DIR):
        shutil.rmtree(LOCAL_DIR)
        print(f"Diretório local {LOCAL_DIR} removido")


def main():
    if not BUCKET_NAME:
        print("ERRO: Defina a variável de ambiente GCS_BUCKET_NAME")
        exit(1)

    print(f"Bucket: {BUCKET_NAME}")
    print(f"Origem: {ORIGIN_PATH}")
    print(f"Output: {OUTPUT_PATH}\n")

    client = get_client()

    try:
        # 1) Baixar arquivos da origem para processamento local (e remove da origem)
        print("=== Baixando arquivos da origem ===")
        download_from_origin(client)

        # 2) Processar SQLite
        print("\n=== Processando banco SQLite ===")
        parquet_path = process_sqlite()

        # 3) Upload do parquet
        print("\n=== Upload do parquet ===")
        upload_parquet(client, parquet_path)

        # 4) Retornar arquivos para a origem
        print("\n=== Retornando arquivos para a origem ===")
        return_files_to_origin(client)

        print("\nProcesso finalizado com sucesso!")

    except Exception as e:
        print(f"\nERRO durante o processamento: {e}")
        # Tenta devolver os arquivos mesmo em caso de erro
        try:
            print("Tentando retornar arquivos para a origem...")
            return_files_to_origin(client)
        except Exception as e2:
            print(f"ERRO ao retornar arquivos: {e2}")
        raise
    finally:
        cleanup_local()


if __name__ == "__main__":
    main()
