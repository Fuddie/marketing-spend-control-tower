# Business requirements

## Purpose

The Marketing Spend Control Tower gives marketing and finance teams a consistent view of campaign spend, attributed revenue, budget pacing, and overspend risk.

## Stakeholders

- Marketing managers who monitor campaign delivery
- Channel owners who adjust spend and budgets
- Finance partners who review marketing efficiency
- Analytics engineers who maintain trusted reporting models

## Business questions

The project must answer:

1. How much has been spent and how much net revenue was attributed to that spend?
2. Which campaigns are ahead of or behind their expected spending pace?
3. Which campaigns are projected to exceed their monthly budget?
4. Which campaign alerts require immediate attention?
5. Can the same metric definitions be used across the dashboard, alerts, and semantic queries?

## Metric definitions

| Metric | Definition |
|---|---|
| Spend | Advertising spend recorded by campaign and date |
| Attributed conversions | Completed orders linked to a campaign through last-click attribution |
| Attributed gross revenue | Gross revenue from completed attributed orders |
| Attributed refund amount | Completed refunds associated with attributed orders |
| Attributed net revenue | Attributed gross revenue minus attributed refund amount |
| ROAS | Attributed net revenue divided by spend |
| Expected spend to date | Monthly budget allocated across active campaign days, accumulated through the reporting date |
| Pacing ratio | Month-to-date spend divided by expected spend to date |
| Projected month-end spend | Average daily spend to date multiplied by active days in the budget month |

All financial reporting uses GBP.

## Alert rules

A campaign is classified as:

- **Critical** when spend continues after the campaign end date
- **Critical** when spend exists without an active budget
- **Critical** when month-to-date spend exceeds the monthly budget
- **Warning** when the pacing ratio is above 1.10
- **Normal** when none of the conditions above apply

Critical alerts have priority 1. Warning alerts have priority 2. Lower priority values are reviewed first.

## Functional requirements

- Generate reproducible campaign, budget, spend, order, attribution, and refund data
- Load complete daily extracts into typed Bronze tables
- Reject an older extract when a newer snapshot has already been loaded
- Validate source relationships, dates, amounts, currencies, and attribution rules
- Build staging, intermediate, and gold models with dbt
- Preserve campaign budget history and apply the correct version by date
- Reconcile attributed net revenue to completed orders and refunds
- Produce daily campaign performance and budget pacing marts
- Surface prioritised campaign alerts
- Support dashboard filtering by reporting period, channel, and campaign
- Allow alert preview without sending an email
- Require explicit configuration before sending alerts through Resend
- Expose governed campaign models and validated queries through Wren

## Reliability requirements

- Source generation must be deterministic for a given run date and random seed
- Bronze ingestion must run inside a transaction
- Database connections must be closed after use
- Dashboard queries must be read-only
- Generated databases, local connection files, and credentials must not be committed
- dbt and Bronze checks must fail the workflow when a data-quality rule is violated

## Acceptance criteria

The solution is accepted when:

- All 17 Bronze quality checks pass
- The dbt build completes without model or test failures
- Campaign-date records are unique in the daily performance mart
- Any post-end spend is classified as critical
- Dashboard totals reconcile to the gold marts
- Alert preview returns the same active alerts as the alert mart
- Wren returns the expected results for the saved business questions
