/*
  mart_cohorts — когортный retention анализ.

  Grain: cohort_month × activity_month (одна строка на пересечение).

  Логика:
  1. Определяем когорту каждого клиента — месяц его ПЕРВОГО заказа
  2. Смотрим в какие месяцы после этого клиент возвращался
  3. Считаем retention_rate — % клиентов когорты, которые были активны в данном месяце

  Используется для: продуктовых решений, оценки эффективности retention-кампаний.
*/

with orders as (
    select
        customer_unique_id,
        order_date
    from {{ ref('int_orders_enriched') }}
    where order_status = 'delivered'
),

-- Шаг 1: определяем когорту — месяц первого заказа клиента
customer_cohorts as (
    select
        customer_unique_id,
        date_trunc(min(order_date), month) as cohort_month
    from orders
    group by customer_unique_id
),

-- Шаг 2: для каждого заказа считаем "номер месяца активности" относительно когорты
order_activity as (
    select
        o.customer_unique_id,
        c.cohort_month,
        date_trunc(o.order_date, month) as activity_month,

        -- Сколько месяцев прошло с первого заказа: 0, 1, 2, 3...
        date_diff(
            date_trunc(o.order_date, month),
            c.cohort_month,
            month
        ) as months_since_first_order

    from orders o
    inner join customer_cohorts c using (customer_unique_id)
),

-- Шаг 3: размер каждой когорты (сколько клиентов в ней изначально)
cohort_sizes as (
    select
        cohort_month,
        count(distinct customer_unique_id) as cohort_size
    from customer_cohorts
    group by cohort_month
),

-- Шаг 4: сколько уникальных клиентов когорты было активно в каждый месяц
retention as (
    select
        cohort_month,
        months_since_first_order,
        count(distinct customer_unique_id) as retained_customers
    from order_activity
    group by cohort_month, months_since_first_order
),

final as (
    select
        r.cohort_month,
        r.months_since_first_order,
        s.cohort_size,
        r.retained_customers,
        round(r.retained_customers / s.cohort_size * 100, 2) as retention_rate_pct

    from retention r
    inner join cohort_sizes s using (cohort_month)

    -- Ограничиваем 12 месяцами — дальше данных и так мало
    where r.months_since_first_order between 0 and 12
)

select * from final
order by cohort_month, months_since_first_order
