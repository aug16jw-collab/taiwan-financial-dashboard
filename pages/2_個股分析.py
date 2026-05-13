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
    _default = st.query_params.get("code", "2330")
    query = st.text_input("輸入股票代號或名稱", placeholder="例如：2330 或 台積電", value=_default)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 技術分析", "📉 財務趨勢", "📋 基本面摘要", "💰 股息歷史", "📐 估值區間"])

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

# ── Tab 4: Dividend History ──
with tab4:
    import yfinance as yf
    ticker_suffix = ".TW" if market == "上市" else ".TWO"
    ticker_str = f"{code}{ticker_suffix}"

    st.markdown(f"#### {code} {name} — 股息發放歷史")
    try:
        tkr = yf.Ticker(ticker_str)
        divs = tkr.dividends
        if divs.empty:
            st.info("查無股息資料（可能是成長股或 yfinance 尚無紀錄）")
        else:
            divs = divs.reset_index()
            divs.columns = ["日期", "每股股息(TWD)"]
            divs["日期"] = pd.to_datetime(divs["日期"]).dt.date

            # Annual aggregation
            divs["年度"] = pd.to_datetime(divs["日期"]).dt.year
            annual = divs.groupby("年度")["每股股息(TWD)"].sum().reset_index()
            annual.columns = ["年度", "年度股息合計(TWD)"]

            d1, d2 = st.columns(2)
            with d1:
                import plotly.graph_objects as go_div
                fig_div = go_div.Figure(go_div.Bar(
                    x=annual["年度"].astype(str),
                    y=annual["年度股息合計(TWD)"],
                    marker_color="#4CAF50",
                    text=annual["年度股息合計(TWD)"].apply(lambda v: f"NT${v:.2f}"),
                    textposition="outside",
                ))
                fig_div.update_layout(
                    title="年度股息合計",
                    xaxis_title="年度",
                    yaxis_title="每股股息 (TWD)",
                    height=350,
                )
                st.plotly_chart(fig_div, use_container_width=True)

            with d2:
                st.markdown("**歷次除息紀錄**")
                disp_divs = divs.sort_values("日期", ascending=False).reset_index(drop=True)
                disp_divs["每股股息(TWD)"] = disp_divs["每股股息(TWD)"].apply(lambda v: f"NT${v:.4f}")
                st.dataframe(disp_divs.drop(columns=["年度"]), use_container_width=True, hide_index=True)

            # Yield estimate
            if price:
                latest_annual = annual["年度股息合計(TWD)"].iloc[-1] if not annual.empty else 0
                est_yield = latest_annual / price * 100
                st.info(f"以目前股價 NT${price:,.2f} 計算，最近完整年度殖利率約 **{est_yield:.2f}%**")
    except Exception as e:
        st.warning(f"無法取得股息資料：{e}")

# ── Tab 5: Valuation Band ──
with tab5:
    st.markdown(f"#### {code} {name} — P/E 估值區間")

    eps_ann = eps_val * 4 if pd.notna(eps_val) else None

    try:
        ticker_suffix5 = ".TW" if market == "上市" else ".TWO"
        tkr5 = yf.Ticker(f"{code}{ticker_suffix5}")
        hist5 = tkr5.history(period="5y")

        if hist5.empty or eps_ann is None or eps_ann <= 0:
            st.info("歷史股價資料不足或 EPS 為零，無法繪製估值區間")
        else:
            hist5 = hist5.reset_index()
            hist5["Date"] = pd.to_datetime(hist5["Date"]).dt.tz_localize(None)
            hist5["PE_implied"] = hist5["Close"] / eps_ann

            pe_10 = hist5["PE_implied"].quantile(0.10)
            pe_25 = hist5["PE_implied"].quantile(0.25)
            pe_50 = hist5["PE_implied"].quantile(0.50)
            pe_75 = hist5["PE_implied"].quantile(0.75)
            pe_90 = hist5["PE_implied"].quantile(0.90)

            import plotly.graph_objects as go_pe
            fig_pe = go_pe.Figure()

            # PE bands as horizontal lines on price chart
            for pct_val, label, color in [
                (pe_90, f"90% PE ({pe_90:.1f}x)", "#F44336"),
                (pe_75, f"75% PE ({pe_75:.1f}x)", "#FF9800"),
                (pe_50, f"中位 PE ({pe_50:.1f}x)", "#9E9E9E"),
                (pe_25, f"25% PE ({pe_25:.1f}x)", "#2196F3"),
                (pe_10, f"10% PE ({pe_10:.1f}x)", "#1565C0"),
            ]:
                price_level = pct_val * eps_ann
                fig_pe.add_hline(
                    y=price_level,
                    line_dash="dash",
                    line_color=color,
                    opacity=0.7,
                    annotation_text=label,
                    annotation_position="right",
                )

            fig_pe.add_trace(go_pe.Scatter(
                x=hist5["Date"],
                y=hist5["Close"],
                name="收盤價",
                mode="lines",
                line=dict(color="#212121", width=1.5),
            ))

            if price:
                fig_pe.add_hline(
                    y=price,
                    line_color="red",
                    line_width=2,
                    annotation_text=f"即時 NT${price:,.2f}",
                    annotation_position="left",
                )

            fig_pe.update_layout(
                title=f"{name} 5年股價 + PE估值帶（以 EPS×4={eps_ann:.2f} 估算）",
                xaxis_title="日期",
                yaxis_title="股價 (TWD)",
                height=430,
                hovermode="x unified",
                showlegend=True,
            )
            st.plotly_chart(fig_pe, use_container_width=True)

            # PE summary table
            pe_rows = [
                {"分位數": "10%（低估區）", "隱含PE": f"{pe_10:.1f}x", "對應股價": f"NT${pe_10*eps_ann:,.2f}"},
                {"分位數": "25%", "隱含PE": f"{pe_25:.1f}x", "對應股價": f"NT${pe_25*eps_ann:,.2f}"},
                {"分位數": "50%（中性）", "隱含PE": f"{pe_50:.1f}x", "對應股價": f"NT${pe_50*eps_ann:,.2f}"},
                {"分位數": "75%", "隱含PE": f"{pe_75:.1f}x", "對應股價": f"NT${pe_75*eps_ann:,.2f}"},
                {"分位數": "90%（高估區）", "隱含PE": f"{pe_90:.1f}x", "對應股價": f"NT${pe_90*eps_ann:,.2f}"},
            ]
            st.dataframe(pd.DataFrame(pe_rows), use_container_width=True, hide_index=True)

            if pe and pe > 0:
                if pe >= pe_75:
                    st.warning(f"目前 PE {pe:.1f}x 高於歷史 75% 分位，股價偏高")
                elif pe <= pe_25:
                    st.success(f"目前 PE {pe:.1f}x 低於歷史 25% 分位，股價偏低")
                else:
                    st.info(f"目前 PE {pe:.1f}x 位於歷史 25%～75% 合理區間")

    except Exception as e:
        st.warning(f"無法計算估值區間：{e}")
