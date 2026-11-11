import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from decimal import Decimal


RANDOM_SEED = 42
NUMBER_OF_CAMPAIGNS = 12
RUN_DATE = date.today()

CHANNELS = [
    "Meta Ads",
    "Google Ads",
    "TikTok Ads",
]

OBJECTIVES = [
    "conversions",
    "traffic",
    "awareness",
]

ALLOWED_STATUSES = {
    "planned",
    "active",
    "completed",
}

MONTHLY_BUDGET_OPTIONS = [
    Decimal("3000.00"),
    Decimal("5000.00"),
    Decimal("7500.00"),
    Decimal("10000.00"),
    Decimal("15000.00"),
]

PACE_MULTIPLIERS = {
    "CMP-008": Decimal("1.40"),
    "CMP-011": Decimal("0.60"),
    "CMP-012": Decimal("1.20"),
}

TRACKING_GAP_CAMPAIGN_ID = "CMP-009"
TRACKING_GAP_DAYS = 3

POST_END_SPEND_CAMPAIGN_ID = "CMP-005"

NUMBER_OF_CUSTOMERS = 180

ORDER_STATUSES = [
    "completed",
    "cancelled",
    "pending",
]

ORDER_STATUS_WEIGHTS = [
    88,
    7,
    5,
]

ORDER_VALUE_OPTIONS = [
    Decimal("35.00"),
    Decimal("49.00"),
    Decimal("75.00"),
    Decimal("99.00"),
    Decimal("125.00"),
    Decimal("175.00"),
    Decimal("250.00"),
]

ATTRIBUTION_RATE_PERCENT = 85


def determine_campaign_status(start_date, end_date, run_date):
    """Determine a campaign's status from its active dates."""

    if run_date < start_date:
        return "planned"

    if run_date > end_date:
        return "completed"

    return "active"

def get_month_starts(start_date, end_date):
    """Return the first day of every month within a date range."""

    months = []

    current_month = date(
        start_date.year,
        start_date.month,
        1,
    )

    final_month = date(
        end_date.year,
        end_date.month,
        1,
    )

    while current_month <= final_month:
        months.append(current_month)

        if current_month.month == 12:
            current_month = date(
                current_month.year + 1,
                1,
                1,
            )
        else:
            current_month = date(
                current_month.year,
                current_month.month + 1,
                1,
            )

    return months

def get_month_end(date_value):
    """Return the final day of the month containing date_value."""

    if date_value.month == 12:
        next_month = date(
            date_value.year + 1,
            1,
            1,
        )
    else:
        next_month = date(
            date_value.year,
            date_value.month + 1,
            1,
        )

    return next_month - timedelta(days=1)

def get_active_days_in_month(
    campaign_start_date,
    campaign_end_date,
    spend_date,
):
    """Calculate the campaign's active days in a given month."""

    month_start = date(
        spend_date.year,
        spend_date.month,
        1,
    )

    month_end = get_month_end(spend_date)

    active_start = max(
        campaign_start_date,
        month_start,
    )

    active_end = min(
        campaign_end_date,
        month_end,
    )

    return (active_end - active_start).days + 1

def get_effective_budget(
    budget_changes,
    campaign_id,
    spend_date,
):
    """Find the latest applicable budget for a campaign and date."""

    budget_month = date(
        spend_date.year,
        spend_date.month,
        1,
    )

    eligible_budgets = []

    for budget in budget_changes:
        effective_date = datetime.fromisoformat(
            budget["effective_at"]
        ).date()

        matches_campaign = (
            budget["campaign_id"] == campaign_id
        )

        matches_month = (
            budget["budget_month"]
            == budget_month.isoformat()
        )

        is_effective = effective_date <= spend_date

        if (
            matches_campaign
            and matches_month
            and is_effective
        ):
            eligible_budgets.append(budget)

    if not eligible_budgets:
        raise ValueError(
            f"No effective budget found for "
            f"{campaign_id} on {spend_date}."
        )

    latest_budget = max(
        eligible_budgets,
        key=lambda budget: budget["effective_at"],
    )

    return Decimal(
        latest_budget["budget_amount"]
    )

def get_pace_multiplier(campaign_id):
    """Return the planned spending behaviour for a campaign."""

    return PACE_MULTIPLIERS.get(
        campaign_id,
        Decimal("1.00"),
    )


