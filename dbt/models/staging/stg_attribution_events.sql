with source as (

    select
        attribution_id,
        order_id,
        campaign_id,
        touchpoint_timestamp,
        attribution_model,
        attribution_weight,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from {{ source(
        'bronze',
        'attribution_events'
    ) }}

),

cleaned as (

    select
        trim(attribution_id) as attribution_id,
        trim(order_id) as order_id,
        trim(campaign_id) as campaign_id,
        touchpoint_timestamp,
        lower(
            trim(attribution_model)
        ) as attribution_model,
        cast(
            attribution_weight as decimal(5, 4)
        ) as attribution_weight,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from source

)

select
    attribution_id,
    order_id,
    campaign_id,
    touchpoint_timestamp,
    attribution_model,
    attribution_weight,
    source_updated_at,
    extract_date,
    ingested_at,
    source_file

from cleaned