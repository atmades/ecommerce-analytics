-- Delivery date must be after purchase date
-- Fails if customer received order before it was purchased (data quality issue)

select order_id
from {{ ref('mart_sales') }}
where delivered_to_customer_at < purchased_at
  and delivered_to_customer_at is not null
