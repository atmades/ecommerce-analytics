# Runbook: Source Schema Change

**Trigger:** dbt pipeline fails with `Unrecognized name: column_name` error  
**SLA:** Fix within 4 business hours  
**Alert channel:** Airflow DAG failure + `#data-contracts` Slack (if configured)

## What happened

A source system changed its schema:
- Column renamed or removed → dbt can't find it
- New column added → usually safe, dbt ignores unknown columns
- Data type changed → may cause silent failures or cast errors

## Step 1 — Identify the change

```bash
# Check what dbt is complaining about
docker compose exec airflow-webserver bash -c \
  "cd /opt/airflow/dbt && dbt compile 2>&1 | grep -i error"
```

## Step 2 — Compare old vs new schema

```sql
-- Check current schema in BigQuery
SELECT column_name, data_type
FROM `YOUR_PROJECT.dataset_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'affected_table'
ORDER BY ordinal_position
```

Compare with column definitions in:
- `ingestion/utils/schemas.py` — BigQuery load schema
- `dbt/models/staging/olist/_sources_olist.yml` — dbt source contract

## Step 3 — Fix

**If column renamed:**
1. Update `schemas.py` with new column name
2. Update `_sources_olist.yml`
3. Update staging model SQL
4. Re-run ingestion + dbt

**If column removed:**
1. Remove from `schemas.py`
2. Remove tests from `_sources_olist.yml`
3. Update staging model SQL
4. Check if downstream models use this column

**If new column added (optional):**
1. Add to `schemas.py` if you want to capture it
2. Add to staging model if useful for analytics

## Step 4 — Verify fix

```bash
cd dbt && dbt compile && dbt run --select staging && dbt test --select staging
```

## Step 5 — Communicate

Notify source team about schema change process:
- Breaking changes require 5 business days advance notice
- Use `#data-contracts` channel (or email if Slack not configured)