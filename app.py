"""
Customer Engagement & Product Utilization Analytics for Retention Strategy
The European Central Bank — Streamlit Dashboard

Run with:  streamlit run app.py
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ----------------------------------------------------------------------------
# Page config & styling
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="Customer Retention Analytics | European Central Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#1F3B57"
GOLD = "#C9A24B"
RED = "#B4453D"
GREY = "#8C9AA6"
GREEN = "#2E7D57"

st.markdown(f"""
<style>
    .main {{ background-color: #FAFBFC; }}
    h1, h2, h3 {{ color: {NAVY}; }}
    div[data-testid="stMetric"] {{
        background-color: white;
        border: 1px solid #E4E9ED;
        border-radius: 10px;
        padding: 14px 18px 8px 18px;
    }}
    div[data-testid="stMetricValue"] {{ color: {NAVY}; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: #EEF1F4; border-radius: 8px 8px 0 0; padding: 8px 16px;
    }}
    .stTabs [aria-selected="true"] {{ background-color: {NAVY}; color: white; }}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Data loading & engineering
# ----------------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv("European_Bank.csv")

    median_bal = df["Balance"].median()
    median_sal = df["EstimatedSalary"].median()

    def classify(row):
        active = row["IsActiveMember"] == 1
        high_bal = row["Balance"] > median_bal
        low_prod = row["NumOfProducts"] <= 1
        if active and not low_prod:
            return "Active Engaged"
        elif not active and low_prod:
            return "Inactive Disengaged"
        elif active and low_prod:
            return "Active Low-Product"
        elif not active and high_bal:
            return "Inactive High-Balance"
        else:
            return "Other"

    df["EngagementProfile"] = df.apply(classify, axis=1)
    df["AgeGroup"] = pd.cut(
        df["Age"], bins=[17, 30, 40, 50, 60, 100],
        labels=["18-30", "31-40", "41-50", "51-60", "60+"]
    )
    # Relationship Strength Index: 0-100 composite of activity + product depth + tenure
    df["RelationshipStrengthIndex"] = (
        df["IsActiveMember"] * 40
        + (df["NumOfProducts"].clip(upper=2) / 2) * 40
        + (df["Tenure"] / df["Tenure"].max()) * 20
    ).round(1)

    df["AtRiskPremium"] = (
        (df["Balance"] > median_bal)
        & (df["EstimatedSalary"] > median_sal)
        & (df["IsActiveMember"] == 0)
        & (df["Exited"] == 0)
    )

    return df, median_bal, median_sal


df_full, MEDIAN_BAL, MEDIAN_SAL = load_data()

# ----------------------------------------------------------------------------
# Sidebar — global filters (per brief: engagement, product sliders, thresholds)
# ----------------------------------------------------------------------------
st.sidebar.markdown(f"### 🏦 The European Central Bank")
st.sidebar.markdown("**Retention Analytics Filters**")
st.sidebar.markdown("---")

geo_sel = st.sidebar.multiselect(
    "Geography", options=sorted(df_full["Geography"].unique()),
    default=sorted(df_full["Geography"].unique())
)

engagement_sel = st.sidebar.multiselect(
    "Engagement profile",
    options=sorted(df_full["EngagementProfile"].unique()),
    default=sorted(df_full["EngagementProfile"].unique()),
)

active_sel = st.sidebar.radio(
    "Activity status", options=["All", "Active only", "Inactive only"], index=0, horizontal=True
)

prod_range = st.sidebar.slider(
    "Number of products held",
    min_value=int(df_full["NumOfProducts"].min()),
    max_value=int(df_full["NumOfProducts"].max()),
    value=(int(df_full["NumOfProducts"].min()), int(df_full["NumOfProducts"].max())),
)

bal_range = st.sidebar.slider(
    "Account balance (€)",
    min_value=0, max_value=int(df_full["Balance"].max()),
    value=(0, int(df_full["Balance"].max())), step=1000, format="€%d",
)

sal_range = st.sidebar.slider(
    "Estimated salary (€)",
    min_value=int(df_full["EstimatedSalary"].min()), max_value=int(df_full["EstimatedSalary"].max()),
    value=(int(df_full["EstimatedSalary"].min()), int(df_full["EstimatedSalary"].max())), step=1000, format="€%d",
)

age_range = st.sidebar.slider(
    "Age", min_value=int(df_full["Age"].min()), max_value=int(df_full["Age"].max()),
    value=(int(df_full["Age"].min()), int(df_full["Age"].max()))
)

st.sidebar.markdown("---")
if st.sidebar.button("↺ Reset filters"):
    st.rerun()

# Apply filters
df = df_full[
    df_full["Geography"].isin(geo_sel)
    & df_full["EngagementProfile"].isin(engagement_sel)
    & df_full["NumOfProducts"].between(prod_range[0], prod_range[1])
    & df_full["Balance"].between(bal_range[0], bal_range[1])
    & df_full["EstimatedSalary"].between(sal_range[0], sal_range[1])
    & df_full["Age"].between(age_range[0], age_range[1])
].copy()

if active_sel == "Active only":
    df = df[df["IsActiveMember"] == 1]
elif active_sel == "Inactive only":
    df = df[df["IsActiveMember"] == 0]

st.sidebar.caption(f"Showing **{len(df):,}** of {len(df_full):,} customers")

if len(df) == 0:
    st.warning("No customers match the current filter selection. Please broaden your filters.")
    st.stop()

# ----------------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------------
st.title("Customer Engagement & Product Utilization Analytics")
st.caption("Retention strategy dashboard · The European Central Bank · Behavioral risk, not just balance")

# Top-line KPI row
churn_rate = df["Exited"].mean() * 100
active_churn = df.loc[df.IsActiveMember == 1, "Exited"].mean() * 100 if (df.IsActiveMember == 1).any() else np.nan
inactive_churn = df.loc[df.IsActiveMember == 0, "Exited"].mean() * 100 if (df.IsActiveMember == 0).any() else np.nan
err_ratio = (inactive_churn / active_churn) if (active_churn and active_churn > 0) else np.nan
at_risk_n = int(df["AtRiskPremium"].sum())

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Customers in view", f"{len(df):,}")
k2.metric("Churn rate", f"{churn_rate:.1f}%")
k3.metric("Engagement Retention Ratio", f"{err_ratio:.2f}x" if not np.isnan(err_ratio) else "—",
          help="Inactive churn rate ÷ active churn rate")
k4.metric("At-risk premium customers", f"{at_risk_n:,}",
          help="High balance, high salary, inactive, not yet churned")
k5.metric("Avg. Relationship Strength", f"{df['RelationshipStrengthIndex'].mean():.1f}/100")

st.markdown("---")

# ----------------------------------------------------------------------------
# Tabs = Core Modules
# ----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Engagement vs Churn Overview",
    "🧩 Product Utilization Impact",
    "🎯 High-Value Disengaged Detector",
    "💪 Retention Strength Scoring",
])

