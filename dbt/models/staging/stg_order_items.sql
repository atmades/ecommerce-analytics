with source as (
    select * from {{ source('raw', 'order_items') }}
),

renamed as (
    select
        order_id,
        order_item_id,
        product_id,
        seller_id,
        shipping_limit_date       as shipping_limit_at,
        price                     as price_brl,
        freight_value             as freight_brl,
        price + freight_value     as total_brl,
        current_timestamp()       as _loaded_at
    from source
)

select * from renamed
