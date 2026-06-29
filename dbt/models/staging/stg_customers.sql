with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix  as zip_code,
        customer_city             as city,
        customer_state            as state,
        current_timestamp()       as _loaded_at
    from source
)

select * from renamed
