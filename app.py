from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="Ecommerce Customers Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NUMERIC_COLUMNS = [
    "Avg. Session Length",
    "Time on App",
    "Time on Website",
    "Length of Membership",
    "Yearly Amount Spent",
]
SPEND = "Yearly Amount Spent"
MEMBERSHIP = "Length of Membership"
APP_TIME = "Time on App"
WEB_TIME = "Time on Website"
SESSION = "Avg. Session Length"
MEMBERSHIP_GROUPS = ["New", "Growing", "Established", "Long-term"]

ALIASES = {
    "avgsessionlength": SESSION,
    "averagesessionlength": SESSION,
    "sessionlength": SESSION,
    "timeonapp": APP_TIME,
    "timeonwebsite": WEB_TIME,
    "lengthofmembership": MEMBERSHIP,
    "yearlyamountspent": SPEND,
    "email": "Email",
    "customeremail": "Email",
}


def normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for column in data.columns:
        key = re.sub(r"[^a-z0-9]", "", str(column).lower())
        renamed[column] = ALIASES.get(key, str(column).strip())
    return data.rename(columns=renamed)


def read_customer_data(uploaded_file):
    if uploaded_file is not None:
        source = uploaded_file.name
        data = pd.read_csv(uploaded_file)
    else:
        root = Path(__file__).resolve().parent
        candidates = [
            root / "Ecommerce Customers.csv",
            root / "Ecommerce_Customers.csv",
            root / "data" / "Ecommerce Customers.csv",
            root / "data" / "Ecommerce_Customers.csv",
        ]
        path = next((candidate for candidate in candidates if candidate.is_file()), None)
        if path is None:
            return None, None, None
        source = path.name
        data = pd.read_csv(path)

    data = normalize_columns(data)
    missing = [column for column in NUMERIC_COLUMNS if column not in data.columns]
    if missing:
        return None, source, f"Missing required columns: {', '.join(missing)}"

    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=NUMERIC_COLUMNS).copy()
    if data.empty:
        return None, source, "No rows contain valid values for all five analysis columns."

    if "Email" not in data.columns:
        data["Email"] = [f"Customer {index + 1}" for index in range(len(data))]
    return data, source, None


def add_membership_groups(data: pd.DataFrame) -> pd.DataFrame:
    grouped = data.copy()
    ranks = grouped[MEMBERSHIP].rank(method="first")
    group_count = min(len(MEMBERSHIP_GROUPS), len(grouped))
    grouped["Membership Group"] = pd.qcut(
        ranks,
        q=group_count,
        labels=MEMBERSHIP_GROUPS[:group_count],
    )
    return grouped


def format_money(value: float) -> str:
    return f"${value:,.2f}"


