import time
from datetime import datetime, timedelta
import requests
import pandas as pd

_CACHE: dict = {}
_CACHE_TS: dict = {}
_TTL = 300

_H = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.twse.com.tw/"}

COLS = ["外資買超(股)", "外資買超(股)", "外資淨買超",
        "投信買進", "投信賣出", "投信淨買超",
        "自營商買進", "自營商賣出", "自營商淨買超", "三大法人合計"]


def _fetch_t86_today() -> pd.DataFrame:
    r = requests.get(
        "https://www.twse.com.tw/rwd/zh/fund/T86?response=json&selectType=ALL",
        headers=_H, verify=False, timeout=15,
    )
    d = r.json()
    if d.get("stat") != "OK" or not d.get("data"):
        return pd.DataFrame()
    rows = []
    for row in d["data"]:
        try:
            def _n(v): return int(str(v).replace(",", "").strip()) if str(v).strip() not in ("", "--") else 0
            rows.append({
                "code":       str(row[0]).strip(),
                "外資淨買超": _n(row[4]),
                "投信淨買超": _n(row[10]),
                "自營商淨買超": _n(row[11]),
                "三大法人合計": _n(row[18]),
            })
        except Exception:
            pass
    return pd.DataFrame(rows)


def get_today_institutional() -> pd.DataFrame:
    key = "t86_today"
    now = time.time()
    if key in _CACHE and now - _CACHE_TS.get(key, 0) < _TTL:
        return _CACHE[key]
    df = pd.DataFrame()
    try:
        df = _fetch_t86_today()
    except Exception:
        pass
    _CACHE[key] = df
    _CACHE_TS[key] = now
    return df


def get_stock_institutional_history(code: str, days: int = 20) -> pd.DataFrame:
    """Fetch last N trading days of institutional data for a single stock."""
    key = f"inst_{code}_{days}"
    now = time.time()
    if key in _CACHE and now - _CACHE_TS.get(key, 0) < _TTL * 6:
        return _CACHE[key]

    records = []
    date = datetime.now()
    attempts = 0
    while len(records) < days and attempts < 40:
        date_str = date.strftime("%Y%m%d")
        try:
            r = requests.get(
                f"https://www.twse.com.tw/rwd/zh/fund/T86?response=json&date={date_str}&selectType=ALL",
                headers=_H, verify=False, timeout=10,
            )
            d = r.json()
            if d.get("stat") == "OK" and d.get("data"):
                tw_date = d.get("date", date_str)
                for row in d["data"]:
                    if str(row[0]).strip() == code:
                        def _n(v): return int(str(v).replace(",", "").strip()) if str(v).strip() not in ("", "--") else 0
                        records.append({
                            "date":       tw_date,
                            "外資淨買超": _n(row[4]),
                            "投信淨買超": _n(row[10]),
                            "自營商淨買超": _n(row[11]),
                            "三大法人合計": _n(row[18]),
                        })
                        break
        except Exception:
            pass
        date -= timedelta(days=1)
        attempts += 1

    df = pd.DataFrame(records).iloc[::-1].reset_index(drop=True) if records else pd.DataFrame()
    _CACHE[key] = df
    _CACHE_TS[key] = now
    return df


def get_tpex_institutional_today() -> pd.DataFrame:
    """Fetch today's OTC institutional data."""
    key = "tpex_inst_today"
    now = time.time()
    if key in _CACHE and now - _CACHE_TS.get(key, 0) < _TTL:
        return _CACHE[key]
    df = pd.DataFrame()
    try:
        r = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_3big_investors",
            headers=_H, verify=False, timeout=10,
        )
        data = r.json()
        rows = []
        for row in data:
            try:
                def _n(v): return int(str(v).replace(",", "").strip()) if str(v).strip() not in ("", "--", "N/A") else 0
                rows.append({
                    "code":       str(row.get("SecuritiesCompanyCode", "")).strip(),
                    "外資淨買超": _n(row.get("ForeignInvestorsBuySellDifference", 0)),
                    "投信淨買超": _n(row.get("InvestmentTrustBuySellDifference", 0)),
                    "自營商淨買超": _n(row.get("DealerBuySellDifference", 0)),
                    "三大法人合計": _n(row.get("TotalBuySellDifference", 0)),
                })
            except Exception:
                pass
        df = pd.DataFrame(rows)
    except Exception:
        pass
    _CACHE[key] = df
    _CACHE_TS[key] = now
    return df
