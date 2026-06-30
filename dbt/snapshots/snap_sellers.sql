{% snapshot snap_sellers %}

{{
    config(
        target_schema='dataset_staging',
        unique_key='seller_id',
        strategy='check',
        check_cols=['city', 'state'],
        invalidate_hard_deletes=True,
    )
}}

select
    seller_id,
    city,
    state
from {{ ref('stg_sellers') }}

{% endsnapshot %}
