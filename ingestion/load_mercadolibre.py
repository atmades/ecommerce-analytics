"""
Загрузка данных MercadoLibre → GCS → BigQuery.

Pipeline:
1. Получаем список категорий (MLA)
2. Для каждой категории получаем топ-продукты через highlights
3. Для каждого продукта получаем детали и цены
4. Сохраняем в GCS и загружаем в BQ

Данные используются для snap_products (SCD Type 2 tracking цен).
"""
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from google.cloud import bigquery, storage

from utils.config import config
from utils.mercadolibre_client import MercadoLibreClient
from utils.rate_limiter import TokenBucketRateLimiter
from utils.gcs_client import get_gcs_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

TODAY = sys.argv[1] if len(sys.argv) > 1 else date.today().isoformat()
SITE_ID = "MLA"
MAX_CATEGORIES = 5      # для учёбы берём первые 5 категорий
MAX_PRODUCTS_PER_CATEGORY = 10  # топ-10 продуктов на категорию


def fetch_categories(client: MercadoLibreClient) -> list[dict]:
    """Получаем все категории сайта."""
    logger.info(f"Получаем категории для {SITE_ID}")
    categories = client.get(f"/sites/{SITE_ID}/categories")
    logger.info(f"Получено категорий: {len(categories)}")
    return categories[:MAX_CATEGORIES]


def fetch_highlights(
    client: MercadoLibreClient,
    limiter: TokenBucketRateLimiter,
    category_id: str
) -> list[str]:
    """Получаем топ product_id для категории."""
    limiter.acquire()
    try:
        data = client.get(f"/highlights/{SITE_ID}/category/{category_id}")
        product_ids = [item["id"] for item in data.get("content", [])]
        return product_ids[:MAX_PRODUCTS_PER_CATEGORY]
    except Exception as e:
        logger.warning(f"Highlights недоступны для {category_id}: {e}")
        return []


def fetch_product(
    client: MercadoLibreClient,
    limiter: TokenBucketRateLimiter,
    product_id: str,
    category_id: str,
    category_name: str,
) -> dict | None:
    """Получаем детали продукта и минимальную цену из listings."""
    limiter.acquire()
    try:
        product = client.get(f"/products/{product_id}")
    except Exception as e:
        logger.warning(f"Продукт {product_id} недоступен: {e}")
        return None

    # Получаем цены из listings
    limiter.acquire()
    min_price = None
    try:
        items_data = client.get(f"/products/{product_id}/items")
        prices = [
            item["price"]
            for item in items_data.get("results", [])
            if item.get("price")
        ]
        min_price = min(prices) if prices else None
    except Exception:
        pass

    return {
        "product_id": product_id,
        "category_id": category_id,
        "category_name": category_name,
        "name": product.get("name"),
        "status": product.get("status"),
        "domain_id": product.get("domain_id"),
        "min_price_ars": min_price,
        "currency": "ARS",
        "ingested_at": datetime.utcnow().isoformat(),
    }


def save_to_gcs(records: list[dict]) -> str:
    """Сохраняем JSONL в GCS."""
    blob_name = f"mercadolibre/products/{TODAY}/products.jsonl"
    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)

    gcs = get_gcs_client()
    bucket = gcs.bucket(config.gcs_bucket)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(content, content_type="application/json")

    uri = f"gs://{config.gcs_bucket}/{blob_name}"
    logger.info(f"Сохранено в GCS: {uri}")
    return uri


def load_to_bq(gcs_uri: str, rows: int) -> None:
    """Загружаем JSONL из GCS в BigQuery."""
    client = bigquery.Client()
    table_ref = f"{config.project_id}.{config.bq_dataset}.mercadolibre_products"

    schema = [
        bigquery.SchemaField("product_id",    "STRING",    "NULLABLE"),
        bigquery.SchemaField("category_id",   "STRING",    "NULLABLE"),
        bigquery.SchemaField("category_name", "STRING",    "NULLABLE"),
        bigquery.SchemaField("name",          "STRING",    "NULLABLE"),
        bigquery.SchemaField("status",        "STRING",    "NULLABLE"),
        bigquery.SchemaField("domain_id",     "STRING",    "NULLABLE"),
        bigquery.SchemaField("min_price_ars", "FLOAT",     "NULLABLE"),
        bigquery.SchemaField("currency",      "STRING",    "NULLABLE"),
        bigquery.SchemaField("ingested_at",   "TIMESTAMP", "NULLABLE"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        write_disposition="WRITE_TRUNCATE",
    )

    job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    job.result()
    logger.info(f"Загружено в BQ: {table_ref} ({rows} строк)")


def main():
    logger.info("=== Старт загрузки MercadoLibre ===")
    client = MercadoLibreClient()
    limiter = TokenBucketRateLimiter(rate=600, per=60)

    categories = fetch_categories(client)
    all_products = []

    for cat in categories:
        cat_id = cat["id"]
        cat_name = cat["name"]
        logger.info(f"Категория: {cat_name} ({cat_id})")

        product_ids = fetch_highlights(client, limiter, cat_id)
        logger.info(f"  Продуктов в highlights: {len(product_ids)}")

        for pid in product_ids:
            product = fetch_product(client, limiter, pid, cat_id, cat_name)
            if product:
                all_products.append(product)

    logger.info(f"Итого продуктов: {len(all_products)}")

    if not all_products:
        logger.error("Нет данных для загрузки")
        sys.exit(1)

    gcs_uri = save_to_gcs(all_products)
    load_to_bq(gcs_uri, len(all_products))

    print(f"\n✅ Загрузка завершена: {len(all_products)} продуктов")


if __name__ == "__main__":
    main()
