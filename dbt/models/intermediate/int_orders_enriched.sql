/*
  int_orders_enriched — заказы обогащённые данными клиента и метриками доставки.

  Здесь считаем производные поля которые нужны нескольким mart-моделям.
  Считаем один раз здесь — переиспользуем везде.
*/

with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

payments as (
    select
        order_id,
        sum(payment_brl) as total_payment_brl,
        count(*)  as payment_count,
        max(payment_type)  as primary_payment_type
    from {{ ref('stg_order_payments') }}
    group by order_id
),

enriched as (
    select
        -- Идентификаторы
        o.order_id,
        o.customer_id,
        c.customer_unique_id,

        -- Статус и временные метки
        o.order_status,
        o.purchased_at,
        o.approved_at,
        o.delivered_to_carrier_at,
        o.delivered_to_customer_at,
        o.estimated_delivery_at,

        -- География клиента
        c.city as customer_city,
        c.state as customer_state,

        -- Платежи
        coalesce(p.total_payment_brl, 0) as total_payment_brl,
        p.payment_count,
        p.primary_payment_type,

        -- Производные метрики доставки
        date_diff(
            date(o.delivered_to_customer_at),
            date(o.purchased_at),
            day
        ) as actual_delivery_days,

        date_diff(
            date(o.estimated_delivery_at),
            date(o.purchased_at),
            day
        ) as estimated_delivery_days,

        -- Доставлен вовремя?
        case
            when o.delivered_to_customer_at <= o.estimated_delivery_at then true
            when o.delivered_to_customer_at is null then null
            else false
        end as is_on_time,

        -- Дата заказа для партиционирования в marts
        date(o.purchased_at) as order_date

    from orders o
    left join customers c using (customer_id)
    left join payments p using (order_id)
)

select * from enriched
