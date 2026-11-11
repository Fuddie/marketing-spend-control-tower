with budget_changes as (

    select
        budget_change_id,
        campaign_id,
        budget_month,
        budget_amount,
        currency_code,
        effective_at,
        change_reason,
        source_updated_at

    from {{ ref('stg_campaign_budget_changes') }}

),

versioned as (

    select
        budget_change_id,
        campaign_id,
        budget_month,
        budget_amount,
        currency_code,
        effective_at as valid_from,
        lead(effective_at) over (
            partition by
                campaign_id,
                budget_month
            order by
                effective_at,
                source_updated_at,
                budget_change_id
        ) as valid_to,
        change_reason,
        source_updated_at,
        row_number() over (
            partition by
                campaign_id,
                budget_month
            order by
                effective_at desc,
                source_updated_at desc,
                budget_change_id desc
        ) as version_rank

    from budget_changes

)

select
    budget_change_id,
    campaign_id,
    budget_month,
    budget_amount,
    currency_code,
    valid_from,
    valid_to,
    change_reason,
    source_updated_at,
    version_rank = 1 as is_current_version

from versioned