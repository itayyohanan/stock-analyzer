#!/usr/bin/env python3
import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from analyzer import StockFetcher, TechnicalIndicators, StockVisualizer

console = Console()


def print_info(symbol: str, info: dict):
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    labels = {
        "longName": "Company", "sector": "Sector", "industry": "Industry",
        "marketCap": "Market Cap", "currentPrice": "Current Price",
        "trailingPE": "P/E (trailing)", "forwardPE": "P/E (forward)",
        "dividendYield": "Dividend Yield", "52WeekHigh": "52W High",
        "52WeekLow": "52W Low", "currency": "Currency",
    }
    for key, label in labels.items():
        val = info.get(key)
        if val is None:
            continue
        if key == "marketCap":
            val = f"${val:,.0f}"
        elif key == "dividendYield" and val:
            val = f"{val * 100:.2f}%"
        elif isinstance(val, float):
            val = f"{val:.2f}"
        table.add_row(label, str(val))

    console.print(Panel(table, title=f"[bold]{symbol}[/bold]", border_style="blue"))


def print_indicators(summary: dict):
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
    table.add_column("Indicator", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Signal", style="bold")

    rsi = summary["rsi"]
    rsi_signal = "[red]Overbought" if rsi > 70 else "[green]Oversold" if rsi < 30 else "[yellow]Neutral"

    macd_signal = "[green]Bullish" if summary["macd"] > summary["macd_signal"] else "[red]Bearish"

    table.add_row("Close", f"${summary['close']:.2f}", "")
    table.add_row("RSI (14)", f"{rsi:.2f}", rsi_signal)
    table.add_row("MACD", f"{summary['macd']:.4f}", macd_signal)
    table.add_row("MA20", f"${summary['ma20']:.2f}", "[green]Above" if summary["above_ma20"] else "[red]Below")
    table.add_row("MA50", f"${summary['ma50']:.2f}", "[green]Above" if summary["above_ma50"] else "[red]Below")
    table.add_row("MA200", f"${summary['ma200']:.2f}", "[green]Above" if summary["above_ma200"] else "[red]Below")
    table.add_row("BB Upper", f"${summary['bb_upper']:.2f}", "")
    table.add_row("BB Lower", f"${summary['bb_lower']:.2f}", "")

    console.print(Panel(table, title="[bold]Technical Indicators[/bold]", border_style="green"))


def main():
    parser = argparse.ArgumentParser(description="Stock Analyzer — technical analysis CLI")
    parser.add_argument("symbol", help="Stock ticker symbol (e.g. AAPL, TSLA)")
    parser.add_argument("--period", default="1y", help="Data period: 1mo, 3mo, 6mo, 1y, 2y, 5y (default: 1y)")
    parser.add_argument("--chart", action="store_true", help="Show interactive chart")
    parser.add_argument("--save", metavar="FILE", help="Save chart to file (e.g. chart.png)")
    args = parser.parse_args()

    symbol = args.symbol.upper()
    console.print(f"\n[bold cyan]Fetching data for [yellow]{symbol}[/yellow]...[/bold cyan]")

    try:
        fetcher = StockFetcher(symbol)
        info = fetcher.get_info()
        df = fetcher.get_history(period=args.period)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    print_info(symbol, info)

    ind = TechnicalIndicators(df)
    ind.add_all()
    summary = ind.get_summary()
    print_indicators(summary)

    if args.chart or args.save:
        viz = StockVisualizer(ind.df, symbol)
        viz.plot(save_path=args.save)


if __name__ == "__main__":
    main()
