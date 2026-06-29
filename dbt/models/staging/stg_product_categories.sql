with source as (
    select * from {{ source('raw', 'product_categories') }}
),

renamed as (
    select
        product_category_name                as category_name_pt,
        product_category_name_english        as category_name_en,
        current_timestamp()                  as _loaded_at
    from source
)

select * from renamed