def generate_campaign_dates(campaign_number, run_date):
    """
    Generate dates that guarantee a mixture of planned,
    active and completed campaigns.
    """

    if campaign_number <= 2:
        # Planned campaigns begin in the future.
        start_date = run_date + timedelta(days=random.randint(5, 20))
        end_date = start_date + timedelta(days=random.randint(30, 60))

    elif campaign_number <= 5:
        # Completed campaigns ended before the current run date.
        end_date = run_date - timedelta(days=random.randint(1, 20))
        start_date = end_date - timedelta(days=random.randint(30, 90))

    else:
        # Active campaigns started in the past and end in the future.
        start_date = run_date - timedelta(days=random.randint(1, 45))
        end_date = run_date + timedelta(days=random.randint(15, 60))

    return start_date, end_date


def generate_campaigns(number_of_campaigns, run_date):
    """Generate synthetic campaign source records."""

    campaigns = []

    for campaign_number in range(1, number_of_campaigns + 1):
        campaign_id = f"CMP-{campaign_number:03d}"

        channel = random.choice(CHANNELS)
        objective = random.choice(OBJECTIVES)

        start_date, end_date = generate_campaign_dates(
            campaign_number=campaign_number,
            run_date=run_date,
        )

        status = determine_campaign_status(
            start_date=start_date,
            end_date=end_date,
            run_date=run_date,
        )

        
        # A campaign must be created before it appears in an extract.
        if start_date > run_date:
            created_date = run_date - timedelta(
                days=random.randint(1, 14)
            )
        else:
            created_date = start_date - timedelta(
                days=random.randint(1, 14)
            )

        # Select an update date between creation and the current run date.
        days_since_creation = (run_date - created_date).days

        updated_date = created_date + timedelta(
            days=random.randint(0, max(days_since_creation, 0))
        )

        created_at = datetime.combine(
            created_date,
            datetime.min.time(),
        ) + timedelta(hours=9)

        source_updated_at = datetime.combine(
            updated_date,
            datetime.min.time(),
        ) + timedelta(hours=12)

        campaign_name = (
            f"{channel} {objective.title()} Campaign "
            f"{campaign_number:02d}"
        )

        campaign = {
            "campaign_id": campaign_id,
            "campaign_name": campaign_name,
            "channel": channel,
            "objective": objective,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "status": status,
            "created_at": created_at.isoformat(),
            "source_updated_at": source_updated_at.isoformat(),
        }

        campaigns.append(campaign)

    return campaigns

