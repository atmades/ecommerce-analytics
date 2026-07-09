-- SCD Type 2 integrity: no overlapping valid periods for same product
-- Catches snapshot logic errors

with periods as (
    select
        product_id,
        dbt_scd_id,
        dbt_valid_from,
        coalesce(dbt_valid_to, '9999-12-31') as dbt_valid_to
    from {{ ref('snap_products') }}
)

select a.product_id
from periods a
join periods b
  on a.product_id = b.product_id
  and a.dbt_scd_id != b.dbt_scd_id
  and a.dbt_valid_from < b.dbt_valid_to
  and a.dbt_valid_to > b.dbt_valid_from
