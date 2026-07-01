/*
  dim_date — calendar dimension table.

  Grain: one row per day (2016-01-01 to 2030-12-31).

  Why we need this:
  - Avoid repeating DATE_TRUNC / EXTRACT logic in every mart model
  - Enables easy filtering by fiscal periods, weekends, holidays
  - JOIN target for mart_sales, mart_cohorts, mart_price_history

  Brazilian holidays: for Olist data (2016-2018)
  Argentine holidays: for MercadoLibre data
*/

{{ config(materialized='table') }}

with date_spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2016-01-01' as date)",
        end_date="cast('2030-12-31' as date)"
    ) }}
),

dates as (
    select
        cast(date_day as date)              as date_day,

        -- Basic attributes
        extract(year from date_day)         as year,
        extract(quarter from date_day)      as quarter,
        extract(month from date_day)        as month,
        format_date('%B', date_day)         as month_name,
        format_date('%b', date_day)         as month_name_short,
        extract(week from date_day)         as week_of_year,
        extract(dayofweek from date_day)    as day_of_week,
        format_date('%A', date_day)         as day_name,
        format_date('%a', date_day)         as day_name_short,
        extract(day from date_day)          as day_of_month,
        extract(dayofyear from date_day)    as day_of_year,

        -- Flags
        extract(dayofweek from date_day) in (1, 7) as is_weekend,
        date_day = date_trunc(date_day, month)     as is_first_day_of_month,
        date_day = last_day(date_day)              as is_last_day_of_month,

        -- Quarter label
        concat(
            'Q', extract(quarter from date_day),
            ' ', extract(year from date_day)
        )                                   as quarter_label,

        -- Month label
        concat(
            format_date('%b', date_day), ' ',
            extract(year from date_day)
        )                                   as month_label,

        -- Brazilian public holidays (fixed dates only)
        -- Carnival and Easter are floating — excluded intentionally
        date_day in (
            -- New Year
            date(extract(year from date_day), 1, 1),
            -- Tiradentes
            date(extract(year from date_day), 4, 21),
            -- Labour Day
            date(extract(year from date_day), 5, 1),
            -- Independence Day BR
            date(extract(year from date_day), 9, 7),
            -- Our Lady of Aparecida
            date(extract(year from date_day), 10, 12),
            -- All Souls Day
            date(extract(year from date_day), 11, 2),
            -- Republic Day
            date(extract(year from date_day), 11, 15),
            -- Christmas
            date(extract(year from date_day), 12, 25)
        )                                   as is_holiday_br,

        -- Argentine public holidays (fixed dates only)
        date_day in (
            -- New Year
            date(extract(year from date_day), 1, 1),
            -- National Memory Day
            date(extract(year from date_day), 3, 24),
            -- Malvinas Veterans Day
            date(extract(year from date_day), 4, 2),
            -- Labour Day
            date(extract(year from date_day), 5, 1),
            -- May Revolution
            date(extract(year from date_day), 5, 25),
            -- Flag Day
            date(extract(year from date_day), 6, 20),
            -- Independence Day AR
            date(extract(year from date_day), 7, 9),
            -- Immaculate Conception
            date(extract(year from date_day), 12, 8),
            -- Christmas
            date(extract(year from date_day), 12, 25)
        )                                   as is_holiday_ar,

        -- Is business day (not weekend, not BR holiday)
        not (
            extract(dayofweek from date_day) in (1, 7)
            or date_day in (
                date(extract(year from date_day), 1, 1),
                date(extract(year from date_day), 4, 21),
                date(extract(year from date_day), 5, 1),
                date(extract(year from date_day), 9, 7),
                date(extract(year from date_day), 10, 12),
                date(extract(year from date_day), 11, 2),
                date(extract(year from date_day), 11, 15),
                date(extract(year from date_day), 12, 25)
            )
        )                                   as is_business_day_br

    from date_spine
)

select * from dates
