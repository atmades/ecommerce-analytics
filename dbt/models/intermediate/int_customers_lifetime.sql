/*
  int_customers_lifetime — агрегированные метрики клиента за всё время.

  customer_unique_id — настоящий ID клиента (один клиент может иметь
  несколько customer_id если делал заказы с разных аккаунтов).
  Используем customer_unique_id для корректного подсчёта LTV.
*/

with orders as (
    select * from {{ ref('int_orders_enriched') }}
    where order_status = 'delivered'
),

lifetime as (
    select
        customer_unique_id,

        -- Активность
        count(distinct order_id)          as total_orders,
        min(order_date)                   as first_order_date,
        max(order_date)                   as last_order_date,
        date_diff(
            max(order_date),
            min(order_date),
            day
        )                                 as customer_age_days,

        -- Финансы
        sum(total_payment_brl)            as ltv_brl,
        avg(total_payment_brl)            as avg_order_value_brl,

        -- Последний заказ
        date_diff(
            current_date(),
            max(order_date),
            day
        )                                 as days_since_last_order

    from orders
    group by customer_unique_id
)

select * from lifetime
