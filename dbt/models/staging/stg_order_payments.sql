with source as (
    select * from {{ source('raw', 'order_payments') }}
),

renamed as (
    select
        order_id,
        payment_sequential,
        payment_type,
        payment_installments      as installments,
        payment_value             as payment_brl,
        current_timestamp()       as _loaded_at
    from source
)

select * from renamed