def generate_budget_changes(campaigns, run_date):
    """Generate initial monthly budgets and selected budget revisions."""

    budget_changes = []
    budget_change_number = 1

    current_budget_month = date(
        run_date.year,
        run_date.month,
        1,
    )

    for campaign in campaigns:
        campaign_id = campaign["campaign_id"]

        campaign_number = int(
            campaign_id.split("-")[1]
        )

        campaign_start_date = date.fromisoformat(
            campaign["start_date"]
        )

        campaign_end_date = date.fromisoformat(
            campaign["end_date"]
        )

        budget_months = get_month_starts(
            start_date=campaign_start_date,
            end_date=campaign_end_date,
        )

        for budget_month in budget_months:
            initial_budget = random.choice(
                MONTHLY_BUDGET_OPTIONS
            )

            first_active_date = max(
                campaign_start_date,
                budget_month,
            )

            proposed_effective_date = (
                first_active_date
                - timedelta(days=random.randint(3, 10))
            )

            initial_effective_date = min(
                proposed_effective_date,
                run_date,
            )

            effective_at = datetime.combine(
                initial_effective_date,
                datetime.min.time(),
            ) + timedelta(hours=9)

            source_updated_at = datetime.combine(
                initial_effective_date,
                datetime.min.time(),
            ) + timedelta(hours=12)

            initial_record = {
                "budget_change_id": (
                    f"BUD-{budget_change_number:04d}"
                ),
                "campaign_id": campaign_id,
                "budget_month": budget_month.isoformat(),
                "budget_amount": str(initial_budget),
                "currency_code": "GBP",
                "effective_at": effective_at.isoformat(),
                "change_reason": "initial allocation",
                "source_updated_at": (
                    source_updated_at.isoformat()
                ),
            }

            budget_changes.append(initial_record)
            budget_change_number += 1

            should_create_revision = (
                campaign["status"] == "active"
                and budget_month == current_budget_month
                and campaign_number % 4 == 0
            )

            if should_create_revision:
                change_direction = random.choice(
                    ["increase", "reduction"]
                )

                if change_direction == "increase":
                    revised_budget = (
                        initial_budget * Decimal("1.20")
                    )
                    change_reason = "increased budget"
                else:
                    revised_budget = (
                        initial_budget * Decimal("0.80")
                    )
                    change_reason = "reduced budget"

                revised_budget = revised_budget.quantize(
                    Decimal("0.01")
                )

                revision_effective_date = (
                    run_date - timedelta(days=2)
                )

                revision_effective_at = datetime.combine(
                    revision_effective_date,
                    datetime.min.time(),
                ) + timedelta(hours=10)

                revision_updated_at = datetime.combine(
                    revision_effective_date,
                    datetime.min.time(),
                ) + timedelta(hours=12)

                revision_record = {
                    "budget_change_id": (
                        f"BUD-{budget_change_number:04d}"
                    ),
                    "campaign_id": campaign_id,
                    "budget_month": budget_month.isoformat(),
                    "budget_amount": str(revised_budget),
                    "currency_code": "GBP",
                    "effective_at": (
                        revision_effective_at.isoformat()
                    ),
                    "change_reason": change_reason,
                    "source_updated_at": (
                        revision_updated_at.isoformat()
                    ),
                }

                budget_changes.append(revision_record)
                budget_change_number += 1

    return budget_changes

def generate_ad_spend_daily(
    campaigns,
    budget_changes,
    run_date,
):
    """Generate daily advertising performance records."""

    spend_records = []

    tracking_gap_start_date = (
        run_date
        - timedelta(days=TRACKING_GAP_DAYS - 1)
    )

    for campaign in campaigns:
        campaign_id = campaign["campaign_id"]

        campaign_start_date = date.fromisoformat(
            campaign["start_date"]
        )

        campaign_end_date = date.fromisoformat(
            campaign["end_date"]
        )

        final_spend_date = min(
            campaign_end_date,
            run_date,
        )

        if (
            campaign_id == POST_END_SPEND_CAMPAIGN_ID
            and campaign_end_date < run_date
        ):
            final_spend_date = min(
                campaign_end_date + timedelta(days=2),
                get_month_end(campaign_end_date),
                run_date,
            )

        if campaign_start_date > final_spend_date:
            continue

        spend_date = campaign_start_date

        while spend_date <= final_spend_date:
            monthly_budget = get_effective_budget(
                budget_changes=budget_changes,
                campaign_id=campaign_id,
                spend_date=spend_date,
            )

            active_days = get_active_days_in_month(
                campaign_start_date=campaign_start_date,
                campaign_end_date=campaign_end_date,
                spend_date=spend_date,
            )

            daily_budget = (
                monthly_budget
                / Decimal(active_days)
            )

            pace_multiplier = get_pace_multiplier(
                campaign_id=campaign_id
            )

            daily_variation = (
                Decimal(random.randint(90, 110))
                / Decimal("100")
            )

            spend_amount = (
                daily_budget
                * pace_multiplier
                * daily_variation
            ).quantize(Decimal("0.01"))

            impressions_per_pound = Decimal(
                random.randint(80, 140)
            )

            impressions = int(
                spend_amount
                * impressions_per_pound
            )

            click_through_rate = (
                Decimal(random.randint(10, 40))
                / Decimal("1000")
            )

            clicks = int(
                Decimal(impressions)
                * click_through_rate
            )

            conversion_rate = (
                Decimal(random.randint(20, 80))
                / Decimal("1000")
            )

            platform_conversions = int(
                Decimal(clicks)
                * conversion_rate
            )

            is_tracking_gap = (
                campaign_id
                == TRACKING_GAP_CAMPAIGN_ID
                and spend_date >= tracking_gap_start_date
            )

            if is_tracking_gap:
                platform_conversions = 0

            source_update_date = min(
                spend_date + timedelta(days=1),
                run_date,
            )

            source_updated_at = datetime.combine(
                source_update_date,
                datetime.min.time(),
            ) + timedelta(hours=6)

            spend_record = {
                "spend_record_id": (
                    f"SPEND-{campaign_id}-"
                    f"{spend_date.strftime('%Y%m%d')}"
                ),
                "campaign_id": campaign_id,
                "spend_date": spend_date.isoformat(),
                "spend_amount": str(spend_amount),
                "impressions": impressions,
                "clicks": clicks,
                "platform_conversions": platform_conversions,
                "currency_code": "GBP",
                "source_updated_at": (
                    source_updated_at.isoformat()
                ),
            }

            spend_records.append(spend_record)
            spend_date += timedelta(days=1)

    return spend_records

