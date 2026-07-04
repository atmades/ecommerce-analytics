-- Daily order volume must not drop more than 30% below 7-day average
-- Catches pipeline failures or data loading issues

with daily_counts as (
    select
        order_date,
        count(*) as order_count,
        avg(count(*)) over (
            order by order_date
            rows between 7 preceding and 1 preceding
        ) as avg_last_7_days
    from {{ ref('mart_sales') }}
    group by order_date
)

select order_date
from daily_counts
where order_date = current_date()
  and order_count < avg_last_7_days * 0.7
