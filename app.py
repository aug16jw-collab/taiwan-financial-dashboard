import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from core.loader import load_all_quarters, get_latest_df, quality_filter
from config import METRIC_DEFS

st.set_page_config(
    page_title="台股財務分析平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Load data (cached) ──
@st.cache_data(show_spinner="載入財報資料中...")
def _load():
    return load_all_quarters()

quarters = _load()
latest   = get_latest_df(quarters)
quality  = quality_filter(latest) if not latest.empty else latest

st.session_state["quarters"] = quarters
st.session_state["latest"]   = latest
st.session_state["quality"]  = quality

# ── Sidebar ──
with st.sidebar:
    st.markdown("## 📈 台股財務分析平台")
    st.markdown("---")

    available_quarters = sorted(quarters.keys(), reverse=True)
    if available_quarters:
        selected_q = st.selectbox(
            "選擇季度",
            available_quarters,
            index=0,
            help="選擇要分析的財報季度",
        )
        st.session_state["selected_quarter"] = selected_q
        st.session_state["selected_df"] = quarters[selected_q]
        cur_df = quarters[selected_q]
    else:
        st.error("找不到財報資料，請確認 data/ 資料夾")
        cur_df = latest

    st.markdown("---")
    q_count = len(available_quarters)
    newest  = available_quarters[0] if available_quarters else "-"
    oldest  = available_quarters[-1] if available_quarters else "-"
    st.markdown(
        f"**資料期數：** {q_count} 季（{oldest} ～ {newest}）\n\n"
        f"**目前季度：** {selected_q if available_quarters else '-'}\n\n"
        f"**分析家數：** {len(cur_df):,} 家\n\n"
        f"**優質企業：** {len(quality_filter(cur_df))} 家",
        unsafe_allow_html=False,
    )

    if st.button("重新載入資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("資料來源：MOPS 公開資訊觀測站\n股價：Yahoo Finance / TWSE OpenAPI")

# ── Landing page ──
st.title("📈 台股財務分析平台")
if available_quarters:
    st.markdown(
        f"**{oldest} ～ {newest}｜共 {q_count} 季財報 × {len(latest):,} 家企業｜基本面 × 技術面 × 即時報價**"
    )
else:
    st.markdown("**基本面 × 技術面 × 即時報價**")

st.markdown("---")

# ── KPI metrics for currently selected quarter ──
import pandas as pd
sel_df   = st.session_state.get("selected_df", latest)
sel_q    = st.session_state.get("selected_quarter", newest)
sel_qual = quality_filter(sel_df) if not sel_df.empty else sel_df

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("分析家數",  f"{len(sel_df):,} 家",  help=f"季度：{sel_q}")
col2.metric("上市家數",  f"{len(sel_df[sel_df['market']=='上市']):,} 家")
col3.metric("上櫃家數",  f"{len(sel_df[sel_df['market']=='上櫃']):,} 家")
col4.metric("優質企業",  f"{len(sel_qual)} 家",   help="毛利率≥20% + 營利率≥5% + ROE≥10% + 自由現金流>0")
col5.metric("資料季數",  f"{q_count} 季",         help=f"{oldest} ～ {newest}")

st.markdown("---")

# ── Multi-quarter market trend ──
if len(quarters) >= 2:
    import plotly.graph_objects as go
    st.markdown("### 📊 全市場關鍵指標趨勢")
    st.caption("各季度全市場中位數變化")

    trend_metrics = [
        ("毛利率(%)",     "gross_margin"),
        ("ROE(%)",        "roe"),
        ("EPS(元)",       "eps"),
        ("負債比率(%)",   "debt_ratio"),
    ]

    q_sorted = sorted(quarters.keys())
    fig = go.Figure()
    colors = ["#2196F3", "#4CAF50", "#FF9800", "#F44336"]

    for (label, field), color in zip(trend_metrics, colors):
        medians = []
        for q in q_sorted:
            v = pd.to_numeric(quarters[q][field], errors="coerce").median()
            medians.append(round(v, 2) if pd.notna(v) else None)
        fig.add_trace(go.Scatter(
            x=q_sorted, y=medians,
            name=label, mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=8),
            connectgaps=True,
        ))

    fig.update_layout(
        height=340, hovermode="x unified",
        legend=dict(orientation="h", y=1.08),
        yaxis_title="中位數",
        margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("---")

# ── Feature guide ──
st.markdown("### 功能導覽")

cols = st.columns(4)
pages = [
    ("📊", "市場總覽",  "全市場指標統計、優質公司名單"),
    ("🔍", "個股分析",  "即時報價、K線、5 季財務趨勢、估值區間"),
    ("🔎", "財務篩選",  "自訂 16 項指標條件篩選"),
    ("🏆", "排行榜",    "毛利率、ROE、EPS 前 20 名"),
]
pages2 = [
    ("🏭", "產業分析",  "各產業財務比較、散佈圖"),
    ("🏦", "法人籌碼",  "外資、投信、自營商買超動向"),
    ("📊", "多股比較",  "最多 6 檔股票同場比較"),
    ("",   "",          ""),
]

for col, (icon, name, desc) in zip(cols, pages):
    if name:
        col.markdown(f"**{icon} {name}**")
        col.caption(desc)

cols2 = st.columns(4)
for col, (icon, name, desc) in zip(cols2, pages2):
    if name:
        col.markdown(f"**{icon} {name}**")
        col.caption(desc)

st.markdown("---")
st.info("💡 **使用提示**：左側選擇季度後，所有頁面會同步切換到該季度資料；個股分析的「財務趨勢」頁籤可跨季比較。")
