import pandas as pd
import ta


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or len(df) < 26:
        return df

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]

    df["MA5"]  = ta.trend.sma_indicator(close, window=5)
    df["MA20"] = ta.trend.sma_indicator(close, window=20)
    df["MA60"] = ta.trend.sma_indicator(close, window=60)
    df["EMA20"] = ta.trend.ema_indicator(close, window=20)

    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    df["BB_upper"] = bb.bollinger_hband()
    df["BB_mid"]   = bb.bollinger_mavg()
    df["BB_lower"] = bb.bollinger_lband()

    df["RSI"] = ta.momentum.rsi(close, window=14)

    macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    df["MACD_line"]   = macd.macd()
    df["MACD_signal"] = macd.macd_signal()
    df["MACD_hist"]   = macd.macd_diff()

    return df
