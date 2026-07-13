/*
  mart_customer_features — feature store for ML models.

  Grain: one unique customer (customer_unique_id).

  Used by: churn prediction, LTV forecasting, customer segmentation ML models.

  Design principles:
  - All features are numeric or binary (ML-ready)
  - No PII fields (customer_unique_id is a hash, not identifying)
  - Features computed from history only (no future data leakage)
  - Target variable: is_churned (days_since_last_order > 365)
*/

with orders as (
    select * from {{ ref('int_orders_enriched') }}
    where order_status = 'delivered'
),

customers as (
    select * from {{ ref('int_customers_lifetime') }}
),

-- Per-customer order statistics
order_stats as (
    select
        customer_unique_id,

        -- Basket features
        max(total_payment_brl)          as max_order_value_brl,
        min(total_payment_brl)          as min_order_value_brl,
        stddev(total_payment_brl)       as stddev_order_value_brl,

        -- Delivery features
        avg(actual_delivery_days)       as avg_delivery_days,
        countif(is_on_time = true)      as on_time_orders,
        countif(is_on_time = false)     as late_orders,

        -- Payment features
        countif(primary_payment_type = 'credit_card')   as credit_card_orders,
        countif(primary_payment_type = 'boleto')        as boleto_orders,
        countif(primary_payment_type = 'voucher')       as voucher_orders,

        -- Geographic diversity (how many different states ordered from)
        count(distinct customer_state)  as states_ordered_from

    from orders
    group by customer_unique_id
),

-- Category diversity
category_stats as (
    select
        o.customer_unique_id,
        count(distinct i.primary_category) as unique_categories_count
    from orders o
    left join {{ ref('mart_sales') }} i using (order_id)
    group by o.customer_unique_id
),

-- Review behavior
review_stats as (
    select
        o.customer_unique_id,
        avg(r.score)        as avg_review_score,
        count(r.score)      as reviews_count,
        countif(r.score = 5) as five_star_reviews,
        countif(r.score <= 2) as low_score_reviews
    from orders o
    left join {{ ref('stg_reviews') }} r using (order_id)
    group by o.customer_unique_id
),

final as (
    select
        -- Key (not a feature — excluded from model training)
        c.customer_unique_id,

        -- ── Recency features ──────────────────────────────────
        c.days_since_last_order,
        date_diff(current_date(), c.first_order_date, day)  as days_since_first_order,

        -- ── Frequency features ────────────────────────────────
        c.total_orders,
        safe_divide(
            c.total_orders,
            nullif(c.customer_age_days, 0)
        ) * 30                                               as orders_per_month,
        safe_divide(
            c.customer_age_days,
            nullif(c.total_orders - 1, 0)
        )                                                    as avg_days_between_orders,

        -- ── Monetary features ─────────────────────────────────
        c.ltv_brl,
        c.avg_order_value_brl,
        os.max_order_value_brl,
        os.min_order_value_brl,
        coalesce(os.stddev_order_value_brl, 0)              as stddev_order_value_brl,

        -- ── Quality features ──────────────────────────────────
        coalesce(rs.avg_review_score, 0)                    as avg_review_score,
        coalesce(rs.reviews_count, 0)                       as reviews_count,
        coalesce(rs.five_star_reviews, 0)                   as five_star_reviews,
        coalesce(rs.low_score_reviews, 0)                   as low_score_reviews,

        -- ── Delivery features ─────────────────────────────────
        coalesce(os.avg_delivery_days, 0)                   as avg_delivery_days,
        coalesce(os.on_time_orders, 0)                      as on_time_orders,
        coalesce(os.late_orders, 0)                         as late_orders,
        safe_divide(
            coalesce(os.on_time_orders, 0),
            nullif(c.total_orders, 0)
        )                                                    as on_time_rate,

        -- ── Payment behavior features ─────────────────────────
        coalesce(os.credit_card_orders, 0)                  as credit_card_orders,
        coalesce(os.boleto_orders, 0)                       as boleto_orders,
        coalesce(os.voucher_orders, 0)                      as voucher_orders,

        -- ── Diversity features ────────────────────────────────
        coalesce(cs.unique_categories_count, 0)             as unique_categories_count,
        coalesce(os.states_ordered_from, 0)                 as states_ordered_from,

        -- ── RFM scores (already numeric 1-4) ─────────────────
        -- from mart_customers via int_customers_lifetime

        -- ── Target variable ───────────────────────────────────
        -- Churn definition: no order in last 365 days
        case
            when c.days_since_last_order > 365 then 1
            else 0
        end                                                  as is_churned,

        -- Soft churn: no order in last 180 days
        case
            when c.days_since_last_order > 180 then 1
            else 0
        end                                                  as is_at_risk

    from customers c
    left join order_stats os    using (customer_unique_id)
    left join category_stats cs using (customer_unique_id)
    left join review_stats rs   using (customer_unique_id)
)

select * from final