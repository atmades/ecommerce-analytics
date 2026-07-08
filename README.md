# E-Commerce Analytics Platform

Production-grade data engineering platform built on **BigQuery + dbt + Airflow**.  
Combines historical e-commerce data (Olist Brazil) with live market data (MercadoLibre Argentina API) to deliver a unified analytics layer with AI-powered querying.

---

## Architecture

MercadoLibre API (live) ──┐
Olist CSV (historical)   ──┼──► GCS Raw Zone ──► BigQuery Raw ──► dbt ──► Marts
Exchange Rates API       ──┘                                          │
├──► Looker Studio
├──► NL→SQL Assistant
└──► ML Features

**Stack:**

| Layer | Technology |
|-------|-----------|
| Storage | Google Cloud Storage |
| Warehouse | Google BigQuery |
| Transformation | dbt Core 1.8 |
| Orchestration | Apache Airflow 2.9 (Docker) |
| Snapshots / SCD Type 2 | dbt Snapshots |
| Semantic Layer | dbt Metrics (MetricFlow spec) |
| IaC | Terraform (planned) |
| Secrets | GCP Secret Manager |
| CI/CD | GitHub Actions |
| LLM Assistant | Ollama / Mistral (local) |
| Containerization | Docker Compose |

---

## Data Model

### Sources
- **Olist** — 100k+ Brazilian e-commerce orders (2016–2018), 8 tables
- **MercadoLibre API** — Live product catalog with prices (Argentina, OAuth2)
- **Exchange Rates API** — Daily BRL→USD conversion rates

### dbt Layers

staging/          ← rename, cast, PII masking (views)
├── olist/        ← 8 models from Olist CSV
└── mercadolibre/ ← 1 model from ML API
intermediate/     ← joins, enrichment, business logic (views)
├── int_orders_enriched
├── int_order_items_enriched
└── int_customers_lifetime
marts/            ← final tables for analysts and dashboards
├── mart_sales           ← 97k delivered orders, grain: order
├── mart_customers        ← 93k customers with RFM segmentation
├── mart_cohorts          ← retention analysis by cohort month
├── mart_sellers          ← 3k seller performance metrics
├── mart_price_history    ← MercadoLibre price changes (SCD Type 2)
└── dim_date              ← calendar table 2016–2030 (BR + AR holidays)
snapshots/        ← SCD Type 2 change tracking
├── snap_sellers  ← tracks city/state changes
└── snap_products ← tracks price/status/category changes (MercadoLibre)

### Data Quality
- **38 tests** — all passing
- Standard: `not_null`, `unique`, `accepted_values`, `relationships`
- Custom: volume anomaly detection, revenue non-negative, SCD period integrity
- Blocking test steps in Airflow DAG — marts don't update if staging tests fail

---

## Business Metrics (Semantic Layer)

Canonical metric definitions in `dbt/metrics/metrics.yml`:

| Metric | Definition |
|--------|-----------|
| `gross_revenue_brl` | Sum of total_payment_brl for delivered orders |
| `order_count` | Count of delivered orders |
| `avg_order_value_brl` | gross_revenue / order_count |
| `avg_delivery_days` | Average days from purchase to delivery |
| `on_time_delivery_rate` | % orders delivered on or before estimated date |
| `monthly_retention_rate` | % cohort customers active in given month |
| `customer_ltv_brl` | Average lifetime value per unique customer |

See [Business Glossary](docs/business_glossary.md) for canonical term definitions.

---

## Quick Start

### Prerequisites
- Docker Desktop
- Google Cloud SDK (`gcloud`)
- GCP project with BigQuery and GCS enabled
- Ollama (for NL→SQL assistant)

### 1. Clone and setup

```bash
git clone https://github.com/atmades/ecommerce-analytics.git
cd ecommerce-analytics

# Create virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure GCP

```bash
# Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# Create resources
gcloud storage buckets create gs://YOUR_BUCKET --location=US
bq mk --dataset --location=US YOUR_PROJECT:dataset_raw
bq mk --dataset --location=US YOUR_PROJECT:dataset_staging
bq mk --dataset --location=US YOUR_PROJECT:dataset_marts

# Create service account
gcloud iam service-accounts create sa-ecommerce
gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member="serviceAccount:sa-ecommerce@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/bigquery.admin"
gcloud projects add-iam-policy-binding YOUR_PROJECT \
  --member="serviceAccount:sa-ecommerce@YOUR_PROJECT.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
gcloud iam service-accounts keys create ~/.gcp/ecommerce-sa.json \
  --iam-account=sa-ecommerce@YOUR_PROJECT.iam.gserviceaccount.com
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your values:
# GCP_PROJECT_ID=your-project-id
# GCS_BUCKET=your-bucket-name
# BQ_DATASET=dataset_raw
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/ecommerce-sa.json
```

### 4. Download Olist dataset

Download from [Kaggle — Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and extract to `data/raw/`.

### 5. Run ingestion

```bash
# Load Olist CSV → GCS → BigQuery
python ingestion/load_olist.py
python ingestion/load_to_bq.py

