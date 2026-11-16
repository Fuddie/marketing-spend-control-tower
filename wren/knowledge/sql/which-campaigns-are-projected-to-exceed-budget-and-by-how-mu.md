---
nl: Which campaigns are projected to exceed budget, and by how much?
sql: SELECT campaign_name, channel, budget_amount, projected_month_end_spend, ROUND(projected_month_end_spend
  / NULLIF(budget_amount, 0), 2) AS projected_budget_ratio FROM campaign_alerts WHERE
  is_projected_to_exceed_budget = TRUE ORDER BY projected_budget_ratio DESC
source: user
datasource: duckdb
---