def generate_orders(
    spend_records,
    run_date,
):
    """Generate synthetic customer orders from advertising activity."""

    orders = []
    order_campaign_links = []
    order_number = 1

    run_date_end = datetime.combine(
        run_date,
        datetime.max.time(),
    )

    for spend_record in spend_records:
        spend_date = date.fromisoformat(
            spend_record["spend_date"]
        )

        spend_amount = Decimal(
            spend_record["spend_amount"]
        )

        estimated_orders = int(
            spend_amount / Decimal("175.00")
        )

        daily_variation = random.choice(
            [-1, 0, 0, 0, 1]
        )

        order_count = max(
            0,
            min(
                estimated_orders + daily_variation,
                5,
            ),
        )

        for _ in range(order_count):
            order_id = f"ORD-{order_number:06d}"

            customer_number = random.randint(
                1,
                NUMBER_OF_CUSTOMERS,
            )

            customer_id = (
                f"CUST-{customer_number:04d}"
            )

            order_hour = random.randint(8, 22)
            order_minute = random.randint(0, 59)

            order_timestamp = datetime.combine(
                spend_date,
                datetime.min.time(),
            ) + timedelta(
                hours=order_hour,
                minutes=order_minute,
            )

            order_status = random.choices(
                ORDER_STATUSES,
                weights=ORDER_STATUS_WEIGHTS,
                k=1,
            )[0]

            gross_revenue = random.choice(
                ORDER_VALUE_OPTIONS
            )

            update_delay_hours = random.randint(
                1,
                72,
            )

            source_updated_at = min(
                order_timestamp
                + timedelta(hours=update_delay_hours),
                run_date_end,
            )

            order = {
                "order_id": order_id,
                "customer_id": customer_id,
                "order_timestamp": (
                    order_timestamp.isoformat()
                ),
                "order_status": order_status,
                "gross_revenue": str(gross_revenue),
                "currency_code": "GBP",
                "source_updated_at": (
                    source_updated_at.isoformat()
                ),
            }

            campaign_link = {
                "order_id": order_id,
                "campaign_id": (
                    spend_record["campaign_id"]
                ),
                "spend_date": (
                    spend_record["spend_date"]
                ),
            }

            orders.append(order)
            order_campaign_links.append(
                campaign_link
            )

            order_number += 1

    return orders, order_campaign_links

def generate_attribution_events(
    orders,
    order_campaign_links,
    run_date,
):
    """Generate last-click marketing attribution events."""

    attribution_events = []
    attribution_number = 1

    orders_by_id = {
        order["order_id"]: order
        for order in orders
    }

    tracking_gap_start_date = (
        run_date
        - timedelta(days=TRACKING_GAP_DAYS - 1)
    )

    run_date_end = datetime.combine(
        run_date,
        datetime.max.time(),
    )

    for link in order_campaign_links:
        campaign_id = link["campaign_id"]

        spend_date = date.fromisoformat(
            link["spend_date"]
        )

        is_tracking_gap = (
            campaign_id
            == TRACKING_GAP_CAMPAIGN_ID
            and spend_date >= tracking_gap_start_date
        )

        if is_tracking_gap:
            continue

        should_attribute = (
            random.randint(1, 100)
            <= ATTRIBUTION_RATE_PERCENT
        )

        if not should_attribute:
            continue

        order = orders_by_id[link["order_id"]]

        order_timestamp = datetime.fromisoformat(
            order["order_timestamp"]
        )

        minutes_before_order = random.randint(
            5,
            360,
        )

        touchpoint_timestamp = (
            order_timestamp
            - timedelta(minutes=minutes_before_order)
        )

        source_updated_at = min(
            order_timestamp
            + timedelta(hours=random.randint(1, 24)),
            run_date_end,
        )

        attribution_event = {
            "attribution_id": (
                f"ATTR-{attribution_number:06d}"
            ),
            "order_id": link["order_id"],
            "campaign_id": campaign_id,
            "touchpoint_timestamp": (
                touchpoint_timestamp.isoformat()
            ),
            "attribution_model": "last_click",
            "attribution_weight": "1.0000",
            "source_updated_at": (
                source_updated_at.isoformat()
            ),
        }

        attribution_events.append(
            attribution_event
        )

        attribution_number += 1

    return attribution_events

