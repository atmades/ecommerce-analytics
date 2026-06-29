/*
  int_order_items_enriched — позиции заказов с названиями категорий на английском.

  Переводим категории PT → EN здесь один раз.
  В mart_sales будем использовать category_name_en.
*/

with items as (
    select * from {{ ref('stg_order_items') }}
),

products as (
    select * from {{ ref('stg_products') }}
),

categories as (
    select * from {{ ref('stg_product_categories') }}
),

enriched as (
    select
        i.order_id,
        i.order_item_id,
        i.product_id,
        i.seller_id,
        i.shipping_limit_at,
        i.price_brl,
        i.freight_brl,
        i.total_brl,

        -- Атрибуты товара
        p.category_name_pt,
        coalesce(c.category_name_en, p.category_name_pt) as category_name_en,
        p.weight_g,
        p.photos_qty

    from items i
    left join products p using (product_id)
    left join categories c using (category_name_pt)
)

select * from enriched
