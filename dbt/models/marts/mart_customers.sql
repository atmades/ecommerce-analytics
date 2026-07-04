/*
  mart_customers — витрина клиентов.

  Grain: один уникальный клиент (customer_unique_id).

  Используется для:
  - RFM-сегментации и маркетинговых кампаний
  - Расчёта LTV
  - Анализа оттока (churn)

  Важно: используем customer_unique_id, не customer_id.
  Один реальный человек может иметь несколько customer_id в Olist.
*/

with customers as (
    select * from {{ ref('int_customers_lifetime') }}
),

-- RFM scoring: делим клиентов на квантили по каждой оси
rfm_scores as (
    select
        customer_unique_id,
        total_orders,
        first_order_date,
        last_order_date,
        customer_age_days,
        ltv_brl,
        avg_order_value_brl,
        days_since_last_order,

        -- R score: чем меньше дней — тем выше балл (1-4)
        ntile(4) over (order by days_since_last_order desc) as r_score,

        -- F score: чем больше заказов — тем выше балл
        ntile(4) over (order by total_orders asc)           as f_score,

        -- M score: чем больше потратил — тем выше балл
        ntile(4) over (order by ltv_brl asc)                as m_score

    from customers
),

-- RFM сегментация на основе комбинации баллов
segmented as (
    select
        *,
        r_score + f_score + m_score as rfm_total,

        case
            -- Champions: покупают часто, недавно, тратят много
            when r_score = 4 and f_score >= 3 and m_score >= 3
                then 'champion'
            -- Loyal: регулярные клиенты с хорошим LTV
            when f_score >= 3 and m_score >= 3
                then 'loyal'
            -- At risk: раньше были активны, давно не покупали
            when r_score <= 2 and f_score >= 3
                then 'at_risk'
            -- Hibernating: мало заказов, давно не покупали
            when r_score <= 2 and f_score <= 2
                then 'hibernating'
            -- New: недавно пришли, мало заказов
            when r_score >= 3 and f_score <= 2
                then 'new'
            -- Lost: всё плохо
            else 'lost'
        end as rfm_segment

    from rfm_scores
),

-- Добавляем среднюю оценку отзывов клиента
reviews as (
    select
        o.customer_unique_id,
        round(avg(r.score), 2) as avg_review_score,
        count(r.score)         as reviews_count
    from {{ ref('int_orders_enriched') }} o
    left join {{ ref('stg_reviews') }} r using (order_id)
    where r.score is not null
    group by o.customer_unique_id
),

final as (
    select
        -- Ключ
        s.customer_unique_id,

        -- Временные метрики
        s.first_order_date,
        s.last_order_date,
        s.customer_age_days,
        s.days_since_last_order,

        -- Финансы
        s.total_orders,
        coalesce(round(s.ltv_brl, 2), 0) as ltv_brl,
        round(s.avg_order_value_brl, 2) as avg_order_value_brl,

        -- RFM
        s.r_score,
        s.f_score,
        s.m_score,
        s.rfm_total,
        s.rfm_segment,

        -- Отзывы
        r.avg_review_score,
        r.reviews_count

    from segmented s
    left join reviews r using (customer_unique_id)
)

select * from final
