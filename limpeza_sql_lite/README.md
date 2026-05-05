# limpeza_sql_lite

Processamento manual (pontual) do banco SQLite do WAHA armazenado no GCS. Extrai mensagens de D-1, gera arquivo Parquet e limpa registros antigos para manter o banco enxuto.

## Fluxo de execução

1. Baixa os arquivos do banco (`gows.db`, `-shm`, `-wal`) do GCS
2. Consulta mensagens de D-1 (grupos, newsletters, lids)
3. Gera arquivo Parquet com os dados extraídos
4. Deleta registros com data diferente de hoje
5. Remove duplicatas na tabela `whatsmeow_lid_map`
6. Executa VACUUM, REINDEX e integrity check
7. Faz upload do Parquet para o path de saída
8. Retorna o banco limpo para o path de origem no GCS

## Variáveis de ambiente

| Variável | Descrição | Default |
|----------|-----------|---------|
| `GCS_BUCKET_NAME` | Nome do bucket no GCS | — |
| `GCS_ORIGIN_PATH` | Path do banco SQLite no bucket | — |
| `GCS_OUTPUT_PATH` | Path de destino para os Parquets | — |

## Execução com Docker

```bash
# Build
docker build -t limpeza-sqlite .

# Run
docker run --rm \
  -e GCS_BUCKET_NAME="meu-bucket" \
  -e GCS_ORIGIN_PATH="waha/db" \
  -e GCS_OUTPUT_PATH="landing/messages" \
  -v /path/to/credentials.json:/app/credentials.json \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
  limpeza-sqlite
```

## Saída

- Arquivo Parquet: `messages_YYYY-MM-DD.parquet` no path de saída configurado
- Colunas: `id`, `date`, `time`, `sender`, `sender2`, `body`, `caption`, `category`

## Execução

Processo executado manualmente de forma pontual, conforme necessidade.
