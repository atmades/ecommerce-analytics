{% snapshot snap_products %}

{{
    config(
        target_schema='dataset_staging',
        unique_key='product_id',
        strategy='check',
        check_cols=['category_name_pt', 'weight_g'],
        invalidate_hard_deletes=True,
    )
}}

select
    product_id,
    category_name_pt,
    weight_g
from {{ ref('stg_products') }}

{% endsnapshot %}
