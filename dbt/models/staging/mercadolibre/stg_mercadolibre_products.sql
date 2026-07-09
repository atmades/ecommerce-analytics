with source as (
    select * from {{ source('mercadolibre', 'mercadolibre_products') }}
),

renamed as (
    select
        product_id,
        category_id,
        category_name,
        name                           as product_name,
        status,
        domain_id,
        min_price_ars                  as price_ars,
        currency,
        cast(ingested_at as timestamp) as ingested_at
    from source
)

select * from renamed
