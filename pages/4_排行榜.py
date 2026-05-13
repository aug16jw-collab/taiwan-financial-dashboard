import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
from core.charts import top20_chart
from config import METRIC_DEFS

st.set_page_config(page_title="排行榜", page_icon="🏆", layout="wide")
st.title("🏆 各指標排行榜")

latest = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))
if latest.empty:
    st.error("無資料，請返回首頁")
    st.stop()

market_opt = st.radio("市場範圍", ["全部", "上市", "上櫃"], horizontal=True)
df = latest if market_opt == "全部" else latest[latest["market"] == market_opt]

RANK_METRICS = [
    ("毛利率(%)",     "gross_margin", True),
    ("營業利益率(%)", "op_margin",    True),
    ("淨利率(%)",     "net_margin",   True),
    ("ROE(%)",        "roe",          True),
    ("ROA(%)",        "roa",          True),
    ("EPS(元)",       "eps",          True),
    ("每股淨值(元)",  "bvps",         True),
    ("自由現金流(千元)","free_cf",    True),
    ("負債最低(%)",   "debt_ratio",   False),
]

tab_labels = [m[0] for m in RANK_METRICS]
tabs = st.tabs(tab_labels)

for tab, (label, field, desc) in zip(tabs, RANK_METRICS):
    with tab:
        col_chart, col_table = st.columns([3, 2])
        with col_chart:
            fig = top20_chart(df, field, label, ascending=not desc)
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            sub = df[["code", "name", "market", field]].copy()
            sub[field] = pd.to_numeric(sub[field], errors="coerce")
            sub = sub.dropna(subset=[field]).sort_values(field, ascending=not desc).head(20).reset_index(drop=True)
            sub.index += 1

            unit = next(m[2] for m in METRIC_DEFS if m[1] == field)
            if unit == "%":
                sub[field] = sub[field].apply(lambda v: f"{v:.1f}%")
            elif unit == "x":
                sub[field] = sub[field].apply(lambda v: f"{v:.2f}x")
            elif unit == "元":
                sub[field] = sub[field].apply(lambda v: f"{v:.2f}")
            else:
                sub[field] = sub[field].apply(lambda v: f"{v:,.0f}")

            sub.columns = ["代號", "名稱", "市場", label]
            sub["代號"] = sub["代號"].astype(int)

            st.dataframe(sub, use_container_width=True)
