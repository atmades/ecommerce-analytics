# ADR-002: dbt Core for Transformations

**Status:** Accepted  
**Date:** 2026-06

## Context

Raw data in BigQuery needs to be transformed into analytics-ready tables.
Two main approaches: SQL-based transformation tools (dbt) or Python scripts.

## Decision

Use **dbt Core** for all transformations.

## Consequences

**Positive:**
- Declarative SQL — transformations are readable and reviewable
- Built-in testing framework (not_null, unique, relationships, custom)
- Automatic data lineage graph — visualize dependencies between models
- `ref()` macro handles dependency ordering automatically
- Industry standard — widely used in production DE teams
- dbt docs generate self-documenting data catalog

**Negative:**
- SQL-only — complex ML feature engineering better done in Python
- dbt Core lacks some dbt Cloud features (semantic layer, CI artifacts)
- Learning curve for Jinja templating and dbt-specific patterns

## Alternatives Considered

**Pure Python (pandas/polars):** More flexible, but no built-in testing, no lineage, no documentation generation. Harder to maintain and review.

**Spark:** Overkill for this dataset size (~100k rows). Adds significant infrastructure complexity.

**SQLMesh:** Newer alternative to dbt with better state management. Less mature ecosystem and fewer resources for learning.