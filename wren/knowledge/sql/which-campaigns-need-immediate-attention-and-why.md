---
nl: Which campaigns need immediate attention, and why?
sql: SELECT campaign_name, channel, alert_severity, alert_reason, month_to_date_spend,
  budget_amount, projected_month_end_spend, pacing_ratio FROM campaign_alerts ORDER
  BY alert_priority
source: user
datasource: duckdb
---
