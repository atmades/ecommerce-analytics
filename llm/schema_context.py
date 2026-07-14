"""
Extracts mart table schemas from BigQuery and formats them
as a prompt context for the LLM.

Why we export schema dynamically (not hardcode):
- Schema evolves as we add columns
- LLM gets accurate, up-to-date field descriptions
- No manual sync needed between code and docs
"""
from google.cloud import bigquery
from utils.config import config

# Tables the LLM is allowed to query
# mart_customers excluded — contains PII fields
ALLOWED_TABLES = [
    "mart_sales",
    "mart_cohorts",
    "mart_sellers",
    "mart_price_history",
    "dim_date",
]


def get_schema_context() -> str:
    """
    Returns a formatted string describing all allowed mart tables.
    Used as system prompt context for the LLM.
    """
    client = get_bq_client()
    lines = []
    lines.append(f"BigQuery project: {config.project_id}")
    lines.append(f"Dataset: dataset_marts")
    lines.append("")
    lines.append("Available tables:")
    lines.append("")

    for table_name in ALLOWED_TABLES:
        table_ref = f"{config.project_id}.dataset_marts.{table_name}"
        try:
            table = client.get_table(table_ref)
            lines.append(f"## {table_name}")
            if table.description:
                lines.append(f"Description: {table.description}")
            lines.append("Columns:")
            for field in table.schema:
                desc = f" — {field.description}" if field.description else ""
                lines.append(f"  - {field.name} ({field.field_type}){desc}")
            lines.append("")
        except Exception as e:
            lines.append(f"## {table_name} [ERROR: {e}]")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print(get_schema_context())