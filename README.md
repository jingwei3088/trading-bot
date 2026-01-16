# BTC Grid + Trend Hybrid Backtester

Lightweight backtesting framework that combines a trend-following indicator set (EMA/ATR) with a grid trading component for BTC. This repository contains data loading, indicator calculation, a simple backtest engine, and utilities for downloading sample price data.

## Repository layout

- `main.py` — entry point for running a backtest
- `config.py` — backtest, grid and indicator configuration
- `download_data.py` — utility to download BTC historical data (uses `yfinance`)
- `modules/` — core modules:
  - `data_feed.py` — load and normalize OHLCV CSV and compute indicators
  - `backtest_engine.py` — backtest logic and trade/equity exports
  - `hybrid_strategy.py` — strategy logic (grid + trend)
- `data/` — place OHLCV CSV files here (ignored by default)
- `results/` — output trade logs and equity curve

## Quickstart

1. Create a Python environment (recommended):

   zsh
   python -m venv .venv
   source .venv/bin/activate

2. Install dependencies:

   zsh
   pip install -r requirements.txt

If `requirements.txt` is not present, install core packages:

   pip install pandas numpy yfinance

3. Download sample data (1h or daily):

   python download_data.py

This will save `data/btc_1h.csv`. Alternatively, place your OHLCV CSV at `data/btc_1h.csv` with headers: `Date,Open,High,Low,Close,Volume`.

4. Run the backtest:

   python main.py

Outputs will be saved to `results/trades.csv` and `results/equity_curve.csv`.

## Notes

- The config in `config.py` points to `data/btc_1h.csv`. Ensure this file contains OHLCV price series (not trade logs).
- Large/raw data and results are ignored by default in `.gitignore`; use Git LFS for versioning large CSVs if needed.
- Do not commit API keys or secrets.

## Contributing

Fixes and improvements welcome. Open issues or submit pull requests with clear descriptions.