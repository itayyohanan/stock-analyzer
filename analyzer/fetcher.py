import yfinance as yf
import pandas as pd


class StockFetcher:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self._ticker = yf.Ticker(self.symbol)

    def get_history(self, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        df = self._ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No data found for symbol '{self.symbol}'")
        return df

    def get_info(self) -> dict:
        info = self._ticker.info
        keys = ["longName", "sector", "industry", "marketCap", "trailingPE",
                "forwardPE", "dividendYield", "52WeekHigh", "52WeekLow",
                "currentPrice", "currency"]
        return {k: info.get(k) for k in keys}
