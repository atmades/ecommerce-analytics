/*
  mart_sellers — витрина продавцов.

  Grain: один продавец.

  Используется для: рейтинговой системы, работы с продавцами,
  выявления проблемных продавцов (медленная доставка, низкие оценки).
*/

with sellers as (
    select * from {{ ref('stg_sellers') }}
),

items as (
    select * from {{ ref('int_order_items_enriched') }}
),

orders as (
    select * from {{ ref('int_orders_enriched') }}
    where order_status = 'delivered'
),

-- Считаем категории отдельно — чисто, без риска дублей
seller_categories as (
    select
        seller_id,
        count(distinct category_name_en) as categories_count
    from items
    group by seller_id
),

-- Метрики продаж
seller_sales as (
    select
        seller_id,
        count(distinct order_id)     as total_orders,
        count(distinct product_id)   as unique_products,
        sum(price_brl)                as total_revenue_brl,
        avg(price_brl)                as avg_item_price_brl
    from items
    group by seller_id
),

-- Метрики доставки — джойним items с orders чтобы получить delivery данные
seller_delivery as (
    select
        i.seller_id,
        avg(o.actual_delivery_days)   as avg_delivery_days,
        countif(o.is_on_time = true) / nullif(count(o.is_on_time), 0) * 100
                                        as on_time_delivery_rate_pct
    from items i
    inner join orders o using (order_id)
    group by i.seller_id
),

-- Отзывы
seller_reviews as (
    select
        i.seller_id,
        avg(r.score)         as avg_review_score,
        count(r.score)        as reviews_count
    from items i
    inner join {{ ref('stg_reviews') }} r using (order_id)
    group by i.seller_id
),

final as (
    select
        s.seller_id,
        s.city                 as seller_city,
        s.state                as seller_state,

        sa.total_orders,
        sa.unique_products,
        c.categories_count,
        round(sa.total_revenue_brl, 2)       as total_revenue_brl,
        round(sa.avg_item_price_brl, 2)      as avg_item_price_brl,

        round(d.avg_delivery_days, 1)        as avg_delivery_days,
        round(d.on_time_delivery_rate_pct, 2) as on_time_delivery_rate_pct,

        round(r.avg_review_score, 2)         as avg_review_score,
        r.reviews_count

    from sellers s
    inner join seller_sales sa     using (seller_id)
    left join seller_categories c  using (seller_id)
    left join seller_delivery d    using (seller_id)
    left join seller_reviews r     using (seller_id)
)

select * from final
