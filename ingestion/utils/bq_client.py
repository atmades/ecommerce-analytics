from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import logging

logger = logging.getLogger(__name__)


# def get_bq_client() -> bigquery.Client:
#     return bigquery.Client()


def get_bq_client():
    if "gcp_credentials" in st.secrets:
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_info(
            dict(st.secrets["gcp_credentials"]),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(
            credentials=credentials,
            project=st.secrets["gcp_credentials"]["project_id"]
        )
    return bigquery.Client()


def load_csv_from_gcs(
    project_id: str,
    dataset_id: str,
    table_id: str,
    gcs_uri: str,
    schema: list[bigquery.SchemaField],
    write_disposition: str = "WRITE_TRUNCATE",
) -> int:
    """
    Загружает CSV из GCS в таблицу BigQuery.

    Args:
        write_disposition:
            WRITE_TRUNCATE — перезаписать таблицу (идемпотентно)
            WRITE_APPEND   — добавить строки
            WRITE_EMPTY    — записать только если таблица пустая

    Returns:
        Количество загруженных строк
    """
    client = get_bq_client()
    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,          # пропустить заголовок
        write_disposition=write_disposition,
        null_marker="",               # пустая строка = NULL
        allow_quoted_newlines=True,   # текст с переносами строк в кавычках
    )

    logger.info(f"Загрузка {gcs_uri} → {table_ref}")
    job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    job.result()  # ждём завершения

    table = client.get_table(table_ref)
    logger.info(f"Загружено строк: {table.num_rows}")
    return table.num_rows
