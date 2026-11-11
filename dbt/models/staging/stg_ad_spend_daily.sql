with source as (

    select
        spend_record_id,
        campaign_id,
        spend_date,
        spend_amount,
        impressions,
        clicks,
        platform_conversions,
        currency_code,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from {{ source('bronze', 'ad_spend_daily') }}

),

cleaned as (

    select
        trim(spend_record_id) as spend_record_id,
        trim(campaign_id) as campaign_id,
        spend_date,
        cast(
            spend_amount as decimal(18, 2)
        ) as spend_amount,
        impressions,
        clicks,
        platform_conversions,
        upper(trim(currency_code)) as currency_code,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from source

)

select
    spend_record_id,
    campaign_id,
    spend_date,
    spend_amount,
    impressions,
    clicks,
    platform_conversions,
    currency_code,
    source_updated_at,
    extract_date,
    ingested_at,
    source_file

from cleaned