from pathlib import Path
import yfinance as yf

df = yf.download("BTC-USD", start="2023-10-05", end="2026-10-05", multi_level_index=False)
df.dropna().to_csv(Path(__file__).parent / "btc_usd_3y.csv")
