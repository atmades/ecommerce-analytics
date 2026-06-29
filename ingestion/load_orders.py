"""
Загрузка заказов Olist из локального CSV в GCS.

Паттерн: Extract (читаем CSV) → Validate (базовые проверки) → Load (пишем в GCS).
Трансформаций здесь нет — это задача dbt.
"""
from pathlib import Path
from datetime import date
import logging
import sys

from utils.config import config
from utils.gcs_client import upload_file, file_exists

# Настройка логирования — видим что происходит в терминале
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Константы этого скрипта
SOURCE_FILE = Path(__file__).parent.parent / "data" / "raw" / "olist_orders_dataset.csv"
# Путь в GCS: orders/2026-06-29/olist_orders_dataset.csv
# Дата в пути позволяет хранить историю загрузок
DESTINATION_BLOB = f"orders/{date.today()}/olist_orders_dataset.csv"


def validate_source(path: Path) -> None:
    """Проверяет что файл существует и не пустой."""
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Файл пустой: {path}")
    logger.info(f"Источник валиден: {path} ({path.stat().st_size / 1024:.1f} KB)")


def load_orders(force: bool = False) -> str:
    """
    Основная функция загрузки.

    Args:
        force: если True — перезаписывает файл в GCS даже если он уже есть.
               Идемпотентность: повторный запуск без force не дублирует данные.

    Returns:
        gs:// URI загруженного файла
    """
    logger.info("=== Старт загрузки orders ===")
    logger.info(f"Проект: {config.project_id}")
    logger.info(f"Bucket: {config.gcs_bucket}")

    # Validate
    validate_source(SOURCE_FILE)

    # Idempotency check — не загружаем повторно если файл уже есть
    if not force and file_exists(config.gcs_bucket, DESTINATION_BLOB):
        logger.info(f"Файл уже существует в GCS: {DESTINATION_BLOB}")
        logger.info("Пропускаем загрузку. Используй --force для перезаписи.")
        return f"gs://{config.gcs_bucket}/{DESTINATION_BLOB}"

    # Load
    uri = upload_file(
        bucket_name=config.gcs_bucket,
        source_path=SOURCE_FILE,
        destination_blob=DESTINATION_BLOB,
    )

    logger.info("=== Загрузка завершена успешно ===")
    return uri


if __name__ == "__main__":
    force = "--force" in sys.argv
    try:
        result = load_orders(force=force)
        print(f"\n✅ Успешно: {result}")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        sys.exit(1)
