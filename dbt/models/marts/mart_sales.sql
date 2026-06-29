/*
  mart_sales — витрина продаж.

  Grain: один заказ (одна строка = один заказ).
  Используется для: выручка по дням/категориям/регионам, операционные отчёты.
*/

with orders as (
    select * from {{ ref('int_orders_enriched') }}
    where order_status = 'delivered'   -- только завершённые заказы
),

items as (
    select
        order_id,
        sum(price_brl)              as items_value_brl,
        sum(freight_brl)            as freight_value_brl,
        sum(total_brl)              as total_items_brl,
        count(distinct product_id)  as unique_products,
        max(category_name_en)       as primary_category
    from {{ ref('int_order_items_enriched') }}
    group by order_id
),

reviews as (
    select
        order_id,
        score                       as review_score
    from {{ ref('stg_reviews') }}
),

final as (
    select
        -- Ключи
        o.order_id,
        o.customer_id,
        o.customer_unique_id,

        -- Время
        o.order_date,
        o.purchased_at,
        o.delivered_to_customer_at,

        -- География
        o.customer_city,
        o.customer_state,

        -- Категория
        i.primary_category,

        -- Финансы
        i.items_value_brl,
        i.freight_value_brl,
        o.total_payment_brl,

        -- Корзина
        i.unique_products,

        -- Доставка
        o.actual_delivery_days,
        o.estimated_delivery_days,
        o.is_on_time,

        -- Оценка
        r.review_score,

        -- Платёж
        o.primary_payment_type

    from orders o
    left join items i   using (order_id)
    left join reviews r using (order_id)
)

select * from final
