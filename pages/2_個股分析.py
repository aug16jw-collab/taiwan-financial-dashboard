import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
from core.loader import search_companies, get_company_info
from core.market import get_realtime_price, get_historical, calc_pe, calc_pb
from core.technical import add_indicators
from core.charts import stock_chart, metric_trend_chart
from config import METRIC_DEFS, THRESHOLDS, COLOR_GOOD, COLOR_BAD

st.set_page_config(page_title="個股分析", page_icon="🔍", layout="wide")
st.title("🔍 個股分析")

quarters = st.session_state.get("quarters", {})
latest   = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))

if latest.empty:
    st.error("無資料，請返回首頁")
    st.stop()

# ── Search ──
col_search, col_period = st.columns([3, 1])
with col_search:
    query = st.text_input("輸入股票代號或名稱", placeholder="例如：2330 或 台積電", value="2330")
with col_period:
    period = st.selectbox("K線期間", ["3mo", "6mo", "1y", "2y"], index=2,
                          format_func=lambda x: {"3mo":"3個月","6mo":"6個月","1y":"1年","2y":"2年"}[x])

if not query.strip():
    st.info("請輸入股票代號或名稱")
    st.stop()

results = search_companies(latest, query.strip())
if results.empty:
    st.warning(f"找不到「{query}」，請確認代號或名稱")
    st.stop()

# If multiple matches, let user pick
if len(results) > 1:
    options = {f"{int(r.code)} {r['name']}": int(r.code) for _, r in results.iterrows()}
    sel = st.selectbox("選擇公司", list(options.keys()))
    code = options[sel]
    company = get_company_info(latest, code)
else:
    company = results.iloc[0]
    code = int(company["code"])

if company is None:
    st.error("找不到該公司資料")
    st.stop()

market = company["market"]
name   = str(company["name"])
st.markdown(f"## {code} {name}　`{market}`")

# ── Real-time price ──
with st.spinner("取得即時報價..."):
    price_info = get_realtime_price(str(code), market)

price     = price_info.get("price")
change    = price_info.get("change")
chg_pct   = price_info.get("change_pct")
eps_val   = company.get("eps")
bvps_val  = company.get("bvps")
pe        = calc_pe(price, eps_val, source_pe=price_info.get("pe"))
pb        = calc_pb(price, bvps_val, source_pb=price_info.get("pb"))
div_yield = price_info.get("div_yield")

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

def _price_str(v):
    return f"NT${v:,.2f}" if v else "N/A"

def _delta_str(v, pct):
    if v is None: return None
    sign = "+" if v >= 0 else ""
    pct_s = f" ({sign}{pct:.2f}%)" if pct else ""
    return f"{sign}{v:.2f}{pct_s}"

pe_src = "TWSE官方" if price_info.get("pe") else "EPS×4估算"
col1.metric("即時股價", _price_str(price), _delta_str(change, chg_pct),
            delta_color="normal" if (change or 0) >= 0 else "inverse")
col2.metric("本益比 (P/E)", f"{pe:.1f}x" if pe else "N/A", help=f"來源：{pe_src}")
col3.metric("市淨比 (P/B)", f"{pb:.2f}x" if pb else "N/A")
col4.metric("殖利率", f"{div_yield:.2f}%" if div_yield else "N/A")
col5.metric("每股盈餘 EPS", f"NT${eps_val:.2f}" if pd.notna(eps_val) else "N/A",
            help="Q1 單季 EPS")
col6.metric("每股淨值 BVPS", f"NT${bvps_val:.2f}" if pd.notna(bvps_val) else "N/A")
col7.metric("ROE", f"{company.get('roe'):.1f}%" if pd.notna(company.get('roe')) else "N/A")

st.markdown("---")

# ── Tabs ──
tab1, tab2, tab3 = st.tabs(["📈 技術分析", "📉 財務趨勢", "📋 基本面摘要"])

