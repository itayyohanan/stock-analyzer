from __future__ import annotations

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


class StockVisualizer:
    def __init__(self, df: pd.DataFrame, symbol: str):
        self.df = df
        self.symbol = symbol

    def plot(self, save_path: str | None = None):
        fig = plt.figure(figsize=(14, 10))
        fig.suptitle(f"{self.symbol} Technical Analysis", fontsize=14, fontweight="bold")
        gs = gridspec.GridSpec(3, 1, height_ratios=[3, 1, 1], hspace=0.1)

        # Price + MAs + Bollinger
        ax1 = fig.add_subplot(gs[0])
        ax1.plot(self.df.index, self.df["Close"], label="Close", linewidth=1.5, color="black")
        for col, color in [("MA20", "blue"), ("MA50", "orange"), ("MA200", "red")]:
            if col in self.df.columns:
                ax1.plot(self.df.index, self.df[col], label=col, linewidth=1, color=color, alpha=0.7)
        if "BB_Upper" in self.df.columns:
            ax1.fill_between(self.df.index, self.df["BB_Lower"], self.df["BB_Upper"],
                             alpha=0.1, color="gray", label="Bollinger Bands")
        ax1.set_ylabel("Price")
        ax1.legend(loc="upper left", fontsize=8)
        ax1.grid(True, alpha=0.3)
        ax1.set_xticklabels([])

        # RSI
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        if "RSI" in self.df.columns:
            ax2.plot(self.df.index, self.df["RSI"], color="purple", linewidth=1)
            ax2.axhline(70, color="red", linestyle="--", linewidth=0.8, alpha=0.7)
            ax2.axhline(30, color="green", linestyle="--", linewidth=0.8, alpha=0.7)
            ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI")
        ax2.grid(True, alpha=0.3)
        ax2.set_xticklabels([])

        # MACD
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        if "MACD" in self.df.columns:
            ax3.plot(self.df.index, self.df["MACD"], label="MACD", color="blue", linewidth=1)
            ax3.plot(self.df.index, self.df["MACD_Signal"], label="Signal", color="orange", linewidth=1)
            colors = ["green" if v >= 0 else "red" for v in self.df["MACD_Hist"]]
            ax3.bar(self.df.index, self.df["MACD_Hist"], color=colors, alpha=0.5, width=1)
        ax3.set_ylabel("MACD")
        ax3.legend(loc="upper left", fontsize=8)
        ax3.grid(True, alpha=0.3)

        plt.xticks(rotation=30, ha="right")
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Chart saved to {save_path}")
        else:
            plt.show()
        plt.close()