def validate_campaigns(campaigns):
    """Validate the generated campaign records before writing them."""

    campaign_ids = [campaign["campaign_id"] for campaign in campaigns]

    if len(campaign_ids) != len(set(campaign_ids)):
        raise ValueError("Duplicate campaign IDs were generated.")

    for campaign in campaigns:
        start_date = date.fromisoformat(campaign["start_date"])
        end_date = date.fromisoformat(campaign["end_date"])

        if end_date < start_date:
            raise ValueError(
                f"{campaign['campaign_id']} has an end date "
                "before its start date."
            )

        if campaign["channel"] not in CHANNELS:
            raise ValueError(
                f"{campaign['campaign_id']} has an invalid channel."
            )

        if campaign["objective"] not in OBJECTIVES:
            raise ValueError(
                f"{campaign['campaign_id']} has an invalid objective."
            )

        if campaign["status"] not in ALLOWED_STATUSES:
            raise ValueError(
                f"{campaign['campaign_id']} has an invalid status."
            )

def validate_budget_changes(budget_changes, campaigns):
    """Validate budget records before writing them."""

    valid_campaign_ids = {
        campaign["campaign_id"]
        for campaign in campaigns
    }

    budget_change_ids = [
        budget["budget_change_id"]
        for budget in budget_changes
    ]

    if len(budget_change_ids) != len(set(budget_change_ids)):
        raise ValueError(
            "Duplicate budget change IDs were generated."
        )

    for budget in budget_changes:
        if budget["campaign_id"] not in valid_campaign_ids:
            raise ValueError(
                f"{budget['budget_change_id']} contains "
                "an unknown campaign ID."
            )

        budget_amount = Decimal(
            budget["budget_amount"]
        )

        if budget_amount <= 0:
            raise ValueError(
                f"{budget['budget_change_id']} has "
                "an invalid budget amount."
            )

        if budget["currency_code"] != "GBP":
            raise ValueError(
                f"{budget['budget_change_id']} has "
                "an invalid currency."
            )

        budget_month = date.fromisoformat(
            budget["budget_month"]
        )

        if budget_month.day != 1:
            raise ValueError(
                f"{budget['budget_change_id']} does not "
                "use the first day of the budget month."
            )

def validate_ad_spend_daily(
    spend_records,
    campaigns,
):
    """Validate daily advertising-spend records."""

    valid_campaign_ids = {
        campaign["campaign_id"]
        for campaign in campaigns
    }

    spend_record_ids = [
        record["spend_record_id"]
        for record in spend_records
    ]

    if len(spend_record_ids) != len(set(spend_record_ids)):
        raise ValueError(
            "Duplicate spend record IDs were generated."
        )

    for record in spend_records:
        campaign_id = record["campaign_id"]

        if campaign_id not in valid_campaign_ids:
            raise ValueError(
                f"{record['spend_record_id']} contains "
                "an unknown campaign ID."
            )

        spend_amount = Decimal(
            record["spend_amount"]
        )

        if spend_amount <= 0:
            raise ValueError(
                f"{record['spend_record_id']} has "
                "an invalid spend amount."
            )

        if record["impressions"] < 0:
            raise ValueError(
                f"{record['spend_record_id']} has "
                "negative impressions."
            )

        if record["clicks"] < 0:
            raise ValueError(
                f"{record['spend_record_id']} has "
                "negative clicks."
            )

        if record["clicks"] > record["impressions"]:
            raise ValueError(
                f"{record['spend_record_id']} has "
                "more clicks than impressions."
            )

        if record["platform_conversions"] < 0:
            raise ValueError(
                f"{record['spend_record_id']} has "
                "negative conversions."
            )

        if (
            record["platform_conversions"]
            > record["clicks"]
        ):
            raise ValueError(
                f"{record['spend_record_id']} has "
                "more conversions than clicks."
            )

        if record["currency_code"] != "GBP":
            raise ValueError(
                f"{record['spend_record_id']} has "
                "an invalid currency."
            )