# Load MercadoLibre API (requires API credentials in Secret Manager)
python ingestion/load_mercadolibre.py
```

### 6. Run dbt

```bash
cd dbt
dbt deps
dbt snapshot
dbt run
dbt test
```

### 7. Start Airflow

```bash
docker compose up -d
# Open http://localhost:8080 (admin/admin)
# Trigger: daily_pipeline
```

### 8. NL→SQL Assistant

```bash
# Install and start Ollama
brew install ollama
brew services start ollama
ollama pull mistral

# Run assistant
python llm/nl_to_sql.py
```

---

## Project Structure

ecommerce_analytics/
├── ingestion/              # Data ingestion scripts
│   ├── load_olist.py       # Olist CSV → GCS
│   ├── load_to_bq.py       # GCS → BigQuery
│   ├── load_mercadolibre.py # MercadoLibre API → GCS → BQ
│   └── utils/              # Shared utilities
│       ├── config.py       # Environment configuration
│       ├── gcs_client.py   # GCS operations
│       ├── bq_client.py    # BigQuery operations
│       ├── secrets.py      # GCP Secret Manager
│       ├── mercadolibre_client.py # OAuth2 API client
│       ├── rate_limiter.py # Token bucket rate limiter
│       └── circuit_breaker.py # Circuit breaker pattern
├── dbt/                    # dbt project
│   ├── models/
│   │   ├── staging/        # Raw → typed views
│   │   ├── intermediate/   # Business logic
│   │   └── marts/          # Final analytics tables
│   ├── snapshots/          # SCD Type 2
│   ├── metrics/            # Semantic Layer definitions
│   ├── tests/              # Custom data quality tests
│   └── macros/             # Reusable SQL macros
├── dags/                   # Airflow DAGs
│   └── daily_pipeline.py   # Main orchestration DAG
├── llm/                    # NL→SQL assistant
│   ├── nl_to_sql.py        # Main assistant
│   ├── schema_context.py   # Dynamic schema extraction
│   └── audit_log.py        # Query audit logging
├── docs/
│   ├── decisions/          # Architecture Decision Records
│   └── business_glossary.md
├── .github/workflows/      # CI/CD
│   ├── ci.yml              # dbt tests on PR
│   └── deploy.yml          # Deploy on merge to main
├── Dockerfile              # Airflow + dbt image
├── docker-compose.yml      # Local Airflow setup
└── pyproject.toml          # Python package config

---

## CI/CD

Every Pull Request to `develop` triggers:
1. `dbt compile` — syntax validation
2. `dbt test --select source:*` — source contract tests
3. `dbt run` — full model rebuild
4. `dbt test` — all 38 data quality tests

Merge to `main` is blocked if any test fails.

---

## MercadoLibre API Setup

1. Register at [MercadoLibre Developers](https://developers.mercadolibre.com.ar/devcenter)
2. Create application with `items` and `catalog` topics
3. Store credentials in GCP Secret Manager:

```bash
echo -n "YOUR_CLIENT_ID" | gcloud secrets create mercadolibre-client-id --data-file=-
echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create mercadolibre-client-secret --data-file=-
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Warehouse | BigQuery | Free tier, native GCS integration, standard in job market |
| Transformation | dbt Core | Declarative SQL, built-in testing, lineage graph |
| SCD Strategy | Type 2 (snapshots) | Full history preserved, no data loss on changes |
| Ingestion pattern | CSV→GCS→BQ | Raw zone as source of truth, reprocessable |
| Import style | Absolute (`ingestion.utils.*`) | No sys.path hacks, works from any directory |
| Local LLM | Ollama/Mistral | Free, no API limits, runs on MacBook M-chip |

See [Architecture Decision Records](docs/decisions/) for detailed rationale.

---

## Known Limitations

- `dbt sl query` (MetricFlow execution) requires dbt Cloud or dbt Core 1.9+. Current version pinned at 1.8.0 for BigQuery compatibility. Metric definitions in `metrics.yml` follow MetricFlow spec and are ready for upgrade.
- Exchange rates ingestion is a stub — `load_exchange_rates.py` not yet implemented. BRL→USD conversion uses static rate in current version.
- MercadoLibre search endpoint (`/sites/MLA/search`) returns 403 with current app permissions. Product data fetched via highlights + products endpoints instead.
- Olist dataset is static (2016–2018). `days_since_last_order` and retention metrics reflect historical data, not live activity.
- Terraform IaC documented in architecture but not yet implemented. Infrastructure currently managed via `gcloud` CLI commands in Quick Start.

---

## Test Results

dbt test --select marts
38 of 38 PASS ✅

---

*Built as a portfolio project demonstrating production-grade Data Engineering practices.*
*Stack: Python · dbt · BigQuery · Airflow · Docker · GCP · Ollama*