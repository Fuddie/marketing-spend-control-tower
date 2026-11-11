with campaigns as (

    select
        campaign_id,
        campaign_name,
        channel,
        objective,
        start_date,
        end_date,
        campaign_status,
        extract_date

    from {{ ref('stg_campaigns') }}

),

run_control as (

    select
        max(extract_date) as run_date

    from campaigns

),

last_spend_dates as (

    select
        campaign_id,
        max(spend_date) as last_spend_date

    from {{ ref('stg_ad_spend_daily') }}

    group by
        campaign_id

),

campaign_ranges as (

    select
        campaigns.campaign_id,
        campaigns.campaign_name,
        campaigns.channel,
        campaigns.objective,
        campaigns.start_date,
        campaigns.end_date,
        campaigns.campaign_status,
        run_control.run_date,

        greatest(
            least(
                campaigns.end_date,
                run_control.run_date
            ),
            coalesce(
                last_spend_dates.last_spend_date,
                campaigns.start_date
            )
        ) as metric_end_date

    from campaigns

    cross join run_control

    left join last_spend_dates
        on campaigns.campaign_id
            = last_spend_dates.campaign_id

),

campaign_dates as (

    select
        campaign_ranges.campaign_id,
        campaign_ranges.campaign_name,
        campaign_ranges.channel,
        campaign_ranges.objective,
        campaign_ranges.start_date,
        campaign_ranges.end_date,
        campaign_ranges.campaign_status,
        campaign_ranges.run_date,
        cast(date_value as date) as metric_date

    from campaign_ranges

    cross join unnest(
        generate_series(
            campaign_ranges.start_date,
            campaign_ranges.metric_end_date,
            interval 1 day
        )
    ) as generated_dates(date_value)

    where campaign_ranges.start_date
        <= campaign_ranges.metric_end_date

),

daily_spend as (

    select
        campaign_id,
        spend_date as metric_date,
        sum(spend_amount) as spend_amount,
        sum(impressions) as impressions,
        sum(clicks) as clicks,
        sum(platform_conversions)
            as platform_conversions

    from {{ ref('stg_ad_spend_daily') }}

    group by
        campaign_id,
        spend_date

),

daily_attribution as (

    select
        campaign_id,
        order_date as metric_date,
        sum(attributed_conversion)
            as attributed_conversions,
        sum(attributed_gross_revenue)
            as attributed_gross_revenue,
        sum(attributed_refund_amount)
            as attributed_refund_amount,
        sum(attributed_net_revenue)
            as attributed_net_revenue

    from {{ ref(
        'int_attributed_order_financials'
    ) }}

    group by
        campaign_id,
        order_date

),

combined as (

    select
        campaign_dates.campaign_id,
        campaign_dates.campaign_name,
        campaign_dates.channel,
        campaign_dates.objective,
        campaign_dates.start_date,
        campaign_dates.end_date,
        campaign_dates.campaign_status,
        campaign_dates.metric_date,
        campaign_dates.run_date,

        coalesce(
            daily_spend.spend_amount,
            0
        ) as spend_amount,

        coalesce(
            daily_spend.impressions,
            0
        ) as impressions,

        coalesce(
            daily_spend.clicks,
            0
        ) as clicks,

        coalesce(
            daily_spend.platform_conversions,
            0
        ) as platform_conversions,

        coalesce(
            daily_attribution.attributed_conversions,
            0
        ) as attributed_conversions,

        coalesce(
            daily_attribution.attributed_gross_revenue,
            0
        ) as attributed_gross_revenue,

        coalesce(
            daily_attribution.attributed_refund_amount,
            0
        ) as attributed_refund_amount,

        coalesce(
            daily_attribution.attributed_net_revenue,
            0
        ) as attributed_net_revenue

    from campaign_dates

    left join daily_spend
        on campaign_dates.campaign_id
            = daily_spend.campaign_id
        and campaign_dates.metric_date
            = daily_spend.metric_date

    left join daily_attribution
        on campaign_dates.campaign_id
            = daily_attribution.campaign_id
        and campaign_dates.metric_date
            = daily_attribution.metric_date

),

with_budget as (

    select
        combined.campaign_id,
        combined.campaign_name,
        combined.channel,
        combined.objective,
        combined.start_date,
        combined.end_date,
        combined.campaign_status,
        combined.metric_date,
        combined.run_date,
        combined.spend_amount,
        combined.impressions,
        combined.clicks,
        combined.platform_conversions,
        combined.attributed_conversions,
        combined.attributed_gross_revenue,
        combined.attributed_refund_amount,
        combined.attributed_net_revenue,
        budget.budget_change_id,
        budget.budget_amount,
        budget.currency_code,

        case
            when combined.metric_date
                between combined.start_date
                and combined.end_date
            then date_diff(
                'day',
                greatest(
                    combined.start_date,
                    cast(
                        date_trunc(
                            'month',
                            combined.metric_date
                        ) as date
                    )
                ),
                least(
                    combined.end_date,
                    last_day(combined.metric_date)
                )
            ) + 1
            else 0
        end as active_days_in_budget_month

    from combined

    left join {{ ref(
        'int_campaign_budget_versions'
    ) }} as budget
        on combined.campaign_id = budget.campaign_id
        and cast(
            date_trunc(
                'month',
                combined.metric_date
            ) as date
        ) = budget.budget_month
        and cast(budget.valid_from as date)
            <= combined.metric_date
        and (
            budget.valid_to is null
            or cast(budget.valid_to as date)
                > combined.metric_date
        )

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

    cast(
        case
            when active_days_in_budget_month > 0
                then budget_amount
                    / active_days_in_budget_month
            else 0
        end
        as decimal(18, 2)
    ) as expected_daily_spend,

    metric_date > end_date
        and spend_amount > 0
        as has_post_end_spend

from with_budget
