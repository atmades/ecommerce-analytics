"""
Загрузка всех CSV файлов Olist в GCS.
Один скрипт вместо семи — общий паттерн, разные источники.
"""
from pathlib import Path
from datetime import date
import logging
import sys

from utils.config import config
from utils.gcs_client import upload_file, file_exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

# Все файлы Olist с их именами в GCS
# Формат: (локальный файл, папка в GCS)
OLIST_FILES = [
    ("olist_orders_dataset.csv",                    "orders"),
    ("olist_order_items_dataset.csv",               "order_items"),
    ("olist_order_payments_dataset.csv",            "order_payments"),
    ("olist_customers_dataset.csv",                 "customers"),
    ("olist_sellers_dataset.csv",                   "sellers"),
    ("olist_products_dataset.csv",                  "products"),
    ("olist_order_reviews_dataset.csv",             "reviews"),
    ("product_category_name_translation.csv", "product_categories"),
]

TODAY = date.today().isoformat()


def load_file(filename: str, folder: str, force: bool = False) -> dict:
    """
    Загружает один файл в GCS.
    Возвращает словарь с результатом — успех или ошибка.
    """
    source = DATA_DIR / filename
    destination = f"{folder}/{TODAY}/{filename}"

    # Validate
    if not source.exists():
        return {"file": filename, "status": "error", "reason": "файл не найден"}
    if source.stat().st_size == 0:
        return {"file": filename, "status": "error", "reason": "файл пустой"}

    # Idempotency
    if not force and file_exists(config.gcs_bucket, destination):
        logger.info(f"⏭  Пропускаем (уже есть): {destination}")
        return {"file": filename, "status": "skipped", "uri": f"gs://{config.gcs_bucket}/{destination}"}

    # Load
    uri = upload_file(
        bucket_name=config.gcs_bucket,
        source_path=source,
        destination_blob=destination,
    )
    return {"file": filename, "status": "success", "uri": uri}


def load_all(force: bool = False) -> None:
    logger.info("=== Старт загрузки Olist → GCS ===")
    logger.info(f"Bucket: {config.gcs_bucket}")
    logger.info(f"Дата партиции: {TODAY}")
    logger.info(f"Файлов к загрузке: {len(OLIST_FILES)}\n")

    results = []
    for filename, folder in OLIST_FILES:
        logger.info(f"Обрабатываем: {filename}")
        result = load_file(filename, folder, force=force)
        results.append(result)

    # Итоговый отчёт
    print("\n" + "="*50)
    print("ИТОГ ЗАГРУЗКИ")
    print("="*50)
    success = [r for r in results if r["status"] == "success"]
    skipped = [r for r in results if r["status"] == "skipped"]
    errors  = [r for r in results if r["status"] == "error"]

    print(f"✅ Загружено:  {len(success)}")
    print(f"⏭  Пропущено: {len(skipped)}")
    print(f"❌ Ошибок:    {len(errors)}")

    if errors:
        print("\nОшибки:")
        for e in errors:
            print(f"  - {e['file']}: {e['reason']}")
        sys.exit(1)


if __name__ == "__main__":
    force = "--force" in sys.argv
    load_all(force=force)
