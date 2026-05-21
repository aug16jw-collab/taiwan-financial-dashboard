import re
from pathlib import Path
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_DIR, QUALITY_CRITERIA

PROCESSED_DIR = DATA_DIR / "processed"


def _to_num(series):
    return pd.to_numeric(series.replace("--", np.nan), errors="coerce")


def _load_income(path):
    df = pd.read_excel(path, header=0)
    df.columns = range(len(df.columns))
    return df[[3, 4, 5, 6, 9, 15, 19, 32]].rename(columns={
        3: "code", 4: "name",
        5: "revenue", 6: "cogs", 9: "gross_profit",
        15: "op_income", 19: "net_income", 32: "eps",
    })


def _load_balance(path):
    df = pd.read_excel(path, header=0)
    df.columns = range(len(df.columns))
    return df[[3, 5, 7, 8, 10, 21, 25]].rename(columns={
        3: "code",
        5: "curr_assets", 7: "total_assets",
        8: "curr_liab", 10: "total_liab",
        21: "equity", 25: "bvps",
    })


def _load_cf(path):
    df = pd.read_excel(path, header=0)
    df.columns = range(len(df.columns))
    return df[[3, 5, 6]].rename(columns={
        3: "code", 5: "op_cf", 6: "inv_cf",
    })


def _compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    raw_cols = ["revenue", "cogs", "gross_profit", "op_income", "net_income",
                "eps", "curr_assets", "total_assets", "curr_liab", "total_liab",
                "equity", "bvps", "op_cf", "inv_cf"]
    for c in raw_cols:
        if c in df.columns:
            df[c] = _to_num(df[c])

    def safe_div(a, b):
        return np.where(df[b].fillna(0) != 0, df[a] / df[b], np.nan)

    df["gross_margin"]  = safe_div("gross_profit", "revenue") * 100
    df["op_margin"]     = safe_div("op_income",    "revenue") * 100
    df["net_margin"]    = safe_div("net_income",   "revenue") * 100
    df["roe"]           = safe_div("net_income",   "equity")  * 100
    df["roa"]           = safe_div("net_income",   "total_assets") * 100
    df["current_ratio"] = safe_div("curr_assets",  "curr_liab")
    df["debt_ratio"]    = safe_div("total_liab",   "total_assets") * 100
    df["free_cf"]       = df["op_cf"].fillna(0) + df["inv_cf"].fillna(0)
    return df


def _find_xlsx(folder: Path, market: str, keyword: str) -> Path:
    """Find an xlsx file matching market and keyword, trying multiple naming patterns."""
    candidates = [
        folder / f"{market}_{keyword}.xlsx",           # 上市_綜合損益表.xlsx
        folder / f"{market} {keyword}.xlsx",           # 上市 綜合損益表.xlsx
    ]
    # Also glob for any file containing both market and keyword
    for p in candidates:
        if p.exists():
            return p
    for p in folder.glob("*.xlsx"):
        if market in p.name and keyword in p.name:
            return p
    raise FileNotFoundError(
        f"找不到 {market} {keyword}.xlsx，資料夾：{folder}\n"
        f"現有檔案：{[f.name for f in folder.glob('*.xlsx')]}"
    )


def load_quarter(folder: Path, market_label: str) -> pd.DataFrame:
    income  = _load_income(_find_xlsx(folder, market_label, "綜合損益表"))
    balance = _load_balance(_find_xlsx(folder, market_label, "資產負債表"))
    cf      = _load_cf(_find_xlsx(folder, market_label, "現金流量表"))
    df = income.merge(balance, on="code").merge(cf, on="code")
    df["market"] = "上市" if market_label == "上市" else "上櫃"
    return _compute_metrics(df)


def load_quarter_combined(quarter_folder: Path) -> pd.DataFrame:
    listed = load_quarter(quarter_folder, "上市")
    otc    = load_quarter(quarter_folder, "上櫃")
    df = pd.concat([listed, otc], ignore_index=True)
    df["code"] = df["code"].astype(int)
    df = df.sort_values(["market", "code"]).reset_index(drop=True)
    return df


def load_all_quarters() -> dict:
    """Load quarters: prefer parquet (git-tracked), fallback to raw XLSX."""
    quarters = {}

    # 1. Load from processed parquet files (for deployment)
    if PROCESSED_DIR.exists():
        for pq in sorted(PROCESSED_DIR.glob("*.parquet")):
            name = pq.stem  # e.g. "2026Q1"
            try:
                quarters[name] = pd.read_parquet(pq)
            except Exception:
                pass

    # 2. Fallback: load from raw XLSX in data/ subdirectories
    for folder in sorted(DATA_DIR.iterdir()):
        if (folder.is_dir()
                and folder.name != "processed"
                and folder.name not in quarters
                and (folder / "上市_綜合損益表.xlsx").exists()):
            try:
                quarters[folder.name] = load_quarter_combined(folder)
            except Exception:
                pass

    return quarters


def get_latest_df(quarters: dict) -> pd.DataFrame:
    if not quarters:
        return pd.DataFrame()
    return quarters[sorted(quarters.keys())[-1]]


def quality_filter(df: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for field, (op, val) in QUALITY_CRITERIA.items():
        col = pd.to_numeric(df[field], errors="coerce")
        mask &= (col >= val) if op == ">=" else (col > val)
    return df[mask].copy()


def get_company_info(df: pd.DataFrame, code: int):
    rows = df[df["code"] == code]
    return rows.iloc[0] if len(rows) > 0 else None


def search_companies(df: pd.DataFrame, query: str) -> pd.DataFrame:
    query = str(query).strip()
    if query.isdigit():
        return df[df["code"] == int(query)]
    return df[df["name"].astype(str).str.contains(query, na=False)]
