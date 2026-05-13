import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from core.industry import add_industry_column, get_industry_list
from core.nav import stock_table
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
    # Clip bar chart range to IQR×3 to avoid one outlier industry distorting scale
    _blo, _bhi = _clip_iqr(agg_sorted[col_val], k=3.0)
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
    fig.update_layout(
        height=420,
        xaxis_tickangle=-35,
        coloraxis_showscale=False,
        yaxis=dict(range=[min(_blo, 0), _bhi * 1.15]),
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Two-column: scatter + boxplot ──
c1, c2 = st.columns(2)

def _clip_iqr(series: pd.Series, k: float = 2.5) -> tuple:
    """Return (lo, hi) whisker bounds using IQR×k, for axis range."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


with c1:
    st.markdown("#### 產業分布 — 毛利率 vs ROE")
    scatter_df = df[["code", "name", "industry", "market", "gross_margin", "roe", "eps"]].copy()
    scatter_df = scatter_df.dropna(subset=["gross_margin", "roe"])

    # Clip display range to IQR×2.5 to suppress extreme outliers
    gm_lo, gm_hi = _clip_iqr(scatter_df["gross_margin"])
    roe_lo, roe_hi = _clip_iqr(scatter_df["roe"])
    plot_df = scatter_df[
        scatter_df["gross_margin"].between(gm_lo, gm_hi) &
        scatter_df["roe"].between(roe_lo, roe_hi)
    ].copy()
    plot_df["eps_size"] = plot_df["eps"].clip(lower=0.01).fillna(0.01)

    fig2 = px.scatter(
        plot_df,
        x="gross_margin",
        y="roe",
        color="industry",
        size="eps_size",
        size_max=18,
        hover_data={"code": True, "name": True, "eps_size": False},
        labels={"gross_margin": "毛利率(%)", "roe": "ROE(%)"},
        opacity=0.75,
    )
    fig2.add_hline(y=10, line_dash="dash", line_color="gray", opacity=0.5,
                   annotation_text="ROE 10%", annotation_position="right")
    fig2.add_vline(x=20, line_dash="dash", line_color="gray", opacity=0.5,
                   annotation_text="毛利 20%", annotation_position="top")
    fig2.update_layout(height=420, showlegend=False,
                       xaxis=dict(range=[max(gm_lo, -20), min(gm_hi, 120)]),
                       yaxis=dict(range=[max(roe_lo, -30), min(roe_hi, 80)]))
    outlier_n = len(scatter_df) - len(plot_df)
    if outlier_n > 0:
        st.caption(f"已排除 {outlier_n} 筆極端值（IQR×2.5 之外）以利觀察")
    st.plotly_chart(fig2, use_container_width=True)

with c2:
    st.markdown(f"#### {metric_label} 產業箱型圖")
    box_df = df[["industry", field]].dropna()
    # Filter outliers per industry for display
    flo, fhi = _clip_iqr(box_df[field], k=3.0)
    box_df_clipped = box_df[box_df[field].between(flo, fhi)]
    industry_order = (
        box_df_clipped.groupby("industry")[field].median()
        .sort_values(ascending=False).index.tolist()
    )
    fig3 = px.box(
        box_df_clipped,
        x="industry",
        y=field,
        category_orders={"industry": industry_order},
        labels={"industry": "產業別", field: metric_label},
        color="industry",
        points=False,  # hide individual outlier dots for cleanliness
    )
    fig3.update_layout(
        height=420,
        showlegend=False,
        xaxis_tickangle=-40,
        yaxis=dict(range=[flo, fhi]),
    )
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
stock_table(disp, key="industry_drill")
