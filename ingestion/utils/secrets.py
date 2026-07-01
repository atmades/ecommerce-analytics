"""
Чтение секретов из GCP Secret Manager.

Почему не .env: секреты в .env видны всем кто получит доступ к файлу
или диску. Secret Manager логирует каждый доступ, поддерживает ротацию
и не хранит ничего в открытом виде на диске.
"""
from google.cloud import secretmanager
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_secret(secret_id: str, project_id: str, version: str = "latest") -> str:
    """
    Читает секрет из Secret Manager. Результат кэшируется в памяти процесса —
    не делаем сетевой запрос на каждый вызов.

    Args:
        secret_id: имя секрета, например 'mercadolibre-client-id'
        project_id: GCP project ID
        version: версия секрета, обычно 'latest'

    Returns:
        Значение секрета как строка
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

    try:
        response = client.access_secret_version(request={"name": name})
        logger.info(f"Секрет получен: {secret_id}")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Не удалось получить секрет {secret_id}: {e}")
        raise
