# ADR-001: BigQuery as Data Warehouse

**Status:** Accepted  
**Date:** 2026-06

## Context

The project needs a cloud data warehouse to store and query analytics data.
Main candidates: BigQuery (Google), Snowflake, Redshift (AWS), DuckDB (local).

## Decision

Use **Google BigQuery**.

## Consequences

**Positive:**
- Free tier: 10 GB storage + 1 TB queries/month — sufficient for this project
- Native integration with GCS (no COPY commands, direct URI loading)
- Columnar storage with automatic partitioning and clustering
- `dbt-bigquery` adapter is mature and well-maintained
- Most common warehouse in Latin American job market (relevant given Olist/MercadoLibre data sources)

**Negative:**
- Vendor lock-in to GCP ecosystem
- Cost can escalate on large unoptimized queries (mitigated by partitioning)
- Requires GCP account setup (barrier for new contributors)

## Alternatives Considered

**Snowflake:** Better multi-cloud support, but no free tier — requires credit card and costs money from day one.

**Redshift:** AWS ecosystem, good performance, but free trial limited to 2 months. GCS integration requires additional tooling.

**DuckDB:** Excellent for local development, truly free, but not a cloud warehouse. Doesn't demonstrate production cloud skills.