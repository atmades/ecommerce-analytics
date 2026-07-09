# Business Glossary

Canonical definitions for all business terms used in this platform.
When in doubt — use these definitions, not ad-hoc interpretations.

---

## Active Customer
A customer who placed at least one **delivered** order in the last 365 days.
Field: `mart_customers.last_order_date >= CURRENT_DATE - 365`

## Gross Revenue
Sum of `price + freight_value` across all items in a **delivered** order.
Returns and cancellations are NOT deducted (this is gross, not net).
Currency: BRL (Brazilian Reais) unless specified otherwise.
Field: `mart_sales.total_payment_brl`

## Net Revenue
Gross Revenue minus returns and refunds.
**Not implemented** in current version — no returns data in Olist dataset.

## Lifetime Value (LTV)
Total gross revenue from a customer since their first order.
Uses `customer_unique_id` (not `customer_id`) to correctly identify
unique individuals — one person may have multiple customer_ids in Olist.
Field: `mart_customers.ltv_brl`

## RFM Segment
Customer classification based on three axes:
- **R (Recency):** days since last order. Score 1-4, higher = more recent.
- **F (Frequency):** number of orders. Score 1-4, higher = more orders.
- **M (Monetary):** total spend. Score 1-4, higher = more spent.

Segments:
| Segment | Definition |
|---------|-----------|
| `champion` | R≥4, F≥3, M≥3 — best customers |
| `loyal` | F≥3, M≥3 — regular high-value customers |
| `at_risk` | R≤2, F≥3 — used to be active, now quiet |
| `hibernating` | R≤2, F≤2 — low activity, low value |
| `new` | R≥3, F≤2 — recently acquired |
| `lost` | everything else |

## Cohort
Group of customers who placed their **first** order in the same calendar month.
Example: "January 2017 cohort" = all customers whose first order was in Jan 2017.
Field: `mart_cohorts.cohort_month`

## Retention Rate
Percentage of customers from a cohort who placed an order in a given month.
Formula: `retained_customers / cohort_size * 100`
Month 0 = always 100% (the cohort definition month itself).
Field: `mart_cohorts.retention_rate_pct`

## On-Time Delivery
An order is considered on-time if:
`order_delivered_customer_date <= order_estimated_delivery_date`
Orders not yet delivered have `is_on_time = NULL` (not false).
Field: `mart_sales.is_on_time`, `mart_sellers.on_time_delivery_rate_pct`

## Seller Status (MercadoLibre)
| Status | Description |
|--------|-------------|
| `platinum` | Top sellers, >99% positive reviews |
| `gold` | >97% positive reviews |
| `silver` | >95% positive reviews |
| `bronze` | Basic level |
| `new` | Less than 10 sales |

## Price Period (SCD Type 2)
A contiguous time range during which a product's price remained unchanged.
`dbt_valid_from` = when this price became active
`dbt_valid_to` = when this price was replaced (NULL = currently active)
Source: `snap_products` snapshot, built into `mart_price_history`