import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from core.loader import search_companies
from core.market import get_historical, get_realtime_price
from config import METRIC_DEFS

st.set_page_config(page_title="多股比較", page_icon="📊", layout="wide")
st.title("📊 多股比較")

latest = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))

if latest.empty:
    st.error("無資料，請返回首頁")
    st.stop()

# ── Stock selection ──
st.markdown("### 選擇比較股票（最多 6 檔）")

col_input, col_period = st.columns([4, 1])
with col_input:
    raw = st.text_input(
        "輸入代號（空格或逗號分隔）",
        placeholder="例如：2330 2317 2454 2412",
        value="2330 2317 2454",
    )
with col_period:
    period = st.selectbox("K線期間", ["3mo", "6mo", "1y", "2y"], index=2,
                          format_func=lambda x: {"3mo":"3個月","6mo":"6個月","1y":"1年","2y":"2年"}[x])

raw_codes = [c.strip().replace(",", "") for c in raw.replace(",", " ").split() if c.strip()][:6]

if not raw_codes:
    st.info("請輸入至少一個股票代號")
    st.stop()

# Resolve codes → company info
resolved = []
for q in raw_codes:
    results = search_companies(latest, q)
    if not results.empty:
        row = results.iloc[0]
        resolved.append({
            "code": str(row["code"]),
            "name": str(row["name"]),
            "market": str(row["market"]),
        })
    else:
        st.warning(f"找不到「{q}」，略過")

if not resolved:
    st.error("無有效股票代號")
    st.stop()

codes = [r["code"] for r in resolved]
names = {r["code"]: r["name"] for r in resolved}
markets = {r["code"]: r["market"] for r in resolved}

st.markdown(f"**比較對象：** {' | '.join(f'{c} {names[c]}' for c in codes)}")
st.markdown("---")

# ── Normalized price chart ──
st.markdown("### 股價相對走勢（基準=100）")

PALETTE = ["#2196F3", "#F44336", "#4CAF50", "#FF9800", "#9C27B0", "#00BCD4"]

with st.spinner("下載歷史股價..."):
    hist_map: dict[str, pd.DataFrame] = {}
    for r in resolved:
        try:
            h = get_historical(r["code"], r["market"], period=period)
            if not h.empty:
                hist_map[r["code"]] = h
        except Exception:
            pass

fig_price = go.Figure()
for i, code in enumerate(codes):
    if code not in hist_map:
        continue
    h = hist_map[code]
    first_close = h["Close"].iloc[0]
    if first_close == 0:
        continue
    normalized = h["Close"] / first_close * 100
    fig_price.add_trace(go.Scatter(
        x=h.index,
        y=normalized,
        name=f"{code} {names.get(code, '')}",
        mode="lines",
        line=dict(color=PALETTE[i % len(PALETTE)], width=2),
    ))

fig_price.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
fig_price.update_layout(
    height=400,
    yaxis_title="相對股價（基準=100）",
    hovermode="x unified",
    legend=dict(orientation="h", y=1.05),
)
st.plotly_chart(fig_price, use_container_width=True)

st.markdown("---")

# ── Real-time prices side by side ──
st.markdown("### 即時報價比較")
with st.spinner("取得即時報價..."):
    price_data = {}
    for r in resolved:
        try:
            price_data[r["code"]] = get_realtime_price(r["code"], r["market"])
        except Exception:
            price_data[r["code"]] = {}

price_cols = st.columns(len(codes))
for i, code in enumerate(codes):
    pi = price_data.get(code, {})
    price = pi.get("price")
    chg_pct = pi.get("change_pct")
    pe = pi.get("pe")
    pb = pi.get("pb")
    div_yield = pi.get("div_yield")

    with price_cols[i]:
        st.markdown(f"**{code} {names.get(code, '')}**")
        if price:
            sign = "+" if (chg_pct or 0) >= 0 else ""
            delta_str = f"{sign}{chg_pct:.2f}%" if chg_pct else None
            st.metric("股價", f"NT${price:,.2f}", delta=delta_str)
        else:
            st.metric("股價", "N/A")
        st.caption(f"P/E: {pe:.1f}x" if pe else "P/E: N/A")
        st.caption(f"P/B: {pb:.2f}x" if pb else "P/B: N/A")
        st.caption(f"殖利率: {div_yield:.2f}%" if div_yield else "殖利率: N/A")

st.markdown("---")

# ── Financial metrics comparison ──
st.markdown("### 財務指標比較")

sel_metrics = st.multiselect(
    "選擇比較指標",
    [m[0] for m in METRIC_DEFS[:9]],
    default=["毛利率(%)", "ROE(%)", "EPS(元)", "負債比率(%)"],
)

if sel_metrics and not latest.empty:
    fields = [next(m[1] for m in METRIC_DEFS if m[0] == lbl) for lbl in sel_metrics]

    rows = []
    for code in codes:
        row_data = {"代號": code, "名稱": names.get(code, "")}
        sub = latest[latest["code"].astype(str) == str(code)]
        if not sub.empty:
            company = sub.iloc[0]
            for lbl, fld in zip(sel_metrics, fields):
                val = company.get(fld)
                row_data[lbl] = round(float(val), 2) if pd.notna(val) else None
        rows.append(row_data)

    comp_df = pd.DataFrame(rows)
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # Radar chart
    st.markdown("#### 雷達圖比較")
    radar_metrics = sel_metrics[:6]
    radar_fields = [next(m[1] for m in METRIC_DEFS if m[0] == lbl) for lbl in radar_metrics]

    fig_radar = go.Figure()
    for i, code in enumerate(codes):
        sub = latest[latest["code"].astype(str) == str(code)]
        if sub.empty:
            continue
        company = sub.iloc[0]
        vals = []
        for fld in radar_fields:
            v = pd.to_numeric(company.get(fld), errors="coerce")
            # normalize to 0-100 percentile within all stocks
            all_v = pd.to_numeric(latest[fld], errors="coerce").dropna()
            if pd.notna(v) and len(all_v) > 0:
                pct = (all_v <= v).mean() * 100
            else:
                pct = 0
            vals.append(pct)
        vals_closed = vals + [vals[0]]
        labels_closed = radar_metrics + [radar_metrics[0]]

        fig_radar.add_trace(go.Scatterpolar(
            r=vals_closed,
            theta=labels_closed,
            name=f"{code} {names.get(code, '')}",
            mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=450,
        legend=dict(orientation="h", y=-0.1),
        title="市場分位數排名（越高=優於越多家公司）",
    )
    st.plotly_chart(fig_radar, use_container_width=True)

st.markdown("---")

# ── Volume comparison ──
st.markdown("### 成交量比較（近期）")

vol_cols = st.columns(len([c for c in codes if c in hist_map]))
i = 0
for code in codes:
    if code not in hist_map:
        continue
    h = hist_map[code]
    recent = h.tail(30)
    fig_vol = go.Figure(go.Bar(
        x=recent.index,
        y=recent["Volume"],
        marker_color=PALETTE[i % len(PALETTE)],
        opacity=0.75,
    ))
    fig_vol.update_layout(
        title=f"{code} {names.get(code, '')} 成交量",
        height=220,
        margin=dict(t=30, b=20, l=20, r=20),
        showlegend=False,
    )
    vol_cols[i].plotly_chart(fig_vol, use_container_width=True)
    i += 1
