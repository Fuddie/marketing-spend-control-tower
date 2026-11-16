select
    campaign_id,
    metric_date,
    count(*) as row_count
from {{ ref('fct_campaign_daily_performance') }}
group by
    campaign_id,
    metric_date
having count(*) > 1
