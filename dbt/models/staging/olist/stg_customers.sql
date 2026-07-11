with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        customer_id,
        customer_unique_id,

        -- PII masking: zip prefix partially masked (first 3 digits only)
        -- city and state are not PII in this context — they are aggregated
        -- geographic attributes, not individually identifying information
        {{ mask_zip('customer_zip_code_prefix') }} as zip_code_masked,
        customer_zip_code_prefix                   as zip_code_raw,

        customer_city   as city,
        customer_state  as state,

        current_timestamp() as _loaded_at
    from source
)

select * from renamed