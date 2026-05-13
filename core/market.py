import time
import requests
import yfinance as yf
import pandas as pd

_CACHE: dict = {}
_CACHE_TS: dict = {}
_TTL = 300  # 5 min

TWSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.twse.com.tw/",
}


def _cached_get(key: str, fetch_fn):
    now = time.time()
    if key in _CACHE and now - _CACHE_TS.get(key, 0) < _TTL:
        return _CACHE[key]
    try:
        result = fetch_fn()
        _CACHE[key] = result
        _CACHE_TS[key] = now
    except Exception:
        pass
    return _CACHE.get(key, {})


def _fetch_twse_prices() -> dict:
    r = requests.get(
        "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
        headers=TWSE_HEADERS, verify=False, timeout=15,
    )
    return {row["Code"]: row for row in r.json()}


def _fetch_twse_pe() -> dict:
    """BWIBBU_ALL: P/E, P/B, dividend yield for all listed stocks."""
    r = requests.get(
        "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL",
        headers=TWSE_HEADERS, verify=False, timeout=15,
    )
    return {row["Code"]: row for row in r.json()}


def _fetch_tpex_prices() -> dict:
    r = requests.get(
        "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
        headers=TWSE_HEADERS, verify=False, timeout=15,
    )
    return {row["SecuritiesCompanyCode"]: row for row in r.json()}


def get_realtime_price(code: str, market: str) -> dict:
    result = {"price": None, "change": None, "change_pct": None,
              "volume": None, "pe": None, "pb": None, "div_yield": None}
    code_str = str(code)

    if market == "上市":
        prices = _cached_get("twse_prices", _fetch_twse_prices)
        pe_data = _cached_get("twse_pe", _fetch_twse_pe)

        row = prices.get(code_str, {})
        pe_row = pe_data.get(code_str, {})

        def _f(d, k):
            try:
                v = str(d.get(k, "")).replace(",", "").strip()
                return float(v) if v and v != "--" else None
            except (ValueError, TypeError):
                return None

        result["price"]     = _f(row, "ClosingPrice")
        result["change"]    = _f(row, "Change")
        result["volume"]    = _f(row, "TradeVolume")
        result["pe"]        = _f(pe_row, "PEratio")
        result["pb"]        = _f(pe_row, "PBratio")
        result["div_yield"] = _f(pe_row, "DividendYield")
        if result["price"] and result["change"]:
            prev = result["price"] - result["change"]
            result["change_pct"] = (result["change"] / prev * 100) if prev else None

    else:  # 上櫃
        prices = _cached_get("tpex_prices", _fetch_tpex_prices)
        row = prices.get(code_str, {})

        def _f2(d, k):
            try:
                v = str(d.get(k, "")).replace(",", "").strip()
                return float(v) if v and v != "--" else None
            except (ValueError, TypeError):
                return None

        result["price"]  = _f2(row, "Close")
        result["change"] = _f2(row, "Change")
        if result["price"] and result["change"]:
            prev = result["price"] - result["change"]
            result["change_pct"] = (result["change"] / prev * 100) if prev else None

    # Fallback to yfinance if price missing
    if not result["price"]:
        suffix = ".TW" if market == "上市" else ".TWO"
        try:
            info = yf.Ticker(f"{code_str}{suffix}").fast_info
            result["price"] = getattr(info, "last_price", None)
        except Exception:
            pass

    return result


def get_historical(code: str, market: str, period: str = "1y") -> pd.DataFrame:
    suffix = ".TW" if market == "上市" else ".TWO"
    df = yf.Ticker(f"{code}{suffix}").history(period=period)
    df.index = pd.to_datetime(df.index)
    return df[["Open", "High", "Low", "Close", "Volume"]].copy()


def calc_pe(price, eps_q1, source_pe=None):
    """Use TWSE official P/E if available, else calculate from EPS."""
    if source_pe:
        return round(float(source_pe), 1)
    if price and eps_q1 and eps_q1 != 0:
        ann = eps_q1 * 4
        if ann > 0:
            return round(price / ann, 1)
    return None


def calc_pb(price, bvps, source_pb=None):
    if source_pb:
        return round(float(source_pb), 2)
    if price and bvps and bvps > 0:
        return round(price / bvps, 2)
    return None
