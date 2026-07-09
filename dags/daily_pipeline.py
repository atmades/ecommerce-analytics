"""
Daily E-Commerce Analytics Pipeline

Schedule: 06:00 UTC daily
SLA: must complete by 08:00 UTC

Flow:
  ingest_olist → ingest_mercadolibre → ingest_exchange_rates
       ↓
  dbt_snapshot
       ↓
  dbt_run_staging → dbt_test_staging (blocking)
       ↓
  dbt_run_intermediate
       ↓
  dbt_run_marts → dbt_test_marts (blocking)
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# ── Default args ────────────────────────────────────────────────────────────

default_args = {
    "owner": "data-team",
    "depends_on_past": False,
    "start_date": days_ago(1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
    "execution_timeout": timedelta(hours=1),
}

# ── DAG definition ───────────────────────────────────────────────────────────

dag = DAG(
    dag_id="daily_pipeline",
    default_args=default_args,
    description="Daily ingestion + dbt transformation pipeline",
    schedule_interval="0 6 * * *",   # 06:00 UTC every day
    catchup=False,                    # don't backfill missed runs
    max_active_runs=1,                # only one run at a time
    dagrun_timeout=timedelta(hours=3),
    tags=["production", "daily"],
)

# ── Helper paths ─────────────────────────────────────────────────────────────

INGESTION_DIR = "/opt/airflow/ingestion"
DBT_DIR = "/opt/airflow/dbt"
PYTHON = "python"
DBT = "dbt"

# ── Tasks: Ingestion ─────────────────────────────────────────────────────────

ingest_olist = BashOperator(
    task_id="ingest_olist",
    bash_command=(
        f"cd {INGESTION_DIR} && "
        f"{PYTHON} load_to_bq.py 2026-06-29"
        # Olist is a static historical dataset — files in GCS never change.
        # Always load from the original upload date partition.
    ),
    dag=dag,
)

ingest_mercadolibre = BashOperator(
    task_id="ingest_mercadolibre",
    bash_command=(
        f"cd {INGESTION_DIR} && "
        f"{PYTHON} load_mercadolibre.py "
        "{{ ds }}"
    ),
    dag=dag,
)

ingest_exchange_rates = BashOperator(
    task_id="ingest_exchange_rates",
    bash_command="echo 'Exchange rates ingestion - TODO'",
    dag=dag,
)


# ── Tasks: dbt snapshot ──────────────────────────────────────────────────────

DBT_CMD = f"cd {DBT_DIR} && dbt"

dbt_snapshot = BashOperator(
    task_id="dbt_snapshot",
    bash_command=f"{DBT_CMD} snapshot",
    dag=dag,
)

# ── Tasks: dbt staging ───────────────────────────────────────────────────────

dbt_run_staging = BashOperator(
    task_id="dbt_run_staging",
    bash_command=f"{DBT_CMD} run --select staging",
    dag=dag,
)

# Blocking — if tests fail, marts won't run
dbt_test_staging = BashOperator(
    task_id="dbt_test_staging",
    bash_command=f"{DBT_CMD} test --select staging",
    dag=dag,
)

# ── Tasks: dbt intermediate ──────────────────────────────────────────────────

dbt_run_intermediate = BashOperator(
    task_id="dbt_run_intermediate",
    bash_command=f"{DBT_CMD} run --select intermediate",
    dag=dag,
)

# ── Tasks: dbt marts ─────────────────────────────────────────────────────────

dbt_run_marts = BashOperator(
    task_id="dbt_run_marts",
    bash_command=f"{DBT_CMD} run --select marts",
    dag=dag,
)

# Blocking — alerts go out if mart tests fail
dbt_test_marts = BashOperator(
    task_id="dbt_test_marts",
    bash_command=f"{DBT_CMD} test --select marts",
    dag=dag,
)

# ── Task dependencies ────────────────────────────────────────────────────────
#
# Ingestion runs in parallel, then snapshot, then staging, then intermediate, then marts
#
# [ingest_olist]          ─┐
# [ingest_mercadolibre]   ─┼─► [dbt_snapshot] ─► [dbt_run_staging] ─► [dbt_test_staging]
# [ingest_exchange_rates] ─┘                                                    │
#                                                                                ▼
#                                                                   [dbt_run_intermediate]
#                                                                                │
#                                                                                ▼
#                                                                      [dbt_run_marts]
#                                                                                │
#                                                                                ▼
#                                                                      [dbt_test_marts]

[ingest_olist, ingest_mercadolibre, ingest_exchange_rates] >> dbt_snapshot
dbt_snapshot >> dbt_run_staging >> dbt_test_staging
dbt_test_staging >> dbt_run_intermediate
dbt_run_intermediate >> dbt_run_marts >> dbt_test_marts