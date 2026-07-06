FROM apache/airflow:2.9.0

USER root
RUN apt-get update && apt-get install -y git && apt-get clean

USER airflow
RUN pip install --no-cache-dir \
    "dbt-bigquery==1.8.0" \
    "dbt-core==1.8.0" \
    "google-cloud-bigquery>=3.0,<4.0" \
    "google-cloud-storage>=2.4,<3.0" \
    "google-cloud-secret-manager" \
    requests \
    tenacity \
    python-dotenv

RUN mkdir -p /home/airflow/.dbt && cat > /home/airflow/.dbt/profiles.yml << 'EOF'
ecommerce_analytics:
  target: prod
  outputs:
    prod:
      type: bigquery
      method: service-account
      project: "{{ env_var('GCP_PROJECT_ID') }}"
      dataset: dataset_staging
      keyfile: /opt/airflow/secrets/ecommerce-sa.json
      location: US
      threads: 4
      timeout_seconds: 300
EOF