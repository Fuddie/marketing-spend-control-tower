---
nl: What are total spend, attributed net revenue, and ROAS?
sql: SELECT ROUND(SUM(spend_amount), 2) AS total_spend, ROUND(SUM(attributed_net_revenue),
  2) AS attributed_net_revenue, ROUND(SUM(attributed_net_revenue) / NULLIF(SUM(spend_amount),
  0), 2) AS roas FROM campaign_daily_performance
source: user
datasource: duckdb
---
