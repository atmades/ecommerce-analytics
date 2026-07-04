/*
  mart_sales — sales fact table.
  Grain: one delivered order.
*/

with orders as (
    select * from {{ ref('int_orders_enriched') }}
    where order_status = 'delivered'
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

-- Агрегируем reviews ДО JOIN — берём среднюю оценку если отзывов несколько
reviews as (
    select
        order_id,
        round(avg(score), 1)  as review_score,
        count(*)               as review_count
    from {{ ref('stg_reviews') }}
    group by order_id
),

final as (
    select
        o.order_id,
        o.customer_id,
        o.customer_unique_id,
        o.order_date,
        o.purchased_at,
        o.delivered_to_customer_at,
        o.customer_city,
        o.customer_state,
        i.primary_category,
        i.items_value_brl,
        i.freight_value_brl,
        o.total_payment_brl,
        i.unique_products,
        o.actual_delivery_days,
        o.estimated_delivery_days,
        o.is_on_time,
        r.review_score,
        r.review_count,
        o.primary_payment_type

    from orders o
    left join items i   using (order_id)
    left join reviews r using (order_id)
)

select * from final
