/*
  stg_orders — staging модель для заказов.

  Что делаем здесь:
  - Переименовываем колонки в единый стиль
  - Приводим типы (TIMESTAMP уже правильный — задали в схеме BQ)
  - Добавляем _loaded_at для отслеживания свежести данных

  Чего НЕ делаем здесь:
  - Никаких JOIN с другими таблицами
  - Никакой бизнес-логики (расчёт дней доставки — это intermediate)
  - Никаких агрегаций
*/

with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        -- Идентификаторы
        order_id,
        customer_id,

        -- Статус
        order_status,

        -- Временные метки (переименовываем для единообразия)
        order_purchase_timestamp as purchased_at,
        order_approved_at as approved_at,
        order_delivered_carrier_date  as delivered_to_carrier_at,
        order_delivered_customer_date as delivered_to_customer_at,
        order_estimated_delivery_date as estimated_delivery_at,

        -- Технические поля
        current_timestamp()        as _loaded_at

    from source
)

select * from renamed
