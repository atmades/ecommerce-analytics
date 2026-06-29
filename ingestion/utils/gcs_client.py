from google.cloud import storage
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_gcs_client() -> storage.Client:
    """Создаёт GCS клиент. Credentials берёт из GOOGLE_APPLICATION_CREDENTIALS."""
    return storage.Client()


def upload_file(
    bucket_name: str,
    source_path: Path,
    destination_blob: str,
) -> str:
    """
    Загружает файл в GCS.

    Args:
        bucket_name: имя bucket без gs://
        source_path: локальный путь к файлу
        destination_blob: путь внутри bucket, например 'orders/2026-06-29.csv'

    Returns:
        gs:// URI загруженного файла
    """
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)

    blob.upload_from_filename(str(source_path))

    uri = f"gs://{bucket_name}/{destination_blob}"
    logger.info(f"Загружено: {source_path} → {uri}")
    return uri


def file_exists(bucket_name: str, blob_name: str) -> bool:
    """Проверяет существование файла в GCS."""
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    return blob.exists()
