from __future__ import annotations

import pandas as pd
import numpy as np


class TechnicalIndicators:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def add_moving_averages(self, windows: list[int] = [20, 50, 200]) -> pd.DataFrame:
        for w in windows:
            self.df[f"MA{w}"] = self.df["Close"].rolling(window=w).mean()
        return self.df

    def add_rsi(self, period: int = 14) -> pd.DataFrame:
        delta = self.df["Close"].diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss
        self.df["RSI"] = 100 - (100 / (1 + rs))
        return self.df

    def add_macd(self, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        ema_fast = self.df["Close"].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df["Close"].ewm(span=slow, adjust=False).mean()
        self.df["MACD"] = ema_fast - ema_slow
        self.df["MACD_Signal"] = self.df["MACD"].ewm(span=signal, adjust=False).mean()
        self.df["MACD_Hist"] = self.df["MACD"] - self.df["MACD_Signal"]
        return self.df

    def add_bollinger_bands(self, period: int = 20, std: float = 2.0) -> pd.DataFrame:
        ma = self.df["Close"].rolling(period).mean()
        sd = self.df["Close"].rolling(period).std()
        self.df["BB_Upper"] = ma + std * sd
        self.df["BB_Middle"] = ma
        self.df["BB_Lower"] = ma - std * sd
        return self.df

    def add_all(self) -> pd.DataFrame:
        self.add_moving_averages()
        self.add_rsi()
        self.add_macd()
        self.add_bollinger_bands()
        return self.df

    def get_summary(self) -> dict:
        latest = self.df.iloc[-1]
        close = latest["Close"]
        return {
            "close": round(close, 2),
            "rsi": round(latest.get("RSI", float("nan")), 2),
            "macd": round(latest.get("MACD", float("nan")), 4),
            "macd_signal": round(latest.get("MACD_Signal", float("nan")), 4),
            "bb_upper": round(latest.get("BB_Upper", float("nan")), 2),
            "bb_lower": round(latest.get("BB_Lower", float("nan")), 2),
            "ma20": round(latest.get("MA20", float("nan")), 2),
            "ma50": round(latest.get("MA50", float("nan")), 2),
            "ma200": round(latest.get("MA200", float("nan")), 2),
            "above_ma20": close > latest.get("MA20", 0),
            "above_ma50": close > latest.get("MA50", 0),
            "above_ma200": close > latest.get("MA200", 0),
        }
