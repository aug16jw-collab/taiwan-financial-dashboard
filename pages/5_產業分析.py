import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.industry import add_industry_column, get_industry_list
from config import METRIC_DEFS

st.set_page_config(page_title="產業分析", page_icon="🏭", layout="wide")
st.title("🏭 產業分析")

latest = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))

if latest.empty:
    st.error("無資料，請返回首頁")
    st.stop()

with st.spinner("載入產業分類..."):
    df = add_industry_column(latest)

industries = get_industry_list(df)

# ── Sidebar filters ──
st.sidebar.header("篩選條件")
market_sel = st.sidebar.radio("市場", ["全部", "上市", "上櫃"])
if market_sel != "全部":
    df = df[df["market"] == market_sel]

sel_industry = st.sidebar.multiselect("產業別", industries, default=[])
if sel_industry:
    df = df[df["industry"].isin(sel_industry)]

metric_label = st.sidebar.selectbox(
    "分析指標",
    [m[0] for m in METRIC_DEFS[:9]],
    index=2,  # default ROE
)
field = next(m[1] for m in METRIC_DEFS if m[0] == metric_label)
unit  = next(m[2] for m in METRIC_DEFS if m[0] == metric_label)

# ── Industry summary ──
numeric_cols = [m[1] for m in METRIC_DEFS[:9]]
agg = (
    df.groupby("industry")[numeric_cols]
    .agg(["mean", "median", "count"])
    .round(2)
)
agg.columns = ["_".join(c) for c in agg.columns]
agg = agg.reset_index()

st.markdown(f"### 各產業「{metric_label}」中位數比較")
col_val = f"{field}_median"
if col_val in agg.columns:
    agg_sorted = agg.sort_values(col_val, ascending=False).dropna(subset=[col_val])
    fig = px.bar(
        agg_sorted,
        x="industry",
        y=col_val,
        color=col_val,
        color_continuous_scale="RdYlGn",
        labels={"industry": "產業別", col_val: f"{metric_label} 中位數"},
        text=agg_sorted[col_val].apply(lambda v: f"{v:.1f}{unit}"),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=420, xaxis_tickangle=-35, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Two-column: scatter + boxplot ──
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### 產業分布 — 毛利率 vs ROE")
    scatter_df = df[["code", "name", "industry", "market", "gross_margin", "roe", "eps"]].copy()
    scatter_df = scatter_df.dropna(subset=["gross_margin", "roe"])
    scatter_df["eps_size"] = scatter_df["eps"].clip(lower=0).fillna(0)
    fig2 = px.scatter(
        scatter_df,
        x="gross_margin",
        y="roe",
        color="industry",
        size="eps_size",
        size_max=20,
        hover_data={"code": True, "name": True, "eps_size": False},
        labels={"gross_margin": "毛利率(%)", "roe": "ROE(%)"},
    )
    fig2.add_hline(y=10, line_dash="dash", line_color="gray", opacity=0.4)
    fig2.add_vline(x=20, line_dash="dash", line_color="gray", opacity=0.4)
    fig2.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

with c2:
    st.markdown(f"#### {metric_label} 產業箱型圖")
    box_df = df[["industry", field]].dropna()
    industry_order = (
        box_df.groupby("industry")[field].median()
        .sort_values(ascending=False).index.tolist()
    )
    fig3 = px.box(
        box_df,
        x="industry",
        y=field,
        category_orders={"industry": industry_order},
        labels={"industry": "產業別", field: metric_label},
        color="industry",
    )
    fig3.update_layout(height=400, showlegend=False, xaxis_tickangle=-35)
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")

# ── Drill-down: single industry ──
st.markdown("### 單一產業深入分析")
drill_ind = st.selectbox("選擇產業", industries)
drill_df = df[df["industry"] == drill_ind].copy()

col_cnt, col_avg_gm, col_avg_roe, col_avg_eps = st.columns(4)
col_cnt.metric("公司家數", len(drill_df))
col_avg_gm.metric("平均毛利率", f"{drill_df['gross_margin'].mean():.1f}%" if not drill_df['gross_margin'].isna().all() else "N/A")
col_avg_roe.metric("平均ROE", f"{drill_df['roe'].mean():.1f}%" if not drill_df['roe'].isna().all() else "N/A")
col_avg_eps.metric("平均EPS", f"{drill_df['eps'].mean():.2f}" if not drill_df['eps'].isna().all() else "N/A")

display_cols = ["code", "name", "market"] + [m[1] for m in METRIC_DEFS[:8]]
disp = drill_df[display_cols].copy()
for m in METRIC_DEFS[:8]:
    disp[m[1]] = pd.to_numeric(disp[m[1]], errors="coerce").round(2)
disp = disp.sort_values("roe", ascending=False).reset_index(drop=True)

disp.columns = ["代號", "名稱", "市場"] + [m[0] for m in METRIC_DEFS[:8]]
st.dataframe(disp, use_container_width=True, hide_index=True)
