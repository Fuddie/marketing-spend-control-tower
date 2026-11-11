with source as (

    select
        refund_id,
        order_id,
        refund_timestamp,
        refund_amount,
        refund_status,
        refund_reason,
        currency_code,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from {{ source('bronze', 'refunds') }}

),

cleaned as (

    select
        trim(refund_id) as refund_id,
        trim(order_id) as order_id,
        refund_timestamp,
        cast(
            refund_timestamp as date
        ) as refund_date,
        cast(
            refund_amount as decimal(18, 2)
        ) as refund_amount,
        lower(trim(refund_status)) as refund_status,
        lower(trim(refund_reason)) as refund_reason,
        upper(trim(currency_code)) as currency_code,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from source

)

select
    refund_id,
    order_id,
    refund_timestamp,
    refund_date,
    refund_amount,
    refund_status,
    refund_reason,
    currency_code,
    source_updated_at,
    extract_date,
    ingested_at,
    source_file

from cleaned