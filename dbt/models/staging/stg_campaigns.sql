with source as (

    select *
    from {{ source('bronze', 'campaigns') }}

),

cleaned as (

    select
        trim(campaign_id) as campaign_id,
        trim(campaign_name) as campaign_name,
        trim(channel) as channel,
        lower(trim(objective)) as objective,
        start_date,
        end_date,
        lower(trim(status)) as campaign_status,
        created_at,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from source

)

select *
from cleaned