# ---- MODULE 1: Engagement vs Churn Overview -------------------------------
with tab1:
    st.subheader("Engagement vs Churn Overview")
    c1, c2 = st.columns([1.2, 1])

    with c1:
        seg = df.groupby("EngagementProfile").agg(
            Customers=("Exited", "size"), ChurnRate=("Exited", "mean")
        ).reset_index().sort_values("ChurnRate", ascending=False)
        seg["ChurnRate"] *= 100
        fig = px.bar(
            seg, x="ChurnRate", y="EngagementProfile", orientation="h",
            color="ChurnRate", color_continuous_scale=[GOLD, RED],
            text=seg["ChurnRate"].round(1).astype(str) + "%",
            labels={"ChurnRate": "Churn Rate (%)", "EngagementProfile": ""},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(showlegend=False, coloraxis_showscale=False, height=380,
                           yaxis={"categoryorder": "total ascending"}, plot_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        active_tbl = df.groupby("IsActiveMember")["Exited"].agg(["mean", "count"]).reset_index()
        active_tbl["IsActiveMember"] = active_tbl["IsActiveMember"].map({0: "Inactive", 1: "Active"})
        active_tbl["mean"] *= 100
        fig2 = px.pie(active_tbl, names="IsActiveMember", values="count",
                       color="IsActiveMember", color_discrete_map={"Active": NAVY, "Inactive": RED}, hole=0.5)
        fig2.update_layout(height=200, margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.metric("Active member churn", f"{active_churn:.1f}%" if not np.isnan(active_churn) else "—")
        st.metric("Inactive member churn", f"{inactive_churn:.1f}%" if not np.isnan(inactive_churn) else "—")

    st.markdown("##### Churn by geography & activity status")
    geo_active = df.groupby(["Geography", "IsActiveMember"])["Exited"].mean().reset_index()
    geo_active["IsActiveMember"] = geo_active["IsActiveMember"].map({0: "Inactive", 1: "Active"})
    geo_active["Exited"] *= 100
    fig3 = px.bar(geo_active, x="Geography", y="Exited", color="IsActiveMember", barmode="group",
                  color_discrete_map={"Active": NAVY, "Inactive": RED},
                  labels={"Exited": "Churn Rate (%)"})
    fig3.update_layout(height=350, plot_bgcolor="white")
    st.plotly_chart(fig3, use_container_width=True)

    st.info(
        "💡 **Reading this module:** Inactive customers churn at roughly **twice the rate** of active "
        "customers across nearly every cut of the data. Engagement status is a stronger churn signal "
        "than geography, age, or balance considered alone."
    )

# ---- MODULE 2: Product Utilization Impact Analysis ------------------------
with tab2:
    st.subheader("Product Utilization Impact Analysis")
    c1, c2 = st.columns(2)

    with c1:
        prod = df.groupby("NumOfProducts")["Exited"].agg(["mean", "count"]).reset_index()
        prod["mean"] *= 100
        fig4 = px.bar(prod, x="NumOfProducts", y="mean", text=prod["mean"].round(1).astype(str) + "%",
                      color="mean", color_continuous_scale=[NAVY, RED],
                      labels={"mean": "Churn Rate (%)", "NumOfProducts": "Number of Products"})
        fig4.update_traces(textposition="outside")
        fig4.update_layout(height=380, coloraxis_showscale=False, plot_bgcolor="white")
        st.plotly_chart(fig4, use_container_width=True)
        st.caption("Two products is the observed retention optimum; 3+ signals a distressed segment.")

    with c2:
        df["ProductTier"] = np.where(df["NumOfProducts"] <= 1, "Single-Product",
                              np.where(df["NumOfProducts"] == 2, "Multi-Product (2)", "Over-Sold (3+)"))
        tier = df.groupby("ProductTier")["Exited"].agg(["mean", "count"]).reset_index()
        tier["mean"] *= 100
        fig5 = px.bar(tier, x="ProductTier", y="mean", text=tier["mean"].round(1).astype(str) + "%",
                      color="ProductTier",
                      color_discrete_map={"Single-Product": GOLD, "Multi-Product (2)": NAVY, "Over-Sold (3+)": RED},
                      labels={"mean": "Churn Rate (%)", "ProductTier": ""})
        fig5.update_traces(textposition="outside")
        fig5.update_layout(height=380, showlegend=False, plot_bgcolor="white")
        st.plotly_chart(fig5, use_container_width=True)
        st.caption("Single- vs multi- vs over-sold product retention comparison.")

    st.markdown("##### Product depth by geography")
    geo_prod = df.groupby(["Geography", "NumOfProducts"])["Exited"].mean().reset_index()
    geo_prod["Exited"] *= 100
    fig6 = px.line(geo_prod, x="NumOfProducts", y="Exited", color="Geography", markers=True,
                   labels={"Exited": "Churn Rate (%)", "NumOfProducts": "Number of Products"},
                   color_discrete_sequence=[NAVY, RED, GOLD])
    fig6.update_layout(height=350, plot_bgcolor="white")
    st.plotly_chart(fig6, use_container_width=True)

    st.warning(
        "⚠️ **Product Depth Index:** churn jumps from 7.6% (2 products) to 82.7% (3 products) and "
        "100% (4 products). This pattern holds across all three markets and likely reflects reactive "
        "or forced product bundling rather than genuine loyalty — recommend a sales-process audit."
    )

# ---- MODULE 3: High-Value Disengaged Customer Detector --------------------
with tab3:
    st.subheader("High-Value Disengaged Customer Detector")
    st.caption("Adjust thresholds in the sidebar (balance, salary) to redefine \"high value\"; use the controls below to size the at-risk list.")

    c1, c2, c3 = st.columns(3)
    with c1:
        detector_bal_pct = st.slider("Balance percentile threshold", 50, 95, 50, step=5,
                                      help="Customers above this balance percentile count as 'high balance'")
    with c2:
        detector_sal_pct = st.slider("Salary percentile threshold", 50, 95, 50, step=5)
    with c3:
        include_exited = st.checkbox("Include already-churned customers", value=False)

    bal_thresh = df_full["Balance"].quantile(detector_bal_pct / 100)
    sal_thresh = df_full["EstimatedSalary"].quantile(detector_sal_pct / 100)

    detector_pool = df[
        (df["Balance"] >= bal_thresh) & (df["EstimatedSalary"] >= sal_thresh) & (df["IsActiveMember"] == 0)
    ]
    if not include_exited:
        detector_pool = detector_pool[detector_pool["Exited"] == 0]

    m1, m2, m3 = st.columns(3)
    m1.metric("At-risk customers identified", f"{len(detector_pool):,}")
    m2.metric("% of filtered base", f"{len(detector_pool) / len(df) * 100:.1f}%")
    m3.metric("Combined balance exposure", f"€{detector_pool['Balance'].sum():,.0f}")

    c1, c2 = st.columns([1, 1])
    with c1:
        fig7 = px.scatter(
            df.sample(min(3000, len(df)), random_state=1), x="Balance", y="EstimatedSalary",
            color="IsActiveMember", color_continuous_scale=[RED, NAVY],
            opacity=0.5, labels={"IsActiveMember": "Active"},
            title="Balance vs. Salary — inactive customers highlighted"
        )
        fig7.add_vline(x=bal_thresh, line_dash="dash", line_color=GOLD)
        fig7.add_hline(y=sal_thresh, line_dash="dash", line_color=GOLD)
        fig7.update_layout(height=420, plot_bgcolor="white")
        st.plotly_chart(fig7, use_container_width=True)

    with c2:
        st.markdown("###### At-Risk Premium Customer List")
        show_cols = ["CustomerId", "Surname", "Geography", "Age", "Balance", "EstimatedSalary",
                     "NumOfProducts", "Tenure", "RelationshipStrengthIndex"]
        st.dataframe(
            detector_pool[show_cols].sort_values("Balance", ascending=False).reset_index(drop=True),
            height=420, use_container_width=True
        )
        st.download_button(
            "⬇ Download at-risk list (CSV)",
            detector_pool[show_cols].to_csv(index=False).encode("utf-8"),
            file_name="at_risk_premium_customers.csv", mime="text/csv"
        )

    st.success(
        f"🎯 **Actionable segment:** {len(detector_pool):,} customers meet the high-value, disengaged "
        "profile. These are prime candidates for prioritized relationship-manager outreach — they are "
        "financially significant, currently retained, but showing the behavioral pattern that precedes churn."
    )

# ---- MODULE 4: Retention Strength Scoring Panels --------------------------
with tab4:
    st.subheader("Retention Strength Scoring")
    st.caption("Relationship Strength Index (0–100) = 40% activity status + 40% product depth (capped at 2) + 20% tenure")

    c1, c2 = st.columns([1, 1])
    with c1:
        fig8 = px.histogram(df, x="RelationshipStrengthIndex", color="Exited", nbins=25,
                            barmode="overlay", opacity=0.65,
                            color_discrete_map={0: NAVY, 1: RED},
                            labels={"Exited": "Churned", "RelationshipStrengthIndex": "Relationship Strength Index"})
        fig8.update_layout(height=380, plot_bgcolor="white")
        st.plotly_chart(fig8, use_container_width=True)

    with c2:
        df["StrengthBand"] = pd.cut(df["RelationshipStrengthIndex"], bins=[-1, 25, 50, 75, 100],
                                     labels=["0-25 (Fragile)", "26-50 (Weak)", "51-75 (Solid)", "76-100 (Sticky)"])
        band = df.groupby("StrengthBand", observed=True)["Exited"].agg(["mean", "count"]).reset_index()
        band["mean"] *= 100
        fig9 = px.bar(band, x="StrengthBand", y="mean", text=band["mean"].round(1).astype(str) + "%",
                      color="mean", color_continuous_scale=[RED, GOLD, NAVY],
                      labels={"mean": "Churn Rate (%)", "StrengthBand": "Relationship Strength Band"})
        fig9.update_traces(textposition="outside")
        fig9.update_layout(height=380, coloraxis_showscale=False, plot_bgcolor="white")
        st.plotly_chart(fig9, use_container_width=True)

    st.markdown("##### Retention stability across engagement tiers & tenure")
    tenure_engagement = df.groupby(["Tenure", "EngagementProfile"], observed=True)["Exited"].mean().reset_index()
    tenure_engagement["Exited"] *= 100
    fig10 = px.line(tenure_engagement, x="Tenure", y="Exited", color="EngagementProfile", markers=True,
                    labels={"Exited": "Churn Rate (%)"},
                    color_discrete_sequence=[NAVY, RED, GOLD, GREY, GREEN])
    fig10.update_layout(height=380, plot_bgcolor="white")
    st.plotly_chart(fig10, use_container_width=True)

    st.markdown("##### Credit card stickiness")
    cc = df.groupby(["HasCrCard", "IsActiveMember"])["Exited"].mean().reset_index()
    cc["HasCrCard"] = cc["HasCrCard"].map({0: "No Card", 1: "Has Card"})
    cc["IsActiveMember"] = cc["IsActiveMember"].map({0: "Inactive", 1: "Active"})
    cc["Exited"] *= 100
    fig11 = px.bar(cc, x="HasCrCard", y="Exited", color="IsActiveMember", barmode="group",
                  color_discrete_map={"Active": NAVY, "Inactive": RED},
                  labels={"Exited": "Churn Rate (%)"})
    fig11.update_layout(height=320, plot_bgcolor="white")
    st.plotly_chart(fig11, use_container_width=True)

    st.info(
        "💡 **Reading this module:** Card ownership alone barely moves churn — the split is driven "
        "almost entirely by activity status. \"Sticky\" (76–100) customers churn far less than "
        "\"Fragile\" (0–25) customers, confirming the composite index tracks real retention risk."
    )

st.markdown("---")
st.caption(
    "Customer Engagement & Product Utilization Analytics for Retention Strategy · "
    "The European Central Bank · Data as of dataset snapshot · Built with Streamlit"
)
