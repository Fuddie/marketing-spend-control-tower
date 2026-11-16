from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE_PATH = PROJECT_ROOT / "warehouse" / "marketing_spend.duckdb"

st.set_page_config(
    page_title="Marketing Spend Control Tower",
    page_icon="📊",
    layout="wide",
)


@st.cache_data(ttl=300, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    """Run one read-only query and close the connection immediately."""
    with duckdb.connect(str(WAREHOUSE_PATH), read_only=True) as connection:
        return connection.execute(sql).fetchdf()


@st.cache_data(ttl=300, show_spinner="Loading governed marketing marts...")
def load_dashboard_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    performance = run_query(
        """
        SELECT *
        FROM gold.fct_campaign_daily_performance
        ORDER BY metric_date, campaign_name
        """
    )

    pacing = run_query(
        """
        SELECT *
        FROM gold.mart_campaign_daily_pacing
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY campaign_id
            ORDER BY metric_date DESC
        ) = 1
        ORDER BY campaign_name
        """
    )

    alerts = run_query(
        """
        SELECT *
        FROM gold.mart_campaign_alerts
        ORDER BY alert_priority, campaign_name
        """
    )

    return performance, pacing, alerts


def convert_numeric_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    frame = frame.copy()
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def format_currency(value: float) -> str:
    return f"£{value:,.0f}"


def style_figure(figure):
    """Keep Plotly charts consistent with Streamlit's dark control-tower theme."""
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(color="#e6edf3"),
        legend=dict(
            bgcolor="rgba(0, 0, 0, 0)",
            borderwidth=0,
            font=dict(color="#e6edf3"),
        ),
    )
    figure.update_xaxes(gridcolor="rgba(255, 255, 255, 0.12)")
    figure.update_yaxes(gridcolor="rgba(255, 255, 255, 0.12)")
    return figure

VERIFIED_QUESTIONS = [
    "Which campaigns need immediate attention, and why?",
    "What are total spend, attributed net revenue, and ROAS?",
    "Which campaigns are projected to exceed budget, and by how much?",
]


def answer_dashboard_question(
    question: str,
    performance: pd.DataFrame,
    pacing: pd.DataFrame,
    alerts: pd.DataFrame,
) -> tuple[str, str, pd.DataFrame | None]:
    """Answer supported business questions from the governed dashboard data."""
    normalised = " ".join(question.lower().strip().split())

    if any(term in normalised for term in ["immediate attention", "active alert", "need attention"]):
        if alerts.empty:
            return "message", "No active alerts match the current filters.", None
        columns = [
            "campaign_name",
            "channel",
            "alert_severity",
            "alert_reason",
            "month_to_date_spend",
            "budget_amount",
            "projected_month_end_spend",
            "pacing_ratio",
        ]
        return (
            "alerts",
            f"{len(alerts)} campaign(s) need attention under the current filters.",
            alerts[columns].sort_values(["alert_priority", "campaign_name"]),
        )

    asks_for_totals = (
        "total spend" in normalised
        or ("spend" in normalised and "revenue" in normalised and "roas" in normalised)
    )
    if asks_for_totals:
        spend = float(performance["spend_amount"].sum())
        revenue = float(performance["attributed_net_revenue"].sum())
        question_roas = revenue / spend if spend else 0.0
        answer = (
            f"Total spend is £{spend:,.2f}, attributed net revenue is "
            f"£{revenue:,.2f}, and ROAS is {question_roas:.2f}x."
        )
        return "message", answer, None

    if (
        ("projected" in normalised or "projection" in normalised)
        and ("budget" in normalised or "overspend" in normalised)
    ):
        projected = pacing[
            pacing["projected_month_end_spend"] > pacing["budget_amount"]
        ].copy()
        if projected.empty:
            return "message", "No campaigns are projected to exceed budget.", None
        projected["projected_overspend"] = (
            projected["projected_month_end_spend"] - projected["budget_amount"]
        )
        columns = [
            "campaign_name",
            "channel",
            "budget_amount",
            "projected_month_end_spend",
            "projected_overspend",
            "pacing_ratio",
        ]
        return (
            "projection",
            f"{len(projected)} campaign(s) are projected to exceed budget.",
            projected[columns].sort_values("projected_overspend", ascending=False),
        )

    campaign_totals = (
        performance.groupby(["campaign_name", "channel"], as_index=False)
        .agg(
            spend=("spend_amount", "sum"),
            net_revenue=("attributed_net_revenue", "sum"),
        )
    )
    campaign_totals["roas"] = (
        campaign_totals["net_revenue"]
        .div(campaign_totals["spend"].where(campaign_totals["spend"] != 0))
        .fillna(0)
    )

    if "highest spend" in normalised or "most spend" in normalised:
        row = campaign_totals.sort_values("spend", ascending=False).iloc[0]
        return (
            "message",
            f"{row['campaign_name']} has the highest spend at £{row['spend']:,.2f}.",
            None,
        )

    if "highest revenue" in normalised or "most revenue" in normalised:
        row = campaign_totals.sort_values("net_revenue", ascending=False).iloc[0]
        return (
            "message",
            f"{row['campaign_name']} has the highest attributed net revenue at "
            f"£{row['net_revenue']:,.2f}.",
            None,
        )

    if "best roas" in normalised or "highest roas" in normalised:
        row = campaign_totals.sort_values("roas", ascending=False).iloc[0]
        return (
            "message",
            f"{row['campaign_name']} has the highest ROAS at {row['roas']:.2f}x.",
            None,
        )

    return (
        "unsupported",
        "This public dashboard answers the verified questions and common questions "
        "about spend, revenue, ROAS, alerts, and budget projections. Broader "
        "questions are available through the local Wren setup documented in the repository.",
        None,
    )


