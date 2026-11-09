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

    status_counts = {}

    for campaign in campaigns:
        status = campaign["status"]
        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    budget_revision_count = sum(
        1
        for budget in budget_changes
        if budget["change_reason"] != "initial allocation"
    )

    print(f"Generated {len(campaigns)} campaign records.")
    print(f"Campaign status counts: {status_counts}")
    print(f"Campaign output: {campaigns_output_path}")

    print(
        f"Generated {len(budget_changes)} "
        "campaign budget records."
    )
    print(
        f"Budget revision count: "
        f"{budget_revision_count}"
    )
    print(f"Budget output: {budgets_output_path}")


if __name__ == "__main__":
    main()