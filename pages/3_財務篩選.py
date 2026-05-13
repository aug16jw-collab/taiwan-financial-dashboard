import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import numpy as np
import pandas as pd
import streamlit as st
from core.nav import stock_table
from config import METRIC_DEFS, COLOR_LISTED, COLOR_OTC

st.set_page_config(page_title="財務篩選", page_icon="⚙️", layout="wide")
st.title("⚙️ 財務篩選器")

latest = st.session_state.get("selected_df", st.session_state.get("latest", pd.DataFrame()))
if latest.empty:
    st.error("無資料，請返回首頁")
    st.stop()

st.markdown("### 篩選條件")
st.caption("拖動滑桿設定各指標的篩選範圍（留空或拖至極端值代表不限制）")

# ── Market filter ──
market_opt = st.radio("市場", ["全部", "上市", "上櫃"], horizontal=True)

# ── Build sliders ──
SLIDABLE = [
    ("毛利率(%)",     "gross_margin", "%",   -50,  100),
    ("營業利益率(%)", "op_margin",    "%",  -100,  100),
    ("淨利率(%)",     "net_margin",   "%",  -200,  100),
    ("ROE(%)",        "roe",          "%",  -100,  200),
    ("ROA(%)",        "roa",          "%",   -50,   50),
    ("流動比率(x)",   "current_ratio","x",     0,   10),
    ("負債比率(%)",   "debt_ratio",   "%",     0,  100),
    ("EPS(元)",       "eps",          "元", -100,  200),
    ("每股淨值(元)",  "bvps",         "元",    0,  500),
    ("自由現金流(千元)","free_cf",    "千元",-5e6, 5e6),
]

filters = {}
cols = st.columns(2)
for i, (label, field, unit, lo, hi) in enumerate(SLIDABLE):
    vals = pd.to_numeric(latest[field], errors="coerce").dropna()
    actual_lo = max(float(vals.quantile(0.01)) if len(vals) else lo, lo)
    actual_hi = min(float(vals.quantile(0.99)) if len(vals) else hi, hi)
    actual_lo = round(actual_lo, 1)
    actual_hi = round(actual_hi, 1)
    if actual_lo >= actual_hi:
        actual_hi = actual_lo + 1

    with cols[i % 2]:
        selected = st.slider(
            label, min_value=float(actual_lo), max_value=float(actual_hi),
            value=(float(actual_lo), float(actual_hi)),
            step=0.1 if unit in ("%", "x", "元") else 1000.0,
            key=f"slider_{field}",
        )
        filters[field] = selected

# ── Apply filters ──
mask = pd.Series(True, index=latest.index)
if market_opt != "全部":
    mask &= latest["market"] == market_opt

for field, (lo, hi) in filters.items():
    col = pd.to_numeric(latest[field], errors="coerce")
    mask &= (col >= lo) & (col <= hi)

result = latest[mask].copy()

st.markdown("---")
st.markdown(f"### 篩選結果：**{len(result)}** 家公司")

if result.empty:
    st.info("目前條件無符合公司，請放寬篩選條件")
    st.stop()

# ── Display ──
display_cols = ["market", "code", "name", "gross_margin", "op_margin",
                "roe", "roa", "eps", "bvps", "current_ratio", "debt_ratio", "free_cf"]
col_names = {
    "market": "市場", "code": "代號", "name": "名稱",
    "gross_margin": "毛利率%", "op_margin": "營業利益率%",
    "roe": "ROE%", "roa": "ROA%", "eps": "EPS",
    "bvps": "每股淨值", "current_ratio": "流動比率",
    "debt_ratio": "負債比率%", "free_cf": "自由現金流(千元)",
}

disp = result[display_cols].copy()
disp["code"] = disp["code"].astype(int)
for pct in ["gross_margin", "op_margin", "roe", "roa", "debt_ratio"]:
    disp[pct] = disp[pct].apply(lambda v: f"{v:.1f}%" if pd.notna(v) else "-")
for yen in ["eps", "bvps"]:
    disp[yen] = disp[yen].apply(lambda v: f"{v:.2f}" if pd.notna(v) else "-")
disp["current_ratio"] = disp["current_ratio"].apply(lambda v: f"{v:.2f}x" if pd.notna(v) else "-")
disp["free_cf"] = disp["free_cf"].apply(lambda v: f"{v:,.0f}" if pd.notna(v) else "-")
disp.columns = [col_names[c] for c in display_cols]

stock_table(disp, key="filter_result_table")

# ── Export ──
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    result.to_excel(writer, index=False, sheet_name="篩選結果")
buf.seek(0)
st.download_button(
    "📥 下載篩選結果 (xlsx)",
    data=buf,
    file_name="financial_screen_result.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
