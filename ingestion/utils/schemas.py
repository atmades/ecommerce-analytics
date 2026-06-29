"""
Схемы BigQuery для всех таблиц Olist.
Явные типы вместо autodetect — в production autodetect ненадёжен:
он может угадать STRING вместо TIMESTAMP или FLOAT вместо INTEGER.
"""
from google.cloud import bigquery

F = bigquery.SchemaField  # короткий алиас

ORDERS = [
    F("order_id",                          "STRING",    "REQUIRED"),
    F("customer_id",                       "STRING",    "REQUIRED"),
    F("order_status",                      "STRING",    "NULLABLE"),
    F("order_purchase_timestamp",          "TIMESTAMP", "NULLABLE"),
    F("order_approved_at",                 "TIMESTAMP", "NULLABLE"),
    F("order_delivered_carrier_date",      "TIMESTAMP", "NULLABLE"),
    F("order_delivered_customer_date",     "TIMESTAMP", "NULLABLE"),
    F("order_estimated_delivery_date",     "TIMESTAMP", "NULLABLE"),
]

ORDER_ITEMS = [
    F("order_id",            "STRING",  "REQUIRED"),
    F("order_item_id",       "INTEGER", "REQUIRED"),
    F("product_id",          "STRING",  "NULLABLE"),
    F("seller_id",           "STRING",  "NULLABLE"),
    F("shipping_limit_date", "TIMESTAMP", "NULLABLE"),
    F("price",               "FLOAT",   "NULLABLE"),
    F("freight_value",       "FLOAT",   "NULLABLE"),
]

ORDER_PAYMENTS = [
    F("order_id",             "STRING",  "REQUIRED"),
    F("payment_sequential",   "INTEGER", "NULLABLE"),
    F("payment_type",         "STRING",  "NULLABLE"),
    F("payment_installments", "INTEGER", "NULLABLE"),
    F("payment_value",        "FLOAT",   "NULLABLE"),
]

CUSTOMERS = [
    F("customer_id",               "STRING", "REQUIRED"),
    F("customer_unique_id",        "STRING", "NULLABLE"),
    F("customer_zip_code_prefix",  "STRING", "NULLABLE"),
    F("customer_city",             "STRING", "NULLABLE"),
    F("customer_state",            "STRING", "NULLABLE"),
]

SELLERS = [
    F("seller_id",              "STRING", "REQUIRED"),
    F("seller_zip_code_prefix", "STRING", "NULLABLE"),
    F("seller_city",            "STRING", "NULLABLE"),
    F("seller_state",           "STRING", "NULLABLE"),
]

PRODUCTS = [
    F("product_id",                   "STRING",  "REQUIRED"),
    F("product_category_name",        "STRING",  "NULLABLE"),
    F("product_name_lenght",          "INTEGER", "NULLABLE"),  # опечатка в оригинале
    F("product_description_lenght",   "INTEGER", "NULLABLE"),  # оставляем как есть в raw
    F("product_photos_qty",           "INTEGER", "NULLABLE"),
    F("product_weight_g",             "FLOAT",   "NULLABLE"),
    F("product_length_cm",            "FLOAT",   "NULLABLE"),
    F("product_height_cm",            "FLOAT",   "NULLABLE"),
    F("product_width_cm",             "FLOAT",   "NULLABLE"),
]

REVIEWS = [
    F("review_id",               "STRING",    "NULLABLE"),
    F("order_id",                "STRING",    "REQUIRED"),
    F("review_score",            "INTEGER",   "NULLABLE"),
    F("review_comment_title",    "STRING",    "NULLABLE"),
    F("review_comment_message",  "STRING",    "NULLABLE"),
    F("review_creation_date",    "TIMESTAMP", "NULLABLE"),
    F("review_answer_timestamp", "TIMESTAMP", "NULLABLE"),
]

PRODUCT_CATEGORIES = [
    F("product_category_name",         "STRING", "REQUIRED"),
    F("product_category_name_english", "STRING", "NULLABLE"),
]