st.title("Marketing Spend Control Tower")
st.caption(
    "Campaign performance, budget pacing and prioritised alerts from governed dbt marts."
)

if not WAREHOUSE_PATH.exists():
    st.error(
        "The DuckDB warehouse was not found. Run the ingestion and dbt pipeline first."
    )
    st.stop()

try:
    performance_df, pacing_df, alerts_df = load_dashboard_data()
except Exception as error:
    st.error(f"Unable to load dashboard data: {error}")
    st.stop()

performance_df = convert_numeric_columns(
    performance_df,
    [
        "spend_amount",
        "impressions",
        "clicks",
        "platform_conversions",
        "attributed_conversions",
        "attributed_gross_revenue",
        "attributed_refund_amount",
        "attributed_net_revenue",
        "budget_amount",
        "expected_daily_spend",
    ],
)
pacing_df = convert_numeric_columns(
    pacing_df,
    [
        "spend_amount",
        "budget_amount",
        "expected_spend_to_date",
        "month_to_date_spend",
        "projected_month_end_spend",
        "month_to_date_net_revenue",
        "daily_roas",
        "month_to_date_roas",
        "pacing_ratio",
    ],
)
alerts_df = convert_numeric_columns(
    alerts_df,
    [
        "alert_priority",
        "spend_amount",
        "budget_amount",
        "month_to_date_spend",
        "expected_spend_to_date",
        "projected_month_end_spend",
        "month_to_date_net_revenue",
        "month_to_date_roas",
        "pacing_ratio",
    ],
)

performance_df["metric_date"] = pd.to_datetime(performance_df["metric_date"])
pacing_df["metric_date"] = pd.to_datetime(pacing_df["metric_date"])
if not alerts_df.empty:
    alerts_df["alert_date"] = pd.to_datetime(alerts_df["alert_date"])

if performance_df.empty:
    st.warning("No campaign performance data is available.")
    st.stop()

minimum_date = performance_df["metric_date"].min().date()
maximum_date = performance_df["metric_date"].max().date()

