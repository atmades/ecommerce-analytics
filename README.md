# E-Commerce Analytics Platform

Production-grade data engineering platform combining historical e-commerce data (Olist Brazil) with live market data (MercadoLibre Argentina API).

[![CI](https://github.com/atmades/ecommerce-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/atmades/ecommerce-analytics/actions/workflows/ci.yml)

---

## Architecture

```mermaid
flowchart LR
    A[Olist CSV] --> D[GCS Raw Zone]
    B[MercadoLibre API] --> D
    C[Exchange Rates API] --> D
    D --> E[BigQuery Raw]
    E --> F[dbt Staging]
    F --> G[dbt Intermediate]
    G --> H[dbt Marts]
    H --> I[Looker Studio]
    H --> J[NL→SQL Assistant]
    H --> K[ML Features]
```

**Stack:** Python · dbt Core 1.8 · BigQuery · Airflow 2.9 · Docker · GCP Secret Manager · GitHub Actions · Ollama/Mistral

---

## Data Model

```mermaid
flowchart TD
    subgraph RAW["dataset_raw (BigQuery)"]
        r1[orders · customers · products · sellers · reviews · payments · categories]
        r2[mercadolibre_products]
    end

    subgraph STAGING["dataset_staging (views)"]
        s1[stg_orders · stg_customers · stg_order_items]
        s2[stg_products · stg_sellers · stg_reviews]
        s3[stg_mercadolibre_products]
        sn1[snap_sellers · snap_products]
    end

    subgraph MARTS["dataset_marts (tables)"]
        m1[mart_sales]
        m2[mart_customers]
        m3[mart_cohorts]
        m4[mart_sellers]
        m5[mart_price_history]
        m6[dim_date]
    end

    RAW --> STAGING
    STAGING --> MARTS
```

| Mart | Grain | Rows | Description |
|------|-------|------|-------------|
| `mart_sales` | order | 97k | Delivered orders with revenue and delivery metrics |
| `mart_customers` | customer | 93k | LTV, RFM segmentation, order history |
| `mart_cohorts` | cohort × month | — | Retention analysis |
| `mart_sellers` | seller | 3k | Performance and quality metrics |
| `mart_price_history` | product × period | — | SCD Type 2 price changes (MercadoLibre) |
| `dim_date` | day | 5k | Calendar with BR/AR holidays |

**Data quality:** 38/38 tests passing ✅

See [MercadoLibre data flow](docs/mercadolibre_data_flow.md) for API integration details and price tracking architecture.

### Olist source schema (ERD)

```mermaid
erDiagram
  orders {
    string order_id PK
    string customer_id FK
    string order_status
    timestamp order_purchase_timestamp
    timestamp order_delivered_customer_date
    timestamp order_estimated_delivery_date
  }
  customers {
    string customer_id PK
    string customer_unique_id
    string customer_zip_code_prefix
    string customer_city
    string customer_state
  }
  order_items {
    string order_id FK
    int order_item_id
    string product_id FK
    string seller_id FK
    float price
    float freight_value
  }
  order_payments {
    string order_id FK
    string payment_type
    int payment_installments
    float payment_value
  }
  order_reviews {
    string order_id FK
    int review_score
    string review_comment_message
    timestamp review_creation_date
  }
  products {
    string product_id PK
    string product_category_name FK
    float product_weight_g
    int product_photos_qty
  }
  sellers {
    string seller_id PK
    string seller_city
    string seller_state
  }
  product_category_name_translation {
    string product_category_name PK
    string product_category_name_english
  }
  orders }o--|| customers : "belongs to"
  orders ||--o{ order_items : "contains"
  orders ||--o{ order_payments : "paid by"
  orders ||--o{ order_reviews : "reviewed in"
  order_items }o--|| products : "references"
  order_items }o--|| sellers : "fulfilled by"
  products }o--|| product_category_name_translation : "translated in"
```

---

## Quick Start

### Prerequisites
- Docker Desktop · Python 3.11+ · GCP project · Ollama

### 1. Clone and install

```bash
git clone https://github.com/atmades/ecommerce-analytics.git
cd ecommerce-analytics
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env  # fill in your GCP values
```

### 2. GCP Setup

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create datasets
bq mk --dataset --location=US YOUR_PROJECT:dataset_raw
bq mk --dataset --location=US YOUR_PROJECT:dataset_staging
bq mk --dataset --location=US YOUR_PROJECT:dataset_marts

# Service account
gcloud iam service-accounts create sa-ecommerce
gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member="serviceAccount:sa-ecommerce@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"
gcloud iam service-accounts keys create ~/.gcp/ecommerce-sa.json \
  --iam-account=sa-ecommerce@YOUR_PROJECT.iam.gserviceaccount.com
```

### 3. Download Olist data

Download from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) → extract to `data/raw/`

### 4. Run pipeline

```bash
# Ingestion
python ingestion/load_olist.py
python ingestion/load_to_bq.py

# dbt
cd dbt && dbt deps && dbt snapshot && dbt run && dbt test

# Airflow
docker compose up -d  # → http://localhost:8080 (admin/admin)
```

### 5. NL→SQL Assistant

```bash
brew install ollama && brew services start ollama
ollama pull mistral
python llm/nl_to_sql.py
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Warehouse | BigQuery | Free tier, GCS integration, market standard |
| Transform | dbt Core | Declarative SQL, testing, lineage |
| History | SCD Type 2 snapshots | Full price/status history, no data loss |
| Ingestion | CSV→GCS→BQ | Raw zone as reprocessable source of truth |
| LLM | Ollama/Mistral | Free, local, no API limits |

See [Architecture Decision Records](docs/decisions/) for details.

---

## Known Limitations

- `dbt sl query` requires dbt Cloud — metrics.yml follows MetricFlow spec, ready for upgrade to dbt 1.9+
- Exchange rates ingestion is a stub — BRL→USD uses static approximation
- MercadoLibre `/search` returns 403 — using highlights + products endpoints instead
- Olist data is historical (2016–2018) — retention metrics reflect past, not live activity
- Terraform IaC planned but not yet implemented

---

## Live Demo

| Resource | Link |
|----------|------|
| Streamlit Dashboard | [ecommerce-analytics.streamlit.app](https://ecommerce-analytics-cadvunukbous32harlxmvk.streamlit.app) |
| Price Gallery | [/price_gallery](https://ecommerce-analytics-cadvunukbous32harlxmvk.streamlit.app/price_gallery) |
| GitHub | [atmades/ecommerce-analytics](https://github.com/atmades/ecommerce-analytics) |

**Dashboard features:**
- MercadoLibre Argentina live price tracking (SCD Type 2)
- Top products by price growth with waterfall charts
- Product gallery with real images from MercadoLibre API
- Daily auto-update via GitHub Actions (06:00 UTC)

---

*Built as a portfolio project demonstrating production-grade Data Engineering practices.*