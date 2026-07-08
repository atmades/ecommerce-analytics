# ADR-003: Incremental Models for mart_sales

**Status:** Accepted  
**Date:** 2026-06

## Context

mart_sales contains ~97k rows and grows daily. Two materialization options:
- `table` (full refresh) — rebuild entire table on every run
- `incremental` — only process new/changed rows

## Decision

Use **incremental materialization** for `mart_sales` with partition-based strategy.

```sql
{{ config(
    materialized='incremental',
    partition_by={"field": "order_date", "data_type": "date", "granularity": "month"},
    cluster_by=["primary_category", "customer_state"]
) }}
```

## Consequences

**Positive:**
- Run time: ~2 min (incremental) vs ~8 min (full refresh)
- BigQuery cost: scans only new partition instead of entire table
- Scales as data grows — processing time stays constant

**Negative:**
- More complex logic — requires `is_incremental()` checks
- Risk of duplicates if unique key logic is wrong
- Full refresh needed after schema changes

## Alternatives Considered

**Full refresh (`table`):** Simpler code, always consistent. Acceptable for current data size but doesn't scale. Used for mart_customers, mart_cohorts, mart_sellers where full rebuild is fast.

**View:** No storage cost, always fresh. Too slow for complex joins at query time — analysts would face multi-second query times.