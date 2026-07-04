-- Revenue must never be negative
-- Zero is allowed (voucher/promo orders)
-- Fails if any delivered order has negative total_payment_brl

select order_id
from {{ ref('mart_sales') }}
where total_payment_brl < 0
