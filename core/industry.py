import time
import requests
import pandas as pd

_CACHE: dict = {}
_CACHE_TS: float = 0
_TTL = 3600 * 6  # 6 hours

TWSE_INDUSTRY_MAP = {
    "01": "水泥工業", "02": "食品工業", "03": "塑膠工業",
    "04": "紡織纖維", "05": "電機機械", "06": "電器電纜",
    "08": "化學工業", "09": "生技醫療", "10": "玻璃陶瓷",
    "11": "造紙工業", "12": "鋼鐵工業", "13": "橡膠工業",
    "14": "汽車工業", "15": "電子工業", "16": "建材營造",
    "17": "航運業",   "18": "觀光餐旅", "19": "金融保險",
    "20": "貿易百貨", "21": "油電燃氣", "22": "半導體業",
    "23": "電腦及週邊", "24": "光電業",  "25": "通信網路",
    "26": "電子零組件", "27": "電子通路", "28": "資訊服務",
    "29": "其他電子", "31": "文化創意",  "32": "農業科技",
    "33": "電子商務", "34": "觀光餐旅",  "35": "綠能環保",
    "36": "數位雲端", "37": "運動休閒",  "38": "居家生活",
    "99": "其他",
}

_H = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.twse.com.tw/"}


def _fetch_industry_map() -> dict:
    code_industry = {}
    try:
        r = requests.get(
            "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
            headers=_H, verify=False, timeout=15,
        )
        for row in r.json():
            vals = list(row.values())
            code = str(vals[1]).strip()
            ind_code = str(vals[5]).strip()
            code_industry[code] = TWSE_INDUSTRY_MAP.get(ind_code, f"其他({ind_code})")
    except Exception:
        pass

    try:
        r2 = requests.get(
            "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap03_O",
            headers=_H, verify=False, timeout=15,
        )
        for row in r2.json():
            code = str(row.get("SecuritiesCompanyCode", "")).strip()
            ind_code = str(row.get("SecuritiesIndustryCode", "")).strip()
            code_industry[code] = TWSE_INDUSTRY_MAP.get(ind_code, f"其他({ind_code})")
    except Exception:
        pass

    return code_industry


def get_industry_map() -> dict:
    global _CACHE, _CACHE_TS
    now = time.time()
    if _CACHE and now - _CACHE_TS < _TTL:
        return _CACHE
    result = _fetch_industry_map()
    if result:
        _CACHE = result
        _CACHE_TS = now
    return _CACHE


def add_industry_column(df: pd.DataFrame) -> pd.DataFrame:
    ind_map = get_industry_map()
    df = df.copy()
    df["industry"] = df["code"].astype(str).map(ind_map).fillna("其他")
    return df


def get_industry_list(df: pd.DataFrame) -> list:
    return sorted(df["industry"].dropna().unique().tolist())
