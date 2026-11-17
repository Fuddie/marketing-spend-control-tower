import argparse
import os
import resend
from html import escape
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


def build_critical_test_alert():
    """Return one fictional critical alert without reading or changing project data."""
    return [
        (
            "TEST-001",
            "Sample Budget Test Campaign",
            "Test Channel",
            "2026-11-17",
            "critical",
            "TEST ONLY: Month-to-date spend has exceeded the monthly budget",
            "GBP",
            4000.00,
            4650.00,
            2266.67,
            6975.00,
            1.1625,
        )
    ]


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


def build_alert_html(alerts):
    if not alerts:
        return """
        <div style="font-family:Arial,sans-serif;color:#172b4d;">
          <h2 style="margin:0 0 12px;">Marketing Spend Control Tower</h2>
          <p>No warning or critical campaign alerts were detected.</p>
        </div>
        """

    has_critical = any(alert[4].lower() == "critical" for alert in alerts)
    overall_label = "CRITICAL" if has_critical else "WARNING"
    header_colour = "#b42318" if has_critical else "#b54708"
    header_background = "#fef3f2" if has_critical else "#fffaeb"

    alert_cards = []
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

        is_critical = severity.lower() == "critical"
        severity_colour = "#b42318" if is_critical else "#b54708"
        severity_background = "#fef3f2" if is_critical else "#fffaeb"
        projected_overspend = projected_month_end_spend - budget_amount
        overspend_text = format_currency(projected_overspend, currency_code)

        alert_cards.append(
            f"""
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
              style="margin:0 0 16px;border:1px solid #d0d5dd;border-left:6px solid {severity_colour};
              border-radius:8px;background:#ffffff;">
              <tr>
                <td style="padding:20px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="font-size:18px;font-weight:700;color:#101828;">
                        {escape(str(campaign_name))}
                      </td>
                      <td align="right">
                        <span style="display:inline-block;padding:5px 10px;border-radius:999px;
                          background:{severity_background};color:{severity_colour};
                          font-size:12px;font-weight:700;letter-spacing:0.4px;">
                          {escape(str(severity).upper())}
                        </span>
                      </td>
                    </tr>
                  </table>
                  <p style="margin:8px 0 18px;color:#475467;font-size:14px;">
                    {escape(str(channel))} &nbsp;|&nbsp; {escape(str(alert_date))}
                  </p>
                  <div style="margin:0 0 18px;padding:12px 14px;border-radius:6px;
                    background:{severity_background};color:{severity_colour};
                    font-size:14px;font-weight:600;">
                    {escape(str(reason))}
                  </div>
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                    style="font-size:14px;color:#344054;">
                    <tr>
                      <td style="padding:7px 0;border-bottom:1px solid #eaecf0;">Monthly budget</td>
                      <td align="right" style="padding:7px 0;border-bottom:1px solid #eaecf0;font-weight:600;">
                        {format_currency(budget_amount, currency_code)}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:7px 0;border-bottom:1px solid #eaecf0;">Month-to-date spend</td>
                      <td align="right" style="padding:7px 0;border-bottom:1px solid #eaecf0;font-weight:600;">
                        {format_currency(month_to_date_spend, currency_code)}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:7px 0;border-bottom:1px solid #eaecf0;">Expected spend to date</td>
                      <td align="right" style="padding:7px 0;border-bottom:1px solid #eaecf0;font-weight:600;">
                        {format_currency(expected_spend_to_date, currency_code)}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:7px 0;border-bottom:1px solid #eaecf0;">Projected month-end spend</td>
                      <td align="right" style="padding:7px 0;border-bottom:1px solid #eaecf0;
                        color:{severity_colour};font-weight:700;">
                        {format_currency(projected_month_end_spend, currency_code)}
                      </td>
                    </tr>
                    <tr>
                      <td style="padding:7px 0;">Projected amount over budget</td>
                      <td align="right" style="padding:7px 0;color:{severity_colour};font-weight:700;">
                        {overspend_text}
                      </td>
                    </tr>
                  </table>
                  <p style="margin:16px 0 0;color:#475467;font-size:13px;">
                    Pacing ratio: <strong>{pacing_ratio:.1%}</strong>
                    &nbsp;|&nbsp; Campaign ID: {escape(str(campaign_id))}
                  </p>
                </td>
              </tr>
            </table>
            """
        )

    return f"""
    <!doctype html>
    <html lang="en">
      <body style="margin:0;padding:0;background:#f2f4f7;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
          style="background:#f2f4f7;">
          <tr>
            <td align="center" style="padding:28px 12px;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                style="max-width:680px;">
                <tr>
                  <td style="padding:24px;border-radius:10px 10px 0 0;
                    background:{header_background};border-top:6px solid {header_colour};">
                    <p style="margin:0 0 8px;color:{header_colour};font-size:13px;
                      font-weight:700;letter-spacing:0.8px;">{overall_label}</p>
                    <h1 style="margin:0;color:#101828;font:700 26px Arial,sans-serif;">
                      Campaign spend requires attention
                    </h1>
                    <p style="margin:10px 0 0;color:#475467;font:15px Arial,sans-serif;">
                      {len(alerts)} campaign alert(s) were detected by the Marketing Spend Control Tower.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:22px;background:#ffffff;">
                    {"".join(alert_cards)}
                    <div style="padding:18px;border-radius:8px;background:#172b4d;color:#ffffff;">
                      <p style="margin:0 0 7px;font:700 15px Arial,sans-serif;">Recommended review</p>
                      <p style="margin:0;font:14px/1.6 Arial,sans-serif;color:#dbe5f4;">
                        Check campaign budgets, bidding, schedules and recent performance before
                        approving additional spend.
                      </p>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td style="padding:16px 22px;border-radius:0 0 10px 10px;
                    background:#e4e7ec;color:#667085;font:12px/1.5 Arial,sans-serif;">
                    Generated from the governed campaign alert mart. Email delivery is opt-in.
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def send_email(subject, text_body, html_body):
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
            "text": text_body,
            "html": html_body,
        }
    )

    return response

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the campaign alert email through Resend.",
    )
    parser.add_argument(
        "--test-critical",
        action="store_true",
        help="Use fictional data to preview or send a red critical test email.",
    )
    args = parser.parse_args()

    alerts = build_critical_test_alert() if args.test_critical else load_alerts()
    message = build_alert_message(alerts)

    print(message)

    if not alerts:
        print("\nNo email sent because there are no active alerts.")
        return

    if not args.send:
        print("\nPREVIEW MODE: no email was sent.")
        return

    alert_date = alerts[0][3]
    highest_severity = (
        "CRITICAL"
        if any(alert[4].lower() == "critical" for alert in alerts)
        else "WARNING"
    )
    subject_prefix = "[TEST] " if args.test_critical else ""
    subject = (
        f"{subject_prefix}{highest_severity}: "
        f"{len(alerts)} campaign spend alert(s) | {alert_date}"
    )
    html_message = build_alert_html(alerts)

    send_email(subject, message, html_message)
    print("\nEmail sent successfully.")


if __name__ == "__main__":
    main()