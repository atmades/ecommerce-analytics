with source as (
    select * from {{ source('raw', 'sellers') }}
),

renamed as (
    select
        seller_id,
        seller_zip_code_prefix    as zip_code,
        seller_city               as city,
        seller_state              as state,
        current_timestamp()       as _loaded_at
    from source
)

select * from renamed
