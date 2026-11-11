with orders as (

    select
        order_id,
        order_timestamp,
        order_date,
        order_status,
        gross_revenue,
        currency_code

    from {{ ref('stg_orders') }}

),

completed_refunds as (

    select
        order_id,
        sum(refund_amount) as completed_refund_amount

    from {{ ref('stg_refunds') }}

    where refund_status = 'completed'

    group by
        order_id

),

attribution as (

    select
        attribution_id,
        order_id,
        campaign_id,
        attribution_model,
        attribution_weight

    from {{ ref('stg_attribution_events') }}

),

joined as (

    select
        attribution.attribution_id,
        attribution.order_id,
        attribution.campaign_id,
        orders.order_timestamp,
        orders.order_date,
        orders.order_status,
        orders.currency_code,
        attribution.attribution_model,
        attribution.attribution_weight,

        case
            when orders.order_status = 'completed'
                then orders.gross_revenue
            else 0
        end as completed_gross_revenue,

        case
            when orders.order_status = 'completed'
                then coalesce(
                    completed_refunds.completed_refund_amount,
                    0
                )
            else 0
        end as completed_refund_amount

    from attribution

    inner join orders
        on attribution.order_id = orders.order_id

    left join completed_refunds
        on attribution.order_id
            = completed_refunds.order_id

)

select
    attribution_id,
    order_id,
    campaign_id,
    order_timestamp,
    order_date,
    order_status,
    currency_code,
    attribution_model,
    attribution_weight,

    cast(
        completed_gross_revenue
        * attribution_weight
        as decimal(18, 2)
    ) as attributed_gross_revenue,

    cast(
        completed_refund_amount
        * attribution_weight
        as decimal(18, 2)
    ) as attributed_refund_amount,

    cast(
        (
            completed_gross_revenue
            - completed_refund_amount
        )
        * attribution_weight
        as decimal(18, 2)
    ) as attributed_net_revenue,

    case
        when order_status = 'completed' then 1
        else 0
    end as attributed_conversion

from joined