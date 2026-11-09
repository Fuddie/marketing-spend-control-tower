import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path


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


def determine_campaign_status(start_date, end_date, run_date):
    """Determine a campaign's status from its active dates."""

    if run_date < start_date:
        return "planned"

    if run_date > end_date:
        return "completed"

    return "active"


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


def main():
    random.seed(RANDOM_SEED)

    campaigns = generate_campaigns(
        number_of_campaigns=NUMBER_OF_CAMPAIGNS,
        run_date=RUN_DATE,
    )

    validate_campaigns(campaigns)

    output_path = write_campaigns_csv(
        campaigns=campaigns,
        run_date=RUN_DATE,
    )

    status_counts = {}

    for campaign in campaigns:
        status = campaign["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"Generated {len(campaigns)} campaign records.")
    print(f"Status counts: {status_counts}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()