# ── Tab 1: Technical Analysis ──
with tab1:
    c_ma, c_bb = st.columns(2)
    show_ma = c_ma.checkbox("顯示均線 MA5/20/60", value=True)
    show_bb = c_bb.checkbox("顯示布林通道", value=True)

    with st.spinner("下載歷史股價..."):
        try:
            hist = get_historical(str(code), market, period=period)
            if hist.empty or len(hist) < 30:
                st.warning("歷史股價資料不足（可能是上市/上櫃代號問題）")
            else:
                hist = add_indicators(hist)
                fig = stock_chart(hist, str(code), name, show_ma=show_ma, show_bb=show_bb)
                st.plotly_chart(fig, use_container_width=True)

                last = hist.iloc[-1]
                st.markdown("#### 最新技術指標")
                ti1, ti2, ti3, ti4, ti5 = st.columns(5)
                ti1.metric("收盤價", f"{last['Close']:.2f}")
                ti2.metric("RSI (14)",
                           f"{last.get('RSI', float('nan')):.1f}" if pd.notna(last.get('RSI')) else "N/A",
                           help=">70 超買，<30 超賣")
                ti3.metric("MA20", f"{last.get('MA20', float('nan')):.2f}" if pd.notna(last.get('MA20')) else "N/A")
                ti4.metric("MACD",
                           f"{last.get('MACD_line', float('nan')):.3f}" if pd.notna(last.get('MACD_line')) else "N/A")
                ti5.metric("BB 位置",
                           f"{((last['Close'] - last.get('BB_lower', last['Close'])) / max(last.get('BB_upper', last['Close']) - last.get('BB_lower', last['Close']), 0.01) * 100):.0f}%" if pd.notna(last.get('BB_upper')) else "N/A",
                           help="0%=下軌，100%=上軌")
        except Exception as e:
            st.error(f"無法取得股價資料：{e}")

# ── Tab 2: Financial Trend ──
with tab2:
    multi_q = {k: v for k, v in quarters.items() if not v.empty}
    if len(multi_q) < 2:
        st.info("目前只有 1 季資料，新增更多季度資料夾（如 data/2025Q4/）後即可顯示趨勢圖")
        st.markdown("**當季財務指標：**")
        trend_data = []
        for label, field, unit in METRIC_DEFS[:8]:
            val = company.get(field)
            trend_data.append({"指標": label, "數值": f"{val:.2f}{unit}" if pd.notna(val) else "-"})
        st.dataframe(pd.DataFrame(trend_data), hide_index=True)
    else:
        trend_options = [m[0] for m in METRIC_DEFS[:9]]
        sel_trends = st.multiselect("選擇趨勢指標", trend_options,
                                    default=["毛利率(%)", "ROE(%)", "EPS(元)"])
        cols = st.columns(min(len(sel_trends), 2))
        for i, sel_label in enumerate(sel_trends):
            field = next(m[1] for m in METRIC_DEFS if m[0] == sel_label)
            fig = metric_trend_chart(multi_q, code, field, sel_label)
            cols[i % 2].plotly_chart(fig, use_container_width=True)

# ── Tab 3: Fundamentals Summary ──
with tab3:
    st.markdown("#### 16 項財務指標")

    metric_rows = []
    for label, field, unit in METRIC_DEFS:
        val = company.get(field)
        thresh_info = THRESHOLDS.get(field)

        if pd.notna(val):
            if unit == "%":
                display = f"{val:.1f}%"
            elif unit == "x":
                display = f"{val:.2f}x"
            elif unit == "元":
                display = f"{val:.2f}"
            else:
                display = f"{val:,.0f}"
        else:
            display = "-"

        status = ""
        if thresh_info and pd.notna(val):
            good_t, higher, bad_t = thresh_info
            if higher:
                status = "✅" if val >= good_t else ("⚠️" if bad_t and val >= bad_t else "❌")
            else:
                status = "✅" if val <= good_t else ("⚠️" if bad_t and val <= bad_t else "❌")

        all_vals = pd.to_numeric(latest[field], errors="coerce")
        if pd.notna(val) and len(all_vals.dropna()) > 0:
            pct_rank = (all_vals.dropna() <= val).mean() * 100 if unit != "%" else None
            pct_rank = (all_vals.dropna() <= val).mean() * 100
            rank_str = f"優於 {pct_rank:.0f}% 企業"
        else:
            rank_str = "-"

        metric_rows.append({
            "指標": label, "數值": display, "評等": status, "市場排名": rank_str,
        })

    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True,
                 column_config={
                     "評等": st.column_config.TextColumn(width="small"),
                 })

    st.markdown("---")
    st.markdown("#### 同類型市場比較")
    comp_field = st.selectbox("選擇比較指標", [m[0] for m in METRIC_DEFS[:9]])
    field = next(m[1] for m in METRIC_DEFS if m[0] == comp_field)
    all_v = pd.to_numeric(latest[field], errors="coerce").dropna()
    company_v = company.get(field)

    if pd.notna(company_v) and len(all_v) > 0:
        from core.charts import distribution_chart
        import plotly.graph_objects as go
        fig = distribution_chart(latest, field, comp_field)
        fig.add_vline(x=float(company_v), line_color="red", line_width=2,
                      annotation_text=f"{name}: {company_v:.1f}", annotation_position="top right")
        st.plotly_chart(fig, use_container_width=True)
