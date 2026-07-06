import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="COVID-19 Regional Impact Tracker",
    page_icon="🦠",
    layout="wide"
)

st.title("🦠 COVID-19 Regional Impact Tracker")
st.markdown("Health department dashboard — track cases, deaths, recoveries & vaccinations by region.")

# ─── Simulated Data Generation ───────────────────────────────────────────────
@st.cache_data
def generate_data():
    regions = ["North Zone", "South Zone", "East Zone", "West Zone", "Central Zone"]
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(180)]

    records = []
    base = {"North Zone": 300, "South Zone": 500, "East Zone": 200,
            "West Zone": 400, "Central Zone": 350}

    for region in regions:
        active = base[region]
        for date in dates:
            new_cases   = max(0, int(active * random.uniform(0.03, 0.08)))
            recoveries  = max(0, int(active * random.uniform(0.04, 0.07)))
            deaths      = max(0, int(active * random.uniform(0.001, 0.005)))
            vaccinated  = min(100, round(random.uniform(40, 80) + (dates.index(date) * 0.1), 1))
            active      = max(0, active + new_cases - recoveries - deaths)

            records.append({
                "date":        date,
                "region":      region,
                "new_cases":   new_cases,
                "active":      active,
                "recoveries":  recoveries,
                "deaths":      deaths,
                "vaccinated":  vaccinated
            })

    return pd.DataFrame(records)

df = generate_data()

# ─── Sidebar Filters ─────────────────────────────────────────────────────────
st.sidebar.header("Filters")

regions_all  = df["region"].unique().tolist()
sel_regions  = st.sidebar.multiselect("Select Regions", regions_all, default=regions_all)

min_date, max_date = df["date"].min(), df["date"].max()
date_range = st.sidebar.date_input("Date Range", [min_date, max_date],
                                    min_value=min_date, max_value=max_date)

metric = st.sidebar.selectbox("Primary Metric",
    ["new_cases", "active", "recoveries", "deaths", "vaccinated"],
    format_func=lambda x: x.replace("_", " ").title())

chart_type = st.sidebar.radio("Chart Type", ["Line", "Bar", "Area"])

# ─── Filter Data ─────────────────────────────────────────────────────────────
start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
filtered = df[
    (df["region"].isin(sel_regions)) &
    (df["date"] >= start) &
    (df["date"] <= end)
]

# ─── KPI Metrics ─────────────────────────────────────────────────────────────
st.subheader("Summary Metrics")
k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total Cases",     f"{filtered['new_cases'].sum():,}")
k2.metric("Active Cases",    f"{filtered['active'].sum():,}")
k3.metric("Recoveries",      f"{filtered['recoveries'].sum():,}")
k4.metric("Deaths",          f"{filtered['deaths'].sum():,}")
k5.metric("Avg Vaccination", f"{filtered['vaccinated'].mean():.1f}%")

st.divider()

# ─── Trend Chart ─────────────────────────────────────────────────────────────
st.subheader(f"{metric.replace('_',' ').title()} Trend by Region")

trend = filtered.groupby(["date", "region"])[metric].sum().reset_index()

if chart_type == "Line":
    fig = px.line(trend, x="date", y=metric, color="region",
                  labels={"date": "Date", metric: metric.replace("_", " ").title()})
elif chart_type == "Bar":
    fig = px.bar(trend, x="date", y=metric, color="region", barmode="group",
                 labels={"date": "Date", metric: metric.replace("_", " ").title()})
else:
    fig = px.area(trend, x="date", y=metric, color="region",
                  labels={"date": "Date", metric: metric.replace("_", " ").title()})

fig.update_layout(legend_title="Region", hovermode="x unified", height=400)
st.plotly_chart(fig, use_container_width=True)

# ─── Two-Column Charts ────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cases vs Recoveries vs Deaths")
    summary = filtered.groupby("region")[["new_cases", "recoveries", "deaths"]].sum().reset_index()
    fig2 = px.bar(summary.melt(id_vars="region", var_name="type", value_name="count"),
                  x="region", y="count", color="type", barmode="group",
                  color_discrete_map={"new_cases": "#378ADD", "recoveries": "#639922", "deaths": "#E24B4A"})
    fig2.update_layout(height=350, legend_title="Type")
    st.plotly_chart(fig2, use_container_width=True)

with col2:
    st.subheader("Vaccination Coverage by Region")
    vax = filtered.groupby("region")["vaccinated"].mean().reset_index()
    fig3 = px.bar(vax, x="vaccinated", y="region", orientation="h",
                  color="vaccinated", color_continuous_scale="Greens",
                  labels={"vaccinated": "Avg Vaccination %", "region": ""})
    fig3.update_layout(height=350, coloraxis_showscale=False)
    fig3.update_traces(text=vax["vaccinated"].round(1).astype(str) + "%", textposition="outside")
    st.plotly_chart(fig3, use_container_width=True)

# ─── Heatmap ─────────────────────────────────────────────────────────────────
st.subheader("Monthly Case Heatmap by Region")
filtered["month"] = filtered["date"].dt.strftime("%b %Y")
heat = filtered.groupby(["region", "month"])["new_cases"].sum().reset_index()
month_order = sorted(heat["month"].unique(), key=lambda x: datetime.strptime(x, "%b %Y"))
heat["month"] = pd.Categorical(heat["month"], categories=month_order, ordered=True)
heat = heat.sort_values("month")
pivot = heat.pivot(index="region", columns="month", values="new_cases")

fig4 = px.imshow(pivot, color_continuous_scale="Reds",
                 labels={"color": "New Cases"}, aspect="auto")
fig4.update_layout(height=300)
st.plotly_chart(fig4, use_container_width=True)

# ─── Region Summary Table ─────────────────────────────────────────────────────
st.subheader("Region-wise Summary Table")

table = filtered.groupby("region").agg(
    Total_Cases   = ("new_cases",  "sum"),
    Active_Cases  = ("active",     "mean"),
    Recoveries    = ("recoveries", "sum"),
    Deaths        = ("deaths",     "sum"),
    Avg_Vax       = ("vaccinated", "mean")
).reset_index()

table["Recovery Rate (%)"] = (table["Recoveries"] / table["Total_Cases"] * 100).round(1)
table["Fatality Rate (%)"] = (table["Deaths"]     / table["Total_Cases"] * 100).round(2)
table["Avg_Vax"]           = table["Avg_Vax"].round(1)
table["Active_Cases"]      = table["Active_Cases"].astype(int)

def severity(row):
    if row["Fatality Rate (%)"] > 0.3:  return "🔴 High"
    if row["Fatality Rate (%)"] > 0.15: return "🟡 Medium"
    return "🟢 Low"

table["Severity"] = table.apply(severity, axis=1)
table.columns = [c.replace("_", " ") for c in table.columns]
st.dataframe(table.set_index("region"), use_container_width=True)

# ─── Pie Chart ────────────────────────────────────────────────────────────────
st.subheader("Case Distribution by Region")
pie_data = filtered.groupby("region")["new_cases"].sum().reset_index()
fig5 = px.pie(pie_data, names="region", values="new_cases", hole=0.4)
fig5.update_traces(textposition="inside", textinfo="percent+label")
fig5.update_layout(height=380, showlegend=True)
st.plotly_chart(fig5, use_container_width=True)

# ─── Footer ──────────────────────────────────────────────────────────────────
st.divider()
st.caption("COVID-19 Regional Impact Tracker | Data is simulated for demonstration purposes.")
