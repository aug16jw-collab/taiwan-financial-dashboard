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
    else:
        st.error("找不到財報資料，請確認 data/ 資料夾")

    st.markdown("---")
    st.markdown(
        f"**資料期數：** {len(available_quarters)} 季\n\n"
        f"**最新季度：** {available_quarters[0] if available_quarters else '-'}\n\n"
        f"**分析家數：** {len(latest):,} 家\n\n"
        f"**優質企業：** {len(quality)} 家",
        unsafe_allow_html=False,
    )

    if st.button("重新載入資料", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("資料來源：MOPS 公開資訊觀測站\n股價：Yahoo Finance / TWSE OpenAPI")

# ── Landing page ──
st.title("📈 台股財務分析平台")
st.markdown("**2026 Q1 財報全市場分析 | 基本面 × 技術面 × 即時報價**")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
col1.metric("分析家數", f"{len(latest):,} 家")
col2.metric("上市家數", f"{len(latest[latest['market']=='上市']):,} 家")
col3.metric("上櫃家數", f"{len(latest[latest['market']=='上櫃']):,} 家")
col4.metric("優質企業", f"{len(quality)} 家", help="毛利率≥20% + 營業利益率≥5% + ROE≥10% + 自由現金流>0")

st.markdown("---")
st.markdown("""
### 功能導覽

| 頁面 | 說明 |
|------|------|
| **市場總覽** | 全市場指標統計、分佈圖、優質公司名單 |
| **個股分析** | 即時報價、K線+技術指標、財務趨勢、本益比 |
| **財務篩選** | 自訂 16 項指標條件，篩選符合標準的公司 |
| **排行榜** | 毛利率、營業利益率、ROE、EPS 各前 20 名 |

> **使用方式**：請從左側選單選擇頁面
""")
