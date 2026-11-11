select
    campaign_id,
    metric_date,
    attributed_gross_revenue,
    attributed_refund_amount,
    attributed_net_revenue

from {{ ref('fct_campaign_daily_performance') }}

where attributed_net_revenue
    <> (
        attributed_gross_revenue
        - attributed_refund_amount
    )