# ADR-006: SCD Type 2 for Product Prices and Seller Status

**Status:** Accepted  
**Date:** 2026-06

## Context

MercadoLibre product prices and seller statuses change over time.
Without history tracking, only the current state is known — past prices
and statuses are lost on each daily ingestion run.

## Decision

Use **dbt Snapshots (SCD Type 2)** to track changes in:
- `snap_products` — tracks `price_ars`, `status`, `category_id`
- `snap_sellers` — tracks `city`, `state`

```sql
{% snapshot snap_products %}
  {{ config(
      unique_key='product_id',
      strategy='check',
      check_cols=['price_ars', 'status', 'category_id'],
      invalidate_hard_deletes=True,
  ) }}
  select * from {{ ref('stg_mercadolibre_products') }}
{% endsnapshot %}
```

Each change creates a new row with `dbt_valid_from` / `dbt_valid_to` period.

## Consequences

**Positive:**
- Complete price history preserved — enables trend analysis
- Built into dbt — no custom CDC tooling needed
- `mart_price_history` built on top — shows price direction and delta
- `invalidate_hard_deletes=True` — handles product removals correctly

**Negative:**
- Storage grows over time (one row per change per product)
- Requires snapshot to run before staging (enforced in Airflow DAG order)
- Strategy `check` requires full table scan on each run

## Alternatives Considered

**SCD Type 1 (overwrite):** Simpler, but loses all history. Unacceptable for price analytics.

**Debezium + Kafka CDC:** Real-time change capture from PostgreSQL WAL. Overkill — our source is an API, not a database with WAL.

**Custom audit table:** Maintain manually with INSERT triggers. More error-prone than dbt's built-in snapshot mechanism.