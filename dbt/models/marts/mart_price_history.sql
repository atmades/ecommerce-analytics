/*
  mart_price_history — price change history for MercadoLibre products.

  Grain: one row per product per price period (product_id + dbt_valid_from).

  Built on top of snap_products (SCD Type 2).
  Shows how prices change over time — direction, delta, duration.

  Used for: pricing analytics, competitor analysis, seasonal trends.
*/

with snapped as (
    select * from {{ ref('snap_products') }}
),

with_periods as (
    select
        product_id,
        category_id,
        category_name,
        product_name,
        status,
        price_ars,
        currency,

        -- Period boundaries
        cast(dbt_valid_from as date)    as valid_from,
        cast(dbt_valid_to as date)      as valid_to,
        dbt_valid_to is null            as is_current,

        -- How many days this price was active
        date_diff(
            coalesce(cast(dbt_valid_to as date), current_date()),
            cast(dbt_valid_from as date),
            day
        )                               as price_duration_days,

        -- Previous price for this product
        lag(price_ars) over (
            partition by product_id
            order by dbt_valid_from
        )                               as prev_price_ars,

        -- Version number (1 = first known price)
        row_number() over (
            partition by product_id
            order by dbt_valid_from
        )                               as price_version

    from snapped
),

final as (
    select
        product_id,
        category_id,
        category_name,
        product_name,
        status,
        price_ars,
        currency,
        valid_from,
        valid_to,
        is_current,
        price_duration_days,
        price_version,
        prev_price_ars,

        -- Price change metrics
        round(price_ars - coalesce(prev_price_ars, price_ars), 2)
                                        as price_delta_ars,

        round(
            (price_ars - coalesce(prev_price_ars, price_ars))
            / nullif(coalesce(prev_price_ars, price_ars), 0) * 100,
            2
        )                               as price_change_pct,

        case
            when prev_price_ars is null     then 'first_record'
            when price_ars > prev_price_ars then 'increase'
            when price_ars < prev_price_ars then 'decrease'
            else 'unchanged'
        end                             as price_change_direction

    from with_periods
)

select * from final
