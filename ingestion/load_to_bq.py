"""
Загрузка всех таблиц Olist из GCS → BigQuery.
Читает файлы из GCS напрямую — ничего не скачивает локально.
"""
from datetime import date
import logging
import sys

from utils.config import config
from utils.bq_client import load_csv_from_gcs
from utils import schemas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TODAY = date.today().isoformat()
BUCKET = f"gs://{config.gcs_bucket}"

# (gcs_folder, gcs_filename, bq_table_name, schema)
TABLES = [
    ("orders",             "olist_orders_dataset.csv",                    "orders",             schemas.ORDERS),
    ("order_items",        "olist_order_items_dataset.csv",               "order_items",        schemas.ORDER_ITEMS),
    ("order_payments",     "olist_order_payments_dataset.csv",            "order_payments",     schemas.ORDER_PAYMENTS),
    ("customers",          "olist_customers_dataset.csv",                 "customers",          schemas.CUSTOMERS),
    ("sellers",            "olist_sellers_dataset.csv",                   "sellers",            schemas.SELLERS),
    ("products",           "olist_products_dataset.csv",                  "products",           schemas.PRODUCTS),
    ("reviews",            "olist_order_reviews_dataset.csv",             "reviews",            schemas.REVIEWS),
    ("product_categories", "product_category_name_translation.csv",       "product_categories", schemas.PRODUCT_CATEGORIES),
]


def load_all() -> None:
    logger.info("=== Старт загрузки GCS → BigQuery ===")
    logger.info(f"Dataset: {config.project_id}.{config.bq_dataset}")

    results = []
    for folder, filename, table_name, schema in TABLES:
        gcs_uri = f"{BUCKET}/{folder}/{TODAY}/{filename}"
        try:
            rows = load_csv_from_gcs(
                project_id=config.project_id,
                dataset_id=config.bq_dataset,
                table_id=table_name,
                gcs_uri=gcs_uri,
                schema=schema,
            )
            results.append({"table": table_name, "status": "success", "rows": rows})
        except Exception as e:
            logger.error(f"Ошибка при загрузке {table_name}: {e}")
            results.append({"table": table_name, "status": "error", "reason": str(e)})

    # Итог
    print("\n" + "="*50)
    print("ИТОГ ЗАГРУЗКИ В BIGQUERY")
    print("="*50)
    for r in results:
        if r["status"] == "success":
            print(f"✅ {r['table']:<25} {r['rows']:>8} строк")
        else:
            print(f"❌ {r['table']:<25} {r['reason']}")

    errors = [r for r in results if r["status"] == "error"]
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    load_all()
