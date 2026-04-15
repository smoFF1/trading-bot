import asyncio

import pandas as pd
import yfinance as yf


def _format_value(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.{decimals}f}"


async def get_technical_context(symbol: str) -> str:
    history = await asyncio.to_thread(lambda: yf.Ticker(symbol).history(period="3mo"))

    if history.empty or "Close" not in history:
        return f"Technical data for {symbol} is unavailable."

    close = pd.to_numeric(history["Close"], errors="coerce").dropna()

    if close.empty:
        return f"Technical data for {symbol} is unavailable."

    current_price = float(close.iloc[-1])

    sma20_series = close.rolling(window=20, min_periods=20).mean()
    sma20 = sma20_series.iloc[-1] if not pd.isna(sma20_series.iloc[-1]) else None

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.rolling(window=14, min_periods=14).mean()
    avg_loss = losses.rolling(window=14, min_periods=14).mean()
    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))
    rsi = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else None

    if sma20 is None:
        price_position = f"Current price is ${current_price:.2f}. 20-day SMA is unavailable."
        trend = "neutral"
    elif current_price > sma20:
        price_position = f"Current price is ${current_price:.2f}, above the 20-day SMA of ${sma20:.2f}."
        trend = "bullish"
    elif current_price < sma20:
        price_position = f"Current price is ${current_price:.2f}, below the 20-day SMA of ${sma20:.2f}."
        trend = "bearish"
    else:
        price_position = f"Current price is ${current_price:.2f}, equal to the 20-day SMA of ${sma20:.2f}."
        trend = "neutral"

    if rsi is None:
        rsi_text = "RSI is unavailable"
    else:
        if rsi >= 70:
            rsi_state = "Overbought"
        elif rsi <= 30:
            rsi_state = "Oversold"
        else:
            rsi_state = "Neutral"
        rsi_text = f"RSI is {_format_value(rsi, 0)} ({rsi_state})"

    return f"{price_position} {rsi_text}. Trend is {trend}."