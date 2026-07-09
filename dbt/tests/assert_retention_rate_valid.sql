-- Retention rate must be between 0 and 100
-- Catches calculation errors in cohort model

select cohort_month, months_since_first_order, retention_rate_pct
from {{ ref('mart_cohorts') }}
where retention_rate_pct < 0
   or retention_rate_pct > 100
