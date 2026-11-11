with daily_performance as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        start_date,
        end_date,
        campaign_status,
        metric_date,
        run_date,
        spend_amount,
        impressions,
        clicks,
        platform_conversions,
        attributed_conversions,
        attributed_gross_revenue,
        attributed_refund_amount,
        attributed_net_revenue,
        budget_change_id,
        budget_amount,
        currency_code,
        active_days_in_budget_month,
        expected_daily_spend,
        has_post_end_spend

    from {{ ref('fct_campaign_daily_performance') }}

),

running_metrics as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        start_date,
        end_date,
        campaign_status,
        metric_date,
        run_date,
        spend_amount,
        impressions,
        clicks,
        platform_conversions,
        attributed_conversions,
        attributed_gross_revenue,
        attributed_refund_amount,
        attributed_net_revenue,
        budget_change_id,
        budget_amount,
        currency_code,
        active_days_in_budget_month,
        expected_daily_spend,
        has_post_end_spend,

        sum(spend_amount) over (
            partition by
                campaign_id,
                date_trunc('month', metric_date)
            order by metric_date
            rows between unbounded preceding
                and current row
        ) as month_to_date_spend,

        sum(attributed_net_revenue) over (
            partition by
                campaign_id,
                date_trunc('month', metric_date)
            order by metric_date
            rows between unbounded preceding
                and current row
        ) as month_to_date_net_revenue

    from daily_performance

),

elapsed_days as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        start_date,
        end_date,
        campaign_status,
        metric_date,
        run_date,
        spend_amount,
        impressions,
        clicks,
        platform_conversions,
        attributed_conversions,
        attributed_gross_revenue,
        attributed_refund_amount,
        attributed_net_revenue,
        budget_change_id,
        budget_amount,
        currency_code,
        active_days_in_budget_month,
        expected_daily_spend,
        has_post_end_spend,
        month_to_date_spend,
        month_to_date_net_revenue,

        case
            when metric_date < start_date then 0

            when metric_date > end_date
                then active_days_in_budget_month

            else date_diff(
                'day',
                greatest(
                    start_date,
                    cast(
                        date_trunc(
                            'month',
                            metric_date
                        ) as date
                    )
                ),
                metric_date
            ) + 1
        end as elapsed_active_days

    from running_metrics

),

calculated as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        start_date,
        end_date,
        campaign_status,
        metric_date,
        run_date,
        spend_amount,
        impressions,
        clicks,
        platform_conversions,
        attributed_conversions,
        attributed_gross_revenue,
        attributed_refund_amount,
        attributed_net_revenue,
        budget_change_id,
        budget_amount,
        currency_code,
        active_days_in_budget_month,
        elapsed_active_days,
        expected_daily_spend,
        has_post_end_spend,
        month_to_date_spend,
        month_to_date_net_revenue,

        cast(
            case
                when active_days_in_budget_month > 0
                    then (
                        budget_amount
                        / active_days_in_budget_month
                    ) * elapsed_active_days
                else 0
            end
            as decimal(18, 2)
        ) as expected_spend_to_date,

        cast(
            case
                when elapsed_active_days > 0
                    then (
                        month_to_date_spend
                        / elapsed_active_days
                    ) * active_days_in_budget_month
                else 0
            end
            as decimal(18, 2)
        ) as projected_month_end_spend,

        cast(
            case
                when spend_amount > 0
                    then attributed_net_revenue
                        / spend_amount
                else null
            end
            as decimal(18, 4)
        ) as daily_roas,

        cast(
            case
                when month_to_date_spend > 0
                    then month_to_date_net_revenue
                        / month_to_date_spend
                else null
            end
            as decimal(18, 4)
        ) as month_to_date_roas

    from elapsed_days

),

with_pacing as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        start_date,
        end_date,
        campaign_status,
        metric_date,
        run_date,
        spend_amount,
        impressions,
        clicks,
        platform_conversions,
        attributed_conversions,
        attributed_gross_revenue,
        attributed_refund_amount,
        attributed_net_revenue,
        budget_change_id,
        budget_amount,
        currency_code,
        active_days_in_budget_month,
        elapsed_active_days,
        expected_daily_spend,
        expected_spend_to_date,
        month_to_date_spend,
        projected_month_end_spend,
        month_to_date_net_revenue,
        daily_roas,
        month_to_date_roas,
        has_post_end_spend,

        cast(
            case
                when expected_spend_to_date > 0
                    then month_to_date_spend
                        / expected_spend_to_date
                else null
            end
            as decimal(18, 4)
        ) as pacing_ratio

    from calculated

)

select
    campaign_id,
    campaign_name,
    channel,
    objective,
    start_date,
    end_date,
    campaign_status,
    metric_date,
    run_date,
    spend_amount,
    impressions,
    clicks,
    platform_conversions,
    attributed_conversions,
    attributed_gross_revenue,
    attributed_refund_amount,
    attributed_net_revenue,
    budget_change_id,
    budget_amount,
    currency_code,
    active_days_in_budget_month,
    elapsed_active_days,
    expected_daily_spend,
    expected_spend_to_date,
    month_to_date_spend,
    projected_month_end_spend,
    month_to_date_net_revenue,
    daily_roas,
    month_to_date_roas,
    pacing_ratio,
    has_post_end_spend,

    projected_month_end_spend > budget_amount
        as is_projected_to_exceed_budget,

    case
        when has_post_end_spend
            then 'critical'

        when budget_amount is null
            and spend_amount > 0
            then 'critical'

        when month_to_date_spend > budget_amount
            then 'critical'

        when pacing_ratio > 1.10
            then 'warning'

        else 'normal'
    end as pacing_status

from with_pacing