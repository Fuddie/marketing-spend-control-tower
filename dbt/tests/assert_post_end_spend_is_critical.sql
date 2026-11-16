select
    campaign_id,
    metric_date,
    end_date,
    spend_amount,
    pacing_status
from {{ ref('mart_campaign_daily_pacing') }}
where has_post_end_spend
    and coalesce(pacing_status, '') <> 'critical'
