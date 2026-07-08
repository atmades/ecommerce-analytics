# Runbook: Pipeline Failure

**Trigger:** Airflow DAG `daily_pipeline` shows FAILED status  
**SLA:** Investigate within 30 minutes of alert  
**Alert channel:** Airflow UI → DAG Runs

## Step 1 — Identify failed task

In Airflow UI:
1. Open `daily_pipeline` → last failed run
2. Click on red task → **Log**
3. Find the error message

## Step 2 — Common failures and fixes

### Ingestion failure (`ingest_olist`, `ingest_mercadolibre`)

Error: 404 Not Found — GCS file not found

**Fix:** File not uploaded to GCS for today's date. Run manually:

```bash
python ingestion/load_olist.py
```

### dbt compilation error

Error: Parsing Error — column not found

**Fix:** Schema change in source. Check `_sources.yml` and update column names.

### dbt test failure (`dbt_test_staging` or `dbt_test_marts`)

Failure in test not_null_...

**Fix:** Data quality issue in source. Check the failing test's compiled SQL in `dbt/target/compiled/`. Query BigQuery to understand the bad rows. Either fix source or adjust test severity.

### BigQuery quota exceeded

Error: 429 Too Many Requests

**Fix:** Wait 60 seconds and re-trigger the failed task in Airflow UI (Task → Clear → Confirm).

## Step 3 — Re-trigger failed task

In Airflow UI:
1. Click on failed task
2. **Clear** → **Confirm**
3. Task will retry from that point — upstream tasks won't re-run

## Step 4 — If DAG is stuck in running state

```bash
docker compose logs airflow-scheduler --tail=50
```

If scheduler is unresponsive:
```bash
docker compose restart airflow-scheduler
```