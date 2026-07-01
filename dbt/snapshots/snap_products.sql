{% snapshot snap_products %}

{{
    config(
        target_schema='dataset_staging',
        unique_key='product_id',
        strategy='check',
        check_cols=['price_ars', 'status', 'category_id'],
        invalidate_hard_deletes=True,
    )
}}

select
    product_id,
    category_id,
    category_name,
    product_name,
    status,
    price_ars,
    currency,
    ingested_at
from {{ ref('stg_mercadolibre_products') }}

{% endsnapshot %}
