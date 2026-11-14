import argparse
import os
import resend
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "warehouse" / "marketing_spend.duckdb"


def load_alerts():
    query = """
        select
            campaign_id,
            campaign_name,
            channel,
            alert_date,
            alert_severity,
            alert_reason,
            currency_code,
            budget_amount,
            month_to_date_spend,
            expected_spend_to_date,
            projected_month_end_spend,
            pacing_ratio
        from gold.mart_campaign_alerts
        order by
            alert_priority,
            pacing_ratio desc,
            campaign_id
    """

    connection = duckdb.connect(str(DATABASE_PATH), read_only=True)

    try:
        return connection.execute(query).fetchall()
    finally:
        connection.close()


def format_currency(amount, currency_code):
    symbols = {"GBP": "£"}
    symbol = symbols.get(currency_code, f"{currency_code} ")
    return f"{symbol}{amount:,.2f}"


def build_alert_message(alerts):
    if not alerts:
        return "No warning or critical campaign alerts were detected."

    lines = [
        "MARKETING SPEND CONTROL TOWER",
        f"Campaign alerts detected: {len(alerts)}",
        "",
    ]

    for alert in alerts:
        (
            campaign_id,
            campaign_name,
            channel,
            alert_date,
            severity,
            reason,
            currency_code,
            budget_amount,
            month_to_date_spend,
            expected_spend_to_date,
            projected_month_end_spend,
            pacing_ratio,
        ) = alert

        lines.extend(
            [
                f"[{severity.upper()}] {campaign_id} | {campaign_name}",
                f"Channel: {channel}",
                f"Alert date: {alert_date}",
                f"Reason: {reason}",
                f"Monthly budget: {format_currency(budget_amount, currency_code)}",
                f"MTD spend: {format_currency(month_to_date_spend, currency_code)}",
                (
                    "Expected spend to date: "
                    f"{format_currency(expected_spend_to_date, currency_code)}"
                ),
                (
                    "Projected month-end spend: "
                    f"{format_currency(projected_month_end_spend, currency_code)}"
                ),
                f"Pacing: {pacing_ratio:.1%}",
                "",
            ]
        )

    return "\n".join(lines)

def send_email(subject, body):
    api_key = os.environ.get("RESEND_API_KEY")
    recipient = os.environ.get("ALERT_RECIPIENT")

    missing = [
        name
        for name, value in {
            "RESEND_API_KEY": api_key,
            "ALERT_RECIPIENT": recipient,
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Missing environment variables: " + ", ".join(missing)
        )

    resend.api_key = api_key

    response = resend.Emails.send(
        {
            "from": "Marketing Spend Control Tower <onboarding@resend.dev>",
            "to": [recipient],
            "subject": subject,
            "text": body,
        }
    )

    return response

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the campaign alert email through Gmail.",
    )
    args = parser.parse_args()

    alerts = load_alerts()
    message = build_alert_message(alerts)

    print(message)

    if not alerts:
        print("\nNo email sent because there are no active alerts.")
        return

    if not args.send:
        print("\nPREVIEW MODE: no email was sent.")
        return

    alert_date = alerts[0][3]
    subject = f"Marketing spend alert | {alert_date}"

    send_email(subject, message)
    print("\nEmail sent successfully.")


if __name__ == "__main__":
    main()