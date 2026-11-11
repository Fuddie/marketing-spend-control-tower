with source as (

    select
        budget_change_id,
        campaign_id,
        budget_month,
        budget_amount,
        currency_code,
        effective_at,
        change_reason,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from {{ source(
        'bronze',
        'campaign_budget_changes'
    ) }}

),

cleaned as (

    select
        trim(budget_change_id) as budget_change_id,
        trim(campaign_id) as campaign_id,
        budget_month,
        cast(
            budget_amount as decimal(18, 2)
        ) as budget_amount,
        upper(trim(currency_code)) as currency_code,
        effective_at,
        lower(trim(change_reason)) as change_reason,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from source

)

select
    budget_change_id,
    campaign_id,
    budget_month,
    budget_amount,
    currency_code,
    effective_at,
    change_reason,
    source_updated_at,
    extract_date,
    ingested_at,
    source_file

from cleaned