def validate_orders(
    orders,
    order_campaign_links,
    campaigns,
    run_date,
):
    """Validate generated orders and their temporary campaign links."""

    valid_campaign_ids = {
        campaign["campaign_id"]
        for campaign in campaigns
    }

    order_ids = [
        order["order_id"]
        for order in orders
    ]

    if len(order_ids) != len(set(order_ids)):
        raise ValueError(
            "Duplicate order IDs were generated."
        )

    allowed_statuses = set(ORDER_STATUSES)

    for order in orders:
        order_timestamp = datetime.fromisoformat(
            order["order_timestamp"]
        )

        source_updated_at = datetime.fromisoformat(
            order["source_updated_at"]
        )

        if order["order_status"] not in allowed_statuses:
            raise ValueError(
                f"{order['order_id']} has an invalid status."
            )

        if Decimal(order["gross_revenue"]) <= 0:
            raise ValueError(
                f"{order['order_id']} has invalid revenue."
            )

        if order["currency_code"] != "GBP":
            raise ValueError(
                f"{order['order_id']} has an invalid currency."
            )

        if source_updated_at < order_timestamp:
            raise ValueError(
                f"{order['order_id']} was updated before "
                "it was created."
            )

        if order_timestamp.date() > run_date:
            raise ValueError(
                f"{order['order_id']} has a future timestamp."
            )

    linked_order_ids = [
        link["order_id"]
        for link in order_campaign_links
    ]

    if set(linked_order_ids) != set(order_ids):
        raise ValueError(
            "Order campaign links do not match the orders."
        )

    for link in order_campaign_links:
        if link["campaign_id"] not in valid_campaign_ids:
            raise ValueError(
                f"{link['order_id']} links to an "
                "unknown campaign."
            )

def validate_attribution_events(
    attribution_events,
    orders,
    campaigns,
):
    """Validate last-click attribution records."""

    valid_order_ids = {
        order["order_id"]
        for order in orders
    }

    valid_campaign_ids = {
        campaign["campaign_id"]
        for campaign in campaigns
    }

    orders_by_id = {
        order["order_id"]: order
        for order in orders
    }

    attribution_ids = [
        event["attribution_id"]
        for event in attribution_events
    ]

    if len(attribution_ids) != len(set(attribution_ids)):
        raise ValueError(
            "Duplicate attribution IDs were generated."
        )

    attributed_order_ids = [
        event["order_id"]
        for event in attribution_events
    ]

    if len(attributed_order_ids) != len(
        set(attributed_order_ids)
    ):
        raise ValueError(
            "An order received more than one "
            "last-click attribution."
        )

    for event in attribution_events:
        order_id = event["order_id"]
        campaign_id = event["campaign_id"]

        if order_id not in valid_order_ids:
            raise ValueError(
                f"{event['attribution_id']} contains "
                "an unknown order ID."
            )

        if campaign_id not in valid_campaign_ids:
            raise ValueError(
                f"{event['attribution_id']} contains "
                "an unknown campaign ID."
            )

        if event["attribution_model"] != "last_click":
            raise ValueError(
                f"{event['attribution_id']} has "
                "an invalid attribution model."
            )

        if Decimal(event["attribution_weight"]) != Decimal(
            "1.0000"
        ):
            raise ValueError(
                f"{event['attribution_id']} has "
                "an invalid attribution weight."
            )

        order_timestamp = datetime.fromisoformat(
            orders_by_id[order_id]["order_timestamp"]
        )

        touchpoint_timestamp = datetime.fromisoformat(
            event["touchpoint_timestamp"]
        )

        source_updated_at = datetime.fromisoformat(
            event["source_updated_at"]
        )

        if touchpoint_timestamp >= order_timestamp:
            raise ValueError(
                f"{event['attribution_id']} has a "
                "touchpoint after the order."
            )

        if source_updated_at < order_timestamp:
            raise ValueError(
                f"{event['attribution_id']} was updated "
                "before the order occurred."
            )

