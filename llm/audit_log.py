"""
Logs every LLM query to BigQuery for audit and cost monitoring.
Table: dataset_raw.llm_audit_log
"""
from google.cloud import bigquery
from datetime import datetime
from utils.config import config


def log_query(
    question: str,
    generated_sql: str,
    tables_referenced: list[str],
    user_id: str = "anonymous",
    tokens_used: int = 0,
) -> None:
    """Writes one audit record to BQ. Fire-and-forget — errors are logged but not raised."""
    client = bigquery.Client()
    table_ref = f"{config.project_id}.dataset_raw.llm_audit_log"

    row = {
        "user_id": user_id,
        "question": question,
        "generated_sql": generated_sql,
        "tables_referenced": tables_referenced,
        "tokens_used": tokens_used,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        errors = client.insert_rows_json(table_ref, [row])
        if errors:
            print(f"Audit log warning: {errors}")
    except Exception as e:
        print(f"Audit log error (non-critical): {e}")