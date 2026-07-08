# ADR-004: Backfill Strategy for Incremental Models

**Status:** Accepted  
**Date:** 2026-06

## Context

When a bug is found in transformation logic or source data changes historically,
incremental models need to be reprocessed for a specific date range without
affecting other partitions or creating duplicates.

## Decision

Parameterized backfill via dbt variables + Airflow DAG trigger.

```bash
# Reprocess specific date range
dbt run \
  --select mart_sales \
  --vars '{"start_date": "2017-01-01", "end_date": "2017-03-31"}' \
  --full-refresh
```

In `mart_sales.sql`:
```sql
{% if var('start_date', none) is not none %}
  WHERE order_date BETWEEN '{{ var("start_date") }}' AND '{{ var("end_date") }}'
{% elif is_incremental() %}
  WHERE order_date >= (SELECT MAX(order_date) FROM {{ this }})
{% endif %}
```

## Consequences

**Positive:**
- Idempotent — running backfill twice produces same result
- Surgical — only reprocesses specified range
- No custom tooling needed — uses native dbt variables

**Negative:**
- Manual process — requires engineer to identify affected range
- Full refresh on partition is required (can't partial update)

## Alternatives Considered

**Delete + reinsert:** Requires DML permissions and careful transaction management. Risk of data loss on failure.

**Separate backfill models:** Duplicate code maintenance burden.