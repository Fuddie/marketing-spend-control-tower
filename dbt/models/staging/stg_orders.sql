with source as (

    select
        order_id,
        customer_id,
        order_timestamp,
        order_status,
        gross_revenue,
        currency_code,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from {{ source('bronze', 'orders') }}

),

cleaned as (

    select
        trim(order_id) as order_id,
        trim(customer_id) as customer_id,
        order_timestamp,
        cast(order_timestamp as date) as order_date,
        lower(trim(order_status)) as order_status,
        cast(
            gross_revenue as decimal(18, 2)
        ) as gross_revenue,
        upper(trim(currency_code)) as currency_code,
        source_updated_at,
        extract_date,
        ingested_at,
        source_file

    from source

)

select
    order_id,
    customer_id,
    order_timestamp,
    order_date,
    order_status,
    gross_revenue,
    currency_code,
    source_updated_at,
    extract_date,
    ingested_at,
    source_file

from cleaned