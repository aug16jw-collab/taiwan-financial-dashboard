import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from core.institutional import (
    get_today_institutional,
    get_tpex_institutional_today,
    get_stock_institutional_history,
)
from core.loader import search_companies
from core.market import get_all_stock_names

st.set_page_config(page_title="法人籌碼", page_icon="🏦", layout="wide")
st.title("🏦 法人籌碼（三大法人）")

latest = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))

# ── Today's aggregate data ──
st.markdown("## 今日三大法人 — 全市場買超排行")

tab_twse, tab_tpex = st.tabs(["上市 (TWSE)", "上櫃 (TPEX)"])

@st.cache_data(ttl=3600, show_spinner=False)
def _load_all_names():
    names = get_all_stock_names()
    # Also merge from latest (MOPS data) as override
    return names


def _show_inst_table(df: pd.DataFrame, market_label: str):
    if df.empty:
        st.warning(f"目前無法取得{market_label}即時法人資料（可能非交易時間）")
        return

    # Build name map: TWSE/TPEX API covers ETFs too; MOPS latest has official names
    api_names = _load_all_names()
    mops_names: dict = {}
    if not latest.empty:
        for _, row in latest[["code", "name"]].iterrows():
            mops_names[str(row["code"])] = str(row["name"])

    def _lookup(code):
        c = str(code)
        return mops_names.get(c) or api_names.get(c) or ""

    df = df.copy()
    df["name"] = df["code"].apply(_lookup)

    inst_col = "三大法人合計"
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 三大法人合計買超 Top 20")
        top20 = df.nlargest(20, inst_col)[["code", "name", "外資淨買超", "投信淨買超", "自營商淨買超", inst_col]]
        top20 = top20.reset_index(drop=True)
        top20.columns = ["代號", "名稱", "外資淨買超(股)", "投信淨買超(股)", "自營商淨買超(股)", "三大合計(股)"]
        st.dataframe(top20, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("#### 三大法人合計賣超 Top 20")
        bot20 = df.nsmallest(20, inst_col)[["code", "name", "外資淨買超", "投信淨買超", "自營商淨買超", inst_col]]
        bot20 = bot20.reset_index(drop=True)
        bot20.columns = ["代號", "名稱", "外資淨買超(股)", "投信淨買超(股)", "自營商淨買超(股)", "三大合計(股)"]
        st.dataframe(bot20, use_container_width=True, hide_index=True)

    st.markdown("#### 法人別買超統計（全市場總計）")
    cols_stat = st.columns(4)
    for i, col_name in enumerate(["外資淨買超", "投信淨買超", "自營商淨買超", "三大法人合計"]):
        total = df[col_name].sum()
        sign = "+" if total >= 0 else ""
        cols_stat[i].metric(col_name, f"{sign}{total:,.0f} 股")

with tab_twse:
    with st.spinner("載入上市法人資料..."):
        twse_inst = get_today_institutional()
    _show_inst_table(twse_inst, "上市")

with tab_tpex:
    with st.spinner("載入上櫃法人資料..."):
        tpex_inst = get_tpex_institutional_today()
    _show_inst_table(tpex_inst, "上櫃")

st.markdown("---")

# ── Individual stock institutional history ──
st.markdown("## 個股法人動向追蹤")

col_search, col_days = st.columns([3, 1])
with col_search:
    query = st.text_input("輸入股票代號或名稱", placeholder="例如：2330 或 台積電", value="2330")
with col_days:
    days = st.selectbox("查詢天數", [10, 20, 30, 60], index=1)

if not query.strip():
    st.info("請輸入股票代號或名稱")
    st.stop()

if not latest.empty:
    results = search_companies(latest, query.strip())
    if results.empty:
        st.warning(f"找不到「{query}」")
        st.stop()
    if len(results) > 1:
        options = {f"{r['code']} {r['name']}": str(r["code"]) for _, r in results.iterrows()}
        sel = st.selectbox("選擇公司", list(options.keys()))
        code = options[sel]
        name = sel
    else:
        row = results.iloc[0]
        code = str(row["code"])
        name = f"{code} {row['name']}"
else:
    code = query.strip()
    name = code

st.markdown(f"### {name} — 近 {days} 個交易日法人動向")

with st.spinner(f"下載 {code} 法人歷史資料（約需 {days // 5 + 5} 秒）..."):
    hist = get_stock_institutional_history(code, days=days)

if hist.empty:
    st.warning("無法取得該股票的法人歷史資料，可能是代號錯誤或資料暫時不可用")
    st.stop()

# ── Chart ──
fig = go.Figure()

colors = {"外資淨買超": "#2196F3", "投信淨買超": "#4CAF50", "自營商淨買超": "#FF9800"}
for col_name, color in colors.items():
    if col_name not in hist.columns:
        continue
    vals = hist[col_name]
    bar_colors = [color if v >= 0 else "#EF5350" for v in vals]
    fig.add_trace(go.Bar(
        x=hist["date"],
        y=vals,
        name=col_name,
        marker_color=bar_colors,
        opacity=0.85,
    ))

fig.add_trace(go.Scatter(
    x=hist["date"],
    y=hist["三大法人合計"],
    name="三大法人合計",
    mode="lines+markers",
    line=dict(color="#9C27B0", width=2),
    yaxis="y2",
))

fig.update_layout(
    title=f"{name} 法人動向（近 {days} 個交易日）",
    xaxis_title="日期",
    yaxis_title="買超股數",
    yaxis2=dict(overlaying="y", side="right", showgrid=False, title="合計"),
    barmode="group",
    height=420,
    legend=dict(orientation="h", y=1.08),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ── Cumulative chart ──
st.markdown("#### 累計法人淨買超")
cum_df = hist.copy()
for col_name in ["外資淨買超", "投信淨買超", "自營商淨買超", "三大法人合計"]:
    if col_name in cum_df.columns:
        cum_df[f"{col_name}_cum"] = cum_df[col_name].cumsum()

fig2 = go.Figure()
for col_name, color in colors.items():
    cum_col = f"{col_name}_cum"
    if cum_col in cum_df.columns:
        fig2.add_trace(go.Scatter(
            x=cum_df["date"],
            y=cum_df[cum_col],
            name=col_name,
            mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ", 0.1)").replace("rgb", "rgba") if color.startswith("rgb") else color,
        ))
fig2.update_layout(
    title="累計淨買超走勢",
    xaxis_title="日期",
    yaxis_title="累計股數",
    height=320,
    hovermode="x unified",
)
st.plotly_chart(fig2, use_container_width=True)

# ── Data table ──
with st.expander("原始資料"):
    disp = hist.copy()
    for c in ["外資淨買超", "投信淨買超", "自營商淨買超", "三大法人合計"]:
        if c in disp.columns:
            disp[c] = disp[c].apply(lambda v: f"{v:+,.0f}")
    st.dataframe(disp, use_container_width=True, hide_index=True)
