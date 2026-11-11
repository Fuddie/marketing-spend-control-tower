"""Run data-quality checks against the Bronze layer."""

from pathlib import Path

import duckdb
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent

WAREHOUSE_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "marketing_spend.duckdb"
)

QUALITY_CHECKS = [
    {
        "name": "campaigns table is not empty",
        "query": """
            SELECT COUNT(*)
            FROM bronze.campaigns
        """,
        "expectation": "positive",
    },
    {
        "name": "budget campaigns exist",
        "query": """
            SELECT COUNT(*)
            FROM bronze.campaign_budget_changes AS budget
            LEFT JOIN bronze.campaigns AS campaign
                ON budget.campaign_id = campaign.campaign_id
            WHERE campaign.campaign_id IS NULL
        """,
        "expectation": "zero",
    },
    {
        "name": "spend campaigns exist",
        "query": """
            SELECT COUNT(*)
            FROM bronze.ad_spend_daily AS spend
            LEFT JOIN bronze.campaigns AS campaign
                ON spend.campaign_id = campaign.campaign_id
            WHERE campaign.campaign_id IS NULL
        """,
        "expectation": "zero",
    },
    {
        "name": "attribution orders exist",
        "query": """
            SELECT COUNT(*)
            FROM bronze.attribution_events AS attribution
            LEFT JOIN bronze.orders AS orders
                ON attribution.order_id = orders.order_id
            WHERE orders.order_id IS NULL
        """,
        "expectation": "zero",
    },
    {
        "name": "attribution campaigns exist",
        "query": """
            SELECT COUNT(*)
            FROM bronze.attribution_events AS attribution
            LEFT JOIN bronze.campaigns AS campaign
                ON attribution.campaign_id
                    = campaign.campaign_id
            WHERE campaign.campaign_id IS NULL
        """,
        "expectation": "zero",
    },
    {
        "name": "refund orders exist",
        "query": """
            SELECT COUNT(*)
            FROM bronze.refunds AS refund
            LEFT JOIN bronze.orders AS orders
                ON refund.order_id = orders.order_id
            WHERE orders.order_id IS NULL
        """,
        "expectation": "zero",
    },
]

QUALITY_CHECKS.extend(
    [
        {
            "name": "campaign dates are valid",
            "query": """
                SELECT COUNT(*)
                FROM bronze.campaigns
                WHERE end_date < start_date
            """,
            "expectation": "zero",
        },
        {
            "name": "budget amounts are positive",
            "query": """
                SELECT COUNT(*)
                FROM bronze.campaign_budget_changes
                WHERE budget_amount <= 0
            """,
            "expectation": "zero",
        },
        {
            "name": "spend amounts are non-negative",
            "query": """
                SELECT COUNT(*)
                FROM bronze.ad_spend_daily
                WHERE spend_amount < 0
            """,
            "expectation": "zero",
        },
        {
            "name": "clicks do not exceed impressions",
            "query": """
                SELECT COUNT(*)
                FROM bronze.ad_spend_daily
                WHERE clicks > impressions
            """,
            "expectation": "zero",
        },
        {
            "name": "order revenue is positive",
            "query": """
                SELECT COUNT(*)
                FROM bronze.orders
                WHERE gross_revenue <= 0
            """,
            "expectation": "zero",
        },
        {
            "name": "refund amounts are positive",
            "query": """
                SELECT COUNT(*)
                FROM bronze.refunds
                WHERE refund_amount <= 0
            """,
            "expectation": "zero",
        },
        {
            "name": "refunds do not exceed order revenue",
            "query": """
                SELECT COUNT(*)
                FROM bronze.refunds AS refund
                INNER JOIN bronze.orders AS orders
                    ON refund.order_id = orders.order_id
                WHERE refund.refund_amount
                    > orders.gross_revenue
            """,
            "expectation": "zero",
        },
        {
            "name": "refunds occur after their orders",
            "query": """
                SELECT COUNT(*)
                FROM bronze.refunds AS refund
                INNER JOIN bronze.orders AS orders
                    ON refund.order_id = orders.order_id
                WHERE refund.refund_timestamp
                    <= orders.order_timestamp
            """,
            "expectation": "zero",
        },
        {
            "name": "last-click weights equal one",
            "query": """
                SELECT COUNT(*)
                FROM bronze.attribution_events
                WHERE attribution_weight <> 1.0000
            """,
            "expectation": "zero",
        },
        {
            "name": "touchpoints occur before orders",
            "query": """
                SELECT COUNT(*)
                FROM bronze.attribution_events AS attribution
                INNER JOIN bronze.orders AS orders
                    ON attribution.order_id = orders.order_id
                WHERE attribution.touchpoint_timestamp
                    > orders.order_timestamp
            """,
            "expectation": "zero",
        },
        {
            "name": "all financial records use GBP",
            "query": """
                SELECT COUNT(*)
                FROM (
                    SELECT currency_code
                    FROM bronze.campaign_budget_changes

                    UNION ALL

                    SELECT currency_code
                    FROM bronze.ad_spend_daily

                    UNION ALL

                    SELECT currency_code
                    FROM bronze.orders

                    UNION ALL

                    SELECT currency_code
                    FROM bronze.refunds
                ) AS currencies
                WHERE currency_code <> 'GBP'
            """,
            "expectation": "zero",
        },
    ]
)

def main():
    """Run every Bronze quality check."""

    if not WAREHOUSE_PATH.is_file():
        raise FileNotFoundError(
            f"Warehouse not found: {WAREHOUSE_PATH}"
        )

    connection = duckdb.connect(
        str(WAREHOUSE_PATH),
        read_only=True,
    )

    failed_checks = []

    try:
        for check in QUALITY_CHECKS:
            result = connection.execute(
                check["query"]
            ).fetchone()[0]

            if check["expectation"] == "zero":
                passed = result == 0

            elif check["expectation"] == "positive":
                passed = result > 0

            else:
                raise ValueError(
                    "Unknown quality-check expectation: "
                    f"{check['expectation']}"
                )

            status = "PASS" if passed else "FAIL"

            print(
                f"{status}: {check['name']} "
                f"(result={result})"
            )

            if not passed:
                failed_checks.append(check["name"])

    finally:
        connection.close()

    print()

    if failed_checks:
        print(
            f"{len(failed_checks)} Bronze "
            "quality check(s) failed."
        )

        for check_name in failed_checks:
            print(f"- {check_name}")

        sys.exit(1)

    print(
        f"All {len(QUALITY_CHECKS)} "
        "Bronze quality checks passed."
    )


if __name__ == "__main__":
    main()