st.markdown(
    """
    <style>
    :root {
        --ink: #173b36;
        --muted: #64736d;
        --paper: #f5f7f3;
        --line: #dce5dc;
        --green: #27736a;
        --coral: #e88365;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }
    section[data-testid="stSidebar"] { background: #eaf0e9; border-right: 1px solid var(--line); }
    .eyebrow { color: var(--green); font-size: .75rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
    .dashboard-title { color: var(--ink); font-size: clamp(2rem, 3vw, 3rem); line-height: 1.08; font-weight: 760; margin: .25rem 0 .45rem; }
    .dashboard-subtitle { color: var(--muted); font-size: 1rem; margin-bottom: 1.6rem; }
    .kpi-card { background: #fff; border: 1px solid var(--line); border-top: 3px solid var(--green); border-radius: 8px; padding: 1rem 1.15rem; min-height: 112px; }
    .kpi-label { color: var(--muted); font-size: .83rem; font-weight: 650; }
    .kpi-value { color: var(--ink); font-size: clamp(1.35rem, 2vw, 1.85rem); font-weight: 760; margin-top: .45rem; white-space: nowrap; }
    .section-heading { color: var(--ink); font-size: 1.2rem; font-weight: 730; margin: 1.35rem 0 .1rem; }
    .section-note { color: var(--muted); font-size: .88rem; margin: 0 0 .65rem; }
    .data-card { border-left: 4px solid var(--coral); background: #fff; padding: .9rem 1rem; border-radius: 4px; color: var(--ink); }
    .insight { color: var(--muted); font-size: .88rem; padding: .45rem 0 .9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Dashboard controls")
    uploaded_file = st.file_uploader("Upload customer CSV", type=["csv"])
    st.caption("Or place `Ecommerce Customers.csv` beside app.py (or in a `data` folder).")

data_error = None
try:
    customers, data_source, data_error = read_customer_data(uploaded_file)
except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as error:
    customers, data_source = None, None
    data_error = f"The CSV could not be read: {error}"

if customers is None:
    if data_error:
        st.error(data_error)
        st.info("Required columns: Avg. Session Length, Time on App, Time on Website, Length of Membership, and Yearly Amount Spent.")
    else:
        st.markdown('<div class="eyebrow">Customer intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="dashboard-title">Ecommerce Customers</div>', unsafe_allow_html=True)
        st.warning("Customer CSV not found. Upload it in the sidebar, or add `Ecommerce Customers.csv` beside app.py or under `data/`.")
    st.stop()

st.sidebar.divider()
st.sidebar.markdown("#### Filter customer segments")


def numeric_filter(label, column):
    lower = float(customers[column].min())
    upper = float(customers[column].max())
    if lower == upper:
        st.sidebar.caption(f"{label}: all rows have the same value ({lower:g}).")
        return lower, upper
    return st.sidebar.slider(
        label,
        min_value=lower,
        max_value=upper,
        value=(lower, upper),
        step=max((upper - lower) / 100, 0.01),
    )


spend_range = numeric_filter("Yearly amount spent", SPEND)
membership_range = numeric_filter("Membership duration", MEMBERSHIP)
app_range = numeric_filter("Time on app", APP_TIME)
website_range = numeric_filter("Time on website", WEB_TIME)

filtered = customers[
    customers[SPEND].between(*spend_range)
    & customers[MEMBERSHIP].between(*membership_range)
    & customers[APP_TIME].between(*app_range)
    & customers[WEB_TIME].between(*website_range)
].copy()

st.markdown('<div class="eyebrow">Customer intelligence / 01</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-title">Ecommerce Customers</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="dashboard-subtitle">A focused view of customer behavior, membership, and annual value.</div>',
    unsafe_allow_html=True,
)

if filtered.empty:
    st.warning("No customers match these filters. Widen one or more ranges to continue.")
    st.stop()

kpis = [
    ("Total Customers", f"{len(filtered):,}"),
    ("Average Yearly Spending", format_money(filtered[SPEND].mean())),
    ("Average App Time", f"{filtered[APP_TIME].mean():.2f} hrs"),
    ("Average Website Time", f"{filtered[WEB_TIME].mean():.2f} hrs"),
]
columns = st.columns(4, gap="medium")
for column, (label, value) in zip(columns, kpis):
    column.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-heading">Explore the seven questions</div>', unsafe_allow_html=True)
st.markdown('<div class="section-note">All charts respond to the sidebar filters.</div>', unsafe_allow_html=True)

chart_config = {"displayModeBar": True, "displaylogo": False, "responsive": True}
plotly_layout = {"paper_bgcolor": "rgba(0,0,0,0)", "plot_bgcolor": "rgba(0,0,0,0)", "font_color": "#173b36", "margin": {"l": 12, "r": 12, "t": 24, "b": 12}}

left, right = st.columns(2, gap="large")
with left:
    st.markdown("**1. Average Yearly Amount Spent**")
    histogram = px.histogram(filtered, x=SPEND, nbins=30, color_discrete_sequence=["#27736a"], labels={SPEND: "Yearly amount spent ($)", "count": "Customers"})
    histogram.update_layout(**plotly_layout, yaxis_title="Customers", xaxis_title="Yearly amount spent ($)")
    st.plotly_chart(histogram, use_container_width=True, config=chart_config)
    st.markdown(f'<div class="insight">The filtered customer average is {format_money(filtered[SPEND].mean())}.</div>', unsafe_allow_html=True)

with right:
    st.markdown("**2. Strongest Factors Related to Yearly Spending**")
    correlation = filtered[NUMERIC_COLUMNS].corr()
    heatmap = px.imshow(correlation, text_auto=".2f", aspect="auto", color_continuous_scale=[[0, "#e88365"], [0.5, "#f5f7f3"], [1, "#27736a"]], zmin=-1, zmax=1, labels={"color": "Correlation"})
    heatmap.update_layout(**plotly_layout, coloraxis_colorbar_title="Correlation")
    st.plotly_chart(heatmap, use_container_width=True, config=chart_config)
    spending_correlations = correlation[SPEND].drop(SPEND).dropna()
    strongest = spending_correlations.abs().idxmax() if not spending_correlations.empty else None
    if strongest is None:
        st.markdown('<div class="insight">A correlation is unavailable for this filtered segment.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="insight">The strongest relationship with yearly spending is <b>{strongest}</b> (r = {correlation.loc[strongest, SPEND]:.2f}); correlation does not imply causation.</div>', unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("**3. App vs Website Time**")
    channel_means = pd.DataFrame({"Channel": ["Time on App", "Time on Website"], "Average time (hours)": [filtered[APP_TIME].mean(), filtered[WEB_TIME].mean()]})
    channel_chart = px.bar(channel_means, x="Channel", y="Average time (hours)", color="Channel", color_discrete_map={"Time on App": "#27736a", "Time on Website": "#e88365"}, text_auto=".2f")
    channel_chart.update_layout(**plotly_layout, showlegend=False, xaxis_title="", yaxis_title="Average time (hours)")
    st.plotly_chart(channel_chart, use_container_width=True, config=chart_config)
    more_used = "the app" if filtered[APP_TIME].mean() >= filtered[WEB_TIME].mean() else "the website"
    st.markdown(f'<div class="insight">Customers spend more average time on {more_used}.</div>', unsafe_allow_html=True)

with right:
    st.markdown("**4. Membership Duration vs Yearly Spending**")
    membership_scatter = px.scatter(filtered, x=MEMBERSHIP, y=SPEND, color=MEMBERSHIP, color_continuous_scale="Teal", hover_data=["Email"], labels={MEMBERSHIP: "Membership duration (years)", SPEND: "Yearly amount spent ($)"})
    membership_scatter.update_layout(**plotly_layout, coloraxis_colorbar_title="Membership\n(years)")
    st.plotly_chart(membership_scatter, use_container_width=True, config=chart_config)
    membership_corr = filtered[MEMBERSHIP].corr(filtered[SPEND])
    membership_text = f"{membership_corr:.2f}" if pd.notna(membership_corr) else "unavailable"
    st.markdown(f'<div class="insight">Membership duration and yearly spending have a correlation of {membership_text}.</div>', unsafe_allow_html=True)

left, right = st.columns(2, gap="large")
with left:
    st.markdown("**5. Top 5 Customers by Yearly Spending**")
    top_customers = filtered.nlargest(min(5, len(filtered)), SPEND).sort_values(SPEND)
    top_chart = px.bar(top_customers, x=SPEND, y="Email", orientation="h", color=SPEND, color_continuous_scale="Teal", labels={SPEND: "Yearly amount spent ($)", "Email": "Customer"}, hover_data={SPEND: ":$.2f"})
    top_chart.update_layout(**plotly_layout, coloraxis_showscale=False, xaxis_title="Yearly amount spent ($)", yaxis_title="")
    st.plotly_chart(top_chart, use_container_width=True, config=chart_config)
    st.markdown("<div class='insight'>Ranked within the currently selected customer segment.</div>", unsafe_allow_html=True)

with right:
    st.markdown("**6. Average Spending by Membership Groups**")
    grouped = add_membership_groups(filtered)
    group_means = grouped.groupby("Membership Group", observed=True)[SPEND].mean().reindex(MEMBERSHIP_GROUPS).dropna().rename("Average yearly spending ($)").reset_index()
    group_chart = px.bar(group_means, x="Membership Group", y="Average yearly spending ($)", color="Membership Group", color_discrete_sequence=["#27736a", "#64a497", "#e8a17b", "#e88365"], text_auto="$.2f", category_orders={"Membership Group": MEMBERSHIP_GROUPS})
    group_chart.update_layout(**plotly_layout, showlegend=False, xaxis_title="Membership duration group", yaxis_title="Average yearly spending ($)")
    st.plotly_chart(group_chart, use_container_width=True, config=chart_config)
    st.markdown("<div class='insight'>Membership groups are divided into four equal-sized duration bands within the filtered data.</div>", unsafe_allow_html=True)

st.markdown("**7. Session Length vs Yearly Spending**")
session_scatter = px.scatter(filtered, x=SESSION, y=SPEND, color=MEMBERSHIP, color_continuous_scale="Teal", hover_data=["Email"], labels={SESSION: "Average session length (minutes)", SPEND: "Yearly amount spent ($)"})
session_scatter.update_layout(**plotly_layout, coloraxis_colorbar_title="Membership\n(years)")
st.plotly_chart(session_scatter, use_container_width=True, config=chart_config)
session_corr = filtered[SESSION].corr(filtered[SPEND])
session_text = f"{session_corr:.2f}" if pd.notna(session_corr) else "unavailable"
st.markdown(f'<div class="insight">Session length and yearly spending have a correlation of {session_text}.</div>', unsafe_allow_html=True)

st.markdown('<div class="section-heading">Data card & conclusion</div>', unsafe_allow_html=True)
data_card, conclusion = st.columns([1, 2], gap="large")
with data_card:
    st.markdown(
        f'<div class="data-card"><b>Data card</b><br>Source: {data_source}<br>Customers in dataset: {len(customers):,}<br>Customers in view: {len(filtered):,}<br>Analysis fields: {len(NUMERIC_COLUMNS)}</div>',
        unsafe_allow_html=True,
    )
with conclusion:
    if strongest is None:
        conclusion_text = "There are not enough varied observations to calculate correlations for the selected customers."
    else:
        spending_direction = "higher" if membership_corr > 0 else "lower" if membership_corr < 0 else "not linearly associated"
        membership_text = f"{membership_corr:.2f}" if pd.notna(membership_corr) else "unavailable"
        conclusion_text = f"The selected customers show their strongest spending relationship with **{strongest}**. Longer membership is associated with **{spending_direction}** yearly spending (r = {membership_text}); these are descriptive patterns, not evidence of cause."
    st.markdown(f"{conclusion_text} The sidebar filters update the full analysis together.")

st.caption("Time measures and dollar amounts use the units recorded in the source dataset.")