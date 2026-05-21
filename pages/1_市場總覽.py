import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from core.loader import quality_filter
from core.charts import distribution_chart, market_pie
from core.nav import stock_table
from config import METRIC_DEFS, THRESHOLDS, COLOR_GOOD, COLOR_BAD, COLOR_LISTED, COLOR_OTC

st.set_page_config(page_title="市場總覽", page_icon="📊", layout="wide")
st.title("📊 市場總覽")

quarters = st.session_state.get("quarters", {})
latest   = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))

if latest.empty:
    st.error("無資料，請返回首頁確認資料已載入")
    st.stop()

quality = quality_filter(latest)
df_listed = latest[latest["market"] == "上市"]
df_otc    = latest[latest["market"] == "上櫃"]

# ── KPI row ──
st.markdown("### 市場概況")
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("總家數", f"{len(latest):,}")
c2.metric("上市", f"{len(df_listed):,}")
c3.metric("上櫃", f"{len(df_otc):,}")
c4.metric("優質企業", f"{len(quality)}")
c5.metric("平均毛利率", f"{latest['gross_margin'].mean():.1f}%")
c6.metric("平均ROE", f"{latest['roe'].mean():.1f}%")

st.markdown("---")

# ── Statistics table ──
st.markdown("### 各指標市場統計")

pct_metrics = [m for m in METRIC_DEFS if m[2] == "%" or m[1] in ("roe", "roa")]
ratio_metrics = [m for m in METRIC_DEFS if m[2] == "x"]

stat_rows = []
for label, field, unit in METRIC_DEFS:
    def _s(df, f):
        v = pd.to_numeric(df[f], errors="coerce")
        return v.mean(), v.median()

    all_avg, all_med = _s(latest, field)
    lst_avg, lst_med = _s(df_listed, field)
    otc_avg, otc_med = _s(df_otc, field)

    thresh = THRESHOLDS.get(field)
    if thresh:
        good_t, higher, bad_t = thresh
        vals_all = pd.to_numeric(latest[field], errors="coerce")
        count = (vals_all >= good_t if higher else vals_all <= good_t).sum()
    else:
        count = None

    def fmt(v, u):
        if pd.isna(v): return "-"
        if u == "%": return f"{v:.1f}%"
        if u == "x": return f"{v:.2f}x"
        if u == "元": return f"{v:.2f}"
        return f"{v:,.0f}"

    stat_rows.append({
        "指標": label,
        "全市場平均": fmt(all_avg, unit),
        "全市場中位數": fmt(all_med, unit),
        "達標家數": f"{count}" if count is not None else "-",
        "上市平均": fmt(lst_avg, unit),
        "上市中位數": fmt(lst_med, unit),
        "上櫃平均": fmt(otc_avg, unit),
        "上櫃中位數": fmt(otc_med, unit),
    })

st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Multi-quarter market trend ──
if len(quarters) >= 2:
    st.markdown("### 📈 多季市場趨勢")
    q_sorted = sorted(quarters.keys())

    trend_sel = st.multiselect(
        "選擇指標",
        [m[0] for m in METRIC_DEFS[:9]],
        default=["毛利率(%)", "ROE(%)", "EPS(元)"],
        key="trend_metric_sel",
    )
    market_filter = st.radio("市場範圍", ["全部", "上市", "上櫃"], horizontal=True, key="trend_mkt")

    COLORS = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"]
    fig_trend = go.Figure()
    for (label, field, _), color in zip(
        [m for m in METRIC_DEFS[:9] if m[0] in trend_sel], COLORS
    ):
        medians, means = [], []
        for q in q_sorted:
            qdf = quarters[q]
            if market_filter != "全部":
                qdf = qdf[qdf["market"] == market_filter]
            v = pd.to_numeric(qdf[field], errors="coerce")
            medians.append(round(v.median(), 2) if not v.isna().all() else None)
            means.append(round(v.mean(), 2) if not v.isna().all() else None)

        fig_trend.add_trace(go.Scatter(
            x=q_sorted, y=medians, name=f"{label}（中位數）",
            mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=8),
            connectgaps=True,
        ))
        fig_trend.add_trace(go.Scatter(
            x=q_sorted, y=means, name=f"{label}（平均）",
            mode="lines", line=dict(color=color, width=1, dash="dot"),
            connectgaps=True, opacity=0.55,
        ))

    fig_trend.update_layout(
        height=380, hovermode="x unified",
        legend=dict(orientation="h", y=1.12, font_size=11),
        margin=dict(t=50, b=20),
        yaxis_title="數值",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Condensed quarter comparison table
    with st.expander("各季度統計數字"):
        rows = []
        for label, field, unit in METRIC_DEFS[:9]:
            row = {"指標": label}
            for q in q_sorted:
                qdf = quarters[q]
                if market_filter != "全部":
                    qdf = qdf[qdf["market"] == market_filter]
                v = pd.to_numeric(qdf[field], errors="coerce").median()
                row[q] = f"{v:.2f}{unit}" if pd.notna(v) else "-"
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.markdown("---")

# ── Distribution charts ──
st.markdown("### 指標分佈")
col_a, col_b = st.columns(2)
with col_a:
    sel_metric = st.selectbox("選擇指標", [m[0] for m in METRIC_DEFS], key="dist_metric")
    field = next(m[1] for m in METRIC_DEFS if m[0] == sel_metric)
    st.plotly_chart(distribution_chart(latest, field, sel_metric), use_container_width=True)
with col_b:
    st.plotly_chart(market_pie(latest), use_container_width=True)

st.markdown("---")

# ── Quality company table ──
st.markdown(f"### 優質企業名單（共 {len(quality)} 家）")
st.caption("篩選條件：毛利率 ≥ 20%、營業利益率 ≥ 5%、ROE ≥ 10%、自由現金流 > 0")

display_cols = ["market", "code", "name", "gross_margin", "op_margin",
                "roe", "roa", "eps", "bvps", "free_cf"]
col_names = {
    "market": "市場", "code": "代號", "name": "名稱",
    "gross_margin": "毛利率(%)", "op_margin": "營業利益率(%)",
    "roe": "ROE(%)", "roa": "ROA(%)",
    "eps": "EPS", "bvps": "每股淨值", "free_cf": "自由現金流",
}

q_display = quality[display_cols].copy()
q_display.columns = [col_names[c] for c in display_cols]

for pct_col in ["毛利率(%)", "營業利益率(%)", "ROE(%)", "ROA(%)"]:
    q_display[pct_col] = q_display[pct_col].apply(
        lambda v: f"{v:.1f}%" if pd.notna(v) else "-"
    )
q_display["EPS"] = q_display["EPS"].apply(
    lambda v: f"{v:.2f}" if pd.notna(v) else "-"
)
q_display["每股淨值"] = q_display["每股淨值"].apply(
    lambda v: f"{v:.2f}" if pd.notna(v) else "-"
)
q_display["自由現金流"] = q_display["自由現金流"].apply(
    lambda v: f"{v:,.0f}" if pd.notna(v) else "-"
)

stock_table(q_display, key="quality_table",
            column_config={"市場": st.column_config.TextColumn(width="small")})
