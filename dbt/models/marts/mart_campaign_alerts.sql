with current_campaign_metrics as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        campaign_status,
        metric_date,
        run_date,
        spend_amount,
        budget_amount,
        currency_code,
        month_to_date_spend,
        expected_spend_to_date,
        projected_month_end_spend,
        month_to_date_net_revenue,
        month_to_date_roas,
        pacing_ratio,
        has_post_end_spend,
        is_projected_to_exceed_budget,
        pacing_status
    from {{ ref('mart_campaign_daily_pacing') }}
    where metric_date = run_date

),

alerts as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        campaign_status,
        metric_date as alert_date,
        pacing_status as alert_severity,

        case
            when has_post_end_spend then 'Spend recorded after campaign end date'
            when budget_amount is null then 'Spend recorded without an active budget'
            when month_to_date_spend > budget_amount then 'Monthly budget exceeded'
            when pacing_ratio > 1.10 then 'Campaign pacing is above 110%'
            else 'Review required'
        end as alert_reason,

        case
            when pacing_status = 'critical' then 1
            when pacing_status = 'warning' then 2
            else 3
        end as alert_priority,

        currency_code,
        spend_amount,
        budget_amount,
        month_to_date_spend,
        expected_spend_to_date,
        projected_month_end_spend,
        month_to_date_net_revenue,
        month_to_date_roas,
        pacing_ratio,
        has_post_end_spend,
        is_projected_to_exceed_budget
    from current_campaign_metrics
    where pacing_status in ('warning', 'critical')

)

select
    campaign_id,
    campaign_name,
    channel,
    objective,
    campaign_status,
    alert_date,
    alert_severity,
    alert_reason,
    alert_priority,
    currency_code,
    spend_amount,
    budget_amount,
    month_to_date_spend,
    expected_spend_to_date,
    projected_month_end_spend,
    month_to_date_net_revenue,
    month_to_date_roas,
    pacing_ratio,
    has_post_end_spend,
    is_projected_to_exceed_budget
from alerts