def write_campaigns_csv(campaigns, run_date):
    """Write campaign records to the daily landing directory."""

    project_root = Path(__file__).resolve().parent.parent

    output_directory = (
        project_root
        / "data"
        / "landing"
        / "campaigns"
        / f"extract_date={run_date.isoformat()}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_directory / "campaigns.csv"

    fieldnames = [
        "campaign_id",
        "campaign_name",
        "channel",
        "objective",
        "start_date",
        "end_date",
        "status",
        "created_at",
        "source_updated_at",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(campaigns)

    return output_path

def write_budget_changes_csv(
    budget_changes,
    run_date,
):
    """Write budget records to the daily landing directory."""

    project_root = Path(__file__).resolve().parent.parent

    output_directory = (
        project_root
        / "data"
        / "landing"
        / "campaign_budget_changes"
        / f"extract_date={run_date.isoformat()}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / "campaign_budget_changes.csv"
    )

    fieldnames = [
        "budget_change_id",
        "campaign_id",
        "budget_month",
        "budget_amount",
        "currency_code",
        "effective_at",
        "change_reason",
        "source_updated_at",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(budget_changes)

    return output_path

def write_ad_spend_daily_csv(
    spend_records,
    run_date,
):
    """Write daily advertising records to the landing directory."""

    project_root = Path(__file__).resolve().parent.parent

    output_directory = (
        project_root
        / "data"
        / "landing"
        / "ad_spend_daily"
        / f"extract_date={run_date.isoformat()}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / "ad_spend_daily.csv"
    )

    fieldnames = [
        "spend_record_id",
        "campaign_id",
        "spend_date",
        "spend_amount",
        "impressions",
        "clicks",
        "platform_conversions",
        "currency_code",
        "source_updated_at",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(spend_records)

    return output_path

def write_orders_csv(
    orders,
    run_date,
):
    """Write order records to the daily landing directory."""

    project_root = Path(__file__).resolve().parent.parent

    output_directory = (
        project_root
        / "data"
        / "landing"
        / "orders"
        / f"extract_date={run_date.isoformat()}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_directory / "orders.csv"

    fieldnames = [
        "order_id",
        "customer_id",
        "order_timestamp",
        "order_status",
        "gross_revenue",
        "currency_code",
        "source_updated_at",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(orders)

    return output_path

def write_attribution_events_csv(
    attribution_events,
    run_date,
):
    """Write attribution events to the landing directory."""

    project_root = Path(__file__).resolve().parent.parent

    output_directory = (
        project_root
        / "data"
        / "landing"
        / "attribution_events"
        / f"extract_date={run_date.isoformat()}"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / "attribution_events.csv"
    )

    fieldnames = [
        "attribution_id",
        "order_id",
        "campaign_id",
        "touchpoint_timestamp",
        "attribution_model",
        "attribution_weight",
        "source_updated_at",
    ]

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(attribution_events)

    return output_path

def main():
    random.seed(RANDOM_SEED)

    campaigns = generate_campaigns(
        number_of_campaigns=NUMBER_OF_CAMPAIGNS,
        run_date=RUN_DATE,
    )

    validate_campaigns(campaigns)

    campaigns_output_path = write_campaigns_csv(
        campaigns=campaigns,
        run_date=RUN_DATE,
    )

    budget_changes = generate_budget_changes(
        campaigns=campaigns,
        run_date=RUN_DATE,
    )

    validate_budget_changes(
        budget_changes=budget_changes,
        campaigns=campaigns,
    )

    budgets_output_path = write_budget_changes_csv(
        budget_changes=budget_changes,
        run_date=RUN_DATE,
    )

    spend_records = generate_ad_spend_daily (
        campaigns=campaigns,
        budget_changes=budget_changes,
        run_date=RUN_DATE,
    )

    validate_ad_spend_daily(
        spend_records=spend_records,
        campaigns=campaigns,
    )

    spend_output_path = write_ad_spend_daily_csv (
        spend_records=spend_records,
        run_date=RUN_DATE,
    )

    orders, order_campaign_links = generate_orders(
        spend_records=spend_records,
        run_date=RUN_DATE,
    )

    validate_orders(
        orders=orders,
        order_campaign_links=order_campaign_links,
        campaigns=campaigns,
        run_date=RUN_DATE,
    )

    orders_output_path = write_orders_csv(
        orders=orders,
        run_date=RUN_DATE,
    )

    status_counts = {}

    for campaign in campaigns:
        status = campaign["status"]
        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )


        orders, order_campaign_links = generate_orders(
        spend_records=spend_records,
        run_date=RUN_DATE,
    )

    validate_orders(
        orders=orders,
        order_campaign_links=order_campaign_links,
        campaigns=campaigns,
        run_date=RUN_DATE,
    )

    orders_output_path = write_orders_csv(
        orders=orders,
        run_date=RUN_DATE,
    )

    attribution_events = generate_attribution_events(
        orders=orders,
        order_campaign_links=order_campaign_links,
        run_date=RUN_DATE,
    )

    validate_attribution_events(
        attribution_events=attribution_events,
        orders=orders,
        campaigns=campaigns,
    )

    attribution_output_path = (
        write_attribution_events_csv(
            attribution_events=attribution_events,
            run_date=RUN_DATE,
        )
    )

    budget_revision_count = sum(
        1
        for budget in budget_changes
        if budget["change_reason"] != "initial allocation"
    )

    tracking_gap_start_date = (
        RUN_DATE
        - timedelta(days=TRACKING_GAP_DAYS - 1)
    )

    tracking_gap_count = sum(
        1
        for record in spend_records
        if (
            record["campaign_id"]
            == TRACKING_GAP_CAMPAIGN_ID
            and date.fromisoformat(record["spend_date"])
            >= tracking_gap_start_date
            and record["platform_conversions"] == 0
        )
    )

    campaign_end_dates = {
        campaign["campaign_id"]: date.fromisoformat(
            campaign["end_date"]
        )
        for campaign in campaigns
    }

    post_end_spend_count = sum(
        1
        for record in spend_records
        if (
            date.fromisoformat(record["spend_date"])
            > campaign_end_dates[record["campaign_id"]]
        )
    )  

    order_status_counts = {}

    for order in orders:
        order_status = order["order_status"]

        order_status_counts[order_status] = (
            order_status_counts.get(
                order_status,
                0,
            ) + 1
        )

    completed_gross_revenue = sum(
        (
            Decimal(order["gross_revenue"])
            for order in orders
            if order["order_status"] == "completed"
        ),
        Decimal("0.00"),
    )

    attributed_order_count = len(
        attribution_events
    )

    unattributed_order_count = (
        len(orders) - attributed_order_count
    )

    if orders:
        attribution_rate = (
            attributed_order_count
            / len(orders)
            * 100
        )
    else:
        attribution_rate = 0

    print(f"Generated {len(campaigns)} campaign records.")
    print(f"Campaign status counts: {status_counts}")
    print(f"Campaign output: {campaigns_output_path}")

    print(
        f"Generated {len(budget_changes)} "
        "campaign budget records."
    )
    print(f"Budget revision count: {budget_revision_count}")
    print(f"Budget output: {budgets_output_path}")

    print(
        f"Generated {len(spend_records)} "
        "daily advertising records."
    )
    print(f"Tracking-gap records: {tracking_gap_count}")
    print(f"Post-end spend records: {post_end_spend_count}")
    print(f"Spend output: {spend_output_path}")
    print(f"Generated {len(orders)} order records.")
    print(f"Order status counts: {order_status_counts}")
    print(
        "Completed gross revenue: "
        f"£{completed_gross_revenue}"
    )
    print(f"Order output: {orders_output_path}")
    print(
        f"Generated {len(attribution_events)} "
        "attribution records."
    )
    print(
        f"Attributed orders: {attributed_order_count}"
    )
    print(
        f"Unattributed orders: {unattributed_order_count}"
    )
    print(
        f"Attribution rate: {attribution_rate:.1f}%"
    )
    print(
        f"Attribution output: {attribution_output_path}"
    )


if __name__ == "__main__":
    main()