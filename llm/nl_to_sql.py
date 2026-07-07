import os
import re
import json
import requests

from ingestion.utils.config import config
from ingestion.utils.secrets import get_secret

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL = "mistral"

ALLOWED_TABLES = [
    "mart_sales",
    "mart_cohorts",
    "mart_sellers",
    "mart_price_history",
    "dim_date",
]

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE",
    "TRUNCATE", "ALTER", "CREATE", "REPLACE",
]

PII_PATTERNS = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
]

SYSTEM_PROMPT = """You are a BigQuery SQL assistant for an e-commerce analytics platform.

Available tables in project {project}, dataset dataset_marts:

{schema}

Rules:
- Use fully qualified table names: `{project}.dataset_marts.table_name`
- Only use tables listed above
- Never generate DROP, DELETE, INSERT, UPDATE, TRUNCATE, ALTER
- Add LIMIT 1000 for non-aggregation queries
- Return ONLY a JSON object with fields:
  - "sql": complete BigQuery SQL query
  - "explanation": brief explanation in the same language as the question
  - "tables_used": list of table names used
- No markdown, no backticks, pure JSON only
"""


def get_schema_context() -> str:
    from google.cloud import bigquery
    client = bigquery.Client()
    lines = []
    for table_name in ALLOWED_TABLES:
        table_ref = f"{config.project_id}.dataset_marts.{table_name}"
        try:
            table = client.get_table(table_ref)
            lines.append(f"Table: {table_name}")
            for field in table.schema:
                desc = f" -- {field.description}" if field.description else ""
                lines.append(f"  {field.name} ({field.field_type}){desc}")
            lines.append("")
        except Exception as e:
            lines.append(f"Table: {table_name} [unavailable: {e}]")
            lines.append("")
    return "\n".join(lines)


def check_pii(question: str) -> bool:
    for pattern in PII_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE):
            return True
    return False


def validate_sql(sql: str) -> tuple:
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{keyword}\b', sql_upper):
            return False, f"Forbidden keyword: {keyword}"
    tables_in_sql = re.findall(r'dataset_marts\.(\w+)', sql, re.IGNORECASE)
    for table in tables_in_sql:
        if table.lower() not in [t.lower() for t in ALLOWED_TABLES]:
            return False, f"Table not in allow-list: {table}"
    return True, ""


def log_query(question: str, sql: str, tables: list) -> None:
    try:
        from google.cloud import bigquery
        from datetime import datetime
        client = bigquery.Client()
        table_ref = f"{config.project_id}.dataset_raw.llm_audit_log"
        row = {
            "question": question,
            "generated_sql": sql,
            "tables_referenced": tables,
            "created_at": datetime.utcnow().isoformat(),
        }
        client.insert_rows_json(table_ref, [row])
    except Exception as e:
        print(f"Audit log warning (non-critical): {e}")


def ask(question: str) -> dict:
    if check_pii(question):
        return {"error": "Question contains personal data. Please rephrase."}

    # Ollama runs locally — no API key needed

    schema = get_schema_context()
    prompt = SYSTEM_PROMPT.format(
        project=config.project_id,
        schema=schema,
    ) + f"\n\nQuestion: {question}"



    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 800,
        },
    }

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        raw_text = data["response"]
    except Exception as e:
        return {"error": f"API call failed: {e}"}


    raw_text = raw_text.strip()
    raw_text = re.sub(r'^```json\s*', '', raw_text)
    raw_text = re.sub(r'\s*```$', '', raw_text)

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except Exception:
                return {"error": f"Failed to parse response: {raw_text[:300]}"}
        else:
            return {"error": f"No JSON in response: {raw_text[:300]}"}

    sql = result.get("sql", "")
    is_valid, error_msg = validate_sql(sql)
    if not is_valid:
        return {"error": f"SQL validation failed: {error_msg}"}

    log_query(question, sql, result.get("tables_used", []))
    return result


if __name__ == "__main__":
    print("E-Commerce Analytics NL->SQL Assistant (Gemini)")
    print("Ask questions in Russian, English, or Spanish.")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            question = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        print("\nGenerating SQL...\n")
        result = ask(question)

        if "error" in result:
            print(f"Error: {result['error']}\n")
        else:
            print(f"SQL:\n{result['sql']}\n")
            print(f"Explanation: {result['explanation']}\n")
            print(f"Tables: {', '.join(result.get('tables_used', []))}\n")
            print("-" * 60 + "\n")