with st.sidebar:
    st.header("Filters")

    selected_dates = st.date_input(
        "Reporting period",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

    available_channels = sorted(performance_df["channel"].dropna().unique().tolist())
    selected_channels = st.multiselect(
        "Channel",
        options=available_channels,
        placeholder="All channels",
    )
    effective_channels = selected_channels or available_channels

    available_campaigns = sorted(
        performance_df.loc[
            performance_df["channel"].isin(effective_channels), "campaign_name"
        ]
        .dropna()
        .unique()
        .tolist()
    )
    selected_campaigns = st.multiselect(
        "Campaign",
        options=available_campaigns,
        placeholder="All campaigns",
    )
    effective_campaigns = selected_campaigns or available_campaigns

    if st.button("Refresh data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates

filtered_performance = performance_df[
    performance_df["metric_date"].dt.date.between(start_date, end_date)
    & performance_df["channel"].isin(effective_channels)
    & performance_df["campaign_name"].isin(effective_campaigns)
].copy()

filtered_pacing = pacing_df[
    pacing_df["channel"].isin(effective_channels)
    & pacing_df["campaign_name"].isin(effective_campaigns)
].copy()

if alerts_df.empty:
    filtered_alerts = alerts_df.copy()
else:
    filtered_alerts = alerts_df[
        alerts_df["channel"].isin(effective_channels)
        & alerts_df["campaign_name"].isin(effective_campaigns)
        & alerts_df["alert_date"].dt.date.between(start_date, end_date)
    ].copy()

if filtered_performance.empty:
    st.warning("No records match the selected filters.")
    st.stop()

total_spend = float(filtered_performance["spend_amount"].sum())
net_revenue = float(filtered_performance["attributed_net_revenue"].sum())
attributed_conversions = int(
    filtered_performance["attributed_conversions"].fillna(0).sum()
)
roas = net_revenue / total_spend if total_spend else 0.0
active_alerts = len(filtered_alerts)

kpi_columns = st.columns(5)
kpi_columns[0].metric("Spend", format_currency(total_spend))
kpi_columns[1].metric("Attributed net revenue", format_currency(net_revenue))
kpi_columns[2].metric("ROAS", f"{roas:.2f}x")
kpi_columns[3].metric("Attributed conversions", f"{attributed_conversions:,}")
kpi_columns[4].metric("Active alerts", f"{active_alerts:,}")

daily_summary = (
    filtered_performance.groupby("metric_date", as_index=False)
    .agg(
        spend_amount=("spend_amount", "sum"),
        expected_daily_spend=("expected_daily_spend", "sum"),
        attributed_net_revenue=("attributed_net_revenue", "sum"),
    )
    .sort_values("metric_date")
)

spend_trend = daily_summary.melt(
    id_vars="metric_date",
    value_vars=["spend_amount", "expected_daily_spend"],
    var_name="series",
    value_name="amount",
)
spend_trend["series"] = spend_trend["series"].map(
    {
        "spend_amount": "Actual spend",
        "expected_daily_spend": "Expected spend",
    }
)

left_chart, right_chart = st.columns(2)

with left_chart:
    st.subheader("Daily spend against plan")
    spend_figure = px.line(
        spend_trend,
        x="metric_date",
        y="amount",
        color="series",
        markers=True,
        labels={"metric_date": "Date", "amount": "GBP", "series": ""},
        color_discrete_map={
            "Actual spend": "#2f80ed",
            "Expected spend": "#f2c94c",
        },
    )
    spend_figure.update_layout(
        legend_orientation="h",
        legend_y=1.12,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(style_figure(spend_figure), use_container_width=True)

with right_chart:
    st.subheader("Daily spend and attributed revenue")
    revenue_figure = px.bar(
        daily_summary,
        x="metric_date",
        y=["spend_amount", "attributed_net_revenue"],
        barmode="group",
        labels={"metric_date": "Date", "value": "GBP", "variable": ""},
        color_discrete_map={
            "spend_amount": "#56ccf2",
            "attributed_net_revenue": "#27ae60",
        },
    )
    revenue_figure.for_each_trace(
        lambda trace: trace.update(
            name={
                "spend_amount": "Spend",
                "attributed_net_revenue": "Net revenue",
            }.get(trace.name, trace.name)
        )
    )
    revenue_figure.update_layout(
        legend_orientation="h",
        legend_y=1.12,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(style_figure(revenue_figure), use_container_width=True)

campaign_summary = (
    filtered_performance.groupby(["campaign_name", "channel"], as_index=False)
    .agg(
        spend=("spend_amount", "sum"),
        net_revenue=("attributed_net_revenue", "sum"),
        conversions=("attributed_conversions", "sum"),
    )
)
campaign_summary["roas"] = (
    campaign_summary["net_revenue"]
    .div(campaign_summary["spend"].where(campaign_summary["spend"] != 0))
    .fillna(0)
)

campaign_chart, pacing_chart = st.columns(2)

with campaign_chart:
    st.subheader("Campaign performance")
    campaign_figure = px.bar(
        campaign_summary.sort_values("net_revenue", ascending=True),
        x="net_revenue",
        y="campaign_name",
        color="channel",
        orientation="h",
        hover_data={"spend": ":,.2f", "roas": ":.2f"},
        labels={
            "net_revenue": "Attributed net revenue (GBP)",
            "campaign_name": "",
            "channel": "Channel",
        },
    )
    campaign_figure.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(style_figure(campaign_figure), use_container_width=True)

with pacing_chart:
    st.subheader("Current budget pacing")
    if filtered_pacing.empty:
        st.info("No current pacing records match the filters.")
    else:
        pacing_figure = px.bar(
            filtered_pacing.sort_values("pacing_ratio", ascending=True),
            x="pacing_ratio",
            y="campaign_name",
            color="pacing_status",
            orientation="h",
            hover_data={
                "month_to_date_spend": ":,.2f",
                "budget_amount": ":,.2f",
                "projected_month_end_spend": ":,.2f",
            },
            labels={
                "pacing_ratio": "Pacing ratio",
                "campaign_name": "",
                "pacing_status": "Status",
            },
            category_orders={
                "pacing_status": ["critical", "warning", "normal"],
            },
            color_discrete_map={
                "critical": "#eb5757",
                "warning": "#f2c94c",
                "normal": "#27ae60",
            },
        )
        pacing_figure.add_vline(x=1.0, line_dash="dash", line_color="#bdbdbd")
        pacing_figure.update_layout(margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(style_figure(pacing_figure), use_container_width=True)


st.divider()
st.subheader("Verified questions")
st.caption(
    "These questions use the same governed marts as the dashboard. "
    "Answers respect the current reporting, channel, and campaign filters."
)

verified_columns = st.columns(3)
selected_verified_question = ""
for index, verified_question in enumerate(VERIFIED_QUESTIONS):
    if verified_columns[index].button(
        verified_question,
        key=f"verified_question_{index}",
        use_container_width=True,
    ):
        selected_verified_question = verified_question

st.subheader("Ask the control tower in English")
question_text = st.text_input(
    "Business question",
    placeholder="For example: Which campaign has the highest ROAS?",
    label_visibility="collapsed",
)
ask_question = st.button("Run question", type="primary")
active_question = selected_verified_question or (
    question_text.strip() if ask_question else ""
)

if active_question:
    st.markdown(f"**Question:** {active_question}")
    answer_type, answer_text, answer_table = answer_dashboard_question(
        active_question,
        filtered_performance,
        filtered_pacing,
        filtered_alerts,
    )
    if answer_type == "unsupported":
        st.info(answer_text)
    else:
        st.success(answer_text)
        if answer_table is not None:
            question_column_config = {
                "campaign_name": "Campaign",
                "channel": "Channel",
                "alert_severity": "Severity",
                "alert_reason": "Reason",
                "month_to_date_spend": st.column_config.NumberColumn(
                    "MTD spend", format="£%.2f"
                ),
                "budget_amount": st.column_config.NumberColumn(
                    "Budget", format="£%.2f"
                ),
                "projected_month_end_spend": st.column_config.NumberColumn(
                    "Projected spend", format="£%.2f"
                ),
                "projected_overspend": st.column_config.NumberColumn(
                    "Projected overspend", format="£%.2f"
                ),
                "pacing_ratio": st.column_config.NumberColumn(
                    "Pacing ratio", format="%.2f"
                ),
            }
            st.dataframe(
                answer_table,
                use_container_width=True,
                hide_index=True,
                column_config=question_column_config,
            )

st.caption(
    "The public question box uses deterministic answers from the governed marts. "
    "The local Wren setup supports broader natural-language questions."
)


st.subheader("Campaign detail")
campaign_table = campaign_summary[
    ["campaign_name", "channel", "spend", "net_revenue", "conversions", "roas"]
].sort_values("net_revenue", ascending=False)
st.dataframe(
    campaign_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "campaign_name": "Campaign",
        "channel": "Channel",
        "spend": st.column_config.NumberColumn("Spend", format="£%.2f"),
        "net_revenue": st.column_config.NumberColumn(
            "Attributed net revenue",
            format="£%.2f",
        ),
        "conversions": st.column_config.NumberColumn(
            "Attributed conversions",
            format="%d",
        ),
        "roas": st.column_config.NumberColumn("ROAS", format="%.2fx"),
    },
)

st.subheader("Prioritised campaign alerts")
if filtered_alerts.empty:
    st.success("No active alerts match the selected filters.")
else:
    alert_columns = [
        "alert_priority",
        "alert_severity",
        "campaign_name",
        "channel",
        "alert_reason",
        "month_to_date_spend",
        "budget_amount",
        "projected_month_end_spend",
        "month_to_date_roas",
        "pacing_ratio",
    ]
    st.dataframe(
        filtered_alerts[alert_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "alert_priority": "Priority",
            "alert_severity": "Severity",
            "campaign_name": "Campaign",
            "channel": "Channel",
            "alert_reason": "Reason",
            "month_to_date_spend": st.column_config.NumberColumn(
                "MTD spend",
                format="£%.2f",
            ),
            "budget_amount": st.column_config.NumberColumn(
                "Budget",
                format="£%.2f",
            ),
            "projected_month_end_spend": st.column_config.NumberColumn(
                "Projected spend",
                format="£%.2f",
            ),
            "month_to_date_roas": st.column_config.NumberColumn(
                "MTD ROAS",
                format="%.2fx",
            ),
            "pacing_ratio": st.column_config.NumberColumn(
                "Pacing ratio",
                format="%.2f",
            ),
        },
    )

st.caption(
    "Source: gold dbt marts in DuckDB. Cached for five minutes and queried read-